# v2 部署说明

## 1. 后端

仓库根目录的 `render.yaml` 可创建一个带持久磁盘的 FastAPI 服务。部署时只把密钥填进服务商的加密环境变量，不要写入仓库或前端：

- `DEEPSEEK_API_KEY`
- `MINIMAX_API_KEY`
- `MINIMAX_VOICE_ID`
- `SCHEDULER_TOKEN`
- `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY` / `VAPID_SUBJECT`

SQLite 与音频都写入 `/data`，重新部署不会丢失。正式迁移前仍应下载一份 v2 完整备份。

## 2. 主动陪伴调度

使用云平台的定时任务，每隔数分钟顺序调用：

1. `POST https://你的后端/api/companion/tick`
2. `POST https://你的后端/api/notifications/dispatch`

两个请求都带请求头 `X-Scheduler-Token: 你的 SCHEDULER_TOKEN`。决策层没有固定每日次数，但若上一条主动消息或来电尚未得到回应，会自动等待；勿扰时段也不会触发。

## 3. 前端

构建前设置 `VITE_API_BASE_URL` 为后端 HTTPS 地址，然后运行 `npm run build`，把 `dist/` 发布到 `v2-preview/`。

iPhone 后台通知必须满足：HTTPS、Safari“添加到主屏幕”、从主屏幕打开、用户主动点击“开启系统通知”。普通网页标签被关闭后不能承诺持续执行 JavaScript；主动决策由后端调度执行。

## 4. App

PWA 是当前可直接使用的安装形态。Capacitor 原生壳可以复用同一份 React 前端，但 iOS 的 CallKit、APNs 签名和上架包需要 Apple Developer Team、证书和真机权限；这些资料不应提交到公开仓库。
