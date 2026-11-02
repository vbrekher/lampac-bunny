#!/usr/bin/env bash
# Public endpoint smoke check. Do not pass authenticated URLs or tokens.
set -euo pipefail
URL="${1:-}"
if [[ -z "$URL" ]]; then echo 'Usage: smoke.sh https://YOUR-MAGIC-CONTAINER-ENDPOINT' >&2; exit 2; fi
case "$URL" in
  https://*|http://localhost:*|http://127.0.0.1:*) ;;
  *) echo 'Use HTTPS for public endpoints, or localhost for development' >&2; exit 2 ;;
esac
if [[ "$URL" == *'?'* || "$URL" == *'#'* || "$URL" == *'@'* ]]; then
  echo 'Pass an endpoint base URL without credentials, query, or fragment' >&2; exit 2
fi
URL="${URL%/}"
for path in '/version?type=hash' '/online.js'; do
  tmp="$(mktemp)"
  trap 'rm -f "${tmp:-}"' EXIT
  code="$(curl --silent --show-error --location --max-redirs 2 --connect-timeout 8 --max-time 30 --output "$tmp" --write-out '%{http_code}' "$URL$path")" || {
    echo "FAIL: $path request failed" >&2; exit 1;
  }
  if [[ "$code" != 200 || ! -s "$tmp" ]]; then
    echo "FAIL: $path (HTTP $code or empty response)" >&2; exit 1
  fi
  printf 'PASS: %-24s HTTP %s\n' "$path" "$code"
  rm -f "$tmp"
  trap - EXIT
done
printf 'LAMPAC_BUNNY_HTTP_SMOKE_PASS\n'
