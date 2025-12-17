# ✅ Function Call 使用前检查清单

使用真实 Function Call 前，请确保完成以下步骤：

## 🔧 必需配置

### [ ] 1. Claude Code 服务已运行
```bash
curl http://localhost:8000/health
```
✅ 返回 200 OK = 正常  
❌ 连接失败 = 需要启动服务

---

### [ ] 2. 配置文件正确
检查 `agents/claude_code_client.py` 第 238 行：
```python
claude_code_client = ClaudeCodeClient(
    base_url="http://localhost:8000",  # ← 确认这个地址正确
    # ...
)
```

---

### [ ] 3. 环境变量已设置
`.env` 文件包含：
```bash
ZHIPU_API_KEY=your-api-key-here  # ← 必需
```

---

### [ ] 4. 测试连接成功
```bash
python tests/test_agent_integration.py
```
应该看到：✅ 连接成功

---

## 🚀 启动步骤

### [ ] 5. 启动带 Agent 的版本
```bash
python run_with_agent.py
```

### [ ] 6. 等待就绪提示
看到：🎤 Ready! Start speaking...

---

## 💬 对话测试

### [ ] 7. 说出测试请求

**试试这些：**
- ✅ "帮我规划一个去北京的旅行"
- ✅ "我要订明天去上海的火车票"
- ✅ "帮我订一个杭州的酒店"

---

## 🔍 验证成功

### [ ] 8. 确认 Function Call 被触发

**看到这些输出 = 成功：**
```
🔔 收到 Function Call: plan_trip
🤖 正在调用 Claude Code Agent...
✅ 执行完成
```

---

## ❌ 如果失败

1. **检查 Claude Code 服务**
   ```bash
   curl http://localhost:8000/health
   ```

2. **查看错误日志**
   ```bash
   python run_with_agent_show_all_details.py
   tail -f result.txt
   ```

3. **运行测试脚本**
   ```bash
   python tests/test_function_call.py
   python tests/test_agent_integration.py
   ```

4. **检查配置文件**
   - `agents/claude_code_client.py`
   - `.env`

---

## 📋 快速命令参考

```bash
# 1. 检查服务
curl http://localhost:8000/health

# 2. 启动助手
python run_with_agent.py

# 3. 详细日志模式
python run_with_agent_show_all_details.py

# 4. 运行测试
python tests/test_function_call.py
python tests/test_agent_integration.py

# 5. 查看日志
tail -f result.txt
```

---

## 🎯 完成！

当所有 ✅ 都勾选后，你就可以开始使用 Function Call 了！

详细文档：[docs/guides/FUNCTION_CALL_USAGE.md](docs/guides/FUNCTION_CALL_USAGE.md)

