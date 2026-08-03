#!/usr/bin/env bash
# Ensure Ollama, then run the 50-day challenge agent.
# Usage:
#   ./run.sh              # log today (multi-goal)
#   ./run.sh status
#   ./run.sh setup
#   ./run.sh goals [list|add|pause X|resume X]
#   ./run.sh 2026-07-19
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! curl -fsS http://127.0.0.1:11434/api/tags >/dev/null; then
  echo "Ollama is not running — starting…"
  sudo systemctl start ollama
  sleep 3
fi

exec python3 "$ROOT/challenge50_agent.py" "$@"
