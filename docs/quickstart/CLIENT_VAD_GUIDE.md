# Client VAD vs Server VAD 使用指南

## 📚 目录

- [什么是 VAD？](#什么是-vad)
- [Server VAD vs Client VAD](#server-vad-vs-client-vad)
- [如何选择？](#如何选择)
- [使用方法](#使用方法)
- [参数调优](#参数调优)

---

## 什么是 VAD？

**VAD (Voice Activity Detection)** = 语音活动检测

用于判断：
- ✅ 用户是否在说话
- ✅ 用户何时停止说话
- ✅ 何时应该触发 AI 回复

---

## Server VAD vs Client VAD

### 🌐 Server VAD（服务器端检测）

**特点：**
- ✅ **简单** - 服务器自动检测，无需客户端处理
- ✅ **可靠** - 服务器端算法稳定
- ❌ **灵活性低** - 参数调整有限
- ❌ **延迟** - 需要等待服务器检测

**工作流程：**
```
用户说话 → 客户端持续发送音频 → 服务器检测到静音 
         → 服务器自动触发回复 → AI 开始响应
```

**配置示例：**
```python
"turn_detection": {
    "type": "server_vad",
    "threshold": 0.7,              # 检测阈值（0.0-1.0）
    "silence_duration_ms": 1000,   # 静音多久判定为说完
    "prefix_padding_ms": 300       # 语音前缓冲
}
```

**适用场景：**
- 🎯 快速原型开发
- 🎯 简单的语音交互
- 🎯 不需要复杂逻辑

---

### 💻 Client VAD（客户端检测）

**特点：**
- ✅ **灵活** - 完全自定义检测逻辑
- ✅ **低延迟** - 本地检测，立即响应
- ✅ **可控** - 可根据场景调整
- ❌ **复杂** - 需要自己实现检测逻辑
- ❌ **依赖客户端** - 需要额外计算资源

**工作流程：**
```
用户说话 → 客户端本地 VAD 检测 → 检测到语音发送到服务器
         → 客户端检测到静音 → 手动提交音频 
         → 手动请求 AI 回复 → AI 开始响应
```

**配置示例：**
```python
"turn_detection": None  # 🔑 关键：禁用服务器 VAD
```

**客户端逻辑：**
```python
# 1. 本地 VAD 检测
has_speech = voice_processor.process(audio_chunk) is not None

# 2. 检测到语音，发送音频
if has_speech:
    ws.send({"type": "input_audio_buffer.append", "audio": base64_audio})

# 3. 检测到静音超过阈值，提交并请求回复
if silence_duration > threshold:
    # 提交音频缓冲
    ws.send({"type": "input_audio_buffer.commit"})
    
    # 请求 AI 回复
    ws.send({
        "type": "response.create",
        "response": {"modalities": ["audio", "text"]}
    })
```

**适用场景：**
- 🎯 需要自定义检测逻辑
- 🎯 多语言支持
- 🎯 复杂的语音交互场景
- 🎯 需要与其他本地处理结合（降噪、回声消除等）

---

## 如何选择？

| 场景 | 推荐方案 | 理由 |
|------|---------|------|
| 🚀 快速开发 | Server VAD | 简单、稳定 |
| 🎮 实时游戏 | Client VAD | 低延迟 |
| 🌍 多语言场景 | Client VAD | 灵活调整 |
| 📱 移动设备 | Server VAD | 省电、省资源 |
| 🎤 专业录音 | Client VAD | 精确控制 |
| 🏢 企业应用 | Server VAD | 稳定可靠 |

---

## 使用方法

### 🌐 使用 Server VAD

```bash
# 启动基础版（Server VAD）
python run_realtime.py

# 或带 Agent 的版本
python run_with_agent.py
```

**特点：**
- 自动检测语音结束
- 自动触发 AI 回复
- 无需手动操作

---

### 💻 使用 Client VAD

```bash
# 启动 Client VAD 版本
python run_clientVAD.py
```

**特点：**
- 本地 VAD 检测（使用 WebRTC VAD）
- 静音 1.5 秒后自动提交
- 更快的响应速度

---

## 参数调优

### 🎛️ Server VAD 参数

**在 `app/realtime.py` 中修改：**

```python
"turn_detection": {
    "type": "server_vad",
    
    # 🔑 threshold: 检测阈值 (0.0-1.0)
    # - 值越高 = 越"挑剔"，不容易误触发
    # - 值越低 = 越敏感，容易检测到噪音
    # 推荐: 0.5-0.7（嘈杂环境用 0.7）
    "threshold": 0.7,
    
    # 🔑 silence_duration_ms: 静音多久算说完
    # - 值越大 = 用户可以停顿更久
    # - 值越小 = 响应更快，但容易打断用户
    # 推荐: 800-1500ms
    "silence_duration_ms": 1000,
    
    # 🔑 prefix_padding_ms: 语音前缓冲
    # - 保留说话前的一小段音频，避免开头被截断
    # 推荐: 300ms
    "prefix_padding_ms": 300
}
```

**调优建议：**

| 场景 | threshold | silence_duration_ms |
|------|-----------|---------------------|
| 安静环境 | 0.5 | 800 |
| 正常环境 | 0.6 | 1000 |
| 嘈杂环境 | 0.7-0.8 | 1200 |
| 慢速讲话 | 0.5 | 1500 |
| 快速对话 | 0.6 | 700 |

---

### 🎛️ Client VAD 参数

**在 `app/realtime_client_vad.py` 中修改：**

#### 1. 本地 VAD 敏感度

```python
# 🔑 vad_aggressiveness: 0-3
# - 0 = 最不激进，更容易检测到语音（适合安静环境）
# - 1 = 正常
# - 2 = 激进，过滤更多噪音（推荐）
# - 3 = 最激进，可能过滤掉轻声说话
voice_processor = SimpleMyVoiceProcessor(
    sample_rate=SAMPLE_RATE,
    vad_aggressiveness=2  # 根据环境调整
)
```

#### 2. 静音检测阈值

```python
# 🔑 silence_threshold_seconds: 静音多久算说完
# - 值越大 = 用户可以停顿更久
# - 值越小 = 响应更快
speech_detector = SpeechDetector(
    silence_threshold_seconds=1.5  # 推荐 1.0-2.0 秒
)
```

**调优建议：**

| 场景 | vad_aggressiveness | silence_threshold |
|------|-------------------|-------------------|
| 安静环境 | 1 | 1.0 |
| 正常环境 | 2 | 1.5 |
| 嘈杂环境 | 3 | 1.5 |
| 慢速讲话 | 1 | 2.0 |
| 快速对话 | 2 | 1.0 |

---

## 🔍 故障排查

### Server VAD 问题

**问题 1: AI 响应太慢**
- ✅ 减小 `silence_duration_ms` (例如 700ms)
- ✅ 降低 `threshold` (例如 0.5)

**问题 2: 说话被打断**
- ✅ 增大 `silence_duration_ms` (例如 1500ms)
- ✅ 提高 `threshold` (例如 0.7)

**问题 3: 噪音误触发**
- ✅ 提高 `threshold` (例如 0.8)
- ✅ 使用 Client VAD 进行更精确控制

---

### Client VAD 问题

**问题 1: 检测不到语音**
- ✅ 降低 `vad_aggressiveness` (例如 1)
- ✅ 检查麦克风音量
- ✅ 查看控制台是否有 "🎤 [开始说话]" 提示

**问题 2: 噪音误触发**
- ✅ 提高 `vad_aggressiveness` (例如 3)
- ✅ 增大 `silence_threshold_seconds`

**问题 3: 响应太慢**
- ✅ 减小 `silence_threshold_seconds` (例如 1.0)

**问题 4: 说话被截断**
- ✅ 增大 `silence_threshold_seconds` (例如 2.0)

---

## 🎯 最佳实践

### Server VAD 最佳实践

1. ✅ **从默认参数开始**
   ```python
   threshold: 0.5, silence_duration_ms: 800
   ```

2. ✅ **逐步调整**
   - 先调整 `silence_duration_ms`
   - 再调整 `threshold`

3. ✅ **测试不同环境**
   - 安静房间
   - 正常办公室
   - 嘈杂街道

---

### Client VAD 最佳实践

1. ✅ **使用合适的 VAD 敏感度**
   ```python
   vad_aggressiveness=2  # 大多数场景适用
   ```

2. ✅ **设置合理的静音阈值**
   ```python
   silence_threshold_seconds=1.5  # 平衡响应速度和用户体验
   ```

3. ✅ **添加调试日志**
   ```python
   print(f"🎤 检测到语音: {has_speech}")
   print(f"🔇 静音时长: {silence_duration:.2f}秒")
   ```

4. ✅ **提供视觉反馈**
   - 显示 "正在说话" 状态
   - 显示 "等待响应" 状态
   - 显示 "AI 回复中" 状态

---

## 📊 对比总结

| 特性 | Server VAD | Client VAD |
|------|-----------|-----------|
| **简单性** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **灵活性** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **延迟** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **可靠性** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **资源占用** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **自定义能力** | ⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## 🚀 快速开始

### 1️⃣ 尝试 Server VAD（推荐新手）

```bash
python run_realtime.py
```

开始说话，系统会自动检测并回复。

---

### 2️⃣ 尝试 Client VAD（推荐进阶）

```bash
python run_clientVAD.py
```

享受更快的响应速度和更精确的控制！

---

## 📞 需要帮助？

遇到问题？查看：
- [项目 README](../README.md)
- [快速开始指南](../QUICK_START_AGENT.md)
- [语音配置指南](../VOICE_CONFIG.md)

祝您使用愉快！🎉

