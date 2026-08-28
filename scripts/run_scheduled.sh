#!/usr/bin/env bash
# Runs one build+upload cycle. Meant to be called from cron/systemd on a
# schedule (see README.md -> "Running on a schedule"). Safe to overlap-call:
# a flock skips the run if a previous one is still going (e.g. a slow upload).
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

mkdir -p "$PROJECT_DIR/output"
LOCK_FILE="$PROJECT_DIR/output/.run.lock"
LOG_FILE="$PROJECT_DIR/output/run.log"

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "$(date -Is) skip: previous run still in progress" >>"$LOG_FILE"
  exit 0
fi

if [ ! -x "$PROJECT_DIR/.venv/bin/activate" ] && [ ! -f "$PROJECT_DIR/.venv/bin/activate" ]; then
  echo "$(date -Is) error: .venv not found, run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >>"$LOG_FILE"
  exit 1
fi

# shellcheck disable=SC1091
source "$PROJECT_DIR/.venv/bin/activate"

{
  echo "=== $(date -Is) starting run ==="
  python main.py --upload --privacy "${YOUTUBE_PRIVACY_STATUS:-public}"
  echo "=== $(date -Is) finished run ==="
} >>"$LOG_FILE" 2>&1
