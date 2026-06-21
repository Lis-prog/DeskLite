#!/usr/bin/env bash
# DeskLite production deploy — run on the VPS from the repo root.
# Usage: ./deploy/deploy.sh
set -euo pipefail

COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml"

echo "==> Pull latest main"
git pull origin main

echo "==> Build images (NEXT_PUBLIC_API_URL from .env)"
$COMPOSE build

echo "==> Run database migrations"
$COMPOSE run --rm backend alembic upgrade head

echo "==> Start / update containers"
$COMPOSE up -d

echo "==> Status"
$COMPOSE ps

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

API_URL="${NEXT_PUBLIC_API_URL:-http://127.0.0.1:8000}"
APP_URL="${FRONTEND_ORIGIN:-http://127.0.0.1:3000}"

echo ""
echo "Deploy complete. Smoke test:"
echo "  curl -s ${API_URL}/api/v1/health"
echo "  open ${APP_URL}"
echo ""
echo "Direct (bypass Caddy, on the VPS only):"
echo "  curl -s http://127.0.0.1:8000/api/v1/health"
echo "  curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3000"
