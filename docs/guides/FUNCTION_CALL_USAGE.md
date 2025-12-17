# 🎯 Function Call 真实使用指南

本指南教你如何在实际对话中使用 Function Call 功能。

## 📋 前置准备

### 1️⃣ 确保 Claude Code 服务运行

Function Call 需要调用 Claude Code Agent，所以首先要启动 Claude Code 服务：

```bash
# 检查 Claude Code 是否运行
curl http://localhost:8000/health

# 如果返回 200 OK，说明服务正常
# 如果连接失败，需要先启动 Claude Code 服务
```

**如果服务未运行，启动它：**
```bash
# 根据你的 Claude Code 项目位置
cd /path/to/claude-code-project
./start.sh  # 或者其他启动命令
```

---

### 2️⃣ 配置 Agent 连接信息

编辑 `agents/claude_code_client.py`，确认配置正确：

```python
# 在文件末尾，检查这个配置
claude_code_client = ClaudeCodeClient(
    base_url="http://localhost:8000",  # 👈 确保这是你的 Agent 服务地址
    api_key=None,  # 👈 如果需要 API Key，在这里配置
    user_id=DEFAULT_USER_ID,
    enable_memory=True
)
```

**常见配置：**
- 本地开发：`http://localhost:8000`
- Docker：`http://host.docker.internal:8000`
- 远程服务：`http://your-server-ip:8000`

---

### 3️⃣ 配置环境变量

确保你的 `.env` 文件包含必要的配置：

```bash
# GLM API Key（必需）
ZHIPU_API_KEY=your-api-key-here

# Memobase 配置（可选，用于记忆功能）
MEMOBASE_URL=http://localhost:8019/
MEMOBASE_ACCESS_TOKEN=secret

# Claude Code 配置（可选）
CLAUDE_CODE_URL=http://localhost:8000
CLAUDE_CODE_API_KEY=your-api-key-here  # 如果需要
```

---

### 4️⃣ 测试 Agent 连接

运行测试脚本验证连接：

```bash
cd tests
python test_agent_integration.py
```

**预期输出：**
```
✅ Claude Code 服务连接成功
✅ Agent 可以正常响应
```

**如果失败：**
- 检查 `base_url` 是否正确
- 检查 Claude Code 服务是否运行
- 检查防火墙设置

---

## 🎤 使用 Function Call

### 启动带 Agent 的语音助手

```bash
cd /Users/xwj/Desktop/gpt-realtime-demo
python run_with_agent.py
```

你会看到：

```
======================================================================
    GLM-Realtime + Claude Code Travel Assistant
======================================================================
🤖 功能:
   • 语音对话 + 实时记忆同步
   • 行程规划（调用 Claude Code Agent）
   • 订票服务（调用 Claude Code Agent + Skill）
   • 订酒店（调用 Claude Code Agent + Skill）

⌨️  快捷键:
   • 空格键 = 完成说话，立即请求 AI 回复
   • Enter键 = 打断 AI 回复

🎤 Ready! Start speaking...
```

---

## 💬 对话示例

### 示例 1: 规划旅行

**你说：**
> "帮我规划一个去北京的旅行，3天，我喜欢文化景点"

**系统流程：**
```
1. 🎤 语音识别: "帮我规划一个去北京的旅行..."
2. 🤖 GLM 判断: 需要调用 plan_trip 函数
3. 📤 发送 Function Call:
   {
     "name": "plan_trip",
     "arguments": {
       "destination": "北京",
       "start_date": "2024-01-15",
       "end_date": "2024-01-18",
       "preferences": "文化景点"
     }
   }
4. 🔄 调用 Claude Code Agent
5. ✅ Agent 返回行程规划
6. 🗣️ GLM 用语音回复: "好的！我为你规划了一个精彩的北京3天游..."
```

**你会在控制台看到：**
```
👤 用户输入: 帮我规划一个去北京的旅行，3天，我喜欢文化景点

🔔 收到 Function Call: plan_trip
   参数: {"destination": "北京", "start_date": "2024-01-15", ...}

🤖 正在调用 Claude Code Agent...
📋 调用行程规划 Agent: 为我规划一次从2024-01-15到2024-01-18去北京的旅行
   ✅ 执行完成
   结果: {
     "success": true,
     "itinerary": [
       "Day 1: 天安门广场、故宫博物院",
       "Day 2: 八达岭长城、明十三陵",
       "Day 3: 颐和园、圆明园"
     ],
     "summary": "北京3天文化深度游"
   }
   📤 结果已发送回 GLM
   📤 请求 GLM 生成语音回复

🤖 AI 回复文字: 好的！我为你规划了一个精彩的北京3天文化之旅...
🔊 播放音频...
```

---

### 示例 2: 订票

**你说：**
> "我要订一张明天从北京到上海的高铁票"

**系统流程：**
```
1. 🎤 语音识别
2. 🤖 GLM 调用: book_ticket
3. 🔄 调用 Claude Code Agent
4. ✅ 返回订票结果
5. 🗣️ 语音回复: "已为您查询到G101次列车..."
```

**控制台输出：**
```
🔔 收到 Function Call: book_ticket
🎫 调用订票 Agent + Skill: 帮我预订2024-01-20从北京到上海的火车票，1人
   ✅ 执行完成
   结果: {
     "success": true,
     "tickets": [...],
     "booking_reference": "TK-20240120-001"
   }
```

---

### 示例 3: 订酒店

**你说：**
> "帮我订一个上海的酒店，入住3晚"

**系统流程类似：**
```
book_hotel → Claude Code Agent → 返回酒店列表 → 语音播报
```

---

## 🔍 如何确认 Function Call 被触发

### 方法 1: 查看控制台日志

当 Function Call 被触发时，你会看到：

```
🔔 收到 Function Call: [函数名]
   参数: {...}
🤖 正在调用 Claude Code Agent...
```

### 方法 2: 使用详细日志版本

运行带详细日志的版本：

```bash
python run_with_agent_show_all_details.py
```

所有消息都会记录到 `result.txt` 文件中。

---

## ❓ 常见问题

### Q1: 为什么 Function Call 没有被触发？

**可能原因：**

1. **说话不够明确**
   ```
   ❌ "我想去北京"  # 太模糊
   ✅ "帮我规划去北京的旅行"  # 明确的规划请求
   ```

2. **没有匹配的 Function**
   ```
   ❌ "今天天气怎么样"  # 没有天气查询 Function
   ✅ "帮我订酒店"  # 有 book_hotel Function
   ```

3. **GLM 决定直接回答**
   ```
   有时 GLM 判断不需要调用 Function，会直接回答
   ```

---

### Q2: Function Call 执行失败怎么办？

**检查步骤：**

1. **检查 Claude Code 服务**
   ```bash
   curl http://localhost:8000/health
   ```

2. **查看错误日志**
   ```bash
   tail -f result.txt  # 如果使用详细日志版本
   ```

3. **测试 Agent 连接**
   ```bash
   python tests/test_agent_integration.py
   ```

4. **检查配置**
   ```python
   # agents/claude_code_client.py
   base_url="http://localhost:8000"  # 确认正确
   ```

---

### Q3: 如何知道有哪些 Function 可以调用？

查看 `agents/function_definitions.py`：

```python
# 当前可用的 3 个 Function:

1. plan_trip       - 规划旅行行程
2. book_ticket     - 预订机票/火车票/汽车票
3. book_hotel      - 预订酒店
```

---

### Q4: 如何添加新的 Function？

**步骤 1**: 在 `function_definitions.py` 中定义

```python
{
    "type": "function",
    "name": "search_restaurant",
    "description": "搜索餐厅",
    "parameters": {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "城市"},
            "cuisine": {"type": "string", "description": "菜系"}
        },
        "required": ["city"]
    }
}
```

**步骤 2**: 在 `claude_code_client.py` 中实现

```python
def search_restaurant(self, city: str, cuisine: str = None):
    """搜索餐厅"""
    # 实现逻辑
    pass
```

**步骤 3**: 在 `execute_function_call` 中添加路由

```python
def execute_function_call(function_name: str, arguments: Dict[str, Any]):
    if function_name == "search_restaurant":
        return claude_code_client.search_restaurant(**arguments)
    # ...
```

---

### Q5: Function Call 很慢怎么办？

**优化方法：**

1. **检查网络延迟**
   ```bash
   ping your-claude-code-server
   ```

2. **使用本地 Agent 服务**
   ```
   本地运行比远程调用快得多
   ```

3. **优化 Agent 实现**
   ```
   简化 Agent 的处理逻辑
   减少不必要的计算
   ```

4. **异步处理**（高级）
   ```python
   # 使用异步调用 Agent
   result = await async_execute_function_call(...)
   ```

---

## 🎯 最佳实践

### ✅ 应该这样说

| 情况 | 推荐说法 |
|------|---------|
| 规划旅行 | "帮我规划一个去[城市]的旅行，[天数]天" |
| 订票 | "我要订[日期]从[城市A]到[城市B]的[交通工具]票" |
| 订酒店 | "帮我订[城市]的酒店，入住[天数]晚" |

### ❌ 避免这样说

- "我想去玩" （太模糊）
- "北京" （不完整）
- "帮我" （没说具体做什么）

---

## 📊 监控 Function Call

### 实时监控

运行详细日志版本：

```bash
# 终端 1: 运行程序
python run_with_agent_show_all_details.py

# 终端 2: 监控日志
tail -f result.txt | grep "Function Call"
```

### 查看历史记录

```bash
# 查看所有 Function Call 记录
grep "收到 Function Call" result.txt

# 统计调用次数
grep "收到 Function Call" result.txt | wc -l
```

---

## 🛠️ 调试技巧

### 1. 使用测试模式

先用测试脚本验证 Function 定义正确：

```bash
python tests/test_function_call.py
```

### 2. 单独测试 Agent 调用

```python
from agents.claude_code_client import execute_function_call

# 直接测试
result = execute_function_call("plan_trip", {
    "destination": "北京",
    "start_date": "2024-01-15",
    "end_date": "2024-01-18"
})

print(result)
```

### 3. 查看完整消息流

在 `app/realtime_with_agent.py` 中添加日志：

```python
def on_message_with_agent(ws, message):
    print(f"📥 收到消息: {message}")  # 添加这行
    data = json.loads(message)
    # ...
```

---

## 🎉 开始使用

准备好了吗？启动你的 Agent 助手：

```bash
# 1. 确保 Claude Code 运行
curl http://localhost:8000/health

# 2. 启动语音助手
python run_with_agent.py

# 3. 开始对话！
```

**试试这些对话：**
- "帮我规划一个去杭州的周末游"
- "我要订明天去上海的火车票"
- "帮我找一个北京的四星酒店"

---

## 📚 相关文档

- [Function Call 测试指南](../../tests/README_FUNCTION_CALL_TEST.md)
- [Agent 集成指南](../integration/AGENT_INTEGRATION.md)
- [Function 定义文件](../../agents/function_definitions.py)

---

**祝使用愉快！🎉**

如有问题，请查看 [故障排查指南](../troubleshooting/DEBUG_GUIDE.md)。

