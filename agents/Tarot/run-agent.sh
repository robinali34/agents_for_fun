#!/usr/bin/env bash
# Internal runner: ensure Ollama + venv (default web search; --offline skips network).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="${1:?missing Python script}"
shift

if [[ ! -f "$ROOT/corpus/waite-rws.json" ]]; then
  echo "本地语料不存在，正在构建……"
  "$ROOT/fetch-corpus.sh"
fi

if ! curl -fsS http://127.0.0.1:11434/api/tags >/dev/null; then
  echo "Ollama 未运行，正在启动……"
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
  echo "创建本地虚拟环境……"
  python3 -m venv "$ROOT/.venv"
  "$ROOT/.venv/bin/pip" install -U pip
fi

if [[ "$OFFLINE" -eq 0 ]]; then
  if ! "$PYTHON" -c 'import ddgs' >/dev/null 2>&1; then
    echo "安装 ddgs（联网搜索）……"
    "$ROOT/.venv/bin/pip" install -U ddgs
  fi
fi

exec "$PYTHON" "$ROOT/$SCRIPT" "$@"
