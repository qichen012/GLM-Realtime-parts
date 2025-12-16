#!/usr/bin/env python3
# coding: utf-8
"""
将 JSONL（每行一个 JSON，包含 "messages": [...]）批量导入 Memobase 的脚本。
【新增功能】支持断点续传/增量更新：会自动跳过已处理的行。
"""

import os
import json
import sys
from requests.exceptions import ConnectionError

# 添加 memobase 到 Python 路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMOBASE_PATH = os.path.join(PROJECT_ROOT, 'memobase')
if MEMOBASE_PATH not in sys.path:
    sys.path.insert(0, MEMOBASE_PATH)

from src.client.memobase.core.entry import MemoBaseClient
from src.client.memobase.core.blob import ChatBlob, BlobType

# --- 配置（请按需修改） ---

# 获取项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ACCESS_TOKEN = "secret"
MEMOBASE_URL = os.getenv("MEMOBASE_URL", "http://localhost:8019/")
JSONL_FILE_PATH = os.path.join(PROJECT_ROOT, "data/save_data.jsonl")
USER_ID = "3f6c7b1a-9d2e-4f8a-b5c3-e1f2a3b4c5d6"

# 新增：进度记录文件，默认保存在同目录下，文件名加 .progress 后缀
PROGRESS_FILE = JSONL_FILE_PATH + ".progress"

# --- 配置结束 ---

def get_last_processed_line():
    """读取上次处理到的行号，如果文件不存在则返回 0"""
    if not os.path.exists(PROGRESS_FILE):
        return 0
    try:
        with open(PROGRESS_FILE, "r") as f:
            content = f.read().strip()
            return int(content) if content else 0
    except Exception:
        return 0

def save_progress(line_no):
    """保存当前处理完成的行号"""
    try:
        with open(PROGRESS_FILE, "w") as f:
            f.write(str(line_no))
    except Exception as e:
        print(f"⚠️ 警告：无法保存进度到 {PROGRESS_FILE}: {e}")

def import_logs_to_memobase():
    print(f"--- 🚀 开始导入对话到 Memobase (增量模式) ---")
    print(f"Memobase 服务器: {MEMOBASE_URL}")
    print(f"日志文件: {JSONL_FILE_PATH}")
    print(f"用户 ID: {USER_ID}")

    # 1. 创建客户端
    try:
        client = MemoBaseClient(api_key=ACCESS_TOKEN, project_url=MEMOBASE_URL)
    except Exception as e:
        print(f"❌ 创建 MemoBaseClient 失败: {e}")
        sys.exit(1)

    # 2. ping / health 检查
    try:
        ok = client.ping()
        if not ok:
            print("❌ Healthcheck 返回失败，请检查服务或 API_KEY。")
            sys.exit(1)
        print("✅ Memobase healthcheck 通过")
    except ConnectionError:
        print(f"❌ 无法连接到 Memobase: {MEMOBASE_URL}")
        print("   请确认服务已启动并且地址/端口正确。")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Healthcheck 时发生错误: {e}")
        sys.exit(1)

    def get_or_create_user_safe(client, user_id):
        try:
            # print(f"🔍 尝试获取用户: {user_id}") # 可以注释掉减少刷屏
            return client.get_user(user_id)
        except Exception as e:
            error_msg = str(e).lower()
            if "404" in error_msg or "not found" in error_msg:
                print(f"💡 用户不存在，正在创建新用户: {user_id} ...")
                try:
                    client.add_user(id=user_id, data={})
                    print(f"✅ 用户创建成功，重新获取对象...")
                    return client.get_user(user_id)
                except Exception as create_e:
                    print(f"❌ 创建用户失败: {create_e}")
                    raise create_e
            else:
                print(f"🧨 获取用户时发生其他异常: {e}")
                raise e

    # 3. 获取或创建用户
    try:
        user = get_or_create_user_safe(client, USER_ID)
        print(f"✅ 成功获取或创建用户: {USER_ID}\n")
    except Exception as e:
        print(f"❌ 无法获取或创建用户: {e}")
        sys.exit(1)

    # 4. 读取进度与文件
    last_line = get_last_processed_line()
    if last_line > 0:
        print(f"📂 发现历史进度：上次已处理到第 {last_line} 行，本次将跳过这些数据。")
    else:
        print(f"📂 未发现历史进度，将从第 1 行开始处理。")

    inserted_count = 0
    skipped_count = 0
    ignored_count = 0 # 记录因为已处理而被跳过的数量

    try:
        with open(JSONL_FILE_PATH, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                line_no = i + 1
                
                # --- 新增逻辑：跳过已处理的行 ---
                if line_no <= last_line:
                    ignored_count += 1
                    continue
                # -----------------------------

                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    print(f"⚠️  第 {line_no} 行 JSON 解析失败，跳过。")
                    skipped_count += 1
                    # 解析失败也要记录进度，防止下次卡死
                    save_progress(line_no)
                    continue

                messages = data.get("messages")
                if not messages or not isinstance(messages, list):
                    print(f"⚠️  第 {line_no} 行没有 'messages' 列表或格式不对，跳过。")
                    skipped_count += 1
                    save_progress(line_no)
                    continue

                try:
                    blob = ChatBlob(messages=messages)
                    user.insert(blob) 
                    user.flush(BlobType.chat, sync=True)

                    inserted_count += 1
                    print(f"  -> 第 {line_no} 行导入完成 (含 {len(messages)} 条消息)。")
                    
                    # --- 新增逻辑：成功后保存进度 ---
                    save_progress(line_no)
                    # ----------------------------

                except Exception as e_insert:
                    print(f"⚠️  第 {line_no} 行插入/处理时出错: {e_insert}")
                    skipped_count += 1
                    # 出错时我们可以选择不保存进度，这样下次还会重试这一行
                    # 如果你希望出错也跳过，可以在这里加 save_progress(line_no)

    except FileNotFoundError:
        print(f"❌ 错误：找不到日志文件：{JSONL_FILE_PATH}")
        sys.exit(1)

    print("\n--- 导入完成 ---")
    print(f"⏭️  跳过旧数据: {ignored_count} 条")
    print(f"🎉 本次成功插入: {inserted_count} 条")
    print(f"🤔 本次错误/跳过: {skipped_count} 条")

if __name__ == "__main__":
    import_logs_to_memobase()