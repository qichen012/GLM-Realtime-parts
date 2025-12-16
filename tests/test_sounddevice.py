import json
import base64
import websocket
import sounddevice as sd
import numpy as np
import threading
import queue
import time
import jwt, os
import sys

# --- 全局变量 ---
API_KEY = os.getenv("ZHIPU_API_KEY")
WS_URL = "wss://open.bigmodel.cn/api/paas/v4/realtime?model=GLM-Realtime"

SAMPLE_RATE = 16000
CHUNK = 1024
# --- [FIX] 计算每个音频块的持续时间 ---
# 1024 / 16000 = 0.064 秒 (即 64 毫秒)
CHUNK_DURATION = CHUNK / SAMPLE_RATE
# --- [END FIX] ---

audio_queue = queue.Queue()
session_ready = threading.Event()
stop_event = threading.Event() # 用于优雅退出

# --- 核心函数 ---

def generate_jwt_token(api_key: str, exp_seconds: int = 3600) -> str:
    """Generate JWT token for authentication."""
    try:
        api_key_id, api_key_secret = api_key.split('.')
    except ValueError:
        raise ValueError("API Key format is incorrect, should be 'API_KEY_ID.API_KEY_SECRET'")
    current_time = int(time.time())
    payload = {"api_key": api_key_id, "exp": current_time + exp_seconds, "timestamp": current_time}
    encoded_jwt = jwt.encode(payload, api_key_secret, algorithm="HS256",
                             headers={"alg": "HS256", "sign_type": "SIGN"})
    return encoded_jwt

def callback(indata, frames, time_info, status):
    """sounddevice input stream callback function."""
    if status:
        print("Microphone Warning:", status, file=sys.stderr)
    
    # --- [NEW CODE] Simple volume check for debugging ---
    # Calculate RMS volume level
    volume_norm = np.linalg.norm(indata) * 10 
    
    # Print a simple indicator if volume is detected
    if volume_norm > 0.5: # Threshold for basic sound presence
        # 使用 \r 实时更新音量
        print(f"🔊 Sound Detected (Level: {volume_norm:.1f})", end='\r', file=sys.stdout, flush=True)
    # --- [END NEW CODE] ---

    if not stop_event.is_set():
        audio_queue.put(indata.copy())

def send_audio_loop(ws):
    """
    Audio sending thread:
    1. Waits for session to be ready.
    2. Loops, takes audio data from queue and sends it.
    3. [FIX] Adds mandatory sleep to respect rate limits.
    """
    session_ready.wait()
    print("🎤 Session ready, starting to send audio stream (pcm16 raw int16)")
    last_send_time = time.time()
    commit_interval = 0.8  # Commit if idle for 0.8s

    while not stop_event.is_set():
        try:
            # 使用较短的超时 (0.01) 来快速响应 stop_event
            chunk = audio_queue.get(timeout=0.01)
            audio_base64 = base64.b64encode(chunk.tobytes()).decode("utf-8")
            
            ws.send(json.dumps({
                "type": "input_audio_buffer.append",
                "audio": audio_base64
            }))
            audio_queue.task_done()
            last_send_time = time.time()

            # --- [FIX] 强制等待音频块的持续时间 ---
            # 这是为了确保发送速率严格遵守 1/CHUNK_DURATION (约 15.6 QPS)
            # 从而避免 "rate_limit_error" (50 QPS 限制)
            time.sleep(CHUNK_DURATION)
            # --- [END FIX] ---

        except queue.Empty:
            # If idle for commit_interval, send commit
            if time.time() - last_send_time > commit_interval:
                try:
                    # Send final commit to ensure server processes the last segment
                    ws.send(json.dumps({"type": "input_audio_buffer.commit"}))
                    last_send_time = time.time()
                except (websocket.WebSocketConnectionClosedException, ConnectionResetError):
                    # Connection likely closed by main thread, exit gracefully
                    break
                except Exception as e:
                    print(f"Failed to send commit: {e}")
                    break
            continue
        
        except (websocket.WebSocketConnectionClosedException, ConnectionResetError, Exception):
            # Capture send exceptions (like connection closed), exit thread
            break
            
    print("🎤 Audio sending thread exited.")


def on_message(ws, message):
    """Handles incoming WebSocket messages."""
    data = json.loads(message)
    msg_type = data.get("type")
    
    if msg_type in ("session.created", "session.updated"):
        print("Session Info:", data.get("session", {}).get("id"))
        session_ready.set() # Crucial: Set session ready event
    elif msg_type == "transcript":
        # === Key Change: Print transcription result ===
        # 这个消息的出现证明服务器成功识别了您的语音！
        print(f"\n📝 Transcription Result: {data.get('text')}")
        # ============================================
    elif msg_type == "response.text.delta":
        # Print real-time reply text
        sys.stdout.write(data.get("text", ""))
        sys.stdout.flush()
    elif msg_type == "response.text.done":
        # Ensure newline after text stream ends
        sys.stdout.write("\n")
        sys.stdout.flush()
        print("✅ Text reply stream ended (may be empty).")
    elif msg_type == "response.audio.delta":
        try:
            audio_base64 = data.get("audio", "")
            if not audio_base64:
                return
                
            audio_bytes = base64.b64decode(audio_base64)
            audio_np = np.frombuffer(audio_bytes, dtype=np.int16)
            sd.play(audio_np, samplerate=SAMPLE_RATE)
            
        except sd.PortAudioError as pa_err:
            print(f"\n❌❌❌ PortAudio Audio Playback Error (This is likely why you hear no sound): {pa_err} ❌❌❌\n")
            if not stop_event.is_set():
                stop_event.set()
                threading.Thread(target=ws.close).start()
        except Exception as e:
            print(f"❌ Failed to play audio: {e}")
            
    elif msg_type == "response.audio.done":
        try:
            # Wait for all buffered audio to finish playing
            sd.wait()
            print("🔊 Entire reply audio playback finished.")
        except sd.PortAudioError as pa_err:
            print(f"\n❌❌❌ PortAudio Error during sd.wait(): {pa_err} ❌❌❌\n")
    elif msg_type == "response.done":
        print("🎉 Entire reply complete.")
    elif msg_type in ("conversation.updated", "conversation.created"):
        print(f"🔹 Conversation Update: {msg_type}")
    elif msg_type in ("session.error", "error"):
        print("❌ Server Error:", data)
    elif msg_type == "session.end":
        print("🎉 Session ended")
        if not stop_event.is_set():
             stop_event.set()
             threading.Thread(target=ws.close).start()
    elif msg_type == "heartbeat":
        pass
    # Handle other key messages starting with known prefixes
    elif msg_type.startswith(("response.", "input_audio_buffer.", "conversation.")):
        print(f"📡 Received service message: {msg_type}")
    else:
        print("💡 Unhandled message:", msg_type)


def on_open(ws):
    """Called when WebSocket connection is established."""
    print("🔌 WebSocket connected, sending session.update ...")
    ws.send(json.dumps({
        "type": "session.update",
        "session": {
            "input_audio_format": "pcm16",
            "output_audio_format": "pcm16",
            "turn_detection": {"type": "server_vad"},
            "voice": "male-qingse",
            "beta_fields": {"chat_mode": "audio", "tts_source": "e2e"}
        }
    }))
    time.sleep(1)
    threading.Thread(target=send_audio_loop, args=(ws,), daemon=True).start()

def on_close(ws, close_status_code, close_msg):
    """Called when WebSocket connection closes."""
    if not stop_event.is_set():
         stop_event.set()
    print(f"🔌 Connection closed: code={close_status_code}, msg={close_msg}")

def on_error(ws, error):
    """Called on WebSocket error."""
    if not stop_event.is_set():
         stop_event.set()
    print("❌ WebSocket error:", error, file=sys.stderr)

# --- Main Program Logic ---

if __name__ == "__main__":
    if not API_KEY:
        print("Please set the ZHIPU_API_KEY environment variable first")
        sys.exit(1)

    try:
        AUTH_TOKEN = generate_jwt_token(API_KEY)
        print("✅ JWT generated successfully")
    except Exception as e:
        print("❌ JWT generation failed:", e)
        sys.exit(1)

    print("--- Speak into the microphone ---")
    websocket.enableTrace(False)
    
    ws = websocket.WebSocketApp(
        WS_URL,
        header=[f"Authorization: Bearer {AUTH_TOKEN}"],
        on_message=on_message,
        on_open=on_open,
        on_close=on_close,
        on_error=on_error
    )
    
    # 1. Start WebSocket connection in a separate thread
    ws_thread = threading.Thread(target=ws.run_forever, daemon=True)
    ws_thread.start()

    try:
        # 2. Start audio input stream
        print("⏳ Waiting for WebSocket connection and session readiness...")
        session_ready.wait(timeout=10) # Wait for session to be ready before mic starts

        if not session_ready.is_set():
            print("❌ Error: WebSocket session was not ready within 10 seconds.")
            sys.exit(1)

        print("🎤 Session ready, start speaking...")
        with sd.InputStream(channels=1, samplerate=SAMPLE_RATE, dtype='int16', callback=callback):
            ws_thread.join() # Wait for the WebSocket thread to finish

    except KeyboardInterrupt:
        print("\nUser interrupted (Ctrl+C)")
    except Exception as e:
        print(f"Runtime error: {e}")
    finally:
        # Signal stop and clean up
        stop_event.set()
        if ws:
             threading.Thread(target=ws.close).start()
        sd.stop()
        print("Exiting.")