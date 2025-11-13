#!/usr/bin/env bash
set -euo pipefail

echo "[build] Building and starting services via Docker Compose..."

if docker compose version >/dev/null 2>&1; then
  docker compose up -d --build
else
  # Fallback for older Docker setups
  docker-compose up -d --build
fi

echo "[build] Done. Use 'docker compose ps' to check status and 'docker compose logs -f' to view logs."