#!/usr/bin/env bash
set -euo pipefail

wait_for_url() {
  local url="$1"
  local attempts="${2:-30}"
  local delay_seconds="${3:-2}"

  for ((attempt = 1; attempt <= attempts; attempt++)); do
    if curl -fsS --max-time 5 "$url" >/dev/null; then
      return 0
    fi
    sleep "$delay_seconds"
  done

  echo "timed out waiting for $url" >&2
  return 1
}

wait_for_url http://localhost:8080/healthz
curl -fsS http://localhost:8080/api/health >/dev/null
curl -fsS http://localhost:8080 >/dev/null

echo "compose smoke check passed"
