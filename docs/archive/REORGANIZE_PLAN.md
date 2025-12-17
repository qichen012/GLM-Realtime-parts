# 项目重组方案

## 📂 新的文件夹结构

```
gpt-realtime-demo/
├── app/                        # 核心应用程序
│   ├── __init__.py
│   ├── realtime.py            # 基础版语音助手
│   ├── realtime_with_agent.py # 集成版语音助手（Agent + Memory）
│   └── quick_start.py         # 快速开始脚本
│
├── agents/                     # Agent 集成模块
│   ├── __init__.py
│   ├── claude_code_client.py  # Claude Code 客户端
│   ├── claude_code_config.py  # Claude Code 配置
│   └── function_definitions.py # Function Call 定义
│
├── memory/                     # 记忆管理模块
│   ├── __init__.py
│   ├── memory_manager.py      # 记忆管理器
│   ├── save_to_mem.py         # 导入对话到 Memobase
│   ├── check_user.py          # 查询用户记忆
│   └── data_logger.py         # 数据日志记录
│
├── tests/                      # 测试文件
│   ├── __init__.py
│   ├── test_agent_integration.py    # Agent 集成测试
│   ├── test_memory_integration.py   # 记忆集成测试
│   ├── test_with_wav.py            # WAV 文件测试
│   ├── test_api.py
│   ├── test_copy.py
│   ├── test_module.py
│   ├── test_sounddevice.py
│   ├── test_time.py
│   └── test.py
│
├── docs/                       # 文档
│   ├── AGENT_INTEGRATION.md   # Agent 集成指南
│   ├── MEMORY_INTEGRATION.md  # 记忆集成指南
│   ├── QUICK_START_AGENT.md   # Agent 快速开始
│   ├── USAGE.md               # 使用说明
│   └── VOICE_CONFIG.md        # 语音配置
│
├── data/                       # 数据文件（原 datas/）
│   ├── save_data.jsonl
│   └── save_data.jsonl.progress
│
├── third_party/                # 第三方库/SDK
│   ├── glm-realtime-sdk/
│   └── memobase/
│
├── config/                     # 配置文件（可选）
│   └── .env.example
│
├── scripts/                    # 实用脚本（可选）
│   └── setup.sh
│
├── README.md                   # 主文档
├── requirements.txt            # Python 依赖
├── package.json                # Node.js 依赖
└── .gitignore

```

## 📋 文件移动清单

### 1. 核心应用 → `app/`
- [x] realtime.py
- [x] realtime_with_agent.py
- [x] quick_start.py

### 2. Agent 模块 → `agents/`
- [x] claude_code_client.py
- [x] claude_code_config.py
- [x] function_definitions.py

### 3. 记忆模块 → `memory/`
- [x] memory_manager.py
- [x] save_to_mem.py
- [x] check_user.py
- [x] data_logger.py

### 4. 测试文件 → `tests/` (整理)
- [x] test_agent_integration.py
- [x] test_memory_integration.py
- [x] test_with_wav.py
- [x] tests/test_*.py (已在 tests 文件夹)

### 5. 文档 → `docs/`
- [x] AGENT_INTEGRATION.md
- [x] MEMORY_INTEGRATION.md
- [x] QUICK_START_AGENT.md
- [x] USAGE.md
- [x] VOICE_CONFIG.md

### 6. 数据 → `data/`
- [x] datas/ → data/

### 7. 第三方库 → `third_party/`
- [x] glm-realtime-sdk/ → third_party/glm-realtime-sdk/
- [x] memobase/ → third_party/memobase/

## 🔧 需要更新的导入路径

重组后需要更新以下文件中的 import 语句：

### `app/realtime_with_agent.py`
```python
# 旧的
from realtime import *
from function_definitions import get_function_definitions
from claude_code_client import execute_function_call
from memory_manager import format_memory_for_glm, DEFAULT_USER_ID

# 新的
from app.realtime import *
from agents.function_definitions import get_function_definitions
from agents.claude_code_client import execute_function_call
from memory.memory_manager import format_memory_for_glm, DEFAULT_USER_ID
```

### `agents/claude_code_client.py`
```python
# 旧的
from memory_manager import format_memory_for_claude, DEFAULT_USER_ID

# 新的
from memory.memory_manager import format_memory_for_claude, DEFAULT_USER_ID
```

### `memory/save_to_mem.py`
```python
# 旧的
from memobase.src.client.memobase.core.entry import MemoBaseClient
from memobase.src.client.memobase.core.blob import ChatBlob, BlobType

# 新的
from third_party.memobase.src.client.memobase.core.entry import MemoBaseClient
from third_party.memobase.src.client.memobase.core.blob import ChatBlob, BlobType
```

### 测试文件
所有测试文件中的导入也需要更新。

## 🎯 重组的好处

1. **清晰的模块化**: 每个功能模块独立在自己的文件夹中
2. **易于维护**: 新功能可以轻松添加到对应文件夹
3. **便于理解**: 新开发者可以快速了解项目结构
4. **扩展性好**: 未来可以轻松添加新的模块
5. **符合 Python 最佳实践**: 标准的项目结构

## 📝 执行步骤

1. 创建新文件夹
2. 移动文件到对应文件夹
3. 在每个模块文件夹创建 `__init__.py`
4. 更新所有 import 路径
5. 运行测试验证
6. 更新 README.md

## ⚠️ 注意事项

- 第三方库 (`glm-realtime-sdk/`, `memobase/`) 可以保持在原位置或移到 `third_party/`
- 如果移动第三方库，需要更新所有相关的 import 路径
- 建议先备份项目再执行重组
- 重组后需要重新运行所有测试

