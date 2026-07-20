#!/usr/bin/env bash
# 带问题五牌；加 --draw 自动抽
# Usage: ./question-5.sh [--draw] [-q 问题] [--offline] [-y] [YYYY-MM-DD]
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$ROOT/run-agent.sh" question_agent.py 5 "$@"
