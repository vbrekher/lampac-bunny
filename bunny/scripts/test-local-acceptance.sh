#!/usr/bin/env bash
# Offline regression: curl (52) while starting must retry, persistent faults must fail.
set -euo pipefail
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/bin"
cat > "$tmp/bin/docker" <<'FAKE_DOCKER'
#!/usr/bin/env bash
case "$1" in
  info) exit 0 ;;
  inspect)
    if [[ "${MOCK_SCENARIO:-}" == exited ]]; then
      if [[ "$*" == *'{{.State.Status}}'* ]]; then echo exited; else echo 'state=exited exit=1'; fi
    else
      if [[ "$*" == *'{{.State.Status}}'* ]]; then echo running; else echo 'state=running exit=0'; fi
    fi
    ;;
  compose)
    if [[ "$*" == *'ps -a -q lampac'* ]]; then echo mockid
    elif [[ "$*" == *'up --no-build --detach'* ]]; then echo MOCK_UP
    elif [[ "$*" == *'ps -a'* ]]; then echo 'mock-container running'
    elif [[ "$*" == *'build'* ]]; then echo MOCK_BUILD
    fi
    ;;
  *) echo "Unexpected docker arguments: $*" >&2; exit 1 ;;
esac
FAKE_DOCKER
cat > "$tmp/bin/curl" <<'FAKE_CURL'
#!/usr/bin/env bash
counter="${MOCK_COUNTER:?}"
n=0
[[ -f "$counter" ]] && n="$(cat "$counter")"
n=$((n+1))
printf '%d' "$n" > "$counter"
out=''
while (($#)); do
  case "$1" in
    --output) out="$2"; shift 2 ;;
    *) shift ;;
  esac
done
if [[ "${MOCK_SCENARIO:-}" != transient || "$n" -le 2 ]]; then
  echo 'curl: (52) Empty reply from server' >&2
  exit 52
fi
printf mock-version-hash > "$out"
printf 200
FAKE_CURL
cat > "$tmp/bin/sleep" <<'FAKE_SLEEP'
#!/usr/bin/env bash
exit 0
FAKE_SLEEP
chmod +x "$tmp/bin/docker" "$tmp/bin/curl" "$tmp/bin/sleep"
export PATH="$tmp/bin:$PATH"
export LAMPAC_ROOT_PASSWORD='local-test-only-strong-passphrase'
export MOCK_COUNTER="$tmp/counter"
export MOCK_SCENARIO=transient
bash "$ROOT_DIR/bunny/scripts/local-acceptance.sh" --no-build > "$tmp/transient.out" 2>&1 || {
  cat "$tmp/transient.out" >&2; exit 1;
}
grep -q '^LAMPAC_BUNNY_LOCAL_ACCEPTANCE_PASS$' "$tmp/transient.out"
[ "$(cat "$MOCK_COUNTER")" = 3 ]
printf 'PASS: transient curl 52 retries then 200\n'
MOCK_COUNTER="$tmp/persistent-counter" MOCK_SCENARIO=persistent \
  bash "$ROOT_DIR/bunny/scripts/local-acceptance.sh" --no-build > "$tmp/persistent.out" 2>&1 && {
    echo 'Persistent failure falsely accepted' >&2; exit 1;
  }
grep -q 'LAMPAC_BUNNY_LOCAL_ACCEPTANCE_FAIL' "$tmp/persistent.out"
! grep -q '^LAMPAC_BUNNY_LOCAL_ACCEPTANCE_PASS$' "$tmp/persistent.out"
printf 'PASS: persistent curl 52 fails closed with diagnostics\n'
MOCK_COUNTER="$tmp/exited-counter" MOCK_SCENARIO=exited \
  bash "$ROOT_DIR/bunny/scripts/local-acceptance.sh" --no-build > "$tmp/exited.out" 2>&1 && {
    echo 'Exited container falsely accepted' >&2; exit 1;
  }
grep -q 'Lampac process is not running (state=exited)' "$tmp/exited.out"
printf 'PASS: exited container fails immediately\n'
printf 'LAMPAC_BUNNY_LOCAL_ACCEPTANCE_REGRESSION_PASS\n'
