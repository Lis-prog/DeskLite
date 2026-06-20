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

echo ""
echo "Deploy complete. Smoke test:"
echo "  curl -s https://api.yourdomain.com/api/v1/health"
echo "  open https://app.yourdomain.com"
