# GLM-Realtime 声音配置指南

## 🎵 可用声音列表

在 `session_config` 中的 `voice` 参数可以设置以下声音：

| 声音名称 | 特点 | 适用场景 |
|---------|------|---------|
| `xiaoyu` | 甜美女声 | 客服、助手、日常对话 ⭐ 推荐 |
| `xiaomei` | 温柔女声 | 温馨场景、情感陪伴 |
| `xiaochen` | 成熟男声 | 正式场合、新闻播报 |
| `xiaoke` | 儿童声音 | 儿童教育、亲子互动 |

## ⚙️ 配置参数说明

### 1. 基础配置

```python
session_config = {
    "type": "session.update",
    "session": {
        "voice": "xiaoyu",        # 选择声音
        "temperature": 0.8,       # 控制表现力
        "modalities": ["audio", "text"],
        "beta_fields": {
            "speed": 1.2          # 控制语速
        }
    }
}
```

### 2. temperature（表现力）

- **范围：** 0.0 - 1.0
- **作用：** 控制语音的自然度和表现力

| 数值 | 效果 | 适用场景 |
|------|------|---------|
| 0.0 - 0.3 | 非常机械、平淡 | 正式播报 |
| 0.4 - 0.6 | 较自然、适度情感 | 常规对话 |
| 0.7 - 0.9 | 自然活泼、富有情感 | 日常聊天 ⭐ |
| 1.0 | 最大表现力 | 故事讲述 |

**推荐值：** `0.7 - 0.8`

### 3. speed（语速）

- **范围：** 0.5 - 2.0
- **作用：** 控制说话速度

| 数值 | 效果 | 适用场景 |
|------|------|---------|
| 0.5 - 0.7 | 很慢 | 教学、老年人 |
| 0.8 - 0.9 | 较慢 | 清晰讲解 |
| 1.0 | 正常 | 标准速度 |
| 1.1 - 1.3 | 稍快 | 日常对话 ⭐ |
| 1.4 - 2.0 | 很快 | 快速播报 |

**推荐值：** `1.1 - 1.2`

## 🎯 推荐配置方案

### 方案 1：日常对话（推荐）

```python
"voice": "xiaoyu",
"temperature": 0.8,
"beta_fields": {
    "speed": 1.2
}
```

**特点：** 甜美女声、自然活泼、语速适中

### 方案 2：专业助手

```python
"voice": "xiaomei",
"temperature": 0.6,
"beta_fields": {
    "speed": 1.0
}
```

**特点：** 温柔女声、稳重专业、标准语速

### 方案 3：正式播报

```python
"voice": "xiaochen",
"temperature": 0.3,
"beta_fields": {
    "speed": 1.0
}
```

**特点：** 成熟男声、平稳清晰、标准语速

### 方案 4：儿童互动

```python
"voice": "xiaoke",
"temperature": 0.9,
"beta_fields": {
    "speed": 1.0
}
```

**特点：** 儿童声音、活泼可爱、易懂

## 📝 如何修改配置

### 修改 test_with_wav.py

找到第 257-276 行的 `session_config`，修改相应参数：

```python
session_config = {
    "type": "session.update",
    "session": {
        "voice": "xiaoyu",      # 👈 修改这里
        "temperature": 0.8,     # 👈 修改这里
        "beta_fields": {
            "speed": 1.2        # 👈 修改这里
        }
    }
}
```

### 修改 realtime.py

找到第 422-442 行的 `session_config`，做相同修改。

### 修改 quick_start.py

它会自动使用 `realtime.py` 的配置。

## 🧪 测试不同配置

运行测试文件快速体验不同配置：

```bash
# 测试当前配置
python test_with_wav.py

# 测试其他音频文件
python test_with_wav.py glm-realtime-sdk/python/samples/input/call_zhangsan.wav
```

## ⚡ 快速调优技巧

如果觉得声音：

- **太粗犷** → 换成 `xiaoyu` 或 `xiaomei`
- **太慢** → 提高 `speed` 到 1.2-1.5
- **太机械** → 提高 `temperature` 到 0.7-0.9
- **太平淡** → 提高 `temperature`，选择活泼的声音
- **太快** → 降低 `speed` 到 0.9-1.0

## 💡 注意事项

1. **参数优先级：** 并非所有参数都一定生效，服务器可能有默认限制
2. **声音可用性：** 某些声音可能在特定区域不可用
3. **测试验证：** 修改后记得测试效果
4. **性能影响：** 过高的 temperature 可能略微增加延迟

## 🔄 实时调整

如果想在运行时切换配置，可以：

1. 修改配置文件
2. 重启程序
3. 新配置会在新会话中生效

---

**当前推荐配置：**
- Voice: `xiaoyu` (甜美女声)
- Temperature: `0.8` (自然活泼)
- Speed: `1.2` (稍快)

试试这个配置，应该会好很多！🎉

