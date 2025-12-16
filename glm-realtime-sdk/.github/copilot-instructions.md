# Copilot 使用说明（面向 AI 编码代理）

以下说明基于仓库可发现的事实，旨在让 AI 代理能快速、安全且可重复地在本项目中开展改动。

**项目结构与大局（为何这样拆）**
- 根目录包含多语言 SDK：`python/`, `golang/`, `frontend/`（TS/Vite）。各 SDK 实现同一实时 WebSocket RT API，方便多平台示例与集成。
- 根脚本 `realtime.py` 是一个参考端到端示例：采集麦克风、通过 WebSocket 发送 base64 编码的 PCM16 数据，并处理 `response.*` 消息。

**关键运行/构建命令（可直接复现）**
- 运行示例客户端（根目录）：
```
python realtime.py
```
- 运行后端/SDK 单元测试（Python）：
```
cd python
poetry install   # 项目使用 poetry/pyproject.toml
poetry run pytest -q
```
- 前端（Vite）：
```
cd frontend
# 若使用 pnpm: pnpm install && pnpm dev
# 或 npm: npm install && npm run dev
```
- Golang 测试/构建：
```
cd golang
go test ./...
```

**认证与环境**
- 服务端采用 JWT，但仓库中的客户端期望你通过环境变量 `ZHIPU_API_KEY` 提供原始 API Key（格式为 `API_KEY_ID.API_KEY_SECRET`）。见 `realtime.py` 中 `generate_jwt_token` 的实现。

**重要实现细节 / 可直接复用的模式**
- 音频格式与分块：采样率 `SAMPLE_RATE=16000`，每块 `CHUNK=1024`（64ms），客户端示例把多个 chunk 聚合为批量发送（`BATCH_SIZE=8`，约 512ms）。参见 `realtime.py:send_audio_loop`。
- 发送协议要点：WebSocket 消息类型常见为 `input_audio_buffer.append`, `input_audio_buffer.commit`, `response.create`，响应内包含 `response.audio.delta`, `response.text.delta`，以及 `response.output_item.done`（有时完整 audio base64 在这里）。
- 音频编码：使用 PCM16 int16 原始字节并 base64 编码。解码是 `np.frombuffer(bytes, dtype=np.int16)`（见 `realtime.py`）。
- 本地日志：对话/转写被记录到 `datas/save_data.jsonl`，记录器在 `data_logger.py`（修改该文件前注意兼容已有数据格式）。

**代码风格与工具链**
- Python：`pyproject.toml` 使用 Poetry，项目配置有 `ruff` 与 `black`，行宽 120。尽量保持这些格式化/lint 规则。
- Frontend：TypeScript + Vite，代码有 ESLint/Prettier 配置。修改 UI/TSX 时保持现有组件与 hooks（`frontend/src/hooks/useRealtimeChat.ts`）的调用约定。
- Go：模块化管理（`go.mod`），遵循标准 go module 工作流。

**对 AI 修改的具体约束与建议**
- 不要改变网络协议/消息类型（`type` 字段）或环境变量名称，除非同时更新所有 SDK 示例并标明兼容性影响。
- 对音频处理改动应保持兼容：输入为 PCM16、输出也应维持同格式或提供明确转换适配层。
- 修改记录器 `data_logger.py` 或 `datas/save_data.jsonl` 格式时，请同时提供向后兼容的迁移脚本或版本说明。

**快速定位示例（文件引用）**
- 端到端示例：`realtime.py`（麦克风采集、send loop、message handler、播放）
- Python SDK：`python/`（`pyproject.toml`、`rtclient/`）
- Frontend demo：`frontend/`（`package.json`、`src/`）
- Golang SDK：`golang/`（`go.mod`、`client/`、`events/`）
- 测试样例：`tests/`（API 验证示例 `tests/test_api.py`）

**当你不确定时该怎么做（优先级和提问）**
1. 小改动（注释、文档、日志）直接提交 PR，CI 通过后合并。
2. 侵入性改动（协议、数据格式、持久化格式）先在 issue 中描述兼容性影响并征询维护者意见。
3. 若需要运行私有/受限的 API（需要有效 `ZHIPU_API_KEY`），请在 PR 描述中注明如何本地复现（不在仓库中提交密钥）。

---
如果你希望我把说明合并进仓库（我已经准备好提交），或希望我补充更多示例（例如 `realtime.py` 中的消息样本或 `data_logger.py` 的 JSON schema），请告诉我哪些部分需要更详细的示例或格式说明。 
