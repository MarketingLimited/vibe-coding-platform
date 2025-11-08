#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "${SCRIPT_DIR}/../.." && pwd)
TEMPLATE_PATH="${REPO_ROOT}/openapi-spec-multitenant.yaml"
OUTPUT_PATH="${1:-${REPO_ROOT}/openapi-spec-multitenant.rendered.yaml}"

if [[ ! -f "${TEMPLATE_PATH}" ]]; then
  echo "[!] لم يتم العثور على ملف المواصفة عند ${TEMPLATE_PATH}" >&2
  exit 1
fi

PUBLIC_BASE="${API_PUBLIC_BASE_URL:-}"
if [[ -z "${PUBLIC_BASE}" ]]; then
  echo "[!] الرجاء ضبط المتغير API_PUBLIC_BASE_URL قبل تشغيل السكربت." >&2
  exit 1
fi

if [[ "${PUBLIC_BASE}" != https://* ]]; then
  echo "[!] يجب أن يبدأ API_PUBLIC_BASE_URL بـ https://" >&2
  exit 1
fi

CONTENT=$(<"${TEMPLATE_PATH}")
PLACEHOLDER="default: https://api.example.com"

if [[ "${CONTENT}" != *"${PLACEHOLDER}"* ]]; then
  echo "[!] لم يتم العثور على قيمة افتراضية يمكن استبدالها في ملف المواصفة." >&2
  exit 1
fi

UPDATED_CONTENT="${CONTENT//${PLACEHOLDER}/default: ${PUBLIC_BASE}}"

printf '%s' "${UPDATED_CONTENT}" > "${OUTPUT_PATH}"

echo "✅ تم إنشاء الملف: ${OUTPUT_PATH}" >&2
