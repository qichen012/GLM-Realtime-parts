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
CHUNK_DURATION = CHUNK / SAMPLE_RATE  # 0.064 秒

audio_queue = queue.Queue()
session_ready = threading.Event()
stop_event = threading.Event()

# 状态追踪
last_audio_time = time.time()
is_speaking = False

# 音频播放缓冲
audio_playback_buffer = []
playback_lock = threading.Lock()

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
    global last_audio_time, is_speaking
    
    if status:
        print("Microphone Warning:", status, file=sys.stderr)
    
    volume_norm = np.linalg.norm(indata) * 10 
    
    if volume_norm > 0.5:
        print(f"🔊 Sound Detected (Level: {volume_norm:.1f})", end='\r', file=sys.stdout, flush=True)
        last_audio_time = time.time()
        is_speaking = True

    if not stop_event.is_set():
        audio_queue.put(indata.copy())

def send_audio_loop(ws):
    """
    优化版音频发送：
    1. 使用速率限制器，确保不超过 50 QPS
    2. 批量累积音频，减少请求次数
    3. 智能检测静音并触发响应
    """
    global is_speaking, last_audio_time
    
    session_ready.wait()
    print("🎤 Session ready, starting to send audio stream")
    
    # 速率限制配置
    MAX_QPS = 45  # 保守一点，使用45而不是50
    MIN_INTERVAL = 1.0 / MAX_QPS  # 每次请求最小间隔 ≈ 0.022秒
    
    # 批量发送配置
    BATCH_SIZE = 8  # 每次累积8个chunk (8 * 64ms = 512ms 音频)
    SILENCE_THRESHOLD = 1.5  # 静音1.5秒触发响应
    
    audio_batch = []
    last_send_time = 0
    
    while not stop_event.is_set():
        try:
            chunk = audio_queue.get(timeout=0.05)
            audio_batch.append(chunk)
            
            # 当累积到足够的音频 且 满足速率限制
            if len(audio_batch) >= BATCH_SIZE:
                # 确保满足最小间隔
                time_since_last_send = time.time() - last_send_time
                if time_since_last_send < MIN_INTERVAL:
                    time.sleep(MIN_INTERVAL - time_since_last_send)
                
                # 发送批量音频
                combined_audio = np.concatenate(audio_batch)
                audio_base64 = base64.b64encode(combined_audio.tobytes()).decode("utf-8")
                
                ws.send(json.dumps({
                    "type": "input_audio_buffer.append",
                    "audio": audio_base64
                }))
                
                last_send_time = time.time()
                audio_batch.clear()
                
                # 清空队列中的已处理任务
                for _ in range(BATCH_SIZE):
                    try:
                        audio_queue.task_done()
                    except:
                        pass

        except queue.Empty:
            # 检测静音并触发响应
            if is_speaking and (time.time() - last_audio_time) > SILENCE_THRESHOLD:
                print("\n⏸️  Detected silence, committing audio and requesting response...")
                
                # 发送剩余的音频
                if audio_batch:
                    # 满足速率限制
                    time_since_last_send = time.time() - last_send_time
                    if time_since_last_send < MIN_INTERVAL:
                        time.sleep(MIN_INTERVAL - time_since_last_send)
                    
                    combined_audio = np.concatenate(audio_batch)
                    audio_base64 = base64.b64encode(combined_audio.tobytes()).decode("utf-8")
                    ws.send(json.dumps({
                        "type": "input_audio_buffer.append",
                        "audio": audio_base64
                    }))
                    audio_batch.clear()
                    last_send_time = time.time()
                
                # 短暂等待，然后commit
                time.sleep(MIN_INTERVAL)
                ws.send(json.dumps({"type": "input_audio_buffer.commit"}))
                
                # 再等待一下，然后请求响应
                time.sleep(MIN_INTERVAL)
                response_request = {
                    "type": "response.create",
                    "response": {
                        "modalities": ["audio", "text"],
                        "instructions": "请用语音回复"
                    }
                }
                print(f"📤 Sending response request: {json.dumps(response_request, ensure_ascii=False)}")
                ws.send(json.dumps(response_request))
                
                is_speaking = False
                last_send_time = time.time()
                print("📤 Response creation requested")
            
            continue
        
        except Exception as e:
            print(f"\n❌ Send error: {e}")
            break
            
    print("🎤 Audio sending thread exited.")


def on_message(ws, message):
    """Handles incoming WebSocket messages."""
    data = json.loads(message)
    msg_type = data.get("type")
    
    # 只在关键消息时打印详细信息
    if msg_type in ("session.created", "session.updated", "error", "session.error"):
        print(f"\n📡 [{msg_type}] {json.dumps(data, ensure_ascii=False, indent=2)}")
    
    if msg_type in ("session.created", "session.updated"):
        print("✅ Session Info:", data.get("session", {}).get("id"))
        session_ready.set()
        
    elif msg_type == "transcript":
        transcript_text = data.get('text', '')
        if transcript_text:
            print(f"\n📝 Transcription: {transcript_text}")
        
    elif msg_type == "response.text.delta":
        text = data.get("text", "")
        if text:
            sys.stdout.write(text)
            sys.stdout.flush()
        
    elif msg_type == "response.text.done":
        sys.stdout.write("\n")
        sys.stdout.flush()
        
    elif msg_type == "response.audio.delta":
        try:
            audio_base64 = data.get("audio", "")
            if not audio_base64:
                print(f"\n⚠️  Received audio.delta with empty audio field!")
                return
                
            audio_bytes = base64.b64decode(audio_base64)
            audio_np = np.frombuffer(audio_bytes, dtype=np.int16)
            
            # 调试信息
            print(f"\n🔊 Audio chunk: {len(audio_bytes)} bytes, {len(audio_np)} samples", end="", flush=True)
            
            # 累积音频到缓冲区
            with playback_lock:
                audio_playback_buffer.append(audio_np)
            
        except Exception as e:
            print(f"\n❌ Audio processing error: {e}")
            import traceback
            traceback.print_exc()
            
    elif msg_type == "response.audio.done":
        try:
            print(f"\n\n🎵 Audio stream complete, preparing playback...")
            
            with playback_lock:
                if audio_playback_buffer:
                    print(f"   Buffered chunks: {len(audio_playback_buffer)}")
                    
                    # 合并所有音频块
                    full_audio = np.concatenate(audio_playback_buffer)
                    print(f"   Total samples: {len(full_audio)}, duration: {len(full_audio)/SAMPLE_RATE:.2f}s")
                    print(f"   Audio range: [{full_audio.min()}, {full_audio.max()}]")
                    
                    # 增加音量（如果太小）
                    max_val = np.abs(full_audio).max()
                    if max_val > 0:
                        if max_val < 10000:
                            volume_boost = 10000 / max_val
                            full_audio = (full_audio * volume_boost).astype(np.int16)
                            print(f"   🔊 Volume boosted by {volume_boost:.2f}x")
                        
                        # 播放音频
                        print(f"   ▶️  Playing audio now...")
                        sd.play(full_audio, samplerate=SAMPLE_RATE, blocking=True)
                        print("   ✅ Playback complete!")
                    else:
                        print("   ⚠️  Audio data is silent (all zeros)")
                    
                    audio_playback_buffer.clear()
                else:
                    print("   ⚠️  No audio chunks were buffered!")
                    
        except Exception as e:
            print(f"\n❌ Error during playback: {e}")
            import traceback
            traceback.print_exc()
            
    elif msg_type == "response.output_item.done":
        # ⭐ 关键发现：智谱 API 把音频放在这里！
        try:
            item = data.get("item", {})
            content_list = item.get("content", [])
            
            for content in content_list:
                if content.get("type") == "audio":
                    audio_base64 = content.get("audio", "")
                    
                    if audio_base64:
                        print(f"\n🎵 Found audio in output_item.done!")
                        
                        # 解码音频
                        audio_bytes = base64.b64decode(audio_base64)
                        full_audio = np.frombuffer(audio_bytes, dtype=np.int16)
                        
                        print(f"   Total samples: {len(full_audio)}, duration: {len(full_audio)/SAMPLE_RATE:.2f}s")
                        print(f"   Audio range: [{full_audio.min()}, {full_audio.max()}]")
                        
                        # 增加音量（如果太小）
                        max_val = np.abs(full_audio).max()
                        if max_val > 0:
                            if max_val < 10000:
                                volume_boost = 10000 / max_val
                                full_audio = (full_audio * volume_boost).astype(np.int16)
                                print(f"   🔊 Volume boosted by {volume_boost:.2f}x")
                            
                            # 播放音频
                            print(f"   ▶️  Playing audio now...")
                            sd.play(full_audio, samplerate=SAMPLE_RATE, blocking=True)
                            print("   ✅ Playback complete!")
                        else:
                            print("   ⚠️  Audio data is silent")
                    
                    # 显示转写文本
                    transcript = content.get("transcript", "")
                    if transcript:
                        print(f"\n📝 Transcript: {transcript}")
                        
        except Exception as e:
            print(f"\n❌ Error processing output_item: {e}")
            import traceback
            traceback.print_exc()
    
    elif msg_type == "response.done":
        print("🎉 Response complete\n" + "="*40)
        
    elif msg_type == "input_audio_buffer.committed":
        print("✅ Audio buffer committed")
        
    elif msg_type == "input_audio_buffer.speech_started":
        print("\n🎤 Speech detected by server VAD")
        
    elif msg_type == "input_audio_buffer.speech_stopped":
        print("⏸️  Speech ended (detected by server VAD)")
        
    elif msg_type in ("session.error", "error"):
        error_info = data.get('error', {})
        error_code = error_info.get('code', '')
        
        # 只显示非速率限制的错误，速率限制错误太多会刷屏
        if error_code != 'rate_limit_error':
            print(f"❌ Error: {error_info.get('message', data)}")
        
    elif msg_type == "heartbeat":
        pass
        
    elif msg_type in ("rate_limits.updated", "conversation.created", "conversation.updated"):
        # 静默处理这些常见消息
        pass
        
    else:
        # 只打印真正未知的消息类型
        if not msg_type.startswith(("response.", "input_audio_buffer.")):
            print(f"💡 Message: {msg_type}")


def on_open(ws):
    """Called when WebSocket connection is established."""
    print("🔌 WebSocket connected, configuring session...")
    session_config = {
        "type": "session.update",
        "session": {
            "input_audio_format": "pcm16",
            "output_audio_format": "pcm16",
            "turn_detection": {"type": "server_vad"},
            "voice": "male-qingse",
            "modalities": ["audio", "text"],  # 明确指定要音频和文本
            "beta_fields": {
                "chat_mode": "audio",
                "tts_source": "e2e"
            }
        }
    }
    print(f"📤 Session config: {json.dumps(session_config, ensure_ascii=False, indent=2)}")
    ws.send(json.dumps(session_config))
    time.sleep(0.5)
    threading.Thread(target=send_audio_loop, args=(ws,), daemon=True).start()

def on_close(ws, close_status_code, close_msg):
    """Called when WebSocket connection closes."""
    if not stop_event.is_set():
         stop_event.set()
    print(f"\n🔌 Connection closed: code={close_status_code}, msg={close_msg}")

def on_error(ws, error):
    """Called on WebSocket error."""
    if not stop_event.is_set():
         stop_event.set()
    print(f"❌ WebSocket error: {error}", file=sys.stderr)

# --- Main Program Logic ---

if __name__ == "__main__":
    if not API_KEY:
        print("❌ Please set the ZHIPU_API_KEY environment variable first")
        sys.exit(1)

    # 先检查音频设备
    print("\n" + "="*50)
    print("🔊 Audio Device Check")
    print("="*50)
    try:
        devices = sd.query_devices()
        print(f"Default input device: {sd.query_devices(kind='input')['name']}")
        print(f"Default output device: {sd.query_devices(kind='output')['name']}")
        
        # 测试音频播放
        print("\n🧪 Testing audio playback...")
        test_tone = (np.sin(2 * np.pi * 440 * np.arange(SAMPLE_RATE) / SAMPLE_RATE) * 5000).astype(np.int16)
        sd.play(test_tone, samplerate=SAMPLE_RATE, blocking=True)
        print("✅ If you heard a beep, audio output is working!")
        time.sleep(0.5)
    except Exception as e:
        print(f"⚠️  Audio device warning: {e}")
    print("="*50 + "\n")

    try:
        AUTH_TOKEN = generate_jwt_token(API_KEY)
        print("✅ JWT generated successfully")
    except Exception as e:
        print(f"❌ JWT generation failed: {e}")
        sys.exit(1)

    print("\n" + "="*50)
    print("    GLM-Realtime Voice Chat")
    print("="*50)
    print("💡 Usage:")
    print("   1. Speak into the microphone")
    print("   2. Pause for 1.5 seconds to get response")
    print("   3. Press Ctrl+C to exit")
    print("="*50 + "\n")
    
    websocket.enableTrace(False)
    
    ws = websocket.WebSocketApp(
        WS_URL,
        header=[f"Authorization: Bearer {AUTH_TOKEN}"],
        on_message=on_message,
        on_open=on_open,
        on_close=on_close,
        on_error=on_error
    )
    
    ws_thread = threading.Thread(target=ws.run_forever, daemon=True)
    ws_thread.start()

    try:
        print("⏳ Waiting for connection...")
        session_ready.wait(timeout=10)

        if not session_ready.is_set():
            print("❌ Session setup timeout")
            sys.exit(1)

        print("🎤 Ready! Start speaking...\n")
        
        with sd.InputStream(channels=1, samplerate=SAMPLE_RATE, dtype='int16', callback=callback):
            ws_thread.join()

    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user")
    except Exception as e:
        print(f"\n❌ Runtime error: {e}")
    finally:
        stop_event.set()
        if ws:
             threading.Thread(target=ws.close).start()
        sd.stop()
        print("Exiting.")