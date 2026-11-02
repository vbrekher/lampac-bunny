#!/usr/bin/env bash
# Offline tests for the Bunny packaging and bootstrap; no Docker, Bunny account or secrets required.
set -euo pipefail
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
command -v jq >/dev/null || { echo 'jq is needed for local preflight' >&2; exit 1; }
sh -n "$ROOT_DIR/bunny/docker-entrypoint.sh"
bash -n "$ROOT_DIR/bunny/scripts/build-image.sh" "$ROOT_DIR/bunny/scripts/smoke.sh"
jq -e '.listen.port == 9118 and .listen.scheme == "http" and (.BaseModule.SkipModules | index("TorrServer") != null)' "$ROOT_DIR/bunny/config/init.conf" >/dev/null

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
mkdir -p "$work/lampac"
entry="$ROOT_DIR/bunny/docker-entrypoint.sh"
template="$ROOT_DIR/bunny/config/init.conf"
export LAMPAC_BUNNY_HOME="$work/lampac" LAMPAC_BUNNY_TEMPLATE="$template"
export LAMPAC_ROOT_PASSWORD='local-test-only-strong-passphrase'
sh "$entry" --configure-only >/dev/null
[ -s "$work/lampac/init.conf" ] && [ -s "$work/lampac/passwd" ]
[ "$(stat -c %a "$work/lampac/passwd")" = 600 ]
[ "$(jq -r '.listen.port' "$work/lampac/init.conf")" = 9118 ]
printf 'PASS: default bootstrap\n'

cp "$work/lampac/init.conf" "$work/saved.conf"
export LAMPAC_BUNNY_CONFIG_B64
LAMPAC_BUNNY_CONFIG_B64=$(printf '%s' '{invalid' | base64 | tr -d '\n')
if sh "$entry" --configure-only >/dev/null 2>&1; then echo 'Invalid JSON was accepted' >&2; exit 1; fi
cmp "$work/lampac/init.conf" "$work/saved.conf"
printf 'PASS: invalid JSON rejected without mutation\n'

LAMPAC_BUNNY_CONFIG_B64=$(printf '%s' '{"listen":{"port":9999,"ip":"0.0.0.0","scheme":"http"}}' | base64 | tr -d '\n')
if sh "$entry" --configure-only >/dev/null 2>&1; then echo 'Invalid port was accepted' >&2; exit 1; fi
cmp "$work/lampac/init.conf" "$work/saved.conf"
printf 'PASS: invalid listener rejected without mutation\n'

LAMPAC_BUNNY_CONFIG_B64=$(jq -c '.online.name="Custom Bunny"' "$template" | base64 | tr -d '\n')
sh "$entry" --configure-only >/dev/null
[ "$(jq -r '.online.name' "$work/lampac/init.conf")" = 'Custom Bunny' ]
printf 'PASS: custom configuration applied\n'

unset LAMPAC_BUNNY_CONFIG_B64
export LAMPAC_ROOT_PASSWORD='short'
if sh "$entry" --configure-only >/dev/null 2>&1; then echo 'Short root password accepted' >&2; exit 1; fi
printf 'PASS: short password rejected\n'

[ -f "$ROOT_DIR/bunny/compose.yaml" ]
[ -f "$ROOT_DIR/bunny/Dockerfile" ] || echo 'NOTE: Bunny Dockerfile is generated at GitHub publication step'
printf 'LAMPAC_BUNNY_PREFLIGHT_PASS\n'
