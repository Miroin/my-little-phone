# v2 部署说明

## 1. 后端

仓库根目录的 `render.yaml` 可创建一个带持久磁盘的 FastAPI 服务。部署时只把密钥填进服务商的加密环境变量，不要写入仓库或前端：

- `DEEPSEEK_API_KEY`
- `MINIMAX_API_KEY`
- `MINIMAX_VOICE_ID`
- `SCHEDULER_TOKEN`
- `MLP_ACCESS_TOKEN`（保护聊天、记忆、相册和付费模型接口的个人访问口令）
- `VAPID_SUBJECT`（通知发送者邮箱）

SQLite 与音频都写入 `/data`，重新部署不会丢失。正式迁移前仍应下载一份 v2 完整备份。

Render 蓝图会自动生成 `MLP_ACCESS_TOKEN`。部署完成后在 Render 环境变量中复制它，再填入小手叽“设置 → 模型与接口 → 个人访问口令”。不要把它写进仓库、截图或分享给其他人。

Web Push 的 VAPID 密钥会在首次启动时自动生成到 `/data/vapid.json`，无需手工粘贴，并会随持久磁盘保留。已有自备密钥时仍可同时设置 `VAPID_PUBLIC_KEY` 和 `VAPID_PRIVATE_KEY` 覆盖自动密钥。

## 2. 主动陪伴调度

仓库已包含 `.github/workflows/companion-scheduler.yml`，无需再找额外定时任务服务。在 GitHub 仓库设置中添加：

- Actions variable：`MLP_BACKEND_URL`，值为部署后的后端 HTTPS 地址。
- Actions secret：`MLP_SCHEDULER_TOKEN`，值与后端的 `SCHEDULER_TOKEN` 相同。

工作流每五分钟顺序调用：

1. `POST https://你的后端/api/companion/tick`
2. `POST https://你的后端/api/notifications/dispatch`

两个请求都带受保护的调度令牌。决策层没有固定每日次数，但若上一条主动消息或来电尚未得到回应，会自动等待；勿扰时段也不会触发。GitHub 定时任务可能有数分钟延迟，因此不是精确闹钟。

注意：GitHub 的定时工作流只会从仓库默认分支运行。开发阶段文件位于 `next-development` 时可以手动检查，但在正式启用后台陪伴前，必须把已经验收的工作流合并到默认分支；不要只在功能分支里填写变量后等待定时触发。

## 3. 前端

构建前设置 `VITE_API_BASE_URL` 为后端 HTTPS 地址，然后运行 `npm run build`，把 `dist/` 发布到 `v2-preview/`。

iPhone 后台通知必须满足：HTTPS、Safari“添加到主屏幕”、从主屏幕打开、用户主动点击“开启系统通知”。普通网页标签被关闭后不能承诺持续执行 JavaScript；主动决策由后端调度执行。

## 4. App

PWA 是当前可直接使用的安装形态。Capacitor 原生壳可以复用同一份 React 前端，但 iOS 的 CallKit、APNs 签名和上架包需要 Apple Developer Team、证书和真机权限；这些资料不应提交到公开仓库。
