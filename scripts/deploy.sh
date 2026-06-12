#!/usr/bin/env bash
set -euo pipefail

# --- Colors & print helpers ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { echo -e "${GREEN}[✓]${NC} $*"; }
info() { echo -e "${YELLOW}[→]${NC} $*"; }
err()  { echo -e "${RED}[✗]${NC} $*" >&2; }

# --- Paths ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$REPO_ROOT/backend"
ENV_FILE="$BACKEND_DIR/.env"
DETAIL_DIR="$BACKEND_DIR/data/context/detail"

# --- Config ---
HEALTH_URL="http://localhost:8000/health"
HEALTH_RETRIES=10
HEALTH_DELAY=3
FORCE_FRESH="${FORCE_FRESH:-0}"

REQUIRED_VARS=(
  GEMINI_API_KEYS
  GROQ_API_KEYS
  ADMIN_SECRET
  CONTEXT_ENCRYPTION_KEY
  UMAMI_SECRET
  ALLOWED_ORIGIN
  MODAL_ENDPOINT
)

preflight() {
  info "Running pre-flight checks..."

  if ! command -v docker &>/dev/null; then
    err "Docker not found. Install Docker first: https://docs.docker.com/engine/install/"
    exit 1
  fi
  ok "Docker found"

  if ! docker compose version &>/dev/null; then
    err "Docker Compose not found. Install the Docker Compose plugin."
    exit 1
  fi
  ok "Docker Compose found"

  if [[ ! -f "$ENV_FILE" ]]; then
    err "backend/.env missing. Copy backend/.env.example and fill in all values."
    exit 1
  fi
  ok ".env found"

  # shellcheck source=/dev/null
  source "$ENV_FILE"

  for var in "${REQUIRED_VARS[@]}"; do
    if [[ -z "${!var:-}" ]]; then
      err "Missing required var: ${var} (check backend/.env)"
      exit 1
    fi
  done
  ok "Required vars present"

  # Export UID/GID for docker-compose.yml user field
  export UID   # exports bash's existing read-only built-in value without re-assigning
  GID="$(id -g)"; export GID
}

detect_mode() {
  if [[ "$FORCE_FRESH" == "1" ]]; then
    echo "fresh"
    return
  fi

  local running
  running=$(docker compose -f "$BACKEND_DIR/docker-compose.yml" ps --services --filter status=running 2>/dev/null || echo "")

  if [[ -n "$running" ]]; then
    echo "update"
  else
    echo "fresh"
  fi
}

decrypt_context() {
  info "Decrypting context files..."
  local count=0

  for enc_file in "$DETAIL_DIR"/*.md.enc; do
    [[ -f "$enc_file" ]] || continue
    local out_file="${enc_file%.enc}"
    openssl enc -d -aes-256-cbc -pbkdf2 -k "$CONTEXT_ENCRYPTION_KEY" -in "$enc_file" -out "$out_file"
    ((++count))
  done

  if [[ $count -eq 0 ]]; then
    info "No .enc files found in $DETAIL_DIR — skipping"
  else
    ok "Decrypted $count context file(s)"
  fi
}

health_check() {
  info "Waiting for API health check..."
  local attempt=1

  while [[ $attempt -le $HEALTH_RETRIES ]]; do
    if curl -sf "$HEALTH_URL" &>/dev/null; then
      ok "API healthy at $HEALTH_URL"
      return 0
    fi
    info "Attempt $attempt/$HEALTH_RETRIES — not ready, retrying in ${HEALTH_DELAY}s..."
    sleep "$HEALTH_DELAY"
    ((attempt++))
  done

  err "API did not become healthy after $((HEALTH_RETRIES * HEALTH_DELAY))s."
  err "Check logs: docker compose -f $BACKEND_DIR/docker-compose.yml logs --tail=50"
  exit 1
}

deploy_fresh() {
  info "Mode: FRESH — building from scratch"
  decrypt_context
  info "Building and starting all services..."
  docker compose -f "$BACKEND_DIR/docker-compose.yml" up -d --build
  ok "Stack is up"
}

deploy_update() {
  info "Mode: UPDATE — pulling latest and rebuilding"
  info "Pulling latest changes..."
  git -C "$REPO_ROOT" pull origin main
  decrypt_context
  info "Rebuilding containers..."
  docker compose -f "$BACKEND_DIR/docker-compose.yml" up -d --build --remove-orphans
  ok "Stack is up"
}

main() {
  echo ""
  echo "[portfolio] Starting deployment..."
  echo ""

  preflight

  local mode
  mode=$(detect_mode)

  if [[ "$mode" == "fresh" ]]; then
    deploy_fresh
  else
    deploy_update
  fi

  health_check

  echo ""
  ok "Deploy complete."
  echo ""
}

main "$@"
