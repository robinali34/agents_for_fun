#!/usr/bin/env bash
#
# Deploy & run the local AI Agent stack (Dify + Ollama) on localhost.
#   Usage:  ./deploy.sh [up|down|restart|status|logs]
#
set -euo pipefail

# --- config -----------------------------------------------------------------
DIFY_DOCKER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OLLAMA_PORT=11434
GPU_PCI="0000:01:00.0"                 # RTX 5070 Laptop
DIFY_URL="http://localhost"
# ---------------------------------------------------------------------------

log()  { printf '\033[1;34m[deploy]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[warn]\033[0m %s\n' "$*"; }
err()  { printf '\033[1;31m[error]\033[0m %s\n' "$*" >&2; }

wake_gpu() {
  if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then
    log "GPU already awake: $(nvidia-smi -L | head -1)"
    return
  fi
  warn "GPU asleep (Optimus D3cold). Waking it (needs sudo)..."
  echo on | sudo tee "/sys/bus/pci/devices/${GPU_PCI}/power/control" >/dev/null || true
  sudo systemctl start nvidia-persistenced.service 2>/dev/null || true
  sudo /sbin/ub-device-create 2>/dev/null || true
  nvidia-smi -L 2>/dev/null | head -1 || warn "GPU still not visible; Ollama will fall back to CPU."
}

ensure_ollama() {
  if curl -fsS "http://127.0.0.1:${OLLAMA_PORT}/api/tags" >/dev/null 2>&1; then
    log "Ollama is running on :${OLLAMA_PORT}"
  else
    log "Starting Ollama service..."
    sudo systemctl start ollama 2>/dev/null || (ollama serve >/tmp/ollama-serve.log 2>&1 &)
    sleep 3
  fi
  # Confirm it listens on all interfaces so Dify containers can reach it
  if ss -tlnp 2>/dev/null | grep -q "127.0.0.1:${OLLAMA_PORT}"; then
    warn "Ollama is bound to 127.0.0.1 only — Dify containers cannot reach it."
    warn "Fix once with:"
    warn "  sudo mkdir -p /etc/systemd/system/ollama.service.d"
    warn "  echo -e '[Service]\\nEnvironment=\"OLLAMA_HOST=0.0.0.0:${OLLAMA_PORT}\"' | sudo tee /etc/systemd/system/ollama.service.d/override.conf"
    warn "  sudo systemctl daemon-reload && sudo systemctl restart ollama"
  fi
}

ensure_env() {
  if [[ ! -f "${DIFY_DOCKER_DIR}/.env" ]]; then
    log "Creating .env from .env.example"
    cp "${DIFY_DOCKER_DIR}/.env.example" "${DIFY_DOCKER_DIR}/.env"
  fi
}

compose() { docker compose -f "${DIFY_DOCKER_DIR}/docker-compose.yaml" "$@"; }

cmd_up() {
  wake_gpu
  ensure_ollama
  ensure_env
  log "Starting Dify containers..."
  compose up -d
  log "Waiting for services..."
  sleep 5
  compose ps
  echo
  log "Dify is up →  ${DIFY_URL}"
  log "Ollama models:"
  curl -fsS "http://127.0.0.1:${OLLAMA_PORT}/api/tags" 2>/dev/null \
    | grep -o '"name":"[^"]*"' | cut -d'"' -f4 | sed 's/^/  - /' || true
}

cmd_down()    { log "Stopping Dify containers..."; compose down; }
cmd_restart() { cmd_down; cmd_up; }
cmd_status()  { compose ps; }
cmd_logs()    { compose logs -f --tail=100; }

case "${1:-up}" in
  up)      cmd_up ;;
  down)    cmd_down ;;
  restart) cmd_restart ;;
  status)  cmd_status ;;
  logs)    cmd_logs ;;
  *) err "Unknown command: $1"; echo "Usage: $0 [up|down|restart|status|logs]"; exit 1 ;;
esac
