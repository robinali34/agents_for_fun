#!/usr/bin/env bash
# Internal runner: ensure Ollama + venv (web search by default; --offline skips network).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="${1:?missing Python script}"
shift

if [[ ! -f "$ROOT/corpus/waite-rws.json" ]]; then
  echo "Local corpus missing — building…"
  "$ROOT/fetch-corpus.sh"
fi

if ! curl -fsS http://127.0.0.1:11434/api/tags >/dev/null; then
  echo "Ollama is not running — starting…"
  sudo systemctl start ollama
  sleep 3
fi

OFFLINE=0
for arg in "$@"; do
  if [[ "$arg" == "--offline" ]]; then
    OFFLINE=1
    break
  fi
done

PYTHON="$ROOT/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  echo "Creating local venv…"
  python3 -m venv "$ROOT/.venv"
  "$ROOT/.venv/bin/pip" install -U pip
fi

if [[ "$OFFLINE" -eq 0 ]]; then
  if ! "$PYTHON" -c 'import ddgs' >/dev/null 2>&1; then
    echo "Installing ddgs (web search)…"
    "$ROOT/.venv/bin/pip" install -U -r "$ROOT/requirements.txt"
  fi
fi

exec "$PYTHON" "$ROOT/$SCRIPT" "$@"
