#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${LULU_PROJECT_ROOT:-/root/autodl-tmp/lulustudio-agent}"
PORT="${LULU_REAL_PORT:-8011}"
BASE_URL="http://127.0.0.1:${PORT}"
CHECKPOINT="${LULU_FLUX_CHECKPOINT:-/root/ComfyUI/models/checkpoints/FLUX1/flux1-dev-fp8.safetensors}"
EPISODE_FILE="${LULU_EPISODE_FILE:-examples/flux_lulu_baseline.json}"

cd "$PROJECT_ROOT"
mkdir -p logs data

if [[ ! -s "$CHECKPOINT" ]]; then
  echo "FLUX checkpoint is missing or empty: $CHECKPOINT" >&2
  exit 1
fi

curl --fail --silent http://127.0.0.1:6006/system_stats >/dev/null

if [[ -f logs/agent-real.pid ]] && kill -0 "$(cat logs/agent-real.pid)" 2>/dev/null; then
  echo "Real Agent is already running: PID $(cat logs/agent-real.pid)"
else
  nohup env \
    LULU_DRY_RUN=false \
    LULU_DB_PATH=data/lulustudio-real.db \
    LULU_COMFYUI_URL=http://127.0.0.1:6006 \
    .venv/bin/lulu-agent serve --host 127.0.0.1 --port "$PORT" \
    >logs/agent-real.log 2>&1 &
  echo "$!" >logs/agent-real.pid
fi

for _ in $(seq 1 30); do
  if curl --fail --silent "$BASE_URL/health" >logs/agent-real-health.json; then
    break
  fi
  sleep 1
done

python - "$BASE_URL" <<'PY'
import json
import sys
import urllib.error
import urllib.request

base_url = sys.argv[1]
with urllib.request.urlopen(f"{base_url}/health", timeout=10) as response:
    health = json.load(response)
if health.get("dry_run") is not False:
    raise SystemExit(f"refusing to run: Agent is still in dry-run mode: {health}")
PY

episode_id="$(python - "$EPISODE_FILE" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    print(json.load(handle)["episode_id"])
PY
)"

if ! curl --fail --silent "$BASE_URL/episodes/$episode_id" >/dev/null; then
  curl --fail --silent \
    -X POST "$BASE_URL/episodes" \
    -H 'Content-Type: application/json' \
    --data-binary "@$EPISODE_FILE" \
    >logs/flux-baseline-create.json
fi

curl --fail --silent \
  -X POST "$BASE_URL/episodes/$episode_id/run" \
  >logs/flux-baseline-result.json

python -m json.tool logs/flux-baseline-result.json
