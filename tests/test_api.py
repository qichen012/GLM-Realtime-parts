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
from datetime import datetime

# --- 配置 ---
API_KEY = os.getenv("ZHIPU_API_KEY")
WS_URL = "wss://open.bigmodel.cn/api/paas/v4/realtime?model=GLM-Realtime"

SAMPLE_RATE = 16000
CHUNK = 1024

# 消息日志文件
LOG_FILE = f"datas/websocket_messages_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"

# --- 全局变量 ---
audio_queue = queue.Queue()
session_ready = threading.Event()
stop_event = threading.Event()
last_audio_time = time.time()
is_speaking = False

# 消息计数器
message_counter = {"total": 0, "by_type": {}}

def log_message(direction, msg_type, data):
    """记录所有WebSocket消息到文件"""
    global message_counter
    
    message_counter["total"] += 1
    message_counter["by_type"][msg_type] = message_counter["by_type"].get(msg_type, 0) + 1
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "direction": direction,  # "send" 或 "receive"
        "type": msg_type,
        "sequence": message_counter["total"],
        "data": data
    }
    
    # 写入文件
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

def generate_jwt_token(api_key: str, exp_seconds: int = 3600) -> str:
    """Generate JWT token for authentication."""
    try:
        api_key_id, api_key_secret = api_key.split('.')
    except ValueError:
        raise ValueError("API Key format is incorrect")
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
    """发送音频流"""
    global is_speaking, last_audio_time
    
    session_ready.wait()
    print("🎤 Session ready, starting to send audio stream")
    
    MAX_QPS = 45  
    MIN_INTERVAL = 1.0 / MAX_QPS
    BATCH_SIZE = 8
    SILENCE_THRESHOLD = 1.5
    
    audio_batch = []
    last_send_time = 0
    
    while not stop_event.is_set():
        try:
            chunk = audio_queue.get(timeout=0.05)
            audio_batch.append(chunk)
            
            if len(audio_batch) >= BATCH_SIZE:
                time_since_last_send = time.time() - last_send_time
                if time_since_last_send < MIN_INTERVAL:
                    time.sleep(MIN_INTERVAL - time_since_last_send)
                
                combined_audio = np.concatenate(audio_batch)
                audio_base64 = base64.b64encode(combined_audio.tobytes()).decode("utf-8")
                
                message = {
                    "type": "input_audio_buffer.append",
                    "audio": f"<{len(audio_base64)} bytes base64>"  # 不记录完整音频
                }
                log_message("send", "input_audio_buffer.append", message)
                
                ws.send(json.dumps({
                    "type": "input_audio_buffer.append",
                    "audio": audio_base64
                }))
                
                last_send_time = time.time()
                audio_batch.clear()
                
                for _ in range(BATCH_SIZE):
                    try:
                        audio_queue.task_done()
                    except:
                        pass

        except queue.Empty:
            if is_speaking and (time.time() - last_audio_time) > SILENCE_THRESHOLD:
                print("\n⏸️  Detected silence, committing audio...")
                
                if audio_batch:
                    time_since_last_send = time.time() - last_send_time
                    if time_since_last_send < MIN_INTERVAL:
                        time.sleep(MIN_INTERVAL - time_since_last_send)
                    
                    combined_audio = np.concatenate(audio_batch)
                    audio_base64 = base64.b64encode(combined_audio.tobytes()).decode("utf-8")
                    
                    message = {
                        "type": "input_audio_buffer.append",
                        "audio": f"<{len(audio_base64)} bytes base64>"
                    }
                    log_message("send", "input_audio_buffer.append", message)
                    
                    ws.send(json.dumps({
                        "type": "input_audio_buffer.append",
                        "audio": audio_base64
                    }))
                    audio_batch.clear()
                    last_send_time = time.time()
                
                time.sleep(MIN_INTERVAL)
                commit_msg = {"type": "input_audio_buffer.commit"}
                log_message("send", "input_audio_buffer.commit", commit_msg)
                ws.send(json.dumps(commit_msg))
                
                time.sleep(MIN_INTERVAL)
                response_request = {
                    "type": "response.create",
                    "response": {
                        "modalities": ["audio", "text"],
                        "instructions": "请用语音回复"
                    }
                }
                log_message("send", "response.create", response_request)
                print(f"📤 Requesting response with audio+text modalities")
                ws.send(json.dumps(response_request))
                
                is_speaking = False
                last_send_time = time.time()
            
            continue
        
        except Exception as e:
            print(f"\n❌ Send error: {e}")
            break
            
    print("🎤 Audio sending thread exited.")

def on_message(ws, message):
    """处理所有WebSocket消息并完整记录"""
    data = json.loads(message)
    msg_type = data.get("type")
    
    # 创建一个用于日志的数据副本
    log_data = data.copy()
    
    # 对于包含音频的消息，记录音频长度而不是完整内容
    if "audio" in log_data and log_data["audio"]:
        audio_len = len(log_data["audio"])
        log_data["audio"] = f"<{audio_len} chars base64>"
        log_data["_audio_present"] = True
        log_data["_audio_length"] = audio_len
    else:
        log_data["_audio_present"] = False
    
    # 检查嵌套的content中的audio
    if "item" in log_data and "content" in log_data["item"]:
        for i, content in enumerate(log_data["item"]["content"]):
            if "audio" in content and content["audio"]:
                audio_len = len(content["audio"])
                log_data["item"]["content"][i]["audio"] = f"<{audio_len} chars base64>"
                log_data["item"]["content"][i]["_audio_present"] = True
                log_data["item"]["content"][i]["_audio_length"] = audio_len
    
    # 记录到文件
    log_message("receive", msg_type, log_data)
    
    # 控制台输出
    if msg_type in ("session.created", "session.updated"):
        print(f"\n✅ [{msg_type}]")
        session_ready.set()
        
    elif msg_type == "conversation.item.input_audio_transcription.completed":
        user_text = data.get("transcript", "")
        if user_text:
            print(f"\n📝 [USER]: {user_text}")
        
    elif msg_type == "response.text.delta":
        text = data.get("text", "")
        if text:
            sys.stdout.write(text)
            sys.stdout.flush()
        
    elif msg_type == "response.text.done":
        sys.stdout.write("\n")
        sys.stdout.flush()
        
    elif msg_type == "response.audio.delta":
        audio_base64 = data.get("audio", "")
        if audio_base64:
            print(f"\n🎵 [audio.delta] Received {len(audio_base64)} chars audio", end="", flush=True)
        else:
            print(f"\n⚠️  [audio.delta] Empty audio field!", end="", flush=True)
            
    elif msg_type == "response.audio.done":
        print(f"\n✅ [audio.done] Audio stream complete")
            
    elif msg_type == "response.output_item.done":
        item = data.get("item", {})
        content_list = item.get("content", [])
        
        print(f"\n📦 [output_item.done] {len(content_list)} content item(s):")
        for i, content in enumerate(content_list):
            content_type = content.get("type")
            has_audio = "audio" in content and content["audio"]
            has_transcript = "transcript" in content and content["transcript"]
            
            print(f"   [{i}] type={content_type}, has_audio={has_audio}, has_transcript={has_transcript}")
            
            if has_transcript:
                print(f"       transcript: {content['transcript'][:100]}...")
    
    elif msg_type == "response.done":
        print("\n" + "="*60)
        print("🎉 Response complete")
        print("="*60)
        
    elif msg_type == "input_audio_buffer.speech_started":
        print("\n🎤 Speech detected by server VAD")
        
    elif msg_type == "input_audio_buffer.speech_stopped":
        print("⏸️  Speech ended by server VAD")
        
    elif msg_type in ("session.error", "error"):
        error_info = data.get('error', {})
        print(f"\n❌ Error: {error_info}")
        
    elif msg_type == "heartbeat":
        pass
        
    elif msg_type in ("rate_limits.updated", "conversation.created", "conversation.updated",
                      "input_audio_buffer.committed"):
        pass  # 静默处理
        
    else:
        print(f"\n💡 [{msg_type}]")

def on_open(ws):
    """WebSocket连接建立"""
    print("🔌 WebSocket connected")
    
    # 🔍 关键：测试不同的配置
    session_config = {
        "type": "session.update",
        "session": {
            "input_audio_format": "pcm16",
            "output_audio_format": "pcm16",
            "turn_detection": {"type": "server_vad"},
            "input_audio_transcription": {"enabled": True},
            "voice": "male-qingse",
            "modalities": ["audio", "text"],  # ⭐ 明确要求音频
            "beta_fields": {
                "chat_mode": "audio"  # ⭐ 可能需要这个
            }
        }
    }
    
    print(f"📤 Sending session config:")
    print(json.dumps(session_config, ensure_ascii=False, indent=2))
    
    log_message("send", "session.update", session_config)
    ws.send(json.dumps(session_config))
    
    time.sleep(0.5)
    threading.Thread(target=send_audio_loop, args=(ws,), daemon=True).start()

def on_close(ws, close_status_code, close_msg):
    """连接关闭"""
    if not stop_event.is_set():
         stop_event.set()
    print(f"\n🔌 Connection closed: {close_status_code}")
    
    # 打印统计
    print("\n" + "="*60)
    print("📊 Message Statistics:")
    print(f"   Total messages: {message_counter['total']}")
    print("   By type:")
    for msg_type, count in sorted(message_counter['by_type'].items()):
        print(f"      {msg_type}: {count}")
    print(f"\n💾 All messages logged to: {LOG_FILE}")
    print("="*60)

def on_error(ws, error):
    """WebSocket错误"""
    if not stop_event.is_set():
         stop_event.set()
    print(f"❌ WebSocket error: {error}", file=sys.stderr)

# --- Main ---
if __name__ == "__main__":
    if not API_KEY:
        print("❌ Please set ZHIPU_API_KEY environment variable")
        sys.exit(1)

    # 创建日志目录
    os.makedirs("datas", exist_ok=True)
    
    print("\n" + "="*60)
    print("🔍 GLM-Realtime DEBUG MODE - Full Message Logger")
    print("="*60)
    print(f"📁 Log file: {LOG_FILE}")
    print("="*60 + "\n")

    try:
        AUTH_TOKEN = generate_jwt_token(API_KEY)
    except Exception as e:
        print(f"❌ JWT generation failed: {e}")
        sys.exit(1)

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
        import traceback
        traceback.print_exc()
    finally:
        stop_event.set()
        if ws:
             threading.Thread(target=ws.close).start()
        sd.stop()
        print("\n👋 Exiting...")