# agents_for_fun

本地好玩的 Agent 工具集：塔罗、健身记录，以及把 Dify + Ollama 跑在本机的部署脚本。

> **说明：** 这里**不包含**完整的 [langgenius/dify](https://github.com/langgenius/dify) 源码（体积大且应走官方仓库）。  
> 只同步你自己的 Agent 代码，以及本机部署相关的自定义脚本。

## 目录

```text
agents/
  Tarot/          # 本地塔罗 Agent（Ollama + 语料 + 可选联网）
  Fitness/        # 健身日记 Agent
infra/
  dify/deploy.sh  # 唤醒 GPU、启动 Ollama、docker compose up
  nvidia/         # Optimus 笔记本 GPU 唤醒 systemd 单元
```

## 前置

- Ubuntu + NVIDIA GPU（可选，Ollama 可走 CPU）
- [Ollama](https://ollama.com/) + 模型如 `qwen2.5:7b`
- Docker / Compose（跑 Dify 时需要）

## 塔罗 Agent

```bash
cd agents/Tarot
./fetch-corpus.sh          # 首次构建本地 78 牌语料
./tarot.sh                 # 菜单
./tarot.sh 3 --draw -q "下周如何安排" -y --offline
```

个人日记（`questions/`、按日期的 md）默认不进仓库，见 `.gitignore`。

## 健身 Agent

```bash
cd agents/Fitness
./run.sh
```

## Dify（本机部署）

1. 克隆官方仓库（与本 repo 分开）：

```bash
git clone https://github.com/langgenius/dify.git ~/dify
cd ~/dify/docker
cp .env.example .env
```

2. 使用本仓库的部署脚本：

```bash
cp infra/dify/deploy.sh ~/dify/docker/deploy.sh
chmod +x ~/dify/docker/deploy.sh
~/dify/docker/deploy.sh up
```

3. 浏览器打开 `http://localhost`，在 Integrations → Model Provider 连接本机 Ollama（`http://host.docker.internal:11434` 或宿主机 IP）。

### GPU 开机唤醒（MSI / Optimus）

```bash
sudo cp infra/nvidia/nvidia-gpu-wake.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now nvidia-gpu-wake.service
```

## 隐私

- 不提交 `.env`、API Key、个人占卜/健身日记
- 语料 `waite-rws.json` 来自公开 Pictorial Key + 本地博客构建脚本

## License

Agent 脚本按个人使用分发；Dify 本体遵循其官方 License。
