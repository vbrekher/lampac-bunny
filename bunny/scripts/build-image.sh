#!/usr/bin/env bash
# Builds this fork's Lampac source (not a generic upstream prebuilt image).
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
IMAGE="${1:-ghcr.io/vbrekher/lampac-bunny:v0.1.0}"
MODE="${2:---load}"
case "$MODE" in
  --load|--push) ;;
  *) printf 'Usage: %s [image:tag] [--load|--push]\n' "$0" >&2; exit 2 ;;
esac
command -v docker >/dev/null 2>&1 || { echo 'Docker is required' >&2; exit 1; }
# This is an amd64 image because Bunny Magic Containers does not currently accept arm64.
docker buildx build --platform linux/amd64 --file "$ROOT_DIR/bunny/Dockerfile" \
  --tag "$IMAGE" "$MODE" "$ROOT_DIR"
printf 'Built %s for linux/amd64 using %s\n' "$IMAGE" "$MODE"
