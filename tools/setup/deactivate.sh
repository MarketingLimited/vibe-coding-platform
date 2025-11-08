#!/usr/bin/env bash

set -euo pipefail

# -----------------------------------------------------------------------------
# Vibe Coding Platform deactivate script.
# Stops the docker compose stack and optionally removes the auxiliary network
# and cached project artifacts to keep local runs isolated between sessions.
# -----------------------------------------------------------------------------

ROOT_DIR="${VIBE_ROOT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
ENV_FILE="$ROOT_DIR/.env"
CONFIG_ENV_FILE="$ROOT_DIR/config/.env"
NETWORK_NAME="vibe-network"

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
fi

echo "[deactivate] Stopping Vibe Coding Platform services..."

if ! command -v docker >/dev/null 2>&1; then
  echo "[deactivate] Docker is not available in PATH." >&2
  exit 1
fi

(cd "$ROOT_DIR" && docker compose down --remove-orphans)

read -r -p "[deactivate] Remove the '$NETWORK_NAME' docker network? [y/N]: " remove_net || true
case "${remove_net,,}" in
  y|yes)
    if docker network ls --format '{{.Name}}' | grep -qx "$NETWORK_NAME"; then
      docker network rm "$NETWORK_NAME"
      echo "[deactivate] Removed docker network '$NETWORK_NAME'."
    else
      echo "[deactivate] Network '$NETWORK_NAME' does not exist."
    fi
    ;;
  *)
    echo "[deactivate] Keeping docker network '$NETWORK_NAME'."
    ;;
esac

if [[ -n "${DATA_DIR:-}" && -d "$DATA_DIR" ]]; then
  read -r -p "[deactivate] Clear cached project/log data under '$DATA_DIR'? [y/N]: " wipe_data || true
  case "${wipe_data,,}" in
    y|yes)
      rm -rf "${DATA_DIR}/projects" "${DATA_DIR}/logs" "${DATA_DIR}/tmp" 2>/dev/null || true
      echo "[deactivate] Cleared cached data from '$DATA_DIR'."
      ;;
    *)
      echo "[deactivate] Leaving cached data untouched."
      ;;
  esac
fi

echo "[deactivate] Done. You can re-run tools/setup/activate.sh to start fresh."
