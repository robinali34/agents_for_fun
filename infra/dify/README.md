# Dify Docker：本机设置与启动

在 Ubuntu 上用 Docker Compose 跑 [Dify](https://github.com/langgenius/dify)，并连接本机 [Ollama](https://ollama.com/)。

本目录只提供 **自定义部署脚本**，不包含 Dify 完整源码。官方代码请单独克隆到例如 `~/dify`。

## 架构（简图）

```text
浏览器 → localhost:80 (nginx)
              │
     ┌────────┼────────┐
     ▼        ▼        ▼
   web      api     worker …
     │
     └──► 宿主机 Ollama :11434  (qwen2.5:7b 等)
```

Dify 跑在 Docker 里；Ollama 跑在宿主机。容器必须能访问宿主机的 `11434`（绑定 `0.0.0.0`，不能只听 `127.0.0.1`）。

## 前置条件

- Docker + Docker Compose v2
- Ollama 已安装，并已拉取至少一个模型，例如：

```bash
ollama pull qwen2.5:7b
```

- （可选）NVIDIA GPU；笔记本 Optimus 可配合仓库里的 `infra/nvidia/nvidia-gpu-wake.service`

## 第一次安装

### 1. 克隆官方 Dify

```bash
git clone https://github.com/langgenius/dify.git ~/dify
cd ~/dify/docker
cp .env.example .env
```

### 2. 安装本仓库的 deploy 脚本

在 `agents_for_fun` 仓库根目录执行：

```bash
cp infra/dify/deploy.sh ~/dify/docker/deploy.sh
chmod +x ~/dify/docker/deploy.sh
```

### 3. 启动

```bash
cd ~/dify/docker
./deploy.sh up
```

脚本会依次：

1. 尝试唤醒 GPU（Optimus 笔记本）
2. 确认 / 启动 Ollama
3. 若缺少 `.env` 则从 `.env.example` 复制
4. `docker compose -f docker-compose.yaml up -d`

浏览器打开：**http://localhost**

## 日常命令

在 `~/dify/docker` 下：

| 命令 | 作用 |
|------|------|
| `./deploy.sh up` | 启动（含 GPU / Ollama 检查） |
| `./deploy.sh status` | 查看容器状态 |
| `./deploy.sh logs` | 跟踪日志 |
| `./deploy.sh restart` | 先 down 再 up |
| `./deploy.sh down` | 停止容器 |

等价的原生 Compose：

```bash
cd ~/dify/docker
docker compose -f docker-compose.yaml up -d
docker compose ps
docker compose logs -f --tail=100
docker compose down
```

## Docker / `.env` 要点

配置文件：`~/dify/docker/.env`（**不要提交到 Git**）。

| 变量 | 含义 | 本机常用 |
|------|------|----------|
| `EXPOSE_NGINX_PORT` | 对外 HTTP 端口 | `80` → http://localhost |
| `EXPOSE_NGINX_SSL_PORT` | HTTPS 端口 | `443` |
| `NGINX_HTTPS_ENABLED` | 是否开 HTTPS | 本机可先 `false` |
| `SECRET_KEY` | 应用密钥 | 首次生成后勿随意改 |
| `INIT_PASSWORD` | 初始管理员相关 | 按官方说明设置 |
| `CONSOLE_*` / `APP_*` URL | 公网/反代地址 | 纯本机可留空 |

数据落在 `~/dify/docker/volumes/`（数据库、上传文件等）。删容器不会自动清 volumes，除非你手动删目录或 `docker compose down -v`。

### 主要容器（典型）

| 服务 | 作用 |
|------|------|
| `nginx` | 对外 80/443 |
| `web` | 前端 |
| `api` / `worker` | 后端与异步任务 |
| `db_postgres` | 数据库 |
| `redis` | 缓存 / 队列 |
| `weaviate` | 向量库 |
| `sandbox` / `plugin_daemon` | 代码沙箱与插件 |

版本号随你克隆的 Dify 发布版变化（例如 1.16.x）。

## 连接本机 Ollama

1. 打开 http://localhost  
2. 进入 **Integrations → Model Provider → Ollama**（Dify 1.16+；旧版可能在 Settings）  
3. Base URL 填**宿主机**地址，例如：
   - `http://172.17.0.1:11434`（常见 Docker bridge 网关）
   - 或本机局域网 IP：`http://192.168.x.x:11434`  
   **不要**填容器内的 `http://127.0.0.1:11434`  
4. 添加模型名，如 `qwen2.5:7b`，保存并测试

### 若 Dify 连不上 Ollama

确认监听地址：

```bash
ss -tlnp | grep 11434
curl -fsS http://127.0.0.1:11434/api/tags
```

若只绑定了 `127.0.0.1`，容器访问不到。一次性修复：

```bash
sudo mkdir -p /etc/systemd/system/ollama.service.d
echo -e '[Service]\nEnvironment="OLLAMA_HOST=0.0.0.0:11434"' | sudo tee /etc/systemd/system/ollama.service.d/override.conf
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

`deploy.sh` 检测到仅本机绑定时也会打印上述提示。

## 与终端 Agent 的分工

| 场景 | 用什么 |
|------|--------|
| 网页 Chatflow / 可视化工作流 | Dify（本页） |
| 终端塔罗 / 健身写本地 Markdown | 仓库 `agents/Tarot`、`agents/Fitness` |

两者共用本机 Ollama，互不替代。

## GPU 开机唤醒（可选）

见仓库 `infra/nvidia/nvidia-gpu-wake.service`：

```bash
sudo cp infra/nvidia/nvidia-gpu-wake.service /etc/systemd/system/
# 如有需要，编辑文件中的 PCI 地址以匹配本机 GPU
sudo systemctl daemon-reload
sudo systemctl enable --now nvidia-gpu-wake.service
```

## 故障排查速查

| 现象 | 检查 |
|------|------|
| 打不开 localhost | `./deploy.sh status`；`ss -tlnp \| grep ':80'` |
| 首次安装卡住 | 看 `./deploy.sh logs`；确认磁盘空间 |
| 模型调用失败 | Ollama URL、模型名、GPU/`nvidia-smi` |
| 改 `.env` 不生效 | `./deploy.sh restart` |

## 隐私

- 勿把 `~/dify/docker/.env` 推进任何公开仓库  
- API Key、管理员密码只放在本机 `.env` 或密钥管理里  
