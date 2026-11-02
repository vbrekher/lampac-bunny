#!/bin/sh
# Independent Bunny deployment bootstrap for Lampac NextGen.
set -eu
umask 077

APP_HOME=${LAMPAC_BUNNY_HOME:-/lampac}
TEMPLATE=${LAMPAC_BUNNY_TEMPLATE:-/opt/lampac-bunny/init.conf}

fail() { printf '%s\n' "lampac-bunny: $*" >&2; exit 1; }

[ -d "$APP_HOME" ] || fail "Application directory not found"
[ -w "$APP_HOME" ] || fail "Application directory is not writable"
[ -r "$TEMPLATE" ] || fail "Bundled configuration template is missing"
command -v jq >/dev/null 2>&1 || fail "jq is required"
command -v base64 >/dev/null 2>&1 || fail "base64 is required"

[ -n "${LAMPAC_ROOT_PASSWORD:-}" ] || fail "Set LAMPAC_ROOT_PASSWORD in Bunny environment variables"
[ "${#LAMPAC_ROOT_PASSWORD}" -ge 16 ] || fail "LAMPAC_ROOT_PASSWORD must contain at least 16 characters"
if printf '%s' "$LAMPAC_ROOT_PASSWORD" | LC_ALL=C grep -q '[[:cntrl:]]'; then
  fail "LAMPAC_ROOT_PASSWORD must not contain control characters"
fi

config_tmp=$(mktemp "$APP_HOME/.init.conf.XXXXXXXX") || fail "Cannot create config file"
pass_tmp=$(mktemp "$APP_HOME/.passwd.XXXXXXXX") || fail "Cannot create password file"
cleanup() { rm -f "$config_tmp" "$pass_tmp"; }
trap cleanup EXIT HUP INT TERM

if [ "${LAMPAC_BUNNY_CONFIG_B64+x}" = x ]; then
  [ -n "$LAMPAC_BUNNY_CONFIG_B64" ] || fail "LAMPAC_BUNNY_CONFIG_B64 is set but empty"
  printf '%s' "$LAMPAC_BUNNY_CONFIG_B64" | base64 -d > "$config_tmp" 2>/dev/null || fail "Invalid base64 configuration"
else
  cp "$TEMPLATE" "$config_tmp" || fail "Cannot copy default configuration"
fi

# Bunny's HTTP(S) endpoint forwards to HTTP on port 9118. Fail closed on incompatible overrides.
jq -e 'type == "object" and (.listen | type == "object" and (.port == 9118) and ((.ip == "0.0.0.0") or (.ip == "any")) and (.scheme == "http"))' "$config_tmp" >/dev/null \
  || fail "init.conf must be valid JSON and listen on http://0.0.0.0:9118 (or ip=any)"

printf '%s' "$LAMPAC_ROOT_PASSWORD" > "$pass_tmp" || fail "Cannot write root password"
chmod 0600 "$config_tmp" "$pass_tmp"
mv -f "$config_tmp" "$APP_HOME/init.conf"
mv -f "$pass_tmp" "$APP_HOME/passwd"

# SQLite databases remain local to a single Bunny pod. The operator must mount/backup storage.
mkdir -p "$APP_HOME/database" "$APP_HOME/cache"
[ -w "$APP_HOME/database" ] || fail "database directory is not writable; check Bunny volume permissions"
[ -w "$APP_HOME/cache" ] || fail "cache directory is not writable; check Bunny volume permissions"

unset LAMPAC_ROOT_PASSWORD LAMPAC_BUNNY_CONFIG_B64
trap - EXIT HUP INT TERM

if [ "${1:-}" = "--configure-only" ]; then
  printf '%s\n' "lampac-bunny: bootstrap checks passed"
  exit 0
fi
[ "$#" -eq 0 ] || fail "Unknown argument; expected no arguments"
cd "$APP_HOME"
exec /usr/share/dotnet/dotnet Core.dll
