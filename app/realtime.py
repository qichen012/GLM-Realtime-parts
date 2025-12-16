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
import pyttsx3
import wave
from io import BytesIO
from memory.data_logger import DialogueLogger
from memory.realtime_sync import create_sync_worker  # 🔑 方案3：实时同步
from dotenv import load_dotenv
from pynput import keyboard  # 用于键盘监听
from .audio_processing import SimpleMyVoiceProcessor

# Load environment variables from .env file
load_dotenv('/Users/xwj/Desktop/gpt-realtime-demo/.env')

# --- 全局变量区域新增 ---
tts_queue = queue.Queue() #创建一个专门放文字的队列

# --- 新增：专门的 TTS 工作线程函数 ---
def tts_worker_thread():
    """
    后台线程：专门负责从队列里取文字并朗读
    这样做不会卡住 WebSocket 的接收线程
    """
    # 在线程内部初始化引擎，确保线程安全
    engine = pyttsx3.init()
    engine.setProperty('rate', 180)
    engine.setProperty('volume', 5.0) # 注意：pyttsx3 音量通常是 0.0-1.0
    
    print("🔊 Local TTS Worker Started")
    
    while not stop_event.is_set():
        try:
            # 等待队列中有文字，超时1秒以便检查 stop_event
            text = tts_queue.get(timeout=1.0)
            
            if text:
                print(f"🗣️  Local TTS Speaking: {text[:20]}...")
                engine.say(text)
                engine.runAndWait() # 这里阻塞只影响这个子线程，不影响主程序
                
            tts_queue.task_done()
            
        except queue.Empty:
            continue
        except Exception as e:
            print(f"❌ TTS Error: {e}")

# 可选：设置声音类型（根据平台不同有所变化）
# voices = tts_engine.getProperty('voices')
# tts_engine.setProperty('voice', voices[0].id)

def speak_local_tts(text: str):
    """非阻塞：将文字放入队列，由后台线程播放"""
    if text and text.strip():
        tts_queue.put(text)

# --- 全局变量 ---
API_KEY = os.getenv("ZHIPU_API_KEY")
WS_URL = "wss://open.bigmodel.cn/api/paas/v4/realtime?model=GLM-Realtime"
logger = DialogueLogger(filename="data/save_data.jsonl")

# 🔑 方案3：实时同步工作器
CURRENT_USER_ID = os.getenv("USER_ID", "3f6c7b1a-9d2e-4f8a-b5c3-e1f2a3b4c5d6")
sync_worker = None  # 延迟初始化，避免启动时连接失败影响主流程

SAMPLE_RATE = 16000
CHUNK = 1024
CHUNK_DURATION = CHUNK / SAMPLE_RATE  # 0.064 秒

# 本地语音处理器（VAD + 预留降噪）
voice_processor = SimpleMyVoiceProcessor(sample_rate=SAMPLE_RATE)

audio_queue = queue.Queue()
session_ready = threading.Event()
stop_event = threading.Event()

# 状态追踪
last_audio_time = time.time()
is_speaking = False

# 音频播放缓冲
audio_playback_buffer = []
playback_lock = threading.Lock()
audio_played_in_response = False  # 标记当前响应是否已播放音频

# 🔑 AI 回复状态（用于打断功能）
ai_is_responding = False
ai_response_lock = threading.Lock()
ws_global = None  # 全局 WebSocket 对象，用于打断功能

# --- 打断功能相关函数 ---

def interrupt_ai_response():
    """打断 AI 的回复"""
    global ai_is_responding, audio_playback_buffer
    
    with ai_response_lock:
        if not ai_is_responding:
            print("💡 AI 当前未在回复，无需打断")
            return
        
        print("\n" + "="*50)
        print("⚡ 检测到打断信号！正在停止 AI 回复...")
        print("="*50)
        
        try:
            # 1. 标记停止
            ai_is_responding = False
            
            # 2. 清空音频播放缓冲
            with playback_lock:
                audio_playback_buffer.clear()
                print("   ✓ 清空音频缓冲")
            
            # 3. 清空 TTS 队列
            while not tts_queue.empty():
                try:
                    tts_queue.get_nowait()
                except queue.Empty:
                    break
            print("   ✓ 清空 TTS 队列")
            
            # 4. 发送取消响应消息给 GLM
            if ws_global:
                try:
                    ws_global.send(json.dumps({"type": "response.cancel"}))
                    print("   ✓ 已发送取消响应命令")
                    
                    # 清空输入音频缓冲
                    time.sleep(0.1)
                    ws_global.send(json.dumps({"type": "input_audio_buffer.clear"}))
                    print("   ✓ 已清空输入音频缓冲")
                except Exception as e:
                    print(f"   ⚠️ 发送取消命令失败: {e}")
            
            print("✅ AI 已停止，您可以继续说话...")
            print("="*50 + "\n")
            
        except Exception as e:
            print(f"❌ 打断处理出错: {e}")


def keyboard_listener_thread():
    """键盘监听线程 - 监听 Enter 键以打断 AI"""
    
    def on_press(key):
        try:
            # 检测 Enter 键
            if key == keyboard.Key.enter:
                if ai_is_responding:
                    interrupt_ai_response()
        except AttributeError:
            pass
    
    print("⌨️  键盘监听已启动 (按 Enter 可打断 AI 回复)")
    
    # 启动监听器
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()


# --- 核心函数 ---

def pcm_to_wav_base64(pcm_data: np.ndarray, sample_rate: int = 16000) -> str:
    """
    将 PCM 音频数据包装成 WAV 格式并转为 base64
    Args:
        pcm_data: int16 格式的 numpy 数组
        sample_rate: 采样率
    Returns:
        base64 编码的 WAV 数据
    """
    wav_io = BytesIO()
    with wave.open(wav_io, "wb") as wav_out:
        wav_out.setnchannels(1)  # 单声道
        wav_out.setsampwidth(2)  # 16bit = 2 bytes
        wav_out.setframerate(sample_rate)
        wav_out.writeframes(pcm_data.tobytes())
    
    wav_io.seek(0)
    return base64.b64encode(wav_io.getvalue()).decode("utf-8")

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

    # 如果已经在停止流程中，直接返回
    if stop_event.is_set():
        return

    # 先经过本地语音处理器（VAD + 预留降噪）
    processed = voice_processor.process(indata)
    if processed is not None:
        audio_queue.put(processed.copy())

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
    MAX_QPS = 45  
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
                
                # 发送批量音频（包装成 WAV 格式）
                combined_audio = np.concatenate(audio_batch)
                audio_base64 = pcm_to_wav_base64(combined_audio, SAMPLE_RATE)
                
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
                
                # 发送剩余的音频（包装成 WAV 格式）
                if audio_batch:
                    # 满足速率限制
                    time_since_last_send = time.time() - last_send_time
                    if time_since_last_send < MIN_INTERVAL:
                        time.sleep(MIN_INTERVAL - time_since_last_send)
                    
                    combined_audio = np.concatenate(audio_batch)
                    audio_base64 = pcm_to_wav_base64(combined_audio, SAMPLE_RATE)
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
    global audio_played_in_response, ai_is_responding, sync_worker  # 声明全局变量
    
    data = json.loads(message)
    msg_type = data.get("type")
    
    # 只在关键消息时打印详细信息
    if msg_type in ("session.created", "session.updated", "error", "session.error"):
        print(f"\n📡 [{msg_type}] {json.dumps(data, ensure_ascii=False, indent=2)}")
    
    if msg_type in ("session.created", "session.updated"):
        print("✅ Session Info:", data.get("session", {}).get("id"))
        session_ready.set()
        
    elif msg_type == "conversation.item.input_audio_transcription.completed":
        # 这就是你的语音转文本！
        user_text = data.get("transcript", "")
        if user_text:
            # 为了区分，我们给它一个特殊的打印前缀
            print(f"\n📝 [USER_TEXT]: {user_text}")
            logger.log_user_input(user_text)
        
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
            # 🔑 标记 AI 开始回复（第一次接收音频时）
            if not ai_is_responding:
                with ai_response_lock:
                    ai_is_responding = True
                    print("\n🔊 [AI 回复中] 按 Enter 可打断")
            
            audio_base64 = data.get("delta", "")  # 🔑 修复：字段名是 "delta" 不是 "audio"
            if not audio_base64:
                print(f"\n⚠️  Received audio.delta with empty delta field!")
                return
                
            audio_bytes = base64.b64decode(audio_base64)
            audio_np = np.frombuffer(audio_bytes, dtype=np.int16)
            
            # 调试信息
            print(f"🔊 Audio chunk: {len(audio_bytes)} bytes", end='\r', flush=True)
            
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
                    original_duration = len(full_audio)/SAMPLE_RATE
                    print(f"   Total samples: {len(full_audio)}, original duration: {original_duration:.2f}s")
                    
                    # 增加音量（如果太小）
                    max_val = np.abs(full_audio).max()
                    if max_val > 0:
                        if max_val < 10000:
                            volume_boost = 10000 / max_val
                            full_audio = (full_audio * volume_boost).astype(np.int16)
                            print(f"   🔊 Volume boosted by {volume_boost:.2f}x")
                        
                        # 🚀 加速播放
                        SPEED_MULTIPLIER = 1.5  # 调整播放速度（推荐 1.3-1.8）
                        playback_rate = int(SAMPLE_RATE * SPEED_MULTIPLIER)
                        adjusted_duration = len(full_audio) / playback_rate
                        
                        print(f"   ⚡ Speed: {SPEED_MULTIPLIER}x, playback duration: {adjusted_duration:.2f}s")
                        print(f"   ▶️  Playing...")
                        sd.play(full_audio, samplerate=playback_rate, blocking=True)
                        print("   ✅ Playback complete!")
                        
                        # 🔑 标记已播放音频，不需要本地TTS了
                        audio_played_in_response = True
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
        # ⭐ 这个事件可能包含音频数据（但通常音频已经通过 audio.done 播放了）
        try:
            item = data.get("item", {})
            content_list = item.get("content", [])
            
            for i, content in enumerate(content_list):
                content_type = content.get("type")
                
                if content_type == "audio":
                    transcript = content.get("transcript", "")
                    
                    # 记录转写文本
                    if transcript:
                        logger.log_assistant_delta(transcript)
                        print(f"\n📝 AI: {transcript}")
                    
                    # 🔑 关键：只在没有通过 audio.done 播放音频时才使用本地 TTS
                    if not audio_played_in_response and transcript:
                        print(f"\n⚠️  No audio received, using local TTS fallback")
                        speak_local_tts(transcript)
                        
        except Exception as e:
            print(f"\n❌ Error processing output_item: {e}")
            import traceback
            traceback.print_exc()
    
    elif msg_type == "response.done":
        # 🔑 标记 AI 回复结束
        with ai_response_lock:
            ai_is_responding = False
        
        print("🎉 Response complete")
        print("🎤 [正在听...] 您可以说话了\n" + "="*40)
        
        # 🔑 方案3：实时同步到 Memobase
        dialogue_data = logger.finalize_turn()
        
        if dialogue_data and sync_worker:
            # 尝试实时同步（异步，不阻塞）
            try:
                success = sync_worker.enqueue(dialogue_data)
                if success:
                    print("📤 [实时同步] 已加入同步队列")
                else:
                    print("⚠️  [实时同步] 加入队列失败，将由定时任务处理")
            except Exception as e:
                print(f"⚠️  [实时同步] 出错: {e}，将由定时任务处理")
        elif dialogue_data and not sync_worker:
            print("💡 [实时同步] 工作器未就绪，将由定时任务处理")
        
        # 🔄 重置音频播放标志，为下一轮对话做准备
        audio_played_in_response = False
        
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
# <--- 修改点：打印所有我们未知的消息的 完整内容！ --->
        if not msg_type.startswith(("response.", "input_audio_buffer.")):
            print(f"💡 Message: {msg_type}")


def on_open(ws):
    """Called when WebSocket connection is established."""
    print("🔌 WebSocket connected, configuring session...")
    session_config = {
        "type": "session.update",
        "session": {
            "input_audio_format": "wav",
            "output_audio_format": "pcm",
            "turn_detection": {
                "type": "server_vad",
                "threshold": 0.5,              # 音量阈值 (0.0-1.0)
                "prefix_padding_ms": 300,      # 说话前缓冲 (毫秒)
                "silence_duration_ms": 2000    # 🔑 静默2秒才判定说完 (毫秒)
            },
            "input_audio_transcription": {
                "enabled": True
            },
            "temperature": 0.8,  # 自然度
            "modalities": ["audio", "text"],
            "beta_fields": {
               "chat_mode": "audio",
               "tts_source": "e2e",  # 端到端语音合成
               "auto_search": False
               # 注意：speed 参数不生效，使用客户端播放加速
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

    # 🔑 方案3：初始化实时同步工作器
    # 注意：这里不需要 global 声明，因为 if __name__ == "__main__" 本身就在模块级别
    print("🔧 初始化 Memobase 实时同步...")
    try:
        sync_worker = create_sync_worker(CURRENT_USER_ID)
        print("✅ 实时同步工作器已启动")
    except Exception as e:
        print(f"⚠️  实时同步工作器初始化失败: {e}")
        print("💡 将使用定时任务作为后备同步方式")
        sync_worker = None

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
    print("   2. Pause for 2 seconds to get response")
    print("   3. Press Enter to interrupt AI")
    print("   4. Press Ctrl+C to exit")
    print("="*50 + "\n")
    
    threading.Thread(target=tts_worker_thread, daemon=True).start()
    
    # 🔑 启动键盘监听线程（用于打断功能）
    threading.Thread(target=keyboard_listener_thread, daemon=True).start()

    websocket.enableTrace(False)
    
    ws = websocket.WebSocketApp(
        WS_URL,
        header=[f"Authorization: Bearer {AUTH_TOKEN}"],
        on_message=on_message,
        on_open=on_open,
        on_close=on_close,
        on_error=on_error
    )
    
    # 🔑 设置全局 WebSocket 对象（用于打断功能）
    ws_global = ws  # 直接赋值，不需要 global 声明
    
    ws_thread = threading.Thread(target=ws.run_forever, daemon=True)
    ws_thread.start()

    try:
        print("⏳ Waiting for connection...")
        session_ready.wait(timeout=10)

        if not session_ready.is_set():
            print("❌ Session setup timeout")
            sys.exit(1)

        print("🎤 [正在听...] Ready! Start speaking...")
        print("💡 提示: AI 回复时按 Enter 键可打断并继续说话\n")
        
        with sd.InputStream(channels=1, samplerate=SAMPLE_RATE, dtype='int16', callback=callback):
            ws_thread.join()

    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user")
    except Exception as e:
        print(f"\n❌ Runtime error: {e}")
    finally:
        print("\n🛑 正在清理资源...")
        stop_event.set()
        
        # 🔑 方案3：停止同步工作器
        if sync_worker:
            print("⏳ 等待同步队列清空...")
            sync_worker.stop(timeout=5)
        
        if ws:
             threading.Thread(target=ws.close).start()
        sd.stop()
        print("✅ 已退出")