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
from memory.realtime_sync import create_sync_worker
from dotenv import load_dotenv
from pynput import keyboard
from .audio_processing import SimpleMyVoiceProcessor

# Load environment variables
load_dotenv('/Users/xwj/Desktop/gpt-realtime-demo/.env')

# --- 全局变量 ---
tts_queue = queue.Queue()

def tts_worker_thread():
    """后台 TTS 工作线程"""
    engine = pyttsx3.init()
    engine.setProperty('rate', 180)
    engine.setProperty('volume', 0.9)
    
    print("🔊 Local TTS Worker Started")
    
    while not stop_event.is_set():
        try:
            text = tts_queue.get(timeout=1.0)
            if text:
                print(f"🗣️  Local TTS Speaking: {text[:20]}...")
                engine.say(text)
                engine.runAndWait()
            tts_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            print(f"❌ TTS Error: {e}")

def speak_local_tts(text: str):
    """非阻塞 TTS"""
    if text and text.strip():
        tts_queue.put(text)

# --- 配置 ---
API_KEY = os.getenv("ZHIPU_API_KEY")
WS_URL = "wss://open.bigmodel.cn/api/paas/v4/realtime?model=GLM-Realtime"
logger = DialogueLogger(filename="data/save_data.jsonl")

# 实时同步工作器
CURRENT_USER_ID = os.getenv("USER_ID", "3f6c7b1a-9d2e-4f8a-b5c3-e1f2a3b4c5d6")
sync_worker = None

SAMPLE_RATE = 16000
CHUNK = 1024
CHUNK_DURATION = CHUNK / SAMPLE_RATE

# 🔑 Client VAD 配置
voice_processor = SimpleMyVoiceProcessor(sample_rate=SAMPLE_RATE, vad_aggressiveness=2)

# 🔑 语音状态管理
class SpeechDetector:
    """客户端语音检测器"""
    def __init__(self, silence_threshold_seconds=1.5):
        self.is_speaking = False
        self.last_speech_time = 0
        self.silence_threshold = silence_threshold_seconds
        self.speech_started = False
    
    def update(self, has_speech):
        """更新语音状态"""
        current_time = time.time()
        
        if has_speech:
            if not self.is_speaking:
                self.is_speaking = True
                self.speech_started = True
                print("\n🎤 [开始说话]")
            self.last_speech_time = current_time
            return "speaking"
        else:
            if self.is_speaking:
                # 检查是否超过静音阈值
                silence_duration = current_time - self.last_speech_time
                if silence_duration > self.silence_threshold:
                    self.is_speaking = False
                    if self.speech_started:
                        self.speech_started = False
                        print(f"\n🔇 [停止说话] (静音 {silence_duration:.1f}秒)")
                        return "speech_end"
            return "silence"

speech_detector = SpeechDetector(silence_threshold_seconds=1.5)

audio_queue = queue.Queue()
session_ready = threading.Event()
stop_event = threading.Event()

# 音频播放缓冲
audio_playback_buffer = []
playback_lock = threading.Lock()
audio_played_in_response = False

# AI 回复状态
ai_is_responding = False
ai_response_lock = threading.Lock()
ws_global = None

# --- 打断功能 ---
def interrupt_ai_response():
    """打断 AI 回复"""
    global ai_is_responding, ws_global
    
    with ai_response_lock:
        if ai_is_responding and ws_global:
            print("\n\n⚠️  [用户打断] 正在取消 AI 回复...")
            try:
                # 清空播放缓冲
                with playback_lock:
                    audio_playback_buffer.clear()
                
                # 停止音频播放
                sd.stop()
                
                # 发送取消请求
                cancel_msg = {
                    "type": "response.cancel"
                }
                ws_global.send(json.dumps(cancel_msg))
                print("   ✅ 已发送取消请求")
                
                ai_is_responding = False
                
                # 清空音频缓冲
                audio_queue.queue.clear()
                print("   🔄 已清空缓冲区，可以继续说话")
                
            except Exception as e:
                print(f"   ❌ 打断失败: {e}")
        else:
            print("\n💡 AI 当前未在回复中")

def on_press(key):
    """键盘监听回调"""
    try:
        if key == keyboard.Key.enter:
            interrupt_ai_response()
    except Exception as e:
        pass

# 启动键盘监听
keyboard_listener = keyboard.Listener(on_press=on_press)
keyboard_listener.start()

# --- JWT Token 生成 ---
def generate_jwt_token(api_key: str, exp_seconds: int = 3600) -> str:
    try:
        api_key_id, api_key_secret = api_key.split('.')
    except ValueError:
        raise ValueError("Invalid API Key format")
    
    current_time = int(time.time())
    payload = {
        "api_key": api_key_id,
        "exp": current_time + exp_seconds,
        "timestamp": current_time
    }
    encoded_jwt = jwt.encode(
        payload, api_key_secret,
        algorithm="HS256",
        headers={"alg": "HS256", "sign_type": "SIGN"}
    )
    return encoded_jwt

# --- 音频采集回调 ---
def audio_callback(indata, frames, time_info, status):
    """sounddevice 回调函数"""
    if status:
        print(f"Audio callback status: {status}")
    if not stop_event.is_set():
        audio_queue.put(indata.copy())

# --- 🔑 Client VAD 音频发送循环 ---
def send_audio_loop(ws):
    """使用 Client VAD 的音频发送循环"""
    global ws_global
    ws_global = ws
    
    print("🎤 开始录音（Client VAD 模式）...")
    print("💡 提示：说话时会自动检测，停顿 1.5 秒后自动提交并请求 AI 回复")
    print("💡 按 Enter 可打断 AI 回复\n")
    
    # 等待会话就绪
    session_ready.wait()
    
    while not stop_event.is_set():
        try:
            # 获取音频数据（超时 0.1 秒）
            audio_chunk = audio_queue.get(timeout=0.1)
            
            # 🔑 本地 VAD 检测
            processed = voice_processor.process(audio_chunk)
            has_speech = processed is not None
            
            # 更新语音状态
            speech_status = speech_detector.update(has_speech)
            
            if has_speech:
                # 检测到语音，发送到服务器
                wav_io = BytesIO()
                with wave.open(wav_io, "wb") as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(SAMPLE_RATE)
                    wav_file.writeframes(processed.tobytes())
                
                wav_io.seek(0)
                audio_base64 = base64.b64encode(wav_io.getvalue()).decode("utf-8")
                
                # 发送音频数据
                message = {
                    "type": "input_audio_buffer.append",
                    "audio": audio_base64
                }
                ws.send(json.dumps(message))
            
            # 🔑 检测到语音结束，提交并请求回复
            if speech_status == "speech_end":
                print("📤 提交音频缓冲...")
                
                # 1. 提交音频
                commit_msg = {
                    "type": "input_audio_buffer.commit"
                }
                ws.send(json.dumps(commit_msg))
                time.sleep(0.1)
                
                # 2. 请求 AI 回复
                response_msg = {
                    "type": "response.create",
                    "response": {
                        "modalities": ["audio", "text"]
                    }
                }
                ws.send(json.dumps(response_msg))
                print("✅ 已请求 AI 回复，等待响应...\n")
                
        except queue.Empty:
            # 即使队列空，也要检查是否超时结束语音
            speech_status = speech_detector.update(False)
            if speech_status == "speech_end":
                print("📤 提交音频缓冲（超时）...")
                commit_msg = {"type": "input_audio_buffer.commit"}
                ws.send(json.dumps(commit_msg))
                time.sleep(0.1)
                
                response_msg = {
                    "type": "response.create",
                    "response": {"modalities": ["audio", "text"]}
                }
                ws.send(json.dumps(response_msg))
                print("✅ 已请求 AI 回复\n")
            continue
        except Exception as e:
            if not stop_event.is_set():
                print(f"❌ 音频发送错误: {e}")
                import traceback
                traceback.print_exc()

# --- 音频播放线程 ---
def play_audio_stream():
    """播放音频流"""
    global audio_played_in_response
    
    while not stop_event.is_set():
        try:
            time.sleep(0.05)
            
            with playback_lock:
                if len(audio_playback_buffer) > 0:
                    if not audio_played_in_response:
                        audio_played_in_response = True
                    
                    full_audio = np.concatenate(audio_playback_buffer)
                    audio_playback_buffer.clear()
                    
                    # 播放音频
                    try:
                        max_val = np.abs(full_audio).max()
                        if max_val > 0:
                            if max_val < 10000:
                                volume_boost = 10000 / max_val
                                full_audio = (full_audio * volume_boost).astype(np.int16)
                            
                            SPEED_MULTIPLIER = 1.3
                            playback_rate = int(SAMPLE_RATE * SPEED_MULTIPLIER)
                            sd.play(full_audio, samplerate=playback_rate, blocking=True)
                    except Exception as e:
                        print(f"❌ 播放错误: {e}")
                        
        except Exception as e:
            if not stop_event.is_set():
                print(f"❌ 播放线程错误: {e}")

# --- WebSocket 消息处理 ---
def on_message(ws, message):
    """处理 WebSocket 消息"""
    global ai_is_responding, audio_played_in_response, sync_worker
    
    data = json.loads(message)
    msg_type = data.get("type")
    
    if msg_type in ("session.created", "session.updated", "error", "session.error"):
        print(f"\n📡 [{msg_type}] {json.dumps(data, ensure_ascii=False, indent=2)}")
    
    if msg_type in ("session.created", "session.updated"):
        print("✅ Session Info:", data.get("session", {}).get("id"))
        session_ready.set()
        
    elif msg_type == "conversation.item.input_audio_transcription.completed":
        user_text = data.get("transcript", "")
        if user_text:
            print(f"\n📝 [USER]: {user_text}")
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
            if not ai_is_responding:
                with ai_response_lock:
                    ai_is_responding = True
                    print("\n🔊 [AI 回复中] 按 Enter 可打断")
            
            audio_base64 = data.get("delta", "")
            if audio_base64:
                audio_bytes = base64.b64decode(audio_base64)
                audio_np = np.frombuffer(audio_bytes, dtype=np.int16)
                
                with playback_lock:
                    audio_playback_buffer.append(audio_np)
                    
        except Exception as e:
            print(f"❌ 音频解码错误: {e}")
    
    elif msg_type == "response.audio_transcript.delta":
        text = data.get("delta", "")
        if text:
            logger.log_assistant_response(text)
    
    elif msg_type == "response.done":
        with ai_response_lock:
            ai_is_responding = False
        
        print("\n" + "="*60)
        print("✅ 回复完成")
        print("="*60)
        
        # 🔑 实时同步到 Memobase
        dialogue_data = logger.finalize_turn(synced=False)
        if dialogue_data and sync_worker:
            success = sync_worker.enqueue(dialogue_data)
            if success:
                logger.info("📤 [实时同步] 已加入同步队列")
                logger.update_sync_status(dialogue_data['id'], synced=True)
            else:
                logger.warning("⚠️  [实时同步] 加入队列失败，将由定时任务处理")
        
        audio_played_in_response = False
    
    elif msg_type == "input_audio_buffer.committed":
        print("✅ 音频已提交")
    
    elif msg_type == "input_audio_buffer.speech_started":
        print("🎤 [服务器检测到语音开始]")
    
    elif msg_type == "input_audio_buffer.speech_stopped":
        print("🔇 [服务器检测到语音停止]")
    
    elif msg_type in ("error", "session.error"):
        error_info = data.get('error', {})
        print(f"❌ 错误: {error_info.get('message', data)}")
    
    elif msg_type == "heartbeat":
        pass
    
    elif msg_type == "rate_limits.updated":
        pass

def on_open(ws):
    """WebSocket 连接建立"""
    global sync_worker
    
    print("🔌 WebSocket connected, configuring session...")
    
    # 🔑 Client VAD 配置 - turn_detection 设置为 None
    session_config = {
        "type": "session.update",
        "session": {
            "input_audio_format": "wav",
            "output_audio_format": "pcm",
            "turn_detection": None,  # 🔑 关键：使用 Client VAD
            "input_audio_transcription": {
                "enabled": True
            },
            "temperature": 0.8,
            "modalities": ["audio", "text"],
            "beta_fields": {
                "chat_mode": "audio",
                "tts_source": "e2e",
                "auto_search": False
            }
        }
    }
    
    print(f"📤 Session config (Client VAD): {json.dumps(session_config, ensure_ascii=False, indent=2)}")
    ws.send(json.dumps(session_config))
    time.sleep(0.5)
    
    # 初始化实时同步
    if not sync_worker:
        try:
            sync_worker = create_sync_worker(CURRENT_USER_ID, logger)
            if sync_worker:
                print("✅ 实时同步工作器已启动")
        except Exception as e:
            print(f"⚠️  实时同步初始化失败（将使用定时备份）: {e}")
    
    # 启动音频发送线程
    threading.Thread(target=send_audio_loop, args=(ws,), daemon=True).start()

def on_close(ws, close_status_code, close_msg):
    """WebSocket 连接关闭"""
    if not stop_event.is_set():
        print(f"🔌 连接已关闭: code={close_status_code}, msg={close_msg}")

def on_error(ws, error):
    """WebSocket 错误"""
    print(f"❌ WebSocket 错误: {error}")

# --- 主程序函数 ---
def main():
    """主程序入口"""
    global sync_worker
    
    if not API_KEY:
        print("❌ 请设置 ZHIPU_API_KEY 环境变量")
        sys.exit(1)
    
    print("\n" + "="*80)
    print("    GLM-Realtime 语音助手 (Client VAD 模式)")
    print("="*80)
    print("📌 模式说明：")
    print("   • Client VAD - 客户端控制语音检测")
    print("   • 自动检测语音结束（静音 1.5 秒）并请求 AI 回复")
    print("   • 按 Enter 可打断 AI 回复")
    print("   • Ctrl+C 退出程序")
    print("="*80 + "\n")
    
    # 生成 JWT Token
    try:
        AUTH_TOKEN = generate_jwt_token(API_KEY)
        print("✅ JWT Token 生成成功\n")
    except Exception as e:
        print(f"❌ JWT Token 生成失败: {e}")
        sys.exit(1)
    
    # 启动 TTS 工作线程
    tts_thread = threading.Thread(target=tts_worker_thread, daemon=True)
    tts_thread.start()
    
    # 启动音频播放线程
    playback_thread = threading.Thread(target=play_audio_stream, daemon=True)
    playback_thread.start()
    
    # 创建 WebSocket 连接
    websocket.enableTrace(False)
    
    ws = websocket.WebSocketApp(
        WS_URL,
        header=[f"Authorization: Bearer {AUTH_TOKEN}"],
        on_message=on_message,
        on_open=on_open,
        on_close=on_close,
        on_error=on_error
    )
    
    # 启动录音
    try:
        with sd.InputStream(
            channels=1,
            samplerate=SAMPLE_RATE,
            dtype='int16',
            blocksize=CHUNK,
            callback=audio_callback
        ):
            print("🎙️  录音设备已启动\n")
            ws.run_forever()
            
    except KeyboardInterrupt:
        print("\n\n👋 用户中断，正在退出...")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        stop_event.set()
        
        # 停止同步工作器
        if sync_worker:
            print("\n🛑 正在停止实时同步...")
            sync_worker.stop(timeout=5)
        
        # 停止音频
        sd.stop()
        
        # 停止键盘监听
        keyboard_listener.stop()
        
        print("\n程序已退出。")

# --- 程序入口 ---
if __name__ == "__main__":
    main()

