#!/usr/bin/env bash
# One-command install: curl -fsSL https://raw.githubusercontent.com/vbrekher/lampac-bunny/main/bunny/scripts/install-bunny.sh | bash
# Prompts for the Bunny account API Key securely; never stores it.
set -euo pipefail

command -v python3 >/dev/null 2>&1 || {
  echo "Python 3.9+ is required. Install Python 3, then retry." >&2
  exit 1
}
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' || {
  echo "Python 3.9+ is required." >&2
  exit 1
}

if [[ "${BASH_SOURCE[0]}" != "bash" && -f "$(dirname -- "${BASH_SOURCE[0]}")/deploy_bunny.py" ]]; then
  python3 "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/deploy_bunny.py" "$@"
else
  command -v curl >/dev/null 2>&1 || { echo "curl is required" >&2; exit 1; }
  temp="$(mktemp -d)"
  trap 'rm -rf "$temp"' EXIT
  script_url="https://raw.githubusercontent.com/vbrekher/lampac-bunny/main/bunny/scripts/deploy_bunny.py"
  curl --proto '=https' --tlsv1.2 --fail --silent --show-error --location \
    --retry 3 --connect-timeout 10 --max-time 45 \
    "$script_url" -o "$temp/deploy_bunny.py"
  python3 "$temp/deploy_bunny.py" "$@"
fi
