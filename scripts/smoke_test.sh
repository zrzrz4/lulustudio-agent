#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${LULU_BASE_URL:-http://127.0.0.1:8010}"
curl --fail --silent "$BASE_URL/health"
printf '\n'
