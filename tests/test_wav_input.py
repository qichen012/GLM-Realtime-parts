#!/usr/bin/env python3
# coding: utf-8
"""
测试脚本：使用 WAV 文件输入，测试 GLM-Realtime 语音回复功能

用法：
    python tests/test_wav_input.py <wav_file_path>
    
示例：
    python tests/test_wav_input.py tests/test_audio.wav
"""

import json
import base64
import websocket
import sounddevice as sd
import numpy as np
import wave
import time
import jwt
import os
import sys
from io import BytesIO
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载环境变量
load_dotenv('/Users/xwj/Desktop/gpt-realtime-demo/.env')

# --- 配置 ---
API_KEY = os.getenv("ZHIPU_API_KEY")
WS_URL = "wss://open.bigmodel.cn/api/paas/v4/realtime?model=GLM-Realtime"
SAMPLE_RATE = 16000

# --- 全局变量 ---
received_audio_chunks = []
received_text = ""
session_ready = False
response_received = False

# --- JWT Token 生成 ---
def generate_jwt_token(api_key: str, exp_seconds: int = 3600) -> str:
    """生成 JWT Token"""
    try:
        api_key, secret = api_key.split(".")
    except Exception as e:
        raise Exception("无效的 API Key")

    payload = {
        "api_key": api_key,
        "exp": datetime.utcnow() + timedelta(seconds=exp_seconds),
        "timestamp": int(datetime.utcnow().timestamp()),
    }

    return jwt.encode(
        payload,
        secret,
        algorithm="HS256",
        headers={"alg": "HS256", "sign_type": "SIGN"},
    )

# --- 音频处理函数 ---
def pcm_to_wav_base64(pcm_data: np.ndarray, sample_rate: int) -> str:
    """将 PCM 数据转换为 WAV 格式的 base64"""
    buffer = BytesIO()
    with wave.open(buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_data.tobytes())
    
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode('utf-8')

def base64_to_pcm(audio_base64: str) -> np.ndarray:
    """将 base64 编码的音频转换为 PCM 数据"""
    audio_bytes = base64.b64decode(audio_base64)
    return np.frombuffer(audio_bytes, dtype=np.int16)

# --- 读取 WAV 文件 ---
def read_wav_file(file_path: str):
    """读取 WAV 文件并返回音频数据"""
    print(f"📂 读取 WAV 文件: {file_path}")
    
    try:
        with wave.open(file_path, 'rb') as wav_file:
            # 检查音频格式
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            framerate = wav_file.getframerate()
            frames = wav_file.getnframes()
            
            print(f"   声道数: {channels}")
            print(f"   采样位数: {sample_width * 8} bit")
            print(f"   采样率: {framerate} Hz")
            print(f"   时长: {frames / framerate:.2f} 秒")
            
            # 读取音频数据
            audio_data = wav_file.readframes(frames)
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            # 如果是立体声，转换为单声道
            if channels == 2:
                audio_array = audio_array.reshape(-1, 2).mean(axis=1).astype(np.int16)
                print("   ⚠️  已转换为单声道")
            
            # 如果采样率不是 16000，需要重采样
            if framerate != SAMPLE_RATE:
                print(f"   ⚠️  需要重采样: {framerate} Hz → {SAMPLE_RATE} Hz")
                # 简单重采样（实际项目中应该用专业库如 librosa）
                duration = len(audio_array) / framerate
                new_length = int(duration * SAMPLE_RATE)
                audio_array = np.interp(
                    np.linspace(0, len(audio_array), new_length),
                    np.arange(len(audio_array)),
                    audio_array
                ).astype(np.int16)
            
            print(f"✅ 音频数据准备完成: {len(audio_array)} 个采样点")
            return audio_array
            
    except FileNotFoundError:
        print(f"❌ 文件不存在: {file_path}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        sys.exit(1)

# --- WebSocket 回调函数 ---
def on_open(ws):
    """连接建立时的回调"""
    global session_ready
    
    print("🔌 WebSocket 连接已建立")
    print("📤 发送会话配置...")
    
    session_config = {
        "type": "session.update",
        "session": {
            "input_audio_format": "wav",
            "output_audio_format": "pcm",
            "turn_detection": {
                "type": "server_vad",
                "threshold": 0.5,
                "prefix_padding_ms": 300,
                "silence_duration_ms": 800  # WAV 文件测试用较短的静音检测
            },
            "input_audio_transcription": {
                "enabled": True
            },
            "temperature": 0.8,
            "modalities": ["audio", "text"],
        }
    }
    
    try:
        ws.send(json.dumps(session_config))
        time.sleep(0.5)
        session_ready = True
        print("✅ 会话配置已发送")
    except Exception as e:
        print(f"❌ 发送会话配置失败: {e}")

def on_message(ws, message):
    """接收消息时的回调"""
    global received_text, response_received, received_audio_chunks
    
    data = json.loads(message)
    msg_type = data.get("type")
    
    # 会话创建/更新
    if msg_type in ("session.created", "session.updated"):
        print(f"✅ 会话就绪: {data.get('session', {}).get('id')}")
    
    # 用户语音转文本
    elif msg_type == "conversation.item.input_audio_transcription.completed":
        user_text = data.get("transcript", "")
        print(f"\n📝 [用户语音识别]: {user_text}")
    
    # AI 文本回复（增量）
    elif msg_type == "response.text.delta":
        text = data.get("text", "")
        received_text += text
        print(text, end="", flush=True)
    
    # AI 文本回复（完成）
    elif msg_type == "response.text.done":
        print()  # 换行
    
    # AI 语音回复（增量）
    elif msg_type == "response.audio.delta":
        audio_base64 = data.get("audio", "")
        if audio_base64:
            audio_chunk = base64_to_pcm(audio_base64)
            received_audio_chunks.append(audio_chunk)
    
    # AI 语音回复（完成）
    elif msg_type == "response.audio.done":
        print("\n🎵 AI 语音回复接收完成")
        if received_audio_chunks:
            print(f"   音频块数: {len(received_audio_chunks)}")
            total_samples = sum(len(chunk) for chunk in received_audio_chunks)
            duration = total_samples / SAMPLE_RATE
            print(f"   总时长: {duration:.2f} 秒")
    
    # 回复完成
    elif msg_type == "response.done":
        global response_received
        response_received = True
        print("🎉 回复完成")
    
    # 错误处理
    elif msg_type in ("session.error", "error"):
        error_info = data.get('error', {})
        print(f"\n❌ 错误: {error_info}")

def on_error(ws, error):
    """错误时的回调"""
    print(f"\n❌ WebSocket 错误: {error}")

def on_close(ws, close_status_code, close_msg):
    """连接关闭时的回调"""
    print(f"\n🔌 连接已关闭: code={close_status_code}, msg={close_msg}")

# --- 主测试函数 ---
def test_wav_input(wav_file_path: str):
    """测试 WAV 文件输入"""
    global session_ready, response_received, received_audio_chunks, received_text
    
    print("\n" + "="*60)
    print("🧪 GLM-Realtime WAV 文件测试")
    print("="*60)
    
    # 检查 API Key
    if not API_KEY:
        print("❌ 请设置 ZHIPU_API_KEY 环境变量")
        sys.exit(1)
    
    # 生成 Token
    try:
        auth_token = generate_jwt_token(API_KEY)
        print("✅ JWT Token 生成成功")
    except Exception as e:
        print(f"❌ JWT Token 生成失败: {e}")
        sys.exit(1)
    
    # 读取 WAV 文件
    audio_data = read_wav_file(wav_file_path)
    
    # 连接 WebSocket
    print("\n🔌 连接 WebSocket...")
    ws = websocket.WebSocketApp(
        WS_URL,
        header=[f"Authorization: Bearer {auth_token}"],
        on_message=on_message,
        on_open=on_open,
        on_close=on_close,
        on_error=on_error
    )
    
    # 启动 WebSocket（在后台线程）
    import threading
    ws_thread = threading.Thread(target=ws.run_forever, daemon=True)
    ws_thread.start()
    
    # 等待会话就绪
    print("⏳ 等待会话建立...")
    timeout = 10
    start_time = time.time()
    while not session_ready and (time.time() - start_time) < timeout:
        time.sleep(0.1)
    
    if not session_ready:
        print("❌ 会话建立超时")
        ws.close()
        sys.exit(1)
    
    print("✅ 会话已就绪\n")
    
    # 发送音频数据
    print("📤 发送音频数据...")
    
    # 将音频数据转换为 WAV base64
    audio_base64 = pcm_to_wav_base64(audio_data, SAMPLE_RATE)
    
    # 发送音频
    ws.send(json.dumps({
        "type": "input_audio_buffer.append",
        "audio": audio_base64
    }))
    
    print("✅ 音频数据已发送")
    
    # 提交音频
    time.sleep(0.5)
    ws.send(json.dumps({"type": "input_audio_buffer.commit"}))
    print("✅ 音频已提交")
    
    # 请求回复
    time.sleep(0.5)
    ws.send(json.dumps({
        "type": "response.create",
        "response": {
            "modalities": ["audio", "text"]
        }
    }))
    print("✅ 已请求回复\n")
    
    # 等待回复
    print("⏳ 等待 AI 回复...\n")
    timeout = 30
    start_time = time.time()
    while not response_received and (time.time() - start_time) < timeout:
        time.sleep(0.1)
    
    if not response_received:
        print("\n❌ 回复超时")
        ws.close()
        sys.exit(1)
    
    # 播放语音回复
    if received_audio_chunks:
        print("\n🔊 播放 AI 语音回复...")
        full_audio = np.concatenate(received_audio_chunks)
        
        # 音量调整
        max_val = np.abs(full_audio).max()
        if max_val > 0 and max_val < 10000:
            volume_boost = 10000 / max_val
            full_audio = (full_audio * volume_boost).astype(np.int16)
            print(f"   🔊 音量提升: {volume_boost:.2f}x")
        
        # 播放
        sd.play(full_audio, samplerate=SAMPLE_RATE, blocking=True)
        print("✅ 播放完成")
    else:
        print("\n⚠️  未收到语音回复")
    
    # 显示文本回复
    if received_text:
        print(f"\n📝 [AI 文本回复]: {received_text}")
    
    # 关闭连接
    time.sleep(1)
    ws.close()
    
    print("\n" + "="*60)
    print("✅ 测试完成")
    print("="*60)

# --- 主程序 ---
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ 用法: python tests/test_wav_input.py <wav_file_path>")
        print("\n示例:")
        print("  python tests/test_wav_input.py tests/test_audio.wav")
        print("  python tests/test_wav_input.py /path/to/your/audio.wav")
        sys.exit(1)
    
    wav_file_path = sys.argv[1]
    test_wav_input(wav_file_path)

