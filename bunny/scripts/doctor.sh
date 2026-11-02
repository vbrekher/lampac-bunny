#!/usr/bin/env bash
# Read-only diagnostics; never prune images, caches, containers or volumes.
set -u
echo '=== Lampac Bunny / Docker Desktop diagnostics (read-only) ==='
echo 'Host filesystem holding current directory:'
df -h . 2>&1 || true
if ! command -v docker >/dev/null 2>&1; then
  echo 'Docker CLI not found. Install/start Docker Desktop.'
  exit 1
fi
echo
echo 'Docker daemon:'
if ! docker info --format 'Server: {{.ServerVersion}} | Root: {{.DockerRootDir}} | Driver: {{.Driver}}' 2>&1; then
  echo 'Docker daemon unavailable. Restart Docker Desktop; do not reset or wipe volumes.'
  exit 1
fi
echo
echo 'Docker allocated/reclaimable usage (not exact VM free space):'
docker system df 2>&1 || true
echo
echo 'Buildx cache usage:'
docker buildx du 2>&1 || true
echo
echo 'To inspect the Linux VM disk limit on macOS: Docker Desktop > Settings > Resources > Advanced.'
echo 'If the daemon is healthy and build cache is unneeded: docker builder prune (interactive).'
echo 'Never run docker system prune --volumes or factory reset without backing up other projects.'
echo 'LAMPAC_BUNNY_DOCTOR_COMPLETE'
