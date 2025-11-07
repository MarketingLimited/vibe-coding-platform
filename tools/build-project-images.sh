#!/usr/bin/env bash

set -euo pipefail

# -----------------------------------------------------------------------------
# Build the base project container images used by the Project Manager service.
# -----------------------------------------------------------------------------

ROOT_DIR="${VIBE_ROOT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
IMAGES_DIR="$ROOT_DIR/project-manager/templates/images"
IMAGE_PREFIX="vibe-project"
IMAGE_TAG="latest"
NO_CACHE=0

usage() {
  cat <<'EOF'
Usage: build-project-images.sh [options]

Options:
  -p, --prefix <name>   Override the Docker image prefix (default: vibe-project)
  -t, --tag <tag>       Override the Docker image tag (default: latest)
      --no-cache        Pass --no-cache to docker build
  -h, --help            Show this help message
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -p|--prefix)
      IMAGE_PREFIX="$2"
      shift 2
      ;;
    -t|--tag)
      IMAGE_TAG="$2"
      shift 2
      ;;
    --no-cache)
      NO_CACHE=1
      shift 1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[build-images] Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ ! -d "$IMAGES_DIR" ]]; then
  echo "[build-images] Image templates directory not found: $IMAGES_DIR" >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "[build-images] Docker binary not available" >&2
  exit 1
fi

build_flags=()
if [[ $NO_CACHE -eq 1 ]]; then
  build_flags+=("--no-cache")
fi

types_built=0
for template_dir in "$IMAGES_DIR"/*; do
  if [[ ! -d "$template_dir" ]]; then
    continue
  fi
  language="$(basename "$template_dir")"
  image_name="${IMAGE_PREFIX}-${language}:${IMAGE_TAG}"
  echo "[build-images] Building ${image_name} from ${template_dir}" >&2
  docker build "${build_flags[@]}" -t "$image_name" "$template_dir"
  types_built=$((types_built + 1))
done

if [[ $types_built -eq 0 ]]; then
  echo "[build-images] No template directories found under $IMAGES_DIR" >&2
  exit 1
fi

echo "[build-images] Built $types_built project images with prefix '${IMAGE_PREFIX}' and tag '${IMAGE_TAG}'."
