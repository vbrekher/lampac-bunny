#!/usr/bin/env bash
# Offline tests for the Bunny packaging and bootstrap; no Docker, Bunny account or secrets required.
set -euo pipefail
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
command -v jq >/dev/null || { echo 'jq is needed for local preflight' >&2; exit 1; }
sh -n "$ROOT_DIR/bunny/docker-entrypoint.sh"
for script in "$ROOT_DIR/bunny/scripts/build-image.sh" "$ROOT_DIR/bunny/scripts/smoke.sh" "$ROOT_DIR/bunny/scripts/doctor.sh"; do
  bash -n "$script"
done
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
mode=$(stat -c %a "$work/lampac/passwd" 2>/dev/null || stat -f %Lp "$work/lampac/passwd")
[ "$mode" = 600 ]
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
[ -f "$ROOT_DIR/bunny/Dockerfile" ] || { echo 'Missing Bunny Dockerfile' >&2; exit 1; }
[ "$(grep -c '^HEALTHCHECK ' "$ROOT_DIR/bunny/Dockerfile")" -eq 1 ] || { echo 'Expected exactly one HEALTHCHECK' >&2; exit 1; }
[ "$(grep -c '^ENTRYPOINT ' "$ROOT_DIR/bunny/Dockerfile")" -eq 1 ] || { echo 'Expected exactly one ENTRYPOINT' >&2; exit 1; }
grep -Fqx -- '!bunny/docker-entrypoint.sh' "$ROOT_DIR/.dockerignore" || { echo 'Bunny entrypoint excluded from build context' >&2; exit 1; }
grep -Fqx -- '!bunny/config/init.conf' "$ROOT_DIR/.dockerignore" || { echo 'Bunny config excluded from build context' >&2; exit 1; }
grep -Fqx -- 'ARG SDK_IMAGE=mcr.microsoft.com/dotnet/sdk:10.0' "$ROOT_DIR/bunny/Dockerfile" || { echo 'Expected .NET SDK base is missing' >&2; exit 1; }
grep -Fqx -- 'ARG RUNTIME_IMAGE=mcr.microsoft.com/dotnet/aspnet:10.0' "$ROOT_DIR/bunny/Dockerfile" || { echo 'Expected ASP.NET runtime base is missing' >&2; exit 1; }
# Official .NET 10 base includes 'app'. Ubuntu GID 1000 is already occupied.
grep -Fqx -- 'USER $APP_UID' "$ROOT_DIR/bunny/Dockerfile" || { echo 'Dockerfile must use the built-in .NET app user' >&2; exit 1; }
grep -Fq -- 'chown -R app:app /lampac /opt/lampac-bunny' "$ROOT_DIR/bunny/Dockerfile" || { echo 'Expected app-owned directories are missing' >&2; exit 1; }
if grep -Eq 'groupadd[[:space:]]+--gid[= ]1000|useradd[[:space:]]+--uid[= ]1000' "$ROOT_DIR/bunny/Dockerfile"; then
  echo 'Dockerfile must not create UID/GID 1000 on Ubuntu-based .NET images' >&2
  exit 1
fi
printf 'PASS: non-root identity without Ubuntu UID/GID collision\n'
printf 'PASS: Dockerfile and build context static audit\n'
printf 'LAMPAC_BUNNY_PREFLIGHT_PASS\n'
