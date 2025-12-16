import asyncio
import websockets
import sounddevice as sd
import numpy as np
import queue
import threading

# --- 配置 ---
# 替换为你联想游戏本的局域网 IP 地址 (例如 192.168.1.10)
SERVER_IP = "10.29.175.39" 
SERVER_PORT = 8765
server_url = f"ws://{SERVER_IP}:{SERVER_PORT}"

# 音频配置 (必须与服务端模型一致，通常是 16k, float32, 单声道)
RATE = 16000
CHUNK = 9600  # 每次发送的数据块大小 (600ms左右)
CHANNELS = 1
AUDIO_FORMAT = 'float32'  # 🔑 Sherpa 推荐使用 float32 格式

# 音频队列
audio_queue = queue.Queue()

def audio_callback(indata, frames, time_info, status):
    """音频输入回调函数"""
    if status:
        print(f"⚠️ Audio status: {status}")
    # 将音频数据放入队列 (已经是 float32 格式)
    audio_queue.put(indata.copy())

async def send_audio():
    print(f"正在连接到服务端 {server_url} ...")
    print(f"📊 音频配置: {RATE}Hz, {AUDIO_FORMAT}, {CHANNELS} 通道")
    
    async with websockets.connect(server_url) as websocket:
        print("✅ 连接成功！开始说话... (按 Ctrl+C 停止)")
        print("🎤 使用 float32 格式，适配 Sherpa 模型\n")
        
        # 启动音频输入流（使用 float32 格式，Sherpa 推荐）
        stream = sd.InputStream(
            channels=CHANNELS,
            samplerate=RATE,
            dtype=AUDIO_FORMAT,  # 🔑 使用 float32 格式
            blocksize=CHUNK,
            callback=audio_callback
        )
        
        stream.start()
        
        async def send():
            """发送音频数据"""
            while True:
                try:
                    # 从队列获取音频数据
                    data = audio_queue.get(timeout=0.1)
                    # 转换为字节并发送
                    await websocket.send(data.tobytes())
                except queue.Empty:
                    await asyncio.sleep(0.01)

        async def receive():
            """接收服务端响应"""
            while True:
                result = await websocket.recv()
                # 这里打印出来的就是经过过滤（如果实现了）的文字
                print(f"🤖 AI 听到: {result}")

        try:
            # 并发执行发送和接收
            await asyncio.gather(send(), receive())
        finally:
            # 确保音频流被正确关闭
            stream.stop()
            stream.close()
            print("🛑 音频流已关闭")

if __name__ == "__main__":
    print("="*60)
    print("🎙️  语音客户端 (for Sherpa Server)")
    print("="*60)
    print(f"📡 服务器地址: {server_url}")
    print(f"🎵 音频格式: {RATE}Hz, {AUDIO_FORMAT}, {CHANNELS} 通道")
    print("="*60 + "\n")
    
    try:
        asyncio.run(send_audio())
    except KeyboardInterrupt:
        print("\n\n👋 停止录音")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()