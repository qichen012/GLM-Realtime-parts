import soundfile as sf
import numpy as np
from scipy import signal
import os
import sys

# 原始文件路径 (您提供的路径)
INPUT_PATH = "glm-realtime-sdk/python/samples/input/give_me_a_joke.wav"
# 输出文件路径
OUTPUT_PATH = "joke_16k.wav"
# 目标采样率
TARGET_SAMPLE_RATE = 16000

def resample_wav(input_path, output_path, target_rate):
    """
    读取 WAV 文件，将其重采样到目标采样率，并保存。
    """
    if not os.path.exists(input_path):
        print(f"❌ 错误: 输入文件未找到: {input_path}")
        return

    try:
        # 1. 读取原始文件
        data, current_rate = sf.read(input_path, dtype='float32')
        print(f"✅ 成功读取文件: {input_path}")
        print(f"   原始采样率: {current_rate} Hz")
        print(f"   原始形状: {data.shape}")

        if current_rate == target_rate:
            print("✅ 采样率已经是 16000 Hz，无需重采样。")
            return

        # 2. 检查声道 (确保是单声道)
        if data.ndim > 1 and data.shape[1] > 1:
            print("⚠️ 警告: 文件为多声道。将其转换为单声道 (取平均)。")
            data = np.mean(data, axis=1)

        # 3. 计算重采样所需比率
        num = target_rate
        den = current_rate
        
        # 4. 执行重采样
        resampled_data = signal.resample_poly(data, num, den)

        # 5. 保存重采样后的文件 (单声道)
        sf.write(output_path, resampled_data, target_rate)
        
        print(f"\n🎉 成功重采样并保存到: {output_path}")
        print(f"   新的采样率: {target_rate} Hz")
        print(f"   请使用这个新文件进行测试。")

    except Exception as e:
        print(f"❌ 重采样过程中发生错误: {e}")

if __name__ == "__main__":
    resample_wav(INPUT_PATH, OUTPUT_PATH, TARGET_SAMPLE_RATE)