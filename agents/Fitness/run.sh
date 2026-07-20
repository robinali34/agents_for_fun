#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! curl -fsS http://127.0.0.1:11434/api/tags >/dev/null; then
  echo "Ollama 未运行，正在启动……"
  sudo systemctl start ollama
  sleep 3
fi

exec python3 "$ROOT/fitness_agent.py"
