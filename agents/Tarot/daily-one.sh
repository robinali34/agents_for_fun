#!/usr/bin/env bash
# Daily one-card: manual entry; add --draw to auto-draw
# Usage:
#   ./daily-one.sh
#   ./daily-one.sh --draw -q "Focus for today" -y
#   ./daily-one.sh --offline 2026-07-19
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$ROOT/run-agent.sh" tarot_agent.py "$@"
