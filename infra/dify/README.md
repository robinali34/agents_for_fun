# Dify Docker — setup and operations

Run [Dify](https://github.com/langgenius/dify) with Docker Compose on Ubuntu, connected to local [Ollama](https://ollama.com/).

This folder ships a **custom `deploy.sh` only**. It does not include the full Dify source tree. Clone the official repo (e.g. to `~/dify`).

## Architecture

```text
Browser → localhost:80 (nginx)
              │
     ┌────────┼────────┐
     ▼        ▼        ▼
   web      api     worker …
     │
     └──► Host Ollama :11434  (e.g. qwen2.5:7b)
```

Dify runs in Docker; Ollama runs on the host. Containers must reach host port `11434` (`0.0.0.0`, not localhost-only).

## Prerequisites

- Docker + Compose v2
- Ollama installed with at least one model:

```bash
ollama pull qwen2.5:7b
```

- Optional NVIDIA GPU; Optimus laptops can use `infra/nvidia/nvidia-gpu-wake.service`

## First-time install

### 1. Clone upstream Dify

```bash
git clone https://github.com/langgenius/dify.git ~/dify
cd ~/dify/docker
cp .env.example .env
```

### 2. Install this repo’s deploy script

```bash
cp ~/rli/agents_for_fun/infra/dify/deploy.sh ~/dify/docker/deploy.sh
chmod +x ~/dify/docker/deploy.sh
```

### 3. Start

```bash
cd ~/dify/docker
./deploy.sh up
```

The script will:

1. Try to wake the GPU (Optimus)
2. Ensure Ollama is running
3. Create `.env` from `.env.example` if missing
4. Run `docker compose -f docker-compose.yaml up -d`

Open **http://localhost**

## Day-to-day commands

From `~/dify/docker`:

| Command | Action |
|---------|--------|
| `./deploy.sh up` | Start (GPU / Ollama checks included) |
| `./deploy.sh status` | List containers |
| `./deploy.sh logs` | Follow logs |
| `./deploy.sh restart` | Down then up |
| `./deploy.sh down` | Stop containers |

Native Compose equivalents:

```bash
cd ~/dify/docker
docker compose -f docker-compose.yaml up -d
docker compose ps
docker compose logs -f --tail=100
docker compose down
```

## Docker / `.env` notes

Config file: `~/dify/docker/.env` (**never commit**).

| Variable | Meaning | Typical local value |
|----------|---------|---------------------|
| `EXPOSE_NGINX_PORT` | Public HTTP port | `80` → http://localhost |
| `EXPOSE_NGINX_SSL_PORT` | HTTPS port | `443` |
| `NGINX_HTTPS_ENABLED` | Enable HTTPS | `false` for simple local use |
| `SECRET_KEY` | App secret | Keep stable after first boot |
| `INIT_PASSWORD` | Initial admin-related | Follow upstream docs |
| `CONSOLE_*` / `APP_*` URLs | Public / reverse-proxy URLs | Leave empty for localhost-only |

Data lives under `~/dify/docker/volumes/`. Stopping containers does not delete volumes unless you use `docker compose down -v` or remove the directory.

### Typical services

| Service | Role |
|---------|------|
| `nginx` | Public 80/443 |
| `web` | Frontend |
| `api` / `worker` | API and async jobs |
| `db_postgres` | Database |
| `redis` | Cache / queue |
| `weaviate` | Vector store |
| `sandbox` / `plugin_daemon` | Code sandbox and plugins |

Image tags follow your cloned Dify release (e.g. 1.16.x).

## Connect local Ollama

1. Open http://localhost  
2. Go to **Integrations → Model Provider → Ollama** (Dify 1.16+; older builds may use Settings)  
3. Set Base URL to a **host** address, e.g.:
   - `http://172.17.0.1:11434` (common Docker bridge gateway)
   - or your LAN IP: `http://192.168.x.x:11434`  
   Do **not** use `http://127.0.0.1:11434` from inside a container  
4. Add a model name such as `qwen2.5:7b`, save, and test

### If Dify cannot reach Ollama

```bash
ss -tlnp | grep 11434
curl -fsS http://127.0.0.1:11434/api/tags
```

If Ollama listens only on `127.0.0.1`, fix once:

```bash
sudo mkdir -p /etc/systemd/system/ollama.service.d
echo -e '[Service]\nEnvironment="OLLAMA_HOST=0.0.0.0:11434"' | sudo tee /etc/systemd/system/ollama.service.d/override.conf
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

`deploy.sh` prints the same hint when it detects a localhost-only bind.

## How this relates to terminal agents

| Use case | Tool |
|----------|------|
| Browser Chatflow / visual workflows | Dify (this guide) |
| Terminal Tarot / fitness Markdown | `agents/Tarot`, `agents/Fitness` |
| Apple DFT workplace onboarding Chatflow | `infra/dify/apps/apple-dft-onboarding/` |

Both share the same host Ollama instance.

### Ready-made app: Apple DFT Workplace Assistant

Importable Chatflow + knowledge docs for settling into a Senior SWE (DFT / hardware test) role:

```bash
# After Dify is up (http://localhost):
# Studio → Import DSL →
#   infra/dify/apps/apple-dft-onboarding/apple-dft-workplace-assistant.yml
```

See `apps/apple-dft-onboarding/README.md`. Personal notes: `~/AI_Data/Workplace/AppleDFT/`.

## Optional GPU wake

See `infra/nvidia/README.md` and `nvidia-gpu-wake.service`.

## Troubleshooting

| Symptom | Check |
|---------|-------|
| localhost unreachable | `./deploy.sh status`; `ss -tlnp \| grep ':80'` |
| First install hangs | `./deploy.sh logs`; disk space |
| Model calls fail | Ollama URL, model name, `nvidia-smi` |
| `.env` changes ignored | `./deploy.sh restart` |

## Privacy

- Never push `~/dify/docker/.env` to a public repo  
- Keep API keys and admin passwords local  
