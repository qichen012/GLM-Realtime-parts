import sounddevice as sd
import numpy as np
import time

duration = 2  # 播放持续时间，单位秒
freq = 440    # 440 Hz A4音高
samplerate = 16000 # 必须使用 16000 Hz，和您的代码保持一致

print(f"🔊 正在尝试播放 {duration} 秒，{freq} Hz 的正弦波 (采样率: {samplerate} Hz)...")

try:
    # 生成时间轴
    t = np.linspace(0., duration, int(samplerate * duration))
    # 生成正弦波数据 (振幅 0.5)
    data = 0.5 * np.sin(2. * np.pi * freq * t)
    
    # 播放音频
    sd.play(data, samplerate=samplerate)
    
    # 阻塞直到播放完毕
    sd.wait()  
    
    print("✅ 播放完毕。如果您听到了声音，则您的 sounddevice 配置是正确的。")

except sd.PortAudioError as e:
    print(f"❌ 播放失败。捕获到 PortAudio 错误: {e}")
    print("   请检查您的系统音频输出设备和 sounddevice 依赖（PortAudio）。")
except Exception as e:
    print(f"❌ 发生未知错误: {e}")