#!/usr/bin/env bash
# Source-based local build and a bounded, fail-closed HTTP readiness check.
set -euo pipefail
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"
MODE="${1:-}"
case "$MODE" in
  ''|--no-build) ;;
  *) printf 'Usage: %s [--no-build]\n' "$0" >&2; exit 2 ;;
esac
[ "$#" -le 1 ] || { printf 'Too many arguments\n' >&2; exit 2; }
: "${LAMPAC_ROOT_PASSWORD:?Set LAMPAC_ROOT_PASSWORD to a strong secret of at least 16 characters}"
if [ "${#LAMPAC_ROOT_PASSWORD}" -lt 16 ]; then
  echo 'LAMPAC_ROOT_PASSWORD must contain at least 16 characters' >&2
  exit 2
fi
command -v docker >/dev/null 2>&1 || { echo 'Docker CLI is required' >&2; exit 1; }
docker info >/dev/null 2>&1 || { echo 'Docker daemon unavailable' >&2; exit 1; }
COMPOSE=(docker compose -f bunny/compose.yaml)
WORK="$(mktemp -d)"
cleanup() {
  status=$?
  if [ "$status" -ne 0 ]; then
    echo "LAMPAC_BUNNY_LOCAL_ACCEPTANCE_FAIL (exit=$status)" >&2
    "${COMPOSE[@]}" ps -a >&2 || true
    container_id="$("${COMPOSE[@]}" ps -a -q lampac 2>/dev/null || true)"
    if [ -n "$container_id" ]; then
      docker inspect --format 'container={{.Name}} state={{.State.Status}} exit={{.State.ExitCode}} restarts={{.RestartCount}} oom={{.State.OOMKilled}} error={{.State.Error}}' "$container_id" >&2 || true
    fi
    echo '=== Lampac container stdout/stderr (last 120 lines) ===' >&2
    "${COMPOSE[@]}" logs --no-color --tail=120 >&2 || true
    echo 'If logs are empty, inspect application logs under /lampac/logs/ in the container.' >&2
  fi
  rm -rf "$WORK"
}
trap cleanup EXIT
bash bunny/scripts/preflight.sh
"${COMPOSE[@]}" config --quiet
if [ "$MODE" != '--no-build' ]; then
  "${COMPOSE[@]}" build
else
  echo 'Using already built lampac-bunny:local image (--no-build).'
fi
"${COMPOSE[@]}" up --no-build --detach
container_id="$("${COMPOSE[@]}" ps -a -q lampac)"
[ -n "$container_id" ] || { echo 'Lampac container not found after compose up' >&2; exit 1; }
echo 'Waiting for Lampac HTTP readiness on http://127.0.0.1:9118 (up to ~2 minutes)...'
ready=false
for ((attempt=1; attempt<=60; attempt++)); do
  : > "$WORK/body"
  : > "$WORK/curl-error"
  http_code="$(curl --silent --show-error --connect-timeout 2 --max-time 5 \
    --output "$WORK/body" --write-out '%{http_code}' \
    'http://127.0.0.1:9118/version?type=hash' 2>"$WORK/curl-error")" || http_code='000'
  if [ "$http_code" = '200' ] && [ -s "$WORK/body" ]; then
    cat "$WORK/body"
    printf '\n'
    ready=true
    break
  fi
  state="$(docker inspect --format '{{.State.Status}}' "$container_id" 2>/dev/null || printf unavailable)"
  case "$state" in
    exited|dead|unavailable)
      printf 'Lampac process is not running (state=%s)\n' "$state" >&2
      exit 1
      ;;
  esac
  if ((attempt % 10 == 0)); then
    printf 'Still starting (attempt=%d/60, last HTTP=%s, container=%s)\n' "$attempt" "$http_code" "$state"
  fi
  if ((attempt < 60)); then sleep 2; fi
done
if [ "$ready" != true ]; then
  printf 'Lampac did not return HTTP 200 with a nonempty body within the readiness window.\n' >&2
  if [ -s "$WORK/curl-error" ]; then
    printf 'Last curl error: ' >&2
    cat "$WORK/curl-error" >&2
  fi
  exit 1
fi
"${COMPOSE[@]}" ps
printf 'LAMPAC_BUNNY_LOCAL_ACCEPTANCE_PASS\n'
