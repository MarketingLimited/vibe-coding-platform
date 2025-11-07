#!/usr/bin/env bash

set -euo pipefail

API_URL="${1:-http://127.0.0.1:9000}"

echo "Checking Vibe Coding API at ${API_URL}" >&2

if command -v jq >/dev/null 2>&1; then
  curl -sf "${API_URL}/health/services" | jq .
else
  curl -sf "${API_URL}/health/services" | python -m json.tool
fi
