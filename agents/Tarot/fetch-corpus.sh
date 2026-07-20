#!/usr/bin/env bash
# Download / rebuild local Tarot interpretation corpus.
# Usage: ./fetch-corpus.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORPUS="$ROOT/corpus"
API_URL="https://raw.githubusercontent.com/ekelen/tarot-api/master/static/card_data.json"

mkdir -p "$CORPUS"

echo "1/2 Downloading public Pictorial Key data (tarot-api)…"
curl -fsSL "$API_URL" -o "$CORPUS/tarot-api-cards.json"
python3 - <<PY
import json
from pathlib import Path
path = Path("$CORPUS/tarot-api-cards.json")
data = json.loads(path.read_text())
print(f"  cards: {len(data['cards'])}")
PY

echo "2/2 Merging optional local blog notes (if present)…"
python3 "$ROOT/scripts/build_corpus.py"

echo
echo "Done. Corpus files:"
echo "  $CORPUS/waite-rws.json"
echo "  $CORPUS/index.md"
echo
echo "Agents prefer local corpus; omit --offline to allow web enrichment."
