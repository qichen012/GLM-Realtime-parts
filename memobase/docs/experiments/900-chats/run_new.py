import json
from typing import cast
from rich import print as pprint
from rich.progress import track
import tiktoken
from time import time, sleep
from memobase import MemoBaseClient, ChatBlob

# --- 配置 ---
PROJECT_URL = "http://localhost:8019"
PROJECT_TOKEN = "secret"
FILE_PATH = "./sharegpt_test_7uOhOjo.json"

# --- 准备工作 ---
ENCODER = tiktoken.encoding_for_model("gpt-4o")
with open(FILE_PATH) as f:
    data = json.load(f)

# --- 数据处理 ---
messages = [
    {"role": "user" if d["from"] == "human" else "assistant", "content": d["value"]}
    for d in data["conversations"]
]

blobs = [
    ChatBlob(
        messages=messages[i : i + 2],
    )
    for i in range(0, len(messages), 2)
]

print("总共有", len(blobs), "个数据块")
print(
    "原始消息的总 Tokens 数为",
    len(ENCODER.encode("\n".join([m["content"] for m in messages]))),
)

# --- MemoBase 客户端初始化 ---
client = MemoBaseClient(
    project_url=PROJECT_URL,
    api_key=PROJECT_TOKEN,
)

assert client.ping()
print("成功连接到 MemoBase 服务器。")

# --- 用户和数据导入 ---
uid = client.add_user()
print("新用户 ID 是:", uid)
u = client.get_user(uid)

print("开始导入消息...")
start = time()
for blob in track(blobs):
    u.insert(blob, sync=True)
    sleep(1) # 添加短暂延迟，避免请求过多导致服务器过载
u.flush(sync=True)

print("总耗时 (秒):", time() - start)

# --- 等待处理完成 ---
print("等待 MemoBase 服务器处理数据...")
while True:
    processing_count = len(u.buffer("chat", "processing"))
    if processing_count > 0:
        print(f"还有 {processing_count} 个聊天记录正在处理中...")
        sleep(1)
    else:
        break

print("所有消息已处理完毕。")

# --- 获取并显示结果 ---
print("\n--- 用户画像总结 (前10条) ---")
pprint(u.profile()[:10])

print("\n--- 所有提示词 ---")
prompts = [m.describe for m in u.profile()]
print("* " + "\n* ".join(sorted(prompts)))