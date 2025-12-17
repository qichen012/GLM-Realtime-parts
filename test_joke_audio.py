#!/usr/bin/env python3
# coding: utf-8
"""
GLM-Realtime 音频测试 - give_me_a_joke.wav
测试 GLM-Realtime 能否正常接收音频并给出音频回复
"""

import json
import base64
import websocket
import sounddevice as sd
import numpy as np
import time
import jwt
import os
import sys
import wave
import threading
from io import BytesIO
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置
API_KEY = os.getenv("ZHIPU_API_KEY")
WS_URL = "wss://open.bigmodel.cn/api/paas/v4/realtime?model=GLM-Realtime"
SAMPLE_RATE = 16000

# 测试文件路径
AUDIO_FILE = "glm-realtime-sdk/python/samples/input/give_me_a_joke.wav"

# 全局变量
audio_playback_buffer = []
session_ready = False
received_audio = False
received_transcript = False


def generate_jwt_token(api_key: str, exp_seconds: int = 3600) -> str:
    """生成 JWT Token"""
    try:
        api_key_id, api_key_secret = api_key.split('.')
    except ValueError:
        raise ValueError("API Key 格式错误，应该是 'API_KEY_ID.API_KEY_SECRET'")
    
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


def on_message(ws, message):
    """处理 WebSocket 消息"""
    global audio_playback_buffer, received_audio, received_transcript
    
    data = json.loads(message)
    msg_type = data.get("type")
    
    # 会话建立
    if msg_type in ("session.created", "session.updated"):
        print(f"✅ 会话已{('建立' if msg_type == 'session.created' else '更新')}")
    
    # 用户输入转写
    elif msg_type == "conversation.item.input_audio_transcription.completed":
        user_text = data.get("transcript", "")
        print(f"\n👤 用户输入: {user_text if user_text else '(转写为空)'}")
    
    # AI 文字回复（流式）
    elif msg_type == "response.audio_transcript.delta":
        text = data.get("delta", "")
        if text:
            sys.stdout.write(text)
            sys.stdout.flush()
    
    # AI 文字回复完成
    elif msg_type == "response.audio_transcript.done":
        transcript = data.get("transcript", "")
        if transcript:
            print(f"\n\n🤖 AI 回复文字: {transcript}")
            received_transcript = True
    
    # 🔑 接收音频数据（流式）
    elif msg_type == "response.audio.delta":
        try:
            audio_base64 = data.get("delta", "")
            if audio_base64:
                audio_bytes = base64.b64decode(audio_base64)
                audio_np = np.frombuffer(audio_bytes, dtype=np.int16)
                audio_playback_buffer.append(audio_np)
                print(f"🔊 收到音频块: {len(audio_bytes)} bytes", end='\r')
        except Exception as e:
            print(f"\n❌ 音频解码错误: {e}")
    
    # 🎵 音频接收完成
    elif msg_type == "response.audio.done":
        print(f"\n\n🎵 音频接收完成！")
        if audio_playback_buffer:
            received_audio = True
            try:
                full_audio = np.concatenate(audio_playback_buffer)
                duration = len(full_audio) / SAMPLE_RATE
                print(f"   📊 音频时长: {duration:.2f} 秒")
                print(f"   📊 样本数: {len(full_audio)}")
                
                # 音量增强
                max_val = np.abs(full_audio).max()
                if max_val > 0:
                    if max_val < 10000:
                        volume_boost = 10000 / max_val
                        full_audio = (full_audio * volume_boost).astype(np.int16)
                        print(f"   🔊 音量增强: {volume_boost:.2f}x")
                    
                    # 🚀 1.5 倍速播放
                    SPEED_MULTIPLIER = 1.5
                    playback_rate = int(SAMPLE_RATE * SPEED_MULTIPLIER)
                    adjusted_duration = len(full_audio) / playback_rate
                    
                    print(f"   ⚡ 播放速度: {SPEED_MULTIPLIER}x")
                    print(f"   ⏱️  播放时长: {adjusted_duration:.2f}秒（原 {duration:.2f}秒）")
                    print(f"   ▶️  正在播放音频...")
                    sd.play(full_audio, samplerate=playback_rate, blocking=True)
                    print("   ✅ 播放完成！")
                else:
                    print("   ⚠️  音频数据为静音")
                
                audio_playback_buffer.clear()
            except Exception as e:
                print(f"   ❌ 播放错误: {e}")
        else:
            print("   ⚠️  未接收到音频数据！")
    
    # 对话完成
    elif msg_type == "response.done":
        print("\n" + "="*70)
        print("🎉 对话完成")
        print("="*70)
        
        # 测试结果总结
        print("\n📋 测试结果:")
        print(f"   • 接收到文字回复: {'✅ 是' if received_transcript else '❌ 否'}")
        print(f"   • 接收到音频回复: {'✅ 是' if received_audio else '❌ 否'}")
        
        if received_audio and received_transcript:
            print("\n✅ 测试成功！GLM-Realtime 能正常给出音频回复")
        else:
            print("\n⚠️  测试部分失败，请检查配置")
        
        print("="*70 + "\n")
        
        # 关闭连接
        time.sleep(1)
        ws.close()
    
    # 音频提交确认
    elif msg_type == "input_audio_buffer.committed":
        print("✅ 音频已提交给 GLM")
    
    # 错误处理
    elif msg_type in ("error", "session.error"):
        error_info = data.get('error', {})
        print(f"❌ 错误: {error_info.get('message', data)}")
    
    # 静默处理的消息类型
    elif msg_type not in ("heartbeat", "rate_limits.updated", "conversation.created", 
                          "conversation.updated", "response.created", 
                          "conversation.item.created"):
        # 调试：打印未知消息
        if os.getenv("DEBUG"):
            print(f"\n💡 [消息类型: {msg_type}]")


def send_audio_in_chunks(ws, wav_file_path):
    """分帧发送音频（模拟实时麦克风输入）"""
    try:
        with wave.open(wav_file_path, "rb") as wave_file:
            channels = wave_file.getnchannels()
            sample_width = wave_file.getsampwidth()
            frame_rate = wave_file.getframerate()
            audio_data = wave_file.readframes(wave_file.getnframes())
        
        print(f"📊 音频参数: 采样率={frame_rate}Hz, 声道={channels}, 位深={sample_width*8}位")
        print(f"📊 原始音频时长: {len(audio_data)/(frame_rate*sample_width*channels):.2f}秒")
        
        # 按 100ms 一包切分音频
        packet_ms = 100
        packet_samples = int(frame_rate * packet_ms / 1000)
        bytes_per_sample = sample_width * channels
        packet_bytes = packet_samples * bytes_per_sample
        
        total_packets = (len(audio_data) + packet_bytes - 1) // packet_bytes
        print(f"📦 总包数: {total_packets}")
        
        # 分帧发送
        for i, pos in enumerate(range(0, len(audio_data), packet_bytes), 1):
            packet_data = audio_data[pos:pos + packet_bytes]
            if not packet_data:
                break
            
            # 构造 WAV 格式
            wav_io = BytesIO()
            with wave.open(wav_io, "wb") as wav_out:
                wav_out.setnchannels(channels)
                wav_out.setsampwidth(sample_width)
                wav_out.setframerate(frame_rate)
                wav_out.writeframes(packet_data)
            
            wav_io.seek(0)
            base64_data = base64.b64encode(wav_io.getvalue()).decode("utf-8")
            
            # 发送音频块
            ws.send(json.dumps({
                "type": "input_audio_buffer.append",
                "audio": base64_data
            }))
            
            print(f"📤 发送进度: {i}/{total_packets}", end='\r')
            time.sleep(packet_ms / 1000)  # 等待 100ms
        
        print(f"\n✅ 音频发送完成")
        
        # 🔑 关键：发送额外的静音以触发 Server VAD
        print("📤 发送静音帧以触发 VAD 检测...")
        silence_duration_ms = 1500  # 1.5秒静音
        silence_packets = silence_duration_ms // packet_ms
        silence_data = b'\x00' * packet_bytes  # 静音数据
        
        for i in range(silence_packets):
            wav_io = BytesIO()
            with wave.open(wav_io, "wb") as wav_out:
                wav_out.setnchannels(channels)
                wav_out.setsampwidth(sample_width)
                wav_out.setframerate(frame_rate)
                wav_out.writeframes(silence_data)
            
            wav_io.seek(0)
            base64_data = base64.b64encode(wav_io.getvalue()).decode("utf-8")
            
            ws.send(json.dumps({
                "type": "input_audio_buffer.append",
                "audio": base64_data
            }))
            
            print(f"📤 静音帧: {i+1}/{silence_packets}", end='\r')
            time.sleep(packet_ms / 1000)
        
        print(f"\n✅ 静音帧发送完成")
        
    except Exception as e:
        print(f"❌ 音频发送失败: {e}")
        import traceback
        traceback.print_exc()


def check_and_trigger_response(ws):
    """检查是否需要手动触发响应"""
    # 等待一段时间看 Server VAD 是否能自动触发
    time.sleep(3)
    
    # 如果 Server VAD 没有自动触发，手动提交并创建响应
    if not received_audio and not received_transcript:
        print("💡 Server VAD 未自动触发，尝试手动提交...")
        
        # 提交音频缓冲区
        ws.send(json.dumps({"type": "input_audio_buffer.commit"}))
        time.sleep(0.2)
        
        # 手动创建响应
        ws.send(json.dumps({"type": "response.create"}))
        print("📤 已手动创建响应请求\n")


def on_open(ws):
    """WebSocket 连接建立"""
    global session_ready
    print("🔌 WebSocket 已连接")
    
    # 配置会话 - 使用 Server VAD 模式，优化语音效果
    session_config = {
        "type": "session.update",
        "session": {
            "input_audio_format": "wav",
            "output_audio_format": "pcm",
            "turn_detection": {
                "type": "server_vad",
                "threshold": 0.5,
                "silence_duration_ms": 800,
                "prefix_padding_ms": 300
            },
            "input_audio_transcription": {"enabled": True},
            "modalities": ["audio", "text"],
            "temperature": 0.8,
            "voice": "female-sweet",  # 🔑 甜美女声
            "beta_fields": {
                "chat_mode": "audio",
                "tts_source": "e2e",
                "auto_search": False,
                "voice": "female-sweet"  # 🔑 甜美女声
            }
        }
    }
    
    print("📤 配置会话（Server VAD 模式）...")
    ws.send(json.dumps(session_config))
    session_ready = True
    
    # 等待会话建立
    time.sleep(1)
    
    # 发送音频文件
    print("\n📤 开始发送音频...")
    send_audio_in_chunks(ws, AUDIO_FILE)
    
    # Server VAD 会自动检测并响应
    print("\n⏳ 等待 Server VAD 自动检测...\n")
    
    # 启动延迟检查线程
    threading.Thread(target=check_and_trigger_response, args=(ws,), daemon=True).start()


def on_close(ws, close_status_code, close_msg):
    """WebSocket 连接关闭"""
    print(f"🔌 连接已关闭")


def on_error(ws, error):
    """WebSocket 错误"""
    print(f"❌ WebSocket 错误: {error}")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("    GLM-Realtime 音频回复测试")
    print("="*70)
    print(f"📁 测试文件: {AUDIO_FILE}")
    print(f"🎯 测试目标: 验证 GLM-Realtime 能否正常给出音频回复")
    print("="*70 + "\n")
    
    # 检查 API Key
    if not API_KEY:
        print("❌ 请设置 ZHIPU_API_KEY 环境变量")
        print("💡 提示: 在项目根目录的 .env 文件中添加:")
        print("   ZHIPU_API_KEY=your_api_key_here")
        sys.exit(1)
    
    # 检查文件是否存在
    if not os.path.exists(AUDIO_FILE):
        print(f"❌ 文件不存在: {AUDIO_FILE}")
        sys.exit(1)
    
    # 生成 JWT Token
    try:
        AUTH_TOKEN = generate_jwt_token(API_KEY)
        print("✅ JWT Token 生成成功\n")
    except Exception as e:
        print(f"❌ JWT Token 生成失败: {e}")
        sys.exit(1)
    
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
    
    try:
        print("⏳ 正在连接 GLM-Realtime...\n")
        ws.run_forever()
        
        # 等待音频播放完成
        time.sleep(1)
        
    except KeyboardInterrupt:
        print("\n\n👋 用户中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        sd.stop()
        print("\n✅ 测试完成\n")


