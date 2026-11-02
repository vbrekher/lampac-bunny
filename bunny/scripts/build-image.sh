#!/usr/bin/env bash
# Reproducible source build, with Docker Desktop storage diagnostics on failure.
set -euo pipefail
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
IMAGE="${1:-ghcr.io/vbrekher/lampac-bunny:v0.1.1}"
MODE="${2:---load}"
case "$MODE" in
  --load|--push) ;;
  *) printf 'Usage: %s [image:tag] [--load|--push]\n' "$0" >&2; exit 2 ;;
esac
command -v docker >/dev/null 2>&1 || { echo 'Docker CLI is required' >&2; exit 1; }
docker info >/dev/null 2>&1 || {
  echo 'Docker Engine is unavailable. Start or restart Docker Desktop, then run bunny/scripts/doctor.sh.' >&2
  exit 1
}
docker buildx version >/dev/null 2>&1 || { echo 'Docker Buildx is required' >&2; exit 1; }
# Local macOS free disk is not the same as the Docker Desktop VM disk allocation.
echo 'Building the lightweight, source-built linux/amd64 profile (no Chromium/GStreamer/FFmpeg).'
echo 'For disk details, run: bash bunny/scripts/doctor.sh'
log_file="$(mktemp)"
trap 'rm -f "$log_file"' EXIT
if docker buildx build --platform linux/amd64 --progress=plain \
    --file "$ROOT_DIR/bunny/Dockerfile" \
    --build-arg "GIT_COMMIT=$(git -C "$ROOT_DIR" rev-parse HEAD 2>/dev/null || printf unknown)" \
    --tag "$IMAGE" "$MODE" "$ROOT_DIR" 2>&1 | tee "$log_file"; then
  printf 'LAMPAC_BUNNY_IMAGE_BUILD_PASS: %s (%s)\n' "$IMAGE" "$MODE"
else
  if grep -Eiq 'read-only file system|input/output error|metadata_v2[.]db|no space left on device' "$log_file"; then
    cat >&2 <<'HELP'

DOCKER_STORAGE_FAILURE: Docker Desktop's Linux VM disk became unwritable.
This is a Docker host/disk problem, not a NuGet package, password or GitHub login problem.
1. Restart Docker Desktop. Do not delete volumes or reset Docker to factory defaults.
2. Docker Desktop -> Settings -> Resources -> Advanced: inspect the disk image limit and usage.
3. Check free space on the Mac and Docker build cache (bash bunny/scripts/doctor.sh).
4. Once Docker is healthy, optionally run 'docker builder prune' interactively to remove unused build cache.
   WARNING: pruning may delete caches useful to other projects. Never prune volumes or all data blindly.
5. If the Docker VM stays read-only after restart and sufficient free space, preserve volumes and
   inspect Docker Desktop diagnostics for disk-image/filesystem corruption before resetting.
HELP
  else
    echo 'Docker build failed for another reason; inspect the first error above.' >&2
  fi
  exit 1
fi
