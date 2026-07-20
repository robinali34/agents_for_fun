#!/usr/bin/env bash
# Download / rebuild local Tarot interpretation corpus.
# Usage: ./fetch-corpus.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORPUS="$ROOT/corpus"
API_URL="https://raw.githubusercontent.com/ekelen/tarot-api/master/static/card_data.json"

mkdir -p "$CORPUS"

echo "1/2 下载公开 Pictorial Key 牌义（tarot-api）……"
curl -fsSL "$API_URL" -o "$CORPUS/tarot-api-cards.json"
python3 - <<'PY'
import json
from pathlib import Path
path = Path("/home/robina/AI_Data/Tarot/corpus/tarot-api-cards.json")
data = json.loads(path.read_text())
print(f"  cards: {len(data['cards'])}")
PY

echo "2/2 合并本地博客韦特全牌解析……"
python3 "$ROOT/scripts/build_corpus.py"

echo
echo "完成。语料位置："
echo "  $CORPUS/waite-rws.json"
echo "  $CORPUS/index.md"
echo
echo "Agent 默认优先使用本地语料；需要联网补充时加 --web"
