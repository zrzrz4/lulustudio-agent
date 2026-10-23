#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${LULU_PROJECT_ROOT:-/root/autodl-tmp/lulustudio-agent}"
PORT="${LULU_PORT:-8010}"
cd "$PROJECT_ROOT"

mkdir -p logs data/artifacts
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

if [[ -f logs/agent.pid ]] && kill -0 "$(cat logs/agent.pid)" 2>/dev/null; then
  echo "LuluStudio Agent is already running: PID $(cat logs/agent.pid)"
  exit 0
fi

nohup .venv/bin/lulu-agent serve --host 0.0.0.0 --port "$PORT" > logs/agent.log 2>&1 &
echo "$!" > logs/agent.pid
echo "LuluStudio Agent started: PID $!, port $PORT"
