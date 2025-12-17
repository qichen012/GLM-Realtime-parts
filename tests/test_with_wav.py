#!/usr/bin/env python3
"""
使用 WAV 文件测试 GLM-Realtime API
测试是否能正常接收音频输出
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
from io import BytesIO
from dotenv import load_dotenv

# 加载环境变量
load_dotenv('/Users/xwj/Desktop/gpt-realtime-demo/.env')

# 配置
API_KEY = os.getenv("ZHIPU_API_KEY")
WS_URL = "wss://open.bigmodel.cn/api/paas/v4/realtime?model=GLM-Realtime"
SAMPLE_RATE = 16000

# 全局变量
audio_playback_buffer = []
session_ready = False


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


def encode_wave_to_base64(wave_file_path):
    """将 WAV 文件转换为 base64 编码"""
    try:
        with wave.open(wave_file_path, "rb") as wave_file:
            # 获取音频参数
            channels = wave_file.getnchannels()
            sample_width = wave_file.getsampwidth()
            frame_rate = wave_file.getframerate()
            frames = wave_file.readframes(wave_file.getnframes())
            
            print(f"📊 音频参数: 声道={channels}, 位深度={sample_width*8}位, 采样率={frame_rate}Hz")
            
            # 创建标准 WAV 格式
            wave_io = BytesIO()
            with wave.open(wave_io, "wb") as wave_out:
                wave_out.setnchannels(channels)
                wave_out.setsampwidth(sample_width)
                wave_out.setframerate(frame_rate)
                wave_out.writeframes(frames)
            
            wave_io.seek(0)
            return base64.b64encode(wave_io.getvalue()).decode("utf-8")
    except Exception as e:
        print(f"❌ 音频文件处理错误: {e}")
        return None


def on_message(ws, message):
    """处理 WebSocket 消息"""
    global audio_playback_buffer
    
    data = json.loads(message)
    msg_type = data.get("type")
    
    # 打印关键消息
    if msg_type in ("session.created", "session.updated"):
        print(f"✅ [{msg_type}]")
        print(f"   配置: {json.dumps(data.get('session', {}), ensure_ascii=False, indent=2)}")
    
    elif msg_type == "conversation.item.input_audio_transcription.completed":
        # 用户输入的转写
        user_text = data.get("transcript", "")
        print(f"\n👤 [用户输入转写]: {user_text if user_text else '(转写为空)'}")
    
    elif msg_type == "response.audio_transcript.delta":
        # AI 回复的转写（流式）
        text = data.get("delta", "")
        if text:
            sys.stdout.write(text)
            sys.stdout.flush()
    
    elif msg_type == "response.audio_transcript.done":
        # AI 回复转写完成
        transcript = data.get("transcript", "")
        if transcript:
            print(f"\n🤖 AI 回复: {transcript}")
    
    elif msg_type == "response.audio.delta":
        # 🔑 关键：接收音频数据
        try:
            audio_base64 = data.get("delta", "")
            if audio_base64:
                audio_bytes = base64.b64decode(audio_base64)
                audio_np = np.frombuffer(audio_bytes, dtype=np.int16)
                audio_playback_buffer.append(audio_np)
                print(f"🔊 收到音频块: {len(audio_bytes)} bytes", end='\r')
        except Exception as e:
            print(f"\n❌ 音频解码错误: {e}")
    
    elif msg_type == "response.audio.done":
        # 🎵 音频接收完成，开始播放
        print(f"\n\n🎵 音频接收完成！")
        if audio_playback_buffer:
            try:
                full_audio = np.concatenate(audio_playback_buffer)
                original_duration = len(full_audio)/SAMPLE_RATE
                print(f"   总样本数: {len(full_audio)}, 原始时长: {original_duration:.2f}秒")
                
                # 音量增强
                max_val = np.abs(full_audio).max()
                if max_val > 0:
                    if max_val < 10000:
                        volume_boost = 10000 / max_val
                        full_audio = (full_audio * volume_boost).astype(np.int16)
                        print(f"   🔊 音量增强: {volume_boost:.2f}x")
                    
                    # 🚀 加速播放：通过提高采样率来加快语速
                    SPEED_MULTIPLIER = 1.5  # 调整播放速度（推荐 1.3-1.8）
                    playback_rate = int(SAMPLE_RATE * SPEED_MULTIPLIER)
                    adjusted_duration = len(full_audio) / playback_rate
                    
                    print(f"   ⚡ 加速播放: {SPEED_MULTIPLIER}x 倍速")
                    print(f"   ▶️  播放时长: {adjusted_duration:.2f}秒（原{original_duration:.2f}秒）")
                    sd.play(full_audio, samplerate=playback_rate, blocking=True)
                    print("   ✅ 播放完成！")
                else:
                    print("   ⚠️  音频数据为静音")
                
                audio_playback_buffer.clear()
            except Exception as e:
                print(f"   ❌ 播放错误: {e}")
        else:
            print("   ⚠️  没有接收到音频数据！")
    
    elif msg_type == "response.output_item.done":
        # 检查是否有音频在这个事件中
        item = data.get("item", {})
        content_list = item.get("content", [])
        
        for content in content_list:
            if content.get("type") == "audio":
                audio_base64 = content.get("audio", "")
                if audio_base64:
                    print(f"\n🎵 在 output_item.done 中发现音频数据！")
                    try:
                        audio_bytes = base64.b64decode(audio_base64)
                        full_audio = np.frombuffer(audio_bytes, dtype=np.int16)
                        print(f"   总样本数: {len(full_audio)}, 时长: {len(full_audio)/SAMPLE_RATE:.2f}秒")
                        
                        # 播放
                        sd.play(full_audio, samplerate=SAMPLE_RATE, blocking=True)
                        print("   ✅ 播放完成！")
                    except Exception as e:
                        print(f"   ❌ 播放错误: {e}")
    
    elif msg_type == "response.done":
        print("\n" + "="*60)
        print("🎉 对话完成")
        print("="*60 + "\n")
        # 关闭连接
        ws.close()
    
    elif msg_type == "input_audio_buffer.committed":
        print("✅ 音频已提交")
    
    elif msg_type in ("error", "session.error"):
        error_info = data.get('error', {})
        print(f"❌ 错误: {error_info.get('message', data)}")
    
    elif msg_type == "heartbeat":
        pass  # 静默处理心跳
    
    elif msg_type not in ("rate_limits.updated", "conversation.created", 
                          "conversation.updated", "response.created",
                          "conversation.item.created"):
        # 🔍 打印未知消息的完整内容，寻找音频数据
        print(f"\n💡 [未知消息类型: {msg_type}]")
        print(f"完整内容: {json.dumps(data, ensure_ascii=False, indent=2)}")


def send_audio_in_chunks(ws):
    """分帧发送音频（模仿官方 Server VAD 示例）"""
    try:
        with wave.open(wav_file_path, "rb") as wave_file:
            channels = wave_file.getnchannels()
            sample_width = wave_file.getsampwidth()
            frame_rate = wave_file.getframerate()
            audio_data = wave_file.readframes(wave_file.getnframes())
        
        print(f"📊 开始分帧发送: 采样率={frame_rate}Hz, 声道={channels}, 位深={sample_width*8}位")
        
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
            
            # 发送
            ws.send(json.dumps({
                "type": "input_audio_buffer.append",
                "audio": base64_data
            }))
            
            print(f"📤 已发送: {i}/{total_packets}", end='\r')
            time.sleep(packet_ms / 1000)  # 等待 100ms
        
        print(f"\n✅ 音频分帧发送完成 (文件已包含静默尾部)")
        
    except Exception as e:
        print(f"❌ 分帧发送失败: {e}")
        import traceback
        traceback.print_exc()


def on_open(ws):
    """WebSocket 连接建立"""
    global session_ready
    print("🔌 WebSocket 已连接")
    
    # 配置会话 - 使用 Server VAD
    session_config = {
        "type": "session.update",
        "session": {
            "input_audio_format": "wav",
            "output_audio_format": "pcm",
            "turn_detection": {
                "type": "server_vad",
                "threshold": 0.5,              # 使用默认阈值，对录制文件友好
                "silence_duration_ms": 800,    # 静默0.8秒判定说完（加快响应）
                "prefix_padding_ms": 300
            },
            "input_audio_transcription": {"enabled": True},
            "modalities": ["audio", "text"],
            "temperature": 0.8,  # 自然度
            "beta_fields": {
                "chat_mode": "audio",
                "tts_source": "e2e",  # 端到端语音合成
                "lang": "zh-cn",
                "accent": "mandarin",
                "auto_search": False
                # 注意：speed 参数不生效，使用客户端播放加速
            }
        }
    }
    
    print("📤 发送会话配置（Server VAD 模式）...")
    ws.send(json.dumps(session_config))
    session_ready = True
    
    # 等待会话建立
    time.sleep(1)
    
    # 分帧发送音频
    print("\n📤 开始分帧发送音频...")
    send_audio_in_chunks(ws)
    
    # Server VAD 模式下不需要手动操作，服务器会自动检测并响应
    print("\n⏳ 等待服务器 VAD 检测并响应...")
    print("💡 提示：Server VAD 会自动检测语音结束并触发响应，无需手动提交\n")


def on_close(ws, close_status_code, close_msg):
    """WebSocket 连接关闭"""
    print(f"🔌 连接已关闭: code={close_status_code}, msg={close_msg}")


def on_error(ws, error):
    """WebSocket 错误"""
    print(f"❌ WebSocket 错误: {error}")


if __name__ == "__main__":
    if not API_KEY:
        print("❌ 请设置 ZHIPU_API_KEY 环境变量")
        sys.exit(1)
    
    # 获取 WAV 文件路径
    if len(sys.argv) < 2:
        # 默认使用示例文件
        wav_file_path = "glm-realtime-sdk/python/samples/input/give_me_a_joke.wav"
        print(f"💡 未指定音频文件，使用默认文件: {wav_file_path}")
    else:
        wav_file_path = sys.argv[1]
    
    if not os.path.exists(wav_file_path):
        print(f"❌ 文件不存在: {wav_file_path}")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("    GLM-Realtime 音频文件测试")
    print("="*60)
    print(f"📁 测试文件: {wav_file_path}")
    print("="*60 + "\n")
    
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
        print("⏳ 正在连接...\n")
        ws.run_forever()
        
        # 等待所有音频播放完成
        time.sleep(1)
        
    except KeyboardInterrupt:
        print("\n\n👋 用户中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        sd.stop()
        print("\n程序退出。")

