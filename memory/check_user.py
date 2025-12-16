#!/usr/bin/env python3
# coding: utf-8

import os
import json
import sys

# 添加 memobase 到 Python 路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMOBASE_PATH = os.path.join(PROJECT_ROOT, 'memobase')
if MEMOBASE_PATH not in sys.path:
    sys.path.insert(0, MEMOBASE_PATH)

from src.client.memobase.core.entry import MemoBaseClient

# --- 配置 ---
ACCESS_TOKEN = "secret"
MEMOBASE_URL = os.getenv("MEMOBASE_URL", "http://localhost:8019/")
# ⚠️ 请确保这里是你刚才导入数据时用的那个 UUID
USER_ID = "3f6c7b1a-9d2e-4f8a-b5c3-e1f2a3b4c5d6" 
# --- 配置结束 ---

def check_user():
    print(f"--- 🔍 开始查询用户数据: {USER_ID} ---")
    
    try:
        client = MemoBaseClient(api_key=ACCESS_TOKEN, project_url=MEMOBASE_URL)
        # 获取用户对象
        user = client.get_user(USER_ID)
        print("✅ 成功连接到用户\n")
    except Exception as e:
        print(f"❌ 无法获取用户，请检查 ID 是否正确: {e}")
        return

    # -------------------------------------------------------
    # 1. 查看用户画像 (Profile)
    # 这是 Memobase 从对话中提取出来的“知识点”或“长期记忆”
    # -------------------------------------------------------
    print(f"=== 👤 User Profile (用户画像/长期记忆) ===")
    try:
        profiles = user.profile()
        if not profiles:
            print("  (暂无画像数据)")
        else:
            for i, p in enumerate(profiles):
                # p 是 UserProfile 对象
                print(f"  [{i+1}] 🏷️  {p.topic} -> {p.sub_topic}")
                print(f"      📝 {p.content}")
    except Exception as e:
        print(f"  ⚠️ 获取画像失败: {e}")
    print("\n")

    # -------------------------------------------------------
    # 2. 查看用户事件 (Event) - 已修复报错问题
    # -------------------------------------------------------
    print(f"=== 📅 User Events (最近事件/记忆流) ===")
    try:
        # topk=30 查看最近 30 条
        events = user.event(topk=30)
        if not events:
            print("  (暂无事件数据)")
        else:
            for i, e in enumerate(events):
                print(f"  [{i+1}] ⏰ {e.created_at} | ID: {e.id}")
                
                # --- 🛡️ 容错代码开始 ---
                # 尝试从多个常见字段名中获取文本，如果都没有，则打印对象本身
                # getattr(对象, '属性名', 默认值)
                event_content = getattr(e, 'content', None) 
                if event_content is None:
                    event_content = getattr(e, 'description', None)
                if event_content is None:
                    event_content = getattr(e, 'summary', None)
                if event_content is None:
                    # 如果以上字段都没有，直接把对象转字符串打印出来，方便调试
                    event_content = str(e)
                # --- 🛡️ 容错代码结束 ---

                print(f"      📄 {event_content}")
                
    except Exception as e:
        print(f"  ⚠️ 获取事件失败: {e}")
    print("\n")

    # -------------------------------------------------------
    # 3. 查看生成的上下文 (Context)
    # -------------------------------------------------------
    print(f"=== 🧠 Context (构建的 LLM 上下文) ===")
    try:
        # 模拟一个新的对话场景，看看 Memobase 会检索出什么记忆
        context_str = user.context(max_token_size=1000)
        print("--------------------------------------------------")
        print(context_str)
        print("--------------------------------------------------")
    except Exception as e:
        print(f"  ⚠️ 获取上下文失败: {e}")

if __name__ == "__main__":
    check_user()