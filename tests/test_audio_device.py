#!/usr/bin/env python3
"""
音频设备诊断工具
用于检测蓝牙耳机音频输出问题
"""

import sounddevice as sd
import numpy as np
import time

print("="*60)
print("🔊 音频设备诊断工具")
print("="*60)

# 1. 列出所有设备
print("\n📋 1. 所有音频设备：")
print("-"*60)
devices = sd.query_devices()
for i, device in enumerate(devices):
    marker = " 👈" if device['name'] == 'soundcore Q20i' else ""
    print(f"[{i}] {device['name']}{marker}")
    print(f"    输入: {device['max_input_channels']} 通道, 输出: {device['max_output_channels']} 通道")

# 2. 当前默认设备
print("\n📍 2. 当前默认设备：")
print("-"*60)
try:
    input_device = sd.query_devices(kind='input')
    output_device = sd.query_devices(kind='output')
    print(f"输入: {input_device['name']}")
    print(f"输出: {output_device['name']}")
except Exception as e:
    print(f"❌ 错误: {e}")

# 3. 测试音频播放（不同音量）
print("\n🧪 3. 测试音频播放：")
print("-"*60)
SAMPLE_RATE = 16000

test_cases = [
    ("低音量", 1000),
    ("中音量", 5000),
    ("高音量", 15000),
    ("超高音量", 25000),
]

for name, amplitude in test_cases:
    print(f"\n🔊 测试 {name} (振幅: {amplitude})")
    # 生成 440Hz 测试音（1秒）
    test_tone = (np.sin(2 * np.pi * 440 * np.arange(SAMPLE_RATE) / SAMPLE_RATE) * amplitude).astype(np.int16)
    
    print(f"   数据范围: min={test_tone.min()}, max={test_tone.max()}")
    print(f"   ▶️  播放中...")
    
    try:
        sd.play(test_tone, samplerate=SAMPLE_RATE, blocking=True)
        print(f"   ✅ 播放完成")
        
        # 询问用户是否听到
        response = input(f"   🎧 你听到声音了吗？(y/n): ").strip().lower()
        if response == 'y':
            print(f"   ✅ 成功！{name} 可以听到")
            break
        else:
            print(f"   ❌ 听不到，继续测试更高音量...")
    except Exception as e:
        print(f"   ❌ 播放错误: {e}")
    
    time.sleep(0.5)

# 4. 测试指定设备
print("\n🎯 4. 测试指定设备播放：")
print("-"*60)

# 查找 soundcore Q20i
q20i_device = None
for i, device in enumerate(devices):
    if 'soundcore Q20i' in device['name'] and device['max_output_channels'] > 0:
        q20i_device = i
        break

if q20i_device is not None:
    print(f"找到设备: [ID:{q20i_device}] soundcore Q20i")
    print("播放测试音（超高音量）...")
    
    test_tone = (np.sin(2 * np.pi * 440 * np.arange(SAMPLE_RATE) / SAMPLE_RATE) * 25000).astype(np.int16)
    
    try:
        sd.play(test_tone, samplerate=SAMPLE_RATE, device=q20i_device, blocking=True)
        print("✅ 播放完成")
        
        response = input("🎧 你听到声音了吗？(y/n): ").strip().lower()
        if response == 'y':
            print("✅ soundcore Q20i 工作正常！")
        else:
            print("❌ soundcore Q20i 可能有问题")
            print("💡 建议：")
            print("   1. 检查蓝牙连接")
            print("   2. 检查耳机是否在播放模式（不是通话模式）")
            print("   3. 检查耳机音量")
            print("   4. 尝试断开重连蓝牙")
    except Exception as e:
        print(f"❌ 播放错误: {e}")
else:
    print("❌ 未找到 soundcore Q20i 设备")

# 5. 系统建议
print("\n" + "="*60)
print("💡 诊断建议：")
print("="*60)
print("如果听不到声音，可能的原因：")
print("1. 🔇 系统音量被静音")
print("2. 🎧 蓝牙耳机未正确连接")
print("3. 🔊 蓝牙耳机音量为0")
print("4. 📱 蓝牙耳机在通话模式（需要切换到音乐模式）")
print("5. 🔌 音频输出到了错误的设备")
print("\n推荐解决方案：")
print("• 打开系统声音设置，确认输出设备是 soundcore Q20i")
print("• 调高系统音量和耳机音量")
print("• 断开并重新连接蓝牙耳机")
print("• 尝试使用电脑内置扬声器测试")
print("="*60)

