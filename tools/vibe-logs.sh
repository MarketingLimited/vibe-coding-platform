#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: tools/vibe-logs.sh [options] [service...]

Stream logs from docker compose services. Defaults to all services defined in
the root docker-compose.yml file.

Options:
  -f, --follow           Follow log output (equivalent to docker compose logs -f)
      --tail <lines>     Limit the number of lines shown per service
  -h, --help             Show this help message

Examples:
  tools/vibe-logs.sh --tail 100 api project-manager
  tools/vibe-logs.sh --follow
USAGE
}

ROOT_DIR="${VIBE_ROOT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

if ! command -v docker >/dev/null 2>&1; then
  echo "[vibe-logs] docker command not found in PATH" >&2
  exit 1
fi

cd "$ROOT_DIR"

FOLLOW=false
TAIL_VALUE=""
SERVICES=()

while (( $# )); do
  case "$1" in
    -f|--follow)
      FOLLOW=true
      shift
      ;;
    --tail)
      if (( $# < 2 )); then
        echo "[vibe-logs] --tail requires a numeric argument" >&2
        usage
        exit 1
      fi
      TAIL_VALUE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      SERVICES+=("$@")
      break
      ;;
    *)
      SERVICES+=("$1")
      shift
      ;;
  esac
done

CMD=(docker compose logs)

if [[ "$FOLLOW" == true ]]; then
  CMD+=("-f")
fi

if [[ -n "$TAIL_VALUE" ]]; then
  CMD+=("--tail" "$TAIL_VALUE")
fi

if [[ ${#SERVICES[@]} -gt 0 ]]; then
  CMD+=("${SERVICES[@]}")
fi

exec "${CMD[@]}"
