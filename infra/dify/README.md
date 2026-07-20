# Dify 本地部署脚本

`deploy.sh` 用于在本机（Ubuntu + 可选 NVIDIA GPU）拉起：

1. 唤醒 Optimus GPU（如需要）
2. 确认 Ollama 在 `0.0.0.0:11434` 可被 Docker 访问
3. `docker compose up -d` 启动 Dify

## 用法

把本文件放到官方 Dify 的 `docker/` 目录后执行：

```bash
./deploy.sh up
./deploy.sh status
./deploy.sh logs
./deploy.sh down
```

请先：

```bash
cp .env.example .env
```

**不要**把含密钥的 `.env` 提交到 Git。
