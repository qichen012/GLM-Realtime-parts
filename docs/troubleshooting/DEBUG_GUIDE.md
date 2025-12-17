# 🔍 调试版本使用指南

## 📝 概述

`run_with_agent_02.py` 是一个带有详细日志记录的调试版本，它会将程序运行的每一步详细信息记录到 `result.txt` 文件中，方便分析问题。

## 🚀 使用方法

### 1. 运行调试版本

```bash
python run_with_agent_02.py
```

### 2. 查看实时日志

程序会将日志同时输出到：
- **终端**：简化版日志
- **result.txt**：详细完整日志

在另一个终端窗口实时查看日志：

```bash
tail -f result.txt
```

### 3. 进行语音对话

- 对着麦克风说话
- 停顿 1.2 秒，等待 AI 回复
- 按 Enter 键可以打断 AI

### 4. 分析日志

程序退出后，查看完整日志：

```bash
cat result.txt
# 或用编辑器打开
open result.txt
```

## 📋 日志分类说明

日志按类别记录，每条日志格式为：

```
[时间戳] [类别] 消息
  数据: {...}
```

### 日志类别

| 类别 | 说明 |
|------|------|
| `INIT` | 初始化过程（模块导入、变量设置） |
| `AUDIO` | 音频设备检查和配置 |
| `MEMORY` | 用户记忆加载 |
| `TOOLS` | 工具/函数定义加载 |
| `CONFIG` | 会话配置 |
| `CONNECTION` | WebSocket 连接状态 |
| `AUTH` | JWT Token 生成 |
| `THREAD` | 线程启动/停止 |
| `WS_MESSAGE` | 接收到的 WebSocket 消息 |
| `WS_MESSAGE_DETAIL` | 重要消息的完整内容 |
| `WS_SEND` | 发送的 WebSocket 消息 |
| `MIC` | 麦克风输入（音量检测） |
| `AUDIO_LOOP` | 音频发送循环 |
| `AUDIO_SEND` | 音频数据发送 |
| `VAD` | 语音活动检测（Server VAD） |
| `TRANSCRIPTION` | 语音转文字 |
| `RESPONSE` | AI 回复 |
| `AUDIO` | 音频接收和播放 |
| `FUNCTION_CALL` | 函数调用 |
| `AGENT` | Claude Code Agent 执行 |
| `SYNC` | Memobase 同步 |
| `STATE` | 状态统计 |
| `ERROR` | 错误信息 |
| `MAIN` | 主程序流程 |

## 🔍 常见问题诊断

### 问题 1：没有检测到语音

查看日志中的：
- `[MIC]` 是否检测到音量
- `[AUDIO_SEND]` 是否发送了音频数据
- `[VAD] 检测到语音开始` 是否出现

**可能原因：**
- 麦克风未正常工作
- 环境太安静，音量太低
- Server VAD 阈值设置不当

### 问题 2：AI 没有回复

查看日志流程：
1. `[VAD] 检测到语音开始` ✅
2. `[VAD] 检测到语音结束` ✅
3. `[RESPONSE] AI 开始生成回复` ❓

**可能原因：**
- 如果没有步骤 2：Server VAD 没有检测到语音结束
- 如果有步骤 2 但没有步骤 3：API 处理超时或错误
- 查看是否有 `[ERROR]` 日志

### 问题 3：Function Call 失败

查看日志：
- `[FUNCTION_CALL]` 函数名和参数
- `[AGENT]` Agent 执行结果
- `[ERROR]` 是否有错误

### 问题 4：音频卡顿或没声音

查看：
- `[AUDIO]` 收到音频块的数量
- `[AUDIO] 音频接收完成` 总块数
- 是否有播放相关的错误

## 📊 状态统计

日志中的 `[STATE]` 记录了关键计数：

```json
{
  "connected": true/false,          // WebSocket 是否连接
  "session_ready": true/false,      // 会话是否就绪
  "audio_sent_count": 0,            // 发送音频次数
  "speech_started_count": 0,        // 检测到语音开始次数
  "speech_stopped_count": 0,        // 检测到语音结束次数
  "response_received_count": 0,     // 收到 AI 回复次数
  "audio_chunks_received": 0,       // 收到音频块数量
  "function_calls": []              // 函数调用记录
}
```

## 💡 使用技巧

1. **对比成功和失败的日志**
   - 先用 WAV 文件测试成功（`python test_joke_audio.py`）
   - 再用实时对话（`python run_with_agent_02.py`）
   - 对比两者的日志，找出差异

2. **聚焦关键事件**
   - 使用 `grep` 筛选特定类别：
   ```bash
   grep "\[VAD\]" result.txt
   grep "\[ERROR\]" result.txt
   grep "\[AUDIO_SEND\]" result.txt
   ```

3. **查看时间线**
   - 每条日志都有时间戳，可以分析事件发生顺序
   - 计算关键事件之间的时间间隔

4. **检查完整消息**
   - `[WS_MESSAGE_DETAIL]` 包含重要消息的完整 JSON
   - 可以查看 Server VAD 的具体配置和状态

## 🎯 典型的成功日志流程

```
[INIT] 开始导入模块...
[INIT] ✅ 所有模块导入成功
[AUDIO] 检查音频设备...
[CONNECTION] WebSocket 连接已建立
[SESSION] 会话建立
[AUDIO_LOOP] 开始发送音频流
[MIC] 检测到高音量: 120000
[AUDIO_SEND] 已发送 10 批音频数据
[VAD] 检测到语音开始 (第 1 次)
[VAD] 检测到语音结束 (第 1 次)
[TRANSCRIPTION] 用户输入转写: 你好
[RESPONSE] AI 开始生成回复 (第 1 次)
[RESPONSE] AI 回复文字: 你好！有什么可以帮你的吗？
[AUDIO] 收到音频块 #1
[AUDIO] 收到音频块 #2
...
[AUDIO] 音频接收完成，总共 50 块
[RESPONSE] AI 回复完成
```

## 🐛 提交问题时

如果需要报告问题，请提供：
1. 完整的 `result.txt` 日志
2. 你的操作步骤
3. 期望的行为 vs 实际的行为
4. 相关的错误信息（如果有）

---

祝调试顺利！🚀

