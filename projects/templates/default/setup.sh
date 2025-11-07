#!/usr/bin/env bash
set -euo pipefail

echo "Bootstrapping project dependencies..."

if [ -f requirements.txt ]; then
  pip install -r requirements.txt || true
fi

if [ -f package.json ]; then
  npm install || true
fi

echo "Setup completed."
