# agents_for_fun

本机「好玩用」的 Agent 与 AI 栈小合集：

- **终端 Agent**：塔罗解读、健身日记（Ollama + Markdown）
- **Dify**：Docker 一键部署脚本，网页里搭 Chatflow / Agent
- **NVIDIA**：笔记本 Optimus GPU 唤醒（可选）

不包含完整 [Dify 上游源码](https://github.com/langgenius/dify)；请官方仓库另装，再用本仓库脚本。

## 仓库结构

```text
agents/
  Tarot/     # 本地塔罗（抽牌 / 语料 / 可选联网）
  Fitness/   # 健身记录
infra/
  dify/      # Docker 部署说明 + deploy.sh   ← 从这里读 Dify 用法
  nvidia/    # GPU 开机唤醒 systemd 单元
```

## 快速开始

### 1）终端塔罗（不依赖 Dify）

```bash
cd agents/Tarot
./fetch-corpus.sh
./tarot.sh
# 或一键：
./tarot.sh 3 --draw -q "下周如何安排" -y --offline
```

详见 [`agents/Tarot/README.md`](agents/Tarot/README.md)。

### 2）健身日记

```bash
cd agents/Fitness
./run.sh
```

### 3）Dify（Docker）

完整步骤（环境、`.env`、Compose、连 Ollama、排错）：

**→ [`infra/dify/README.md`](infra/dify/README.md)**

最短路径：

```bash
git clone https://github.com/langgenius/dify.git ~/dify
cd ~/dify/docker && cp .env.example .env

# 从本仓库拷脚本
cp /path/to/agents_for_fun/infra/dify/deploy.sh ./deploy.sh
chmod +x deploy.sh
./deploy.sh up
```

浏览器打开 http://localhost ，在 **Integrations → Model Provider → Ollama** 填宿主机地址（如 `http://172.17.0.1:11434`）。

## 前置

| 组件 | 用途 |
|------|------|
| [Ollama](https://ollama.com/) + `qwen2.5:7b` 等 | 终端 Agent 与 Dify 共用 |
| Docker / Compose | 仅跑 Dify 需要 |
| NVIDIA 驱动（可选） | 加速推理；Optimus 见 `infra/nvidia/` |

## 隐私与 Git

- 不提交 `.env`、API Key、个人占卜/健身日记  
- `.gitignore` 已排除 `questions/`、按日期 md、`.venv`、`volumes/`  
- 语料来自公开 Pictorial Key + 本地博客构建脚本  

## License

本仓库脚本按个人使用分发；Dify 本体遵循其官方 License。
