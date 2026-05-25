#!/bin/bash
# Triggered by launchd Saturday 12:00 local time.

set -euo pipefail

REPO=/Users/leric/Desktop/code/obsidian-second-brain
PROMPT=$REPO/scripts/cron/weekly-recap-prompt.txt
LOG=/tmp/langlive-weekly-recap.log

source ~/.zshrc 2>/dev/null || source ~/.bashrc 2>/dev/null || true

cd "$REPO"

{
  echo "==== $(date '+%Y-%m-%d %H:%M:%S') weekly-recap fired ===="
  claude -p "$(cat "$PROMPT")" --output-format text
  echo "==== exit code: $? ===="
} >> "$LOG" 2>&1
