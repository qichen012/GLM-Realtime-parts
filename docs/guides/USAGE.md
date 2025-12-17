# GLM-Realtime 使用指南

## 🎯 功能概述

本项目提供了基于智谱 GLM-Realtime API 的实时语音对话系统，支持真实的语音输入和输出。

## 📁 文件说明

### 1. `realtime.py` - 基础实时语音对话
**功能：**
- ✅ 实时语音输入（通过麦克风）
- ✅ GLM-Realtime 语音输出（真实 AI 语音）
- ✅ 语音转文本显示
- ✅ 对话记录保存到本地 JSONL 文件

**适用场景：**
- 简单的语音对话测试
- 不需要长时记忆功能
- 只需要本地保存对话记录

**运行：**
```bash
python realtime.py
```

---

### 2. `quick_start.py` - 完整版（带 Memobase 记忆系统）
**功能：**
- ✅ 所有 `realtime.py` 的功能
- ✅ **自动保存对话到 Memobase 记忆库**
- ✅ **支持长时记忆和智能检索**
- ✅ **跨会话记忆管理**

**适用场景：**
- 需要 AI 记住历史对话
- 构建具有长期记忆的对话系统
- 需要检索历史对话内容

**运行：**
```bash
python quick_start.py
```

---

### 3. `test_with_wav.py` - WAV 文件测试工具
**功能：**
- 使用 WAV 音频文件测试 API
- 不需要麦克风
- 适合调试和开发

**运行：**
```bash
# 使用默认测试文件
python test_with_wav.py

# 使用指定文件
python test_with_wav.py path/to/your/audio.wav
```

---

## 🚀 快速开始

### 1. 环境配置

确保 `.env` 文件包含必要的配置：

```bash
# 智谱 API Key（必需）
ZHIPU_API_KEY=your_api_key_here

# Memobase 配置（使用 quick_start.py 时需要）
MEMOBASE_ACCESS_TOKEN=your_token_here
MEMOBASE_URL=your_memobase_url
USER_ID=your_user_id
```

### 2. 选择运行模式

**简单测试：**
```bash
python realtime.py
```

**完整功能（推荐）：**
```bash
python quick_start.py
```

### 3. 使用说明

1. 🎤 对着麦克风说话
2. ⏸️  停顿 1.5 秒，等待 AI 响应
3. 🔊 听到 AI 的语音回复
4. 🔄 继续对话...
5. ⌨️  按 `Ctrl+C` 退出

---

## 📊 对话数据

### 本地存储
所有对话自动保存到：
- 文件：`data/save_data.jsonl`
- 格式：每行一个 JSON 对象
- 内容：完整的用户-AI 对话记录

### Memobase 存储（仅 quick_start.py）
- 自动同步到云端记忆库
- 支持跨会话检索
- 进度文件：`data/save_data.jsonl.progress`

---

## 🔧 技术细节

### 音频格式
- **输入格式：** WAV (16kHz, 16-bit, Mono)
- **输出格式：** PCM (16kHz, 16-bit, Mono)
- **发送方式：** 每 512ms 批量发送（8 个 64ms chunk）

### VAD 模式
- **Server VAD：** 服务器自动检测语音开始/结束
- **静音检测：** 1.5 秒无声音触发响应

### 关键配置
```python
{
    "input_audio_format": "wav",      # WAV 格式输入
    "output_audio_format": "pcm",     # PCM 格式输出
    "turn_detection": {"type": "server_vad"},
    "beta_fields": {
        "chat_mode": "audio",
        "tts_source": "e2e"           # 端到端语音合成
    }
}
```

---

## 🐛 常见问题

### Q: 听不到 AI 的语音回复？
A: 确保：
1. 音频设备正常工作（程序启动时会播放测试音）
2. 配置中包含 `"tts_source": "e2e"`
3. 使用的是修复后的版本

### Q: Memobase 连接失败？
A: 
- 检查 `.env` 中的 Memobase 配置
- 即使失败，语音对话功能仍可正常使用
- 可以直接使用 `realtime.py` 避免 Memobase 依赖

### Q: 麦克风无响应？
A: 
1. 检查系统麦克风权限
2. 确认音频设备列表中的设备名称
3. 调整麦克风音量

---

## 📝 更新日志

### v2.0 (最新)
- ✅ 修复了音频接收问题
- ✅ 实现真实的 GLM-Realtime 语音输出
- ✅ 移除了本地 TTS 备用方案
- ✅ 优化了音频发送格式（WAV 封装）
- ✅ 改进了用户界面和提示信息

### v1.0
- 基础语音对话功能
- 本地 TTS 作为临时方案

---

## 📄 License

MIT License

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

