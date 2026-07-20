#!/usr/bin/env bash
# First-time challenge config (title, goal, start date).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$ROOT/run.sh" setup
