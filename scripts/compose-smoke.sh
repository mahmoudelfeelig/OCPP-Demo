#!/usr/bin/env bash
set -euo pipefail

curl -fsS http://localhost:8080/healthz >/dev/null
curl -fsS http://localhost:8080/api/health >/dev/null
curl -fsS http://localhost:8080 >/dev/null

echo "compose smoke check passed"
