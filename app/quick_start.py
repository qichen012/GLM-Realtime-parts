#!/usr/bin/env python3
# coding: utf-8
"""
GLM-Realtime + Memobase 集成脚本

功能：
1. 实时语音对话（使用 GLM-Realtime API）
2. 自动接收并播放 AI 语音回复
3. 每轮对话自动保存到 Memobase 记忆库
4. 支持长时记忆和上下文检索
"""

import os
import json
import threading
from save_to_mem import (
    MemoBaseClient, 
    ChatBlob, 
    BlobType,
    ACCESS_TOKEN,
    MEMOBASE_URL,
    USER_ID,
    PROGRESS_FILE
)

# 导入 realtime.py 的必要模块（但不直接运行它）
import sys
import realtime

# --- 核心功能：保存最新一条记录 ---

def init_memobase():
    """初始化 Memobase 客户端"""
    try:
        client = MemoBaseClient(api_key=ACCESS_TOKEN, project_url=MEMOBASE_URL)
        
        if not client.ping():
            print("❌ Memobase 连接失败")
            return None, None, None
        
        print("   ✅ Memobase 连接成功")
        
        # 获取或创建用户
        try:
            user = client.get_user(USER_ID)
            print(f"   👤 用户: {USER_ID}")
        except Exception as e:
            if "404" in str(e).lower() or "not found" in str(e).lower():
                print(f"   💡 创建新用户: {USER_ID}")
                client.add_user(id=USER_ID, data={})
                user = client.get_user(USER_ID)
            else:
                raise e
        
        # 读取进度
        last_line = 0
        if os.path.exists(PROGRESS_FILE):
            with open(PROGRESS_FILE, "r") as f:
                content = f.read().strip()
                last_line = int(content) if content else 0
        
        print(f"   📊 历史对话: {last_line} 轮\n")
        return client, user, last_line
        
    except Exception as e:
        print(f"   ⚠️  Memobase 初始化失败: {e}")
        print("   ⚠️  将继续对话功能，但不保存到 Memobase\n")
        return None, None, 0

def save_latest_conversation(user, last_line):
    """保存最新的一条对话到 Memobase"""
    if not user:
        # Memobase 未启用，静默跳过
        return last_line
    
    jsonl_file = "data/save_data.jsonl"
    
    try:
        if not os.path.exists(jsonl_file):
            # 对话文件还不存在
            return last_line
            
        with open(jsonl_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        
        # 没有新记录
        if total_lines <= last_line:
            return last_line
        
        # 获取最新一条
        latest_line = lines[-1].strip()
        
        if not latest_line:
            return last_line
        
        data = json.loads(latest_line)
        messages = data.get("messages")
        
        if not messages or not isinstance(messages, list):
            return last_line
        
        # 保存到 Memobase
        blob = ChatBlob(messages=messages)
        user.insert(blob)
        user.flush(BlobType.chat, sync=True)
        
        # 更新进度
        last_line = total_lines
        with open(PROGRESS_FILE, "w") as f:
            f.write(str(last_line))
        
        # 统计对话内容
        user_msgs = sum(1 for m in messages if m.get("role") == "user")
        ai_msgs = sum(1 for m in messages if m.get("role") == "assistant")
        print(f"\n💾 [Memobase] 已保存 (👤 {user_msgs} 条用户 + 🤖 {ai_msgs} 条 AI)\n")
        return last_line
        
    except Exception as e:
        print(f"\n⚠️  [Memobase] 保存失败: {e}")
        return last_line

# --- 修改 realtime.py 的 on_message 函数 ---

def wrap_on_message(original_on_message, user, last_line_container):
    """包装原始的 on_message，在 response.done 时触发保存"""
    def wrapped_on_message(ws, message):
        # 先调用原始处理函数
        original_on_message(ws, message)
        
        # 检查是否是对话完成
        data = json.loads(message)
        if data.get("type") == "response.done":
            # 自动保存最新记录
            last_line_container[0] = save_latest_conversation(user, last_line_container[0])
    
    return wrapped_on_message

# --- 主程序 ---

if __name__ == "__main__":
    print("\n" + "="*60)
    print("    GLM-Realtime + Memobase Memory System")
    print("="*60)
    print("🎯 功能:")
    print("   • 实时语音对话（支持真实语音输出）")
    print("   • 自动保存对话到 Memobase 记忆库")
    print("   • 支持长时记忆和智能检索")
    print("="*60 + "\n")
    
    # 初始化 Memobase
    print("📚 初始化 Memobase 记忆系统...")
    client, user, last_line = init_memobase()
    
    # 用列表包装以便在闭包中修改
    last_line_container = [last_line]
    
    # 修改 realtime.py 的 on_message 函数
    original_on_message = realtime.on_message
    realtime.on_message = wrap_on_message(original_on_message, user, last_line_container)
    
    # 运行 realtime.py 的主程序
    print("🚀 启动实时语音对话系统...\n")
    
    try:
        # 执行 realtime.py 的主逻辑
        if not realtime.API_KEY:
            print("❌ 请先设置 ZHIPU_API_KEY 环境变量")
            sys.exit(1)

        # 音频设备检查
        print("="*50)
        print("🔊 音频设备检查")
        print("="*50)
        import sounddevice as sd
        import numpy as np
        try:
            print(f"输入设备: {sd.query_devices(kind='input')['name']}")
            print(f"输出设备: {sd.query_devices(kind='output')['name']}")
            
            print("\n🧪 测试音频播放...")
            test_tone = (np.sin(2 * np.pi * 440 * np.arange(realtime.SAMPLE_RATE) / realtime.SAMPLE_RATE) * 5000).astype(np.int16)
            sd.play(test_tone, samplerate=realtime.SAMPLE_RATE, blocking=True)
            print("✅ 如果听到提示音，说明音频输出正常")
            import time
            time.sleep(0.5)
        except Exception as e:
            print(f"⚠️  音频设备警告: {e}")
        print("="*50 + "\n")

        # 生成 JWT Token
        try:
            AUTH_TOKEN = realtime.generate_jwt_token(realtime.API_KEY)
            print("✅ JWT Token 生成成功")
        except Exception as e:
            print(f"❌ JWT Token 生成失败: {e}")
            sys.exit(1)

        print("\n" + "="*50)
        print("💡 使用说明:")
        print("   1. 对着麦克风说话")
        print("   2. 停顿 1.5 秒等待 AI 回复")
        print("   3. AI 会用语音回复（真实语音输出）")
        print("   4. 每轮对话自动保存到 Memobase")
        print("   5. 按 Ctrl+C 退出")
        print("="*50 + "\n")

        import websocket
        websocket.enableTrace(False)
        
        ws = websocket.WebSocketApp(
            realtime.WS_URL,
            header=[f"Authorization: Bearer {AUTH_TOKEN}"],
            on_message=realtime.on_message,  # 使用修改后的版本
            on_open=realtime.on_open,
            on_close=realtime.on_close,
            on_error=realtime.on_error
        )
        
        ws_thread = threading.Thread(target=ws.run_forever, daemon=True)
        ws_thread.start()

        print("⏳ 等待连接...")
        realtime.session_ready.wait(timeout=10)

        if not realtime.session_ready.is_set():
            print("❌ 会话设置超时")
            sys.exit(1)

        print("\n" + "="*50)
        print("✅ 系统准备就绪！")
        print("="*50)
        if user:
            print("📝 对话将自动保存到 Memobase 记忆库")
        print("🎤 请开始说话...\n")
        
        with sd.InputStream(channels=1, samplerate=realtime.SAMPLE_RATE, 
                           dtype='int16', callback=realtime.callback):
            ws_thread.join()

    except KeyboardInterrupt:
        print("\n\n👋 用户中断，正在退出...")
    except Exception as e:
        print(f"\n❌ 运行错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        realtime.stop_event.set()
        if 'ws' in locals():
            threading.Thread(target=ws.close).start()
        sd.stop()
        
        # 显示统计信息
        if user and last_line_container:
            print(f"\n📊 本次会话统计:")
            print(f"   总对话轮数: {last_line_container[0]} 轮")
            print(f"   已同步到 Memobase 记忆库")
        
        print("\n✅ 程序已安全退出。再见！\n")