# Memobase 记忆集成指南

## 🎯 功能概述

本系统已集成 **Memobase 长期记忆功能**，让 GLM-Realtime 和 Claude Code Agent 能够：
- 记住用户的历史对话
- 了解用户的偏好和习惯
- 提供个性化服务
- 在多次对话间保持上下文连续性

## 📐 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        用户语音输入                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│              GLM-Realtime API                                │
│              • 语音识别                                       │
│              • 意图理解                                       │
│              • 🧠 加载用户记忆到 Prompt                       │
│              • Function Call 识别                            │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ├──────────── Function Call ────────────┐
                       │                                        │
┌──────────────────────▼──────────────────────┐                │
│        Claude Code Agent                    │                │
│        • 🧠 加载用户记忆到 Prompt            │                │
│        • 调用 Sub Agent & Skill             │                │
└──────────────────────┬──────────────────────┘                │
                       │                                        │
                       └────────────────────────────────────────┤
                                                                │
                       ┌────────────────────────────────────────▼─┐
                       │          Memobase 服务                   │
                       │          • 存储用户对话                   │
                       │          • 提取用户画像                   │
                       │          • 构建记忆上下文                 │
                       └──────────────────────────────────────────┘
```

## 📁 新增文件说明

### `memory_manager.py` - 记忆管理器

核心模块，负责从 Memobase 获取和格式化用户记忆。

**主要功能：**
- 连接 Memobase 服务
- 获取用户的完整记忆上下文
- 为 GLM 和 Claude Code 格式化记忆
- 提供用户画像摘要

**主要函数：**
```python
# 获取用户记忆
get_user_memory(user_id, max_token_size=1000) -> str

# 为 GLM 格式化记忆
format_memory_for_glm(user_id) -> str

# 为 Claude Code 格式化记忆
format_memory_for_claude(user_id) -> str
```

### `test_memory_integration.py` - 测试脚本

用于测试记忆集成功能是否正常工作。

**运行测试：**
```bash
python test_memory_integration.py
```

## 🔧 配置说明

### 1. Memobase 服务配置

在 `memory_manager.py` 中配置：

```python
# --- 配置 ---
ACCESS_TOKEN = os.getenv("MEMOBASE_ACCESS_TOKEN", "secret")
MEMOBASE_URL = os.getenv("MEMOBASE_URL", "http://localhost:8019/")
DEFAULT_USER_ID = "3f6c7b1a-9d2e-4f8a-b5c3-e1f2a3b4c5d6"
# --- 配置结束 ---
```

**或使用环境变量：**
```bash
export MEMOBASE_ACCESS_TOKEN="your_token"
export MEMOBASE_URL="http://localhost:8019/"
```

### 2. 用户 ID 配置

在 `realtime_with_agent.py` 中可以修改当前用户 ID：

```python
# 全局用户 ID（可以根据实际情况修改）
CURRENT_USER_ID = "your-user-id-here"
```

### 3. 启用/禁用记忆功能

在 `claude_code_client.py` 中：

```python
claude_code_client = ClaudeCodeClient(
    base_url="http://localhost:8000",
    api_key=None,
    user_id=DEFAULT_USER_ID,
    enable_memory=True  # 👈 设置为 False 可禁用记忆
)
```

## 🚀 使用流程

### 步骤 1: 启动 Memobase 服务

确保 Memobase 服务正在运行：

```bash
# 方式 1: 如果使用 Docker
cd memobase/src/server
docker-compose up -d

# 方式 2: 如果本地运行
# 参考 memobase 文档启动服务
```

验证服务：
```bash
curl http://localhost:8019/healthcheck
```

### 步骤 2: 导入历史对话（如果有）

如果你已有历史对话数据：

```bash
python save_to_mem.py
```

这会将 `data/save_data.jsonl` 中的对话导入到 Memobase。

### 步骤 3: 测试记忆集成

```bash
python test_memory_integration.py
```

应该看到类似输出：
```
🧪 =========================================================
   Memobase 记忆集成测试
============================================================

📡 测试 1: Memobase 连接
============================================================
✅ Memobase 连接成功！

🧠 测试 2: 获取用户记忆
============================================================
🧠 成功获取用户记忆 (User ID: 3f6c7b1a...)
✅ 成功获取用户记忆 (1234 字符)

...

📊 测试总结
============================================================
  ✅ 通过 - Memobase 连接
  ✅ 通过 - 获取用户记忆
  ✅ 通过 - GLM 格式化
  ✅ 通过 - Claude 格式化
  ✅ 通过 - 用户画像

总计: 5/5 测试通过

🎉 所有测试通过！记忆集成功能正常！
```

### 步骤 4: 运行带记忆的语音助手

```bash
python realtime_with_agent.py
```

启动时会看到：
```
🔌 WebSocket connected, configuring session with Agent support...
🧠 正在加载用户记忆...
   ✅ 用户记忆已加载
📤 Session config:
   - Tools: 3 个
     • plan_trip: 规划旅行行程...
     • book_ticket: 预订机票、火车票...
     • book_hotel: 预订酒店...
   - 用户记忆: 已加载

🎤 Ready! Start speaking...
```

## 💡 使用示例

### 示例 1: 个性化行程规划

**场景：** 用户之前提到过喜欢历史文化

**用户说：**
> "帮我规划一个北京3天的旅行"

**系统行为：**
1. GLM 从记忆中知道用户喜欢历史文化
2. 调用 Claude Code Agent 时会传递这个偏好
3. 返回的行程会包含更多历史文化景点（故宫、长城等）

**输出：**
> "根据您对历史文化的兴趣，我为您规划了3天的北京行程。第一天我们去故宫和天坛..."

### 示例 2: 记住用户信息

**第一次对话：**
- 用户："我是北京邮电大学的学生"
- AI："好的，了解了！"
- （信息保存到 Memobase）

**第二天对话：**
- 用户："推荐一些学校附近的景点"
- AI："作为北邮的学生，您可以去..."（自然运用记忆）

### 示例 3: 连续性对话

**场景：** 跨对话的连续性

**昨天：**
- 用户："我想买一部新手机"
- AI："好的，有什么预算吗？"

**今天：**
- 用户："我昨天想买什么来着？"
- AI："您昨天提到想买一部新手机"

## 🔍 记忆内容示例

用户记忆会以结构化的方式存储和提取：

```markdown
# 📚 用户记忆

## User Current Profile:
- basic_info::phone: User wants to buy a new phone [mention 2025/11/26]
- basic_info::location: User is from Beijing [mention 2025/11/19]
- life_circumstances::education: User is a student at Beijing University 
  of Posts and Telecommunications [mention 2025/11/19]
- interest::video_game: User is playing "Horizon" [mention 2025/11/19]
- personal_narrative::emotional_states: User expressed feeling happy 
  [mention 2025/11/27]

## Past Events:
- User wants to buy a new phone. [mention 2025/11/26] // schedule
- User greeted in Chinese. [mention 2025/11/26] // event
- User is interested in fast food brands, specifically KFC and McDonald's. 
  [mention 2025/11/19] // info
...
```

## 🎨 记忆如何影响对话

### GLM-Realtime 侧

记忆被添加到 session 的 `instructions` 字段：

```python
system_instructions = """你是一个智能旅行助手，能帮用户规划行程、订票、订酒店。

请根据用户的历史记忆提供个性化、贴心的服务。
如果用户的记忆中有相关信息（如偏好、习惯、历史计划等），请自然地运用这些信息。
不要刻意提及"我看到你的记忆"，而是自然地体现在服务中。

# 📚 用户记忆
[用户的完整记忆内容]
"""
```

### Claude Code Agent 侧

记忆被添加到任务描述中：

```python
enhanced_task = f"""帮我预订北京的酒店，入住时间2024-01-05到2024-01-08，1间房，1人

# 📚 用户记忆
[用户的完整记忆内容]

请根据以上用户记忆提供个性化服务。"""
```

## 🐛 常见问题

### Q1: 记忆未加载？

**检查：**
1. Memobase 服务是否运行：`curl http://localhost:8019/healthcheck`
2. 用户 ID 是否正确
3. 用户是否有记忆数据：`python check_user.py`

**解决：**
```bash
# 查看日志
python test_memory_integration.py

# 如果用户不存在，先导入数据
python save_to_mem.py
```

### Q2: 记忆太长导致超时？

**解决：** 调整 `max_token_size` 参数

```python
# 在 memory_manager.py 中
context_str = user.context(max_token_size=500)  # 减小 token 数量
```

### Q3: 不想使用记忆功能？

**临时禁用：**
```python
# 在 claude_code_client.py 中
claude_code_client = ClaudeCodeClient(
    base_url="http://localhost:8000",
    enable_memory=False  # 👈 禁用记忆
)
```

### Q4: 如何清空用户记忆？

**方法 1:** 通过 Memobase API
```python
from memobase.src.client.memobase.core.entry import MemoBaseClient

client = MemoBaseClient(api_key="secret", project_url="http://localhost:8019/")
# 删除用户（需要参考 Memobase 文档）
```

**方法 2:** 使用新的用户 ID
```python
# 在 realtime_with_agent.py 中
CURRENT_USER_ID = "new-user-id-here"
```

## 📊 性能考虑

### 记忆加载时间

- **首次加载:** ~200-500ms（取决于记忆量）
- **缓存后:** <50ms
- **推荐:** 在 session 初始化时加载一次，不要每次对话都重新加载

### Token 消耗

- 用户记忆会占用额外的 token
- 建议设置合理的 `max_token_size`（默认 1000）
- 对于复杂任务可以增加，简单任务可以减少

### 优化建议

```python
# 方案 1: 根据任务类型动态调整
if task_type == "simple_query":
    memory = get_user_memory(user_id, max_token_size=500)
else:
    memory = get_user_memory(user_id, max_token_size=1500)

# 方案 2: 只使用用户画像（不包含事件）
summary = memory_manager.get_user_profile_summary(user_id)
```

## 🔄 持续记忆更新

### 自动更新

每次对话后，新的信息会自动保存到 Memobase：

1. 用户说话 → GLM 处理
2. 对话内容发送到 Memobase
3. Memobase 提取新的用户信息
4. 下次对话时自动加载最新记忆

### 手动更新

如果需要批量导入新的对话：

```bash
# 追加新对话到 save_data.jsonl
# 然后运行（支持增量更新）
python save_to_mem.py
```

## 📝 最佳实践

### 1. 记忆内容的自然运用

❌ **不好的做法：**
> "我看到你的记忆中说你喜欢历史，所以..."

✅ **好的做法：**
> "根据您对历史文化的兴趣，我推荐..."

### 2. 隐私保护

- 敏感信息要加密存储
- 定期清理过期记忆
- 遵守数据保护法规

### 3. 记忆粒度

- 太细：导致记忆冗余，消耗过多 token
- 太粗：丢失重要细节
- 推荐：重要信息详细记录，琐碎信息忽略

### 4. 记忆验证

定期检查记忆的准确性：
```bash
python check_user.py
```

## 🎯 下一步计划

- [ ] 支持多用户会话管理
- [ ] 添加记忆重要性评分
- [ ] 实现记忆遗忘机制（自动清理旧记忆）
- [ ] 支持记忆的手动编辑
- [ ] 添加记忆可视化界面

## 📚 相关文档

- [Memobase 官方文档](https://github.com/memobase/memobase)
- [Agent 集成指南](./AGENT_INTEGRATION.md)
- [快速开始](./QUICK_START_AGENT.md)

---

**祝使用愉快！🎉**

有问题欢迎反馈！

