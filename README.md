# GLM-Realtime 语音助手

基于 GLM-Realtime API 的智能语音助手系统，集成 Claude Code Agent 和 Memobase 长期记忆功能。

## ✨ 核心亮点

### 🚀 实时记忆同步（方案3：混合模式）⭐ 最新

**对话结束立即同步，记忆零延迟生效！**

- ⚡ **实时同步**：对话结束后 < 100ms 同步到 Memobase
- 🛡️ **双重保障**：实时同步 + 容错备份，确保 100% 数据完整性
- 🔄 **异步处理**：不阻塞对话流程，用户无感知
- 📊 **状态追踪**：每条记录都有同步状态，可审计全过程

```
用户: 我最近喜欢吃川菜
AI: 好的，我记住了 ✅ [立即同步到 Memobase]

[立即生效，无需等待]

用户: 推荐一个餐厅
AI: 根据您喜欢川菜，推荐... ✅
```

### 💬 智能打断功能

- ⏸️ **VAD 优化**：2秒停顿容忍，避免误判
- ⚡ **Enter 键打断**：AI 回复时按 Enter 可立即打断
- 🔄 **无缝继续**：打断后可直接继续说话

### 🤖 Claude Code Agent 集成

- 🗺️ 行程规划
- 🎫 智能订票
- 🏨 酒店预订

## 📂 项目结构

```
gpt-realtime-demo/
├── app/                        # 核心应用程序
│   ├── realtime.py            # 基础版语音助手
│   ├── realtime_with_agent.py # 集成版（Agent + Memory）
│   └── quick_start.py         # 快速开始脚本
│
├── agents/                     # Agent 集成模块
│   ├── claude_code_client.py  # Claude Code 客户端
│   ├── claude_code_config.py  # 配置文件
│   └── function_definitions.py # Function Call 定义
│
├── memory/                     # 记忆管理模块
│   ├── realtime_sync.py       # 🔑 实时同步核心模块（方案3）
│   ├── auto_sync_daemon.py    # 🛡️ 容错备份守护进程（方案3）
│   ├── memory_manager.py      # 记忆管理器
│   ├── save_to_mem.py         # 批量导入对话到 Memobase
│   ├── check_user.py          # 查询用户记忆
│   ├── data_logger.py         # 数据日志记录（增强版）
│   ├── start_daemon.sh        # 守护进程启动脚本
│   ├── stop_daemon.sh         # 守护进程停止脚本
│   └── check_daemon.sh        # 守护进程状态检查
│
├── tests/                      # 测试文件
│   ├── test_agent_integration.py    # Agent 测试
│   ├── test_memory_integration.py   # 记忆测试
│   └── test_*.py                    # 其他测试
│
├── docs/                       # 📚 文档目录
│   ├── quickstart/            # 🚀 快速开始
│   │   ├── QUICK_START_AGENT.md
│   │   └── CLIENT_VAD_GUIDE.md
│   ├── guides/                # 📖 使用指南
│   │   ├── SPACEBAR_TRIGGER_GUIDE.md
│   │   ├── MANUAL_TRIGGER_GUIDE.md
│   │   ├── INTERRUPT_GUIDE.md
│   │   ├── VOICE_CONFIG.md
│   │   └── USAGE.md
│   ├── integration/           # 🔧 集成指南
│   │   ├── AGENT_INTEGRATION.md
│   │   ├── MEMORY_INTEGRATION.md
│   │   ├── AUTO_SYNC_GUIDE.md
│   │   └── REALTIME_SYNC_GUIDE.md
│   ├── troubleshooting/       # 🔍 故障排查
│   │   ├── AUDIO_TROUBLESHOOTING.md
│   │   ├── BLUETOOTH_FIX.md
│   │   └── DEBUG_GUIDE.md
│   └── archive/               # 📦 归档文档
│       ├── INTERRUPT_FEATURE_COMPLETE.md
│       ├── REALTIME_SYNC_COMPLETE.md
│       └── REORGANIZATION_COMPLETE.md
│
├── data/                       # 数据文件
│   ├── save_data.jsonl
│   └── save_data.jsonl.progress
│
├── glm-realtime-sdk/          # GLM SDK
├── memobase/                  # Memobase SDK
│
├── run_realtime.py            # 启动基础版（便捷脚本）
├── run_with_agent.py          # 启动集成版（便捷脚本）
├── run_quick_start.py         # 快速开始（便捷脚本）
├── start_auto_sync.py         # 启动自动同步守护进程
│
└── README.md                  # 本文件
```

## 🚀 快速开始

### 方式 1: 基础版语音助手

```bash
python run_realtime.py
# 或
cd app && python realtime.py
```

### 方式 2: 集成版（推荐）

包含 Agent 和记忆功能：

```bash
python run_with_agent.py
# 或
cd app && python realtime_with_agent.py
```

### 方式 3: 快速开始

```bash
python run_quick_start.py
# 或
cd app && python quick_start.py
```

## 📚 功能模块

### 1. 核心语音功能 (`app/`)
- ✅ 实时语音对话
- ✅ 语音识别
- ✅ 语音合成
- ✅ VAD（语音活动检测）- 优化为2秒停顿容忍 ⭐ 新增
- ✅ **智能打断功能** - Enter 键打断 AI 回复 ⭐ 新增

### 2. Agent 集成 (`agents/`)
- ✅ 行程规划 Agent
- ✅ 订票 Agent + Skill
- ✅ 订酒店 Agent + Skill
- ✅ Function Call 支持

### 3. 记忆管理 (`memory/`)
- ✅ 用户画像提取
- ✅ 事件记忆
- ✅ 上下文构建
- ✅ 个性化对话
- ✅ **实时同步** - 对话结束立即同步到 Memobase（< 100ms 延迟）⭐ 最新
- ✅ **容错备份** - 定时任务处理失败记录（双重保障）⭐ 最新

## 🧪 测试

### 测试 Agent 集成
```bash
cd tests && python test_agent_integration.py
```

### 测试记忆功能
```bash
cd tests && python test_memory_integration.py
```

### 查询用户记忆
```bash
cd memory && python check_user.py
```

### 导入对话数据

**⚡ 方式 1: 实时自动同步（推荐）**

对话结束后自动同步到 Memobase，**无需任何操作**！

```bash
# 运行集成版本时自动启用实时同步
python run_with_agent.py
```

特性：
- ✅ **实时同步** - 对话结束立即同步（< 100ms 延迟）
- ✅ **异步处理** - 不阻塞对话流程
- ✅ **自动重试** - 失败自动重试 3 次
- ✅ **零配置** - 开箱即用

**🛡️ 方式 2: 容错备份守护进程（可选）**

作为实时同步的备份，处理实时同步失败的记录：

```bash
# 启动后台容错守护进程
python start_auto_sync.py

# 或后台运行
./memory/start_daemon.sh background
```

特性：
- ✅ **容错保障** - 处理实时同步失败的记录
- ✅ **定时扫描** - 每 5 分钟扫描一次未同步记录
- ✅ **状态追踪** - 只处理 `synced=false` 的记录
- ✅ **双重保障** - 确保 100% 数据同步

**📝 方式 3: 手动批量导入**

适用于批量导入历史对话：

```bash
cd memory && python save_to_mem.py
```

> 💡 **推荐组合**: 实时同步（方式1） + 容错守护进程（方式2）= 完美双保险

详见 [实时同步指南](docs/REALTIME_SYNC_GUIDE.md)。

## 📖 详细文档

### 🚀 快速开始
- [Agent 快速上手](docs/quickstart/QUICK_START_AGENT.md) - Agent 功能快速开始
- [Client VAD 指南](docs/quickstart/CLIENT_VAD_GUIDE.md) - 客户端 VAD 使用

### 📖 使用指南
- [空格键触发指南](docs/guides/SPACEBAR_TRIGGER_GUIDE.md) - 手动触发语音结束
- [手动触发指南](docs/guides/MANUAL_TRIGGER_GUIDE.md) - 手动触发机制说明
- [智能打断指南](docs/guides/INTERRUPT_GUIDE.md) - VAD 优化 + Enter 键打断 ⭐
- [语音配置指南](docs/guides/VOICE_CONFIG.md) - 语音参数调优
- [完整使用手册](docs/guides/USAGE.md) - 详细使用说明

### 🔧 集成指南
- [实时同步指南](docs/integration/REALTIME_SYNC_GUIDE.md) - 实时同步 + 容错备份（方案3）⭐⭐⭐
- [Agent 集成指南](docs/integration/AGENT_INTEGRATION.md) - 如何集成 Claude Code Agent
- [记忆集成指南](docs/integration/MEMORY_INTEGRATION.md) - 如何使用 Memobase 记忆
- [容错同步指南](docs/integration/AUTO_SYNC_GUIDE.md) - 容错备份守护进程

### 🔍 故障排查
- [音频故障排查](docs/troubleshooting/AUDIO_TROUBLESHOOTING.md) - 音频相关问题解决
- [蓝牙问题修复](docs/troubleshooting/BLUETOOTH_FIX.md) - 蓝牙音频设备问题
- [调试指南](docs/troubleshooting/DEBUG_GUIDE.md) - 系统调试方法

## ⚙️ 配置

### 环境变量

```bash
# GLM API
export ZHIPU_API_KEY="your-api-key"

# Memobase
export MEMOBASE_URL="http://localhost:8019/"
export MEMOBASE_ACCESS_TOKEN="secret"

# Claude Code (可选)
export CLAUDE_CODE_URL="http://localhost:8000"
```

### 配置文件

- `agents/claude_code_config.py` - Claude Code 配置
- `memory/memory_manager.py` - Memobase 配置

## 🔧 依赖安装

```bash
pip install -r requirements.txt
```

主要依赖：
- `websocket-client` - WebSocket 通信
- `sounddevice` - 音频处理
- `numpy` - 数值计算
- `requests` - HTTP 请求
- `pynput` - 键盘监听（打断功能）⭐ 新增
- `memobase` - 记忆管理

## 💡 使用示例

### 基础对话
```
用户: "你好"
AI: "你好！有什么可以帮你的吗？"
```

### Agent 功能
```
用户: "帮我规划一个北京3天的旅行"
AI: (调用行程规划 Agent)
    "好的！为您规划了精彩的3天行程..."
```

### 记忆功能
```
第一天:
用户: "我是北邮的学生"
AI: "好的，了解了！"

第二天:
用户: "推荐学校附近的景点"
AI: "作为北邮的学生，您可以去..."
```

## 🛠️ 开发指南

### 添加新的 Agent

1. 在 `agents/function_definitions.py` 中定义新的 Function
2. 在 `agents/claude_code_client.py` 中实现客户端方法
3. 更新 `execute_function_call` 函数

### 自定义记忆管理

修改 `memory/memory_manager.py` 中的配置：

```python
# 调整记忆 token 大小
context = get_user_memory(user_id, max_token_size=1500)

# 使用用户画像摘要
summary = memory_manager.get_user_profile_summary(user_id)
```

## ⚠️ 注意事项

1. **运行位置**: 可以从项目根目录或子目录运行，import 路径已自动处理
2. **Memobase 服务**: 使用记忆功能前需启动 Memobase 服务
3. **Claude Code 服务**: 使用 Agent 功能需要 Claude Code 服务
4. **音频设备**: 确保麦克风和扬声器正常工作

## 🐛 故障排除

### 导入错误
```bash
# 确保从正确的位置运行
python run_with_agent.py  # 从根目录

# 或者
cd app && python realtime_with_agent.py
```

### 记忆未加载
```bash
# 检查 Memobase 服务
curl http://localhost:8019/healthcheck

# 测试记忆功能
cd tests && python test_memory_integration.py
```

### Agent 调用失败
```bash
# 测试 Agent 连接
cd tests && python test_agent_integration.py
```

## 📝 更新日志

### v1.0.0 (2025-11-27)
- ✅ 重组项目结构
- ✅ 模块化设计
- ✅ 添加便捷启动脚本
- ✅ 集成 Memobase 记忆
- ✅ 集成 Claude Code Agent

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

---

**祝使用愉快！🎉**

有问题请查看 `docs/` 目录下的详细文档。

