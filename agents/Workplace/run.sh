#!/usr/bin/env bash
# Workplace (Apple DFT) agent — generate plans and always save Markdown.
# Usage:
#   ./run.sh plan [30|60|90|weekly|learning|1on1|custom] [YYYY-MM-DD]
#   ./run.sh save [kind] [YYYY-MM-DD]   # paste/pipe Markdown from Dify
#   ./run.sh list
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! curl -fsS http://127.0.0.1:11434/api/tags >/dev/null; then
  echo "Ollama is not running — starting…"
  sudo systemctl start ollama
  sleep 3
fi

exec python3 "$ROOT/workplace_agent.py" "$@"
