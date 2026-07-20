# agents_for_fun

A small local stack for fun agents and AI tooling:

- **Terminal agents** — Tarot, fitness logs, **50-day challenge** (Ollama → Markdown)
- **Dify** — Docker deploy helper for browser Chatflows / Agents
- **NVIDIA** — optional Optimus laptop GPU wake service

This repo does **not** vendor the full [Dify upstream](https://github.com/langgenius/dify). Clone Dify separately, then use the scripts here.

**Repo location (this machine):** `~/rli/agents_for_fun`

**Everyday launchers (journals stay here):** `~/AI_Data/` — thin `.sh` wrappers call this repo after reboot without re-setup. See `~/AI_Data/README.md`.

## Layout

```text
agents/
  Tarot/        # Local RWS corpus + draw / interpret CLI
  Fitness/      # Daily fitness journal CLI
  Challenge50/  # 50-day challenge accountability CLI
infra/
  dify/         # Docker deploy docs + deploy.sh
  nvidia/       # GPU wake systemd unit
```

## Dependencies

| Dependency | Required for | Notes |
|------------|--------------|--------|
| Python 3.10+ | Tarot, Fitness, Challenge50 | stdlib + optional venv |
| [Ollama](https://ollama.com/) | All local LLM calls | Default model: `qwen2.5:7b` |
| `curl`, `bash` | Launch scripts | |
| Docker + Compose v2 | Dify only | |
| `ddgs` (PyPI) | Tarot **web** search | Installed into `agents/Tarot/.venv` automatically when needed |
| Optional blog dir | Tarot corpus rebuild / local excerpts | `TAROT_BLOG_POSTS` (default `~/rli/blog_book_notes/_posts`) |
| NVIDIA driver (optional) | Faster Ollama | See `infra/nvidia/` on Optimus laptops |

Quick checks:

```bash
python3 --version
curl -fsS http://127.0.0.1:11434/api/tags | head
docker compose version   # only if using Dify
```

## Quick start

### 1) Tarot (no Dify)

```bash
cd ~/rli/agents_for_fun/agents/Tarot
./fetch-corpus.sh          # once: rebuild local 78-card corpus
./tarot.sh                 # menu
./tarot.sh 3 --draw -q "How should I plan next week?" -y --offline
```

See [`agents/Tarot/README.md`](agents/Tarot/README.md).

### 2) Fitness log

```bash
cd ~/rli/agents_for_fun/agents/Fitness
./run.sh
# or: ~/AI_Data/Fitness/run.sh
```

### 3) 50-day challenge

```bash
~/AI_Data/Challenge50/setup.sh    # once
~/AI_Data/Challenge50/run.sh      # daily log
~/AI_Data/Challenge50/status.sh   # Day N/50
```

See [`agents/Challenge50/README.md`](agents/Challenge50/README.md).

### 4) Dify (Docker)

Full guide: **[`infra/dify/README.md`](infra/dify/README.md)**

```bash
git clone https://github.com/langgenius/dify.git ~/dify
cd ~/dify/docker && cp .env.example .env

cp ~/rli/agents_for_fun/infra/dify/deploy.sh ./deploy.sh
chmod +x deploy.sh
./deploy.sh up
```

Open http://localhost → **Integrations → Model Provider → Ollama**  
Use a host-reachable base URL such as `http://172.17.0.1:11434` (not container `127.0.0.1`).

## Privacy

- Do not commit `.env`, API keys, or personal journals
- `.gitignore` excludes dated notes, `questions/`, `.venv`, Docker volumes
- Bundled card text comes from public Pictorial Key data (+ optional local blog rebuild)

## License

Scripts in this repo are for personal use. Dify itself follows its upstream license.
