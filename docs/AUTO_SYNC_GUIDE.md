# Memobase 自动同步守护进程使用指南

## 🎯 功能说明

自动同步守护进程会在后台定期将对话记录自动导入到 Memobase，无需手动执行。

**特点：**
- ✅ 自动定时同步（默认每5分钟）
- ✅ 增量更新，不会重复导入
- ✅ 支持前台和后台运行
- ✅ 优雅退出，不丢失数据
- ✅ 详细日志记录

## 🚀 快速开始

### 方式 1: Python 直接启动（前台）

```bash
python start_auto_sync.py
```

**优点**: 可以实时看到日志输出  
**缺点**: 关闭终端会停止运行

**输出示例：**
```
🚀 Memobase 自动同步守护进程启动
============================================================
📂 对话文件: /Users/xwj/Desktop/gpt-realtime-demo/data/save_data.jsonl
🔄 同步间隔: 300 秒 (5 分钟)
📝 日志文件: /Users/xwj/Desktop/gpt-realtime-demo/data/auto_sync.log
============================================================

✅ 守护进程运行中... (按 Ctrl+C 退出)
💡 提示: 每 5 分钟自动同步一次对话到 Memobase

⏰ 定时同步触发 (300秒)
📥 同步完成: 新增 3 条对话
```

### 方式 2: Shell 脚本启动（后台）

```bash
# 后台运行
./memory/start_daemon.sh background

# 或简写
./memory/start_daemon.sh bg
```

**优点**: 后台运行，关闭终端不受影响  
**缺点**: 看不到实时日志（需要查看日志文件）

## 🔧 管理命令

### 启动守护进程

```bash
# 前台运行（可看到实时日志）
python start_auto_sync.py

# 后台运行
./memory/start_daemon.sh background
```

### 停止守护进程

```bash
./memory/stop_daemon.sh
```

### 检查运行状态

```bash
./memory/check_daemon.sh
```

**输出示例：**
```
🔍 检查守护进程状态...

✅ 守护进程运行中
📝 进程 ID: 12345

进程信息:
  PID  PPID     ELAPSED CMD
12345     1    00:15:32 python start_auto_sync.py

最近的日志 (最后10行):
─────────────────────────────────────
2025-11-27 10:15:00 [INFO] 📥 同步完成: 新增 2 条对话
2025-11-27 10:20:00 [INFO] ⏰ 定时同步触发 (300秒)
...
```

### 查看实时日志

```bash
tail -f data/auto_sync.log
```

## ⚙️ 配置说明

### 环境变量配置

```bash
# Memobase 服务地址
export MEMOBASE_URL="http://localhost:8019/"

# API Token
export MEMOBASE_ACCESS_TOKEN="secret"

# 同步间隔（秒）- 默认300秒(5分钟)
export MEMOBASE_SYNC_INTERVAL="300"
```

### 修改同步间隔

**方式 1: 环境变量**
```bash
# 改为每2分钟同步一次
export MEMOBASE_SYNC_INTERVAL="120"
python start_auto_sync.py
```

**方式 2: 修改代码**
编辑 `memory/auto_sync_daemon.py`：
```python
# 同步间隔（秒）- 默认每5分钟同步一次
SYNC_INTERVAL = int(os.getenv("MEMOBASE_SYNC_INTERVAL", "300"))
```

改为：
```python
SYNC_INTERVAL = int(os.getenv("MEMOBASE_SYNC_INTERVAL", "120"))  # 2分钟
```

## 📝 日志文件

### 日志位置

- **守护进程日志**: `data/auto_sync.log`
- **标准输出日志** (后台模式): `data/auto_sync_stdout.log`
- **进程 ID 文件**: `data/auto_sync.pid`

### 查看日志

```bash
# 查看最后 20 行
tail -n 20 data/auto_sync.log

# 实时查看
tail -f data/auto_sync.log

# 搜索错误
grep ERROR data/auto_sync.log
```

## 🔄 工作流程

```
1. 启动守护进程
   ↓
2. 连接 Memobase 服务
   ↓
3. 立即执行首次同步
   ↓
4. 每隔 N 秒检查是否需要同步
   ↓
5. 到达同步时间 → 执行同步
   ↓
6. 读取 data/save_data.jsonl
   ↓
7. 只导入新增的对话（增量）
   ↓
8. 更新进度文件 data/save_data.jsonl.progress
   ↓
9. 记录日志
   ↓
10. 继续等待下一次同步
```

## 💡 使用场景

### 场景 1: 开发测试

```bash
# 前台运行，实时查看日志
python start_auto_sync.py
```

按 `Ctrl+C` 可以随时停止。

### 场景 2: 生产环境

```bash
# 后台运行
./memory/start_daemon.sh background

# 查看状态
./memory/check_daemon.sh

# 查看日志
tail -f data/auto_sync.log
```

### 场景 3: 与语音助手配合

**终端 1**: 运行语音助手
```bash
python run_with_agent.py
```

**终端 2**: 运行自动同步
```bash
python start_auto_sync.py
```

这样对话会自动同步到 Memobase，下次对话时 AI 就能记住！

## 🐛 故障排除

### Q1: 守护进程启动失败

**检查 Memobase 服务**：
```bash
curl http://localhost:8019/healthcheck
```

如果失败，先启动 Memobase 服务。

### Q2: 同步不工作

**查看日志**：
```bash
tail -n 50 data/auto_sync.log
```

常见原因：
- Memobase 服务未启动
- 对话文件路径错误
- 网络连接问题

### Q3: 进程残留

```bash
# 查找进程
ps aux | grep auto_sync_daemon

# 手动杀死进程
kill <PID>

# 清理 PID 文件
rm data/auto_sync.pid
```

### Q4: 重复导入

守护进程使用 `data/save_data.jsonl.progress` 记录进度，不会重复导入。

如果需要重新导入所有数据：
```bash
# 删除进度文件
rm data/save_data.jsonl.progress

# 重启守护进程
./memory/stop_daemon.sh
./memory/start_daemon.sh background
```

## 📊 监控和统计

### 查看同步统计

```bash
# 查看总共同步了多少条
grep "同步完成" data/auto_sync.log | wc -l

# 查看最近的同步
grep "同步完成" data/auto_sync.log | tail -10

# 查看错误
grep "ERROR" data/auto_sync.log
```

## 🔒 安全建议

1. **生产环境**: 使用环境变量配置敏感信息
2. **日志轮转**: 定期清理或轮转日志文件
3. **权限控制**: 确保日志和数据文件权限正确

## 🎯 最佳实践

### 推荐配置

```bash
# 开发环境：2分钟同步一次（快速测试）
export MEMOBASE_SYNC_INTERVAL="120"

# 生产环境：5-10分钟同步一次（平衡性能和实时性）
export MEMOBASE_SYNC_INTERVAL="300"
```

### 启动顺序

```bash
# 1. 启动 Memobase 服务
cd memobase && docker-compose up -d

# 2. 启动自动同步守护进程
./memory/start_daemon.sh background

# 3. 启动语音助手
python run_with_agent.py
```

### 停止顺序

```bash
# 1. 停止语音助手 (Ctrl+C)

# 2. 停止守护进程
./memory/stop_daemon.sh

# 3. 停止 Memobase 服务（可选）
cd memobase && docker-compose down
```

## 📚 相关文档

- [记忆集成指南](./MEMORY_INTEGRATION.md)
- [Agent 集成指南](./AGENT_INTEGRATION.md)
- [项目 README](../README.md)

---

**祝使用愉快！🎉**

有问题欢迎反馈！

