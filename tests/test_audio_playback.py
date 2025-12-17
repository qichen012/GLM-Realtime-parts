#!/usr/bin/env python3
"""
简单的音频播放测试
验证 sounddevice 是否能正常播放
"""

import sounddevice as sd
import numpy as np

print("🔊 音频播放测试")
print("="*50)

# 测试1：播放440Hz测试音
print("\n测试 1: 播放 440Hz 测试音（1秒）")
SAMPLE_RATE = 16000
test_tone = (np.sin(2 * np.pi * 440 * np.arange(SAMPLE_RATE) / SAMPLE_RATE) * 5000).astype(np.int16)

print(f"   样本数: {len(test_tone)}")
print(f"   采样率: {SAMPLE_RATE}Hz")
print(f"   播放中...")

sd.play(test_tone, samplerate=SAMPLE_RATE, blocking=True)
print("   ✅ 测试音播放完成！")

# 测试2：1.5倍速播放
print("\n测试 2: 1.5倍速播放同样的测试音")
SPEED_MULTIPLIER = 1.5
playback_rate = int(SAMPLE_RATE * SPEED_MULTIPLIER)
adjusted_duration = len(test_tone) / playback_rate

print(f"   播放速度: {SPEED_MULTIPLIER}x")
print(f"   播放采样率: {playback_rate}Hz")
print(f"   时长: {adjusted_duration:.2f}秒")
print(f"   播放中...")

sd.play(test_tone, samplerate=playback_rate, blocking=True)
print("   ✅ 加速播放完成！")

print("\n" + "="*50)
print("✅ 所有测试完成！")
print("\n如果你听到了两次\"哔\"声，说明音频播放正常。")
print("第二次应该比第一次快（高音）。")

