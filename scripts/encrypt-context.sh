#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$REPO_ROOT/backend/.env"
DETAIL_DIR="$REPO_ROOT/backend/data/context/detail"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Error: $ENV_FILE not found" >&2
  exit 1
fi

source "$ENV_FILE"

if [[ -z "${CONTEXT_ENCRYPTION_KEY:-}" ]]; then
  echo "Error: CONTEXT_ENCRYPTION_KEY is not set in $ENV_FILE" >&2
  exit 1
fi

for f in "$DETAIL_DIR"/*.md; do
  [[ -f "$f" ]] || continue
  openssl enc -aes-256-cbc -pbkdf2 -k "$CONTEXT_ENCRYPTION_KEY" -in "$f" -out "${f}.enc"
  echo "Encrypted: ${f##*/} → ${f##*/}.enc"
done

echo "Done. Stage the .enc files and commit."
