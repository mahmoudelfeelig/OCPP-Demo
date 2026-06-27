#!/usr/bin/env bash
set -euo pipefail

docker compose down -v
docker compose up -d --build
./scripts/compose-smoke.sh

echo "demo reset complete"
