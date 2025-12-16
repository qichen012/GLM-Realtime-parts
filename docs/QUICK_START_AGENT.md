# 🚀 Claude Code Agent 集成快速启动

## 📦 你现在拥有的文件

```
gpt-realtime-demo/
├── 📄 function_definitions.py      # Function Call 定义
├── 📄 claude_code_client.py        # Claude Code 客户端
├── 📄 claude_code_config.py        # 配置文件 ⚙️
├── 📄 realtime_with_agent.py       # 集成版主程序 ⭐
├── 📄 test_agent_integration.py    # 测试脚本 🧪
├── 📄 AGENT_INTEGRATION.md         # 详细文档 📚
└── 📄 QUICK_START_AGENT.md         # 本文件

原有文件：
├── 📄 realtime.py                  # 基础版（不带 Agent）
├── 📄 quick_start.py               # 基础版 + Memobase
└── 📄 test_with_wav.py             # WAV 测试工具
```

## ⚡ 30秒快速启动

### 步骤 1：配置 Claude Code 地址

编辑 `claude_code_config.py`：

```python
CLAUDE_CODE_CONFIG = {
    "base_url": "http://localhost:8000",  # 👈 改成你同伴的地址
    "api_key": None,                      # 👈 如果需要，填写 API Key
}
```

### 步骤 2：测试连接

```bash
python test_agent_integration.py
```

### 步骤 3：启动语音助手

```bash
python realtime_with_agent.py
```

**搞定！** 🎉

## 🗣️ 试试这些指令

启动后，对着麦克风说：

### 行程规划
- "帮我规划一个3天的北京旅行"
- "我想去上海玩，给我做个攻略"
- "下周末去杭州，帮我安排一下"

### 订票
- "订一张明天去上海的火车票"
- "帮我买一张后天北京到广州的机票"
- "我要从深圳到上海的高铁，2月1号"

### 订酒店
- "帮我订一个杭州的酒店"
- "我要在北京住3天，订个四星酒店"
- "上海的五星级酒店，靠近外滩的"

## 🔧 与同伴对接

### 你需要从同伴那里获取：

#### 1. 服务地址
```
Claude Code 服务地址：http://____:____
```

#### 2. API 接口格式

问同伴："我要调用你的 Agent，接口是什么样的？"

可能的格式：
```python
# 格式 A：统一接口
POST /api/agent/execute
{
    "agent_name": "trip_planner",
    "task": "...",
    "parameters": {...}
}

# 格式 B：独立接口
POST /api/trip-planner
POST /api/ticket-booking
POST /api/hotel-booking
```

#### 3. 返回格式

问同伴："返回的数据格式是什么？"

```python
# 期望格式
{
    "success": true,
    "data": {...},
    "message": "..."
}
```

### 修改客户端代码

根据实际接口，修改 `claude_code_client.py` 中的 `_call_agent` 方法。

## 🐛 遇到问题？

### 问题 1：Claude Code 连接失败

```bash
# 检查服务是否运行
curl http://localhost:8000/health

# 检查网络
ping localhost
```

### 问题 2：Function Call 没触发

**症状：** 说话了但没调用 Agent

**检查：**
1. 语音是否清晰
2. 查看终端是否显示 `🔔 收到 Function Call`
3. Tools 配置是否发送成功

### 问题 3：Agent 调用出错

**症状：** 显示 `❌ 执行出错`

**检查：**
1. 接口格式是否匹配
2. 参数是否完整
3. Claude Code 服务日志

## 📊 系统流程图

```
说话："帮我订一张去上海的火车票"
    ↓
GLM 语音识别 → "帮我订一张去上海的火车票"
    ↓
GLM 理解意图 → book_ticket
    ↓
提取参数 → {ticket_type: "train", ...}
    ↓
调用 Claude Code → ticket_booking Agent + Skill
    ↓
返回结果 → {"success": true, "tickets": [...]}
    ↓
GLM 生成语音 → "好的，我找到了3趟车..."
    ↓
播放语音 🔊
```

## 🎯 三种运行模式对比

| 功能 | realtime.py | quick_start.py | realtime_with_agent.py |
|------|-------------|----------------|------------------------|
| 语音对话 | ✅ | ✅ | ✅ |
| Memobase | ❌ | ✅ | ❌ |
| Agent 调用 | ❌ | ❌ | ✅ |
| 行程规划 | ❌ | ❌ | ✅ |
| 订票 | ❌ | ❌ | ✅ |
| 订酒店 | ❌ | ❌ | ✅ |

**推荐：** 使用 `realtime_with_agent.py` 获得完整的旅行助手功能！

## 📝 下一步计划

- [ ] 测试 Claude Code 连接
- [ ] 验证 Function Call 流程
- [ ] 测试行程规划功能
- [ ] 测试订票功能
- [ ] 测试订酒店功能
- [ ] 优化用户体验
- [ ] 添加错误处理
- [ ] 部署到生产环境

## 🎉 成功后的样子

```bash
$ python realtime_with_agent.py

=============================================================
    GLM-Realtime + Claude Code Travel Assistant
=============================================================
🤖 功能:
   • 语音对话
   • 行程规划（调用 Claude Code Agent）
   • 订票服务（调用 Claude Code Agent + Skill）
   • 订酒店（调用 Claude Code Agent + Skill）

💡 使用示例:
   「帮我规划一个去北京的旅行」
   「我要订一张明天去上海的火车票」
   「帮我订一个杭州的酒店」
=============================================================

🎤 Ready! Start speaking...

[你说话]
📝 [USER_TEXT]: 帮我订一张去上海的火车票

🔔 收到 Function Call: book_ticket
   参数: {"ticket_type": "train", ...}

🤖 正在调用 Claude Code Agent...
🎫 调用订票 Agent + Skill: ...
   ✅ 执行完成
   结果: {"success": true, ...}
   📤 结果已发送回 GLM
   📤 请求 GLM 生成语音回复

🎵 Audio stream complete, preparing playback...
   ▶️  Playing...
   ✅ Playback complete!

[AI 用语音告诉你车次信息]
```

---

**准备好了吗？开始你的智能旅行助手之旅吧！** 🚀✈️🏨

