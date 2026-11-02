#!/usr/bin/env bash
# One-command local build + HTTP acceptance; fails closed and shows useful logs.
set -euo pipefail
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"
: "${LAMPAC_ROOT_PASSWORD:?Set LAMPAC_ROOT_PASSWORD (16+ chars), for example: export LAMPAC_ROOT_PASSWORD=\$(openssl rand -hex 24)}"
if [ "${#LAMPAC_ROOT_PASSWORD}" -lt 16 ]; then
  echo 'LAMPAC_ROOT_PASSWORD must be at least 16 characters' >&2
  exit 2
fi
command -v docker >/dev/null || { echo 'Docker CLI required' >&2; exit 1; }
docker info >/dev/null || { echo 'Docker daemon unavailable' >&2; exit 1; }
trap 'status=$?; if [ "$status" -ne 0 ]; then echo "LAMPAC_BUNNY_LOCAL_ACCEPTANCE_FAIL (exit=$status)" >&2; docker compose -f bunny/compose.yaml ps >&2 || true; docker compose -f bunny/compose.yaml logs --tail=100 >&2 || true; fi' EXIT
bash bunny/scripts/preflight.sh
docker compose -f bunny/compose.yaml config --quiet
docker compose -f bunny/compose.yaml build
docker compose -f bunny/compose.yaml up --no-build --detach
echo 'Waiting for HTTP response on 127.0.0.1:9118...'
curl --fail --silent --show-error --retry 20 --retry-delay 3 --retry-connrefused \
  'http://127.0.0.1:9118/version?type=hash'
printf '\nLAMPAC_BUNNY_LOCAL_ACCEPTANCE_PASS\n'
docker compose -f bunny/compose.yaml ps
