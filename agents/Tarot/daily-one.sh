#!/usr/bin/env bash
# 每日一抽：手输牌；加 --draw 自动抽
# Usage:
#   ./daily-one.sh
#   ./daily-one.sh --draw -q "今日焦点" -y
#   ./daily-one.sh --offline 2026-07-19
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$ROOT/run-agent.sh" tarot_agent.py "$@"
