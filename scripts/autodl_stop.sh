#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${LULU_PROJECT_ROOT:-/root/autodl-tmp/lulustudio-agent}"
cd "$PROJECT_ROOT"

if [[ ! -f logs/agent.pid ]]; then
  echo "No PID file found"
  exit 0
fi

PID="$(cat logs/agent.pid)"
if kill -0 "$PID" 2>/dev/null; then
  kill "$PID"
  echo "Stopped LuluStudio Agent: PID $PID"
else
  echo "Process $PID is not running"
fi
rm -f logs/agent.pid
