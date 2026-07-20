#!/usr/bin/env bash
# Three-card question; add --draw to auto-draw
# Usage: ./question-3.sh [--draw] [-q "question"] [--offline] [-y] [YYYY-MM-DD]
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$ROOT/run-agent.sh" question_agent.py 3 "$@"
