#!/usr/bin/env bash

set -euo pipefail

DATA_DIR=${1:-/var/vibe}
OUTPUT_DIR=${2:-$(pwd)}
TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
ARCHIVE="vibe-backup-${TIMESTAMP}.tar.gz"

echo "Creating backup from ${DATA_DIR} into ${OUTPUT_DIR}/${ARCHIVE}" >&2

tar -czf "${OUTPUT_DIR}/${ARCHIVE}" -C "${DATA_DIR}" projects logs redis || {
  echo "Backup failed" >&2
  exit 1
}

echo "Backup completed: ${OUTPUT_DIR}/${ARCHIVE}" >&2
