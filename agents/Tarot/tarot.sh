#!/usr/bin/env bash
# Unified Tarot launcher.
# Usage:
#   ./tarot.sh
#   ./tarot.sh daily --draw -q "Focus for today" -y --offline
#   ./tarot.sh 3 --draw -q "How should I plan next week?" -y
#   ./tarot.sh 5 --draw -q "Project bottleneck" --offline
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<'EOF'
Local Tarot agent

Usage:
  ./tarot.sh                  Interactive menu
  ./tarot.sh daily [opts]     Daily single card
  ./tarot.sh 3|question-3     Three-card (Situation / Obstacle / Advice)
  ./tarot.sh 5|question-5     Five-card spread

Options:
  --draw / --auto     Auto-draw from 78 cards (manual entry still available)
  -q / --question     Question text (skips some prompts)
  --offline           Local corpus only (no web)
  -y / --yes          Skip confirm / overwrite prompts
  --seed TEXT         Reproducible draw seed
  YYYY-MM-DD          Date override

Examples:
  ./tarot.sh daily --draw -q "What should I notice today?" -y
  ./tarot.sh 3 --draw -q "How should I plan next week?" -y --offline
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

MODE="${1:-}"
if [[ -n "$MODE" && "$MODE" != "-"* ]]; then
  shift
fi

run_daily() {
  exec "$ROOT/run-agent.sh" tarot_agent.py "$@"
}

run_q() {
  local n="$1"
  shift
  exec "$ROOT/run-agent.sh" question_agent.py "$n" "$@"
}

case "$MODE" in
  "" )
    echo "Local Tarot agent"
    echo "1) Daily one card (manual)"
    echo "2) Daily one card (auto-draw)"
    echo "3) Three-card question (manual)"
    echo "4) Three-card question (auto-draw)"
    echo "5) Five-card question (auto-draw)"
    echo "6) Rebuild local corpus"
    echo "q) Quit"
    read -r -p "Choice: " choice
    case "$choice" in
      1) run_daily ;;
      2) run_daily --draw ;;
      3) run_q 3 ;;
      4) run_q 3 --draw ;;
      5) run_q 5 --draw ;;
      6) exec "$ROOT/fetch-corpus.sh" ;;
      q|Q) exit 0 ;;
      *) echo "Invalid choice"; exit 1 ;;
    esac
    ;;
  daily|one|1) run_daily "$@" ;;
  3|question-3|q3) run_q 3 "$@" ;;
  5|question-5|q5) run_q 5 "$@" ;;
  help) usage ;;
  *)
    echo "Unknown mode: $MODE"
    usage
    exit 1
    ;;
esac
