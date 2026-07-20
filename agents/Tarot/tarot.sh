#!/usr/bin/env bash
# Unified Tarot launcher (inspired by tarot-oracle / 2acrestudios interactive CLI).
# Usage:
#   ./tarot.sh                         # interactive menu
#   ./tarot.sh daily --draw -q "今日焦点" -y --offline
#   ./tarot.sh 3 --draw -q "下周如何安排" -y
#   ./tarot.sh 5 --draw -q "项目卡点" --offline
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<'EOF'
本地塔罗 Agent

用法:
  ./tarot.sh                  交互菜单
  ./tarot.sh daily [选项]     每日一抽
  ./tarot.sh 3|question-3     三牌（现状/阻碍/建议）
  ./tarot.sh 5|question-5     五牌

常用选项:
  --draw / --auto     从 78 张牌自动抽（可重复；实体牌仍可手输）
  -q / --question     问题文本（跳过部分交互）
  --offline           不联网，只用本地语料
  -y / --yes          跳过确认/覆盖提问
  --seed TEXT         可复现抽牌种子
  YYYY-MM-DD          指定日期

示例（类似开源 oracle "question" --interpret）:
  ./tarot.sh daily --draw -q "今天注意什么" -y
  ./tarot.sh 3 --draw -q "下周如何安排" -y --offline
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
    echo "本地塔罗 Agent"
    echo "1) 每日一抽（手输牌）"
    echo "2) 每日一抽（自动抽牌）"
    echo "3) 三牌问题（手输）"
    echo "4) 三牌问题（自动抽牌）"
    echo "5) 五牌问题（自动抽牌）"
    echo "6) 重建本地语料"
    echo "q) 退出"
    read -r -p "选择: " choice
    case "$choice" in
      1) run_daily ;;
      2) run_daily --draw ;;
      3) run_q 3 ;;
      4) run_q 3 --draw ;;
      5) run_q 5 --draw ;;
      6) exec "$ROOT/fetch-corpus.sh" ;;
      q|Q) exit 0 ;;
      *) echo "无效选择"; exit 1 ;;
    esac
    ;;
  daily|one|1) run_daily "$@" ;;
  3|question-3|q3) run_q 3 "$@" ;;
  5|question-5|q5) run_q 5 "$@" ;;
  help) usage ;;
  *)
    echo "未知模式：$MODE"
    usage
    exit 1
    ;;
esac
