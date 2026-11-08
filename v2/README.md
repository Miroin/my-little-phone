# 小手叽 v2

v2 在不影响旧版 `index.html` 的前提下重建。目标是让网页、PWA 和后续 App 共用同一套前端与后端，而不是继续把所有功能堆进单个 HTML。

## 目录

- `frontend/`：React + TypeScript + Vite。负责聊天、通话、记忆和设置界面。
- `backend/`：FastAPI。负责模型请求、密钥保护、统一记录聊天与通话，并给主动消息和推送预留入口。

## 当前实现

- 聊天、通话、记忆使用统一会话数据结构。
- DeepSeek、MiniMax 密钥只从服务端环境变量读取。
- 浏览器不持有模型密钥；只在用户设备本地保存独立的服务访问口令。
- 通话记录保留双方身份、时长与逐轮原文，并支持浏览器语音识别、模型回复和 MiniMax 自动播放。
- 主动陪伴、主动来电、PWA 推送、人物档案、完整备份和 Capacitor iOS/Android 工程已经接入。

## 记忆后端（第一层已落地）

- `memory_items`：人格、关系、用户、事件、感受、计划和互动样本分层保存。
- `memory_evidence`：保存可回查的原始聊天证据和 SHA-256 指纹。
- `memory_jobs`：为历史导入、提取、向量化、合并与备份保存断点状态。
- `memory_feedback`：按消息和场景保存“像/不像沈砚”的评价。
- `memory_usage`：记录每次回复实际使用了哪些记忆，便于排查。
- `/api/memory-search`：当前提供不依赖向量服务的关键词降级检索。

完整原则、数据结构和实施顺序见 [`MEMORY_DESIGN.md`](./MEMORY_DESIGN.md)。

历史聊天迁移只读取原文件并生成预览，候选必须人工确认才写入长期记忆，绝不会自动清空旧数据。部署与外部账号步骤见 [`DEPLOYMENT.md`](./DEPLOYMENT.md)，准确完成度见 [`STATUS.md`](./STATUS.md)。
