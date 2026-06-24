# Tour Ops System on Render

这是一个可部署到 Render 的旅行社团队报账系统，包含企业微信回调入口。

## 功能

- `/` 健康检查
- `/dashboard` 报账系统后台
- `/api/state` 团队共享数据读写
- `/api/wecom/callback` 企业微信回调接口
- `/api/wecom/send-test` 企业微信测试消息接口

## Render 部署步骤

1. 把本目录上传到一个 GitHub 仓库。
2. 打开 Render，选择 New Web Service。
3. 连接这个 GitHub 仓库。
4. Render 会读取 `render.yaml` 自动部署。
5. 部署完成后得到类似 `https://tour-ops-system.onrender.com` 的 HTTPS 地址。
6. 打开 `https://你的地址.onrender.com/dashboard` 使用系统。

## 企业微信配置

在企业微信管理后台创建自建应用后，配置：

- 回调 URL：`https://你的地址.onrender.com/api/wecom/callback`
- Token：填入 Render 环境变量 `WECOM_CALLBACK_TOKEN` 的同一个值
- 企业 ID：填入 `WECOM_CORP_ID`
- AgentId：填入 `WECOM_AGENT_ID`
- Secret：填入 `WECOM_AGENT_SECRET`

## 重要说明

Render 默认文件系统在重新部署时可能不是长期持久存储。正式使用建议：

- 给 Render 服务挂载 Persistent Disk，并把 `APP_DATA_DIR` 指到磁盘路径
- 或后续改接 PostgreSQL / 对象存储

图片附件当前会随报账数据保存，适合小团队试运行。正式大量上传发票和转账截图时，建议改为 NAS、S3 或企业微信素材存储。
