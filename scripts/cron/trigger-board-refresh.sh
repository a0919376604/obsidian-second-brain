#!/bin/bash
# Triggered by launchd Mon-Fri 09:00 local time.
# Pipes the prompt to `claude -p` for non-interactive execution.

set -euo pipefail

REPO=/Users/leric/Desktop/code/obsidian-second-brain
PROMPT=$REPO/scripts/cron/board-refresh-prompt.txt
LOG=/tmp/langlive-board-refresh.log

# Pick up the user's shell environment (claude CLI, PATH, etc.)
source ~/.zshrc 2>/dev/null || source ~/.bashrc 2>/dev/null || true

cd "$REPO"

{
  echo "==== $(date '+%Y-%m-%d %H:%M:%S') board-refresh fired ===="
  claude -p "$(cat "$PROMPT")" --output-format text
  echo "==== exit code: $? ===="
} >> "$LOG" 2>&1
