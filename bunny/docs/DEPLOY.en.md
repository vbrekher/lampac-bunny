# Lampac Bunny — deploy to bunny.net (EN)

Lampac Bunny is a **standalone Lampac backend**. It does not depend on Lampa Multilingual Edition and can serve any compatible client. Only connect to content sources you are entitled to use.

> **Status:** source adapter and offline checks prepared; live Bunny deployment, content providers, playback and volume restoration **not yet verified**. Do not expose this app unprotected in production.


## Fix a read-only Docker Desktop disk

The provided build log failed **inside Docker Desktop storage**, not GitHub or NuGet: `dpkg: Input/output error`, `NuGet: Read-only file system`, then `metadata_v2.db: read-only file system`.

1. **Restart Docker Desktop** without Factory Reset or deleting other projects' volumes.
2. Run `bash bunny/scripts/doctor.sh` (read-only diagnostics).
3. Check Mac free space and **Docker Desktop → Settings → Resources → Advanced**. Increase or relocate the VM disk through Docker Desktop itself, not Finder.
4. Once Docker is healthy, you may interactively run `docker builder prune` to discard **unused build caches** if acceptable. Do **not** run `docker system prune --volumes`.
5. Rebuild after updating the repository:

```bash
git pull --ff-only
bash bunny/scripts/doctor.sh
bash bunny/scripts/preflight.sh
bash bunny/scripts/build-image.sh ghcr.io/vbrekher/lampac-bunny:v0.1.1 --load
```

The new `bunny/Dockerfile` is a **LIGHT profile**: it compiles Lampac source against official .NET 10 images but does **not install** Chromium, GStreamer or FFmpeg. The starter configuration disables the related modules. Do not enable them through a JSON override; a separately tested enhanced image is required. A persistent read-only VM after restart and sufficient space needs Docker disk investigation while preserving volumes, not a blind reset.

## 1. Build locally

Requires Docker with buildx, Bash and Git; `jq` is needed for offline preflight.

```bash
git clone https://github.com/vbrekher/lampac-bunny.git
cd lampac-bunny
bash bunny/scripts/preflight.sh
bash bunny/scripts/build-image.sh ghcr.io/vbrekher/lampac-bunny:v0.1.1 --load
# To publish after docker login ghcr.io:
bash bunny/scripts/build-image.sh ghcr.io/vbrekher/lampac-bunny:v0.1.1 --push
```

`--load` builds a local image; `--push` publishes it to your registry. The Dockerfile builds this fork's .NET source; it does not simply wrap an upstream binary. Expect a large image and a resource-intensive build due to browser and media dependencies.

For local development:

```bash
export LAMPAC_ROOT_PASSWORD="$(openssl rand -hex 24)"
docker compose -f bunny/compose.yaml up --build -d
curl -fsS 'http://127.0.0.1:9118/version?type=hash'
```

Keep the password out of Git and public logs.

## 2. Deploy to Bunny Magic Containers

Open [Bunny Dashboard](https://dash.bunny.net/) → **Magic Containers → Add App**:

1. Select your published **linux/amd64** image `ghcr.io/vbrekher/lampac-bunny:v0.1.1`; connect GHCR first if the image is private.
2. Create **one CDN endpoint** forwarding to container port **9118**. TLS terminates at Bunny; Lampac listens on HTTP internally.
3. Attach a persistent volume at `/lampac/database` (for example, 5 GB). A second optional volume can go to `/lampac/cache` (for example, 2 GB). Trial accounts support only one volume.
4. Add `LAMPAC_ROOT_PASSWORD` in Environment Variables (unique, at least 16 characters).
5. Choose **one region, one replica, no autoscaling**. Lampac's embedded SQLite is not distributed.
6. Add HTTP startup/readiness/liveness checks: path `/version?type=hash`, port 9118, and allow a generous initial startup window.
7. Before sharing the endpoint, configure proper access controls, rate limits and route restrictions. A Bunny CDN endpoint is **public** by default; upstream modules are not all suitable for public exposure.
8. Deploy, inspect logs and verify:

```bash
bash bunny/scripts/smoke.sh 'https://YOUR-CONTAINER-ENDPOINT'
```

This checks the health URL and `/online.js`, not actual media availability or codec support.

## 3. Optional modules and configuration

The safe-start template disables stateful and risky modules (including TorrServer, JacRed, Sync, TimeCode, GStreamer, DLNA, WebLog and SISI). They remain in the source code and can be enabled only after validating security, networking and resources.

To override the configuration, edit a local copy of `bunny/config/init.conf`, then encode it:

```bash
base64 < bunny/config/init.conf | tr -d '\n'
```

Paste the result into the Bunny `LAMPAC_BUNNY_CONFIG_B64` environment variable. The decoded file must be valid JSON, with HTTP on `0.0.0.0:9118` (or `ip=any`). The entrypoint fails closed on invalid settings. Restart the container to apply configuration. Never embed secrets in the JSON preset.

## 4. Persistence and caveats

- `/lampac/database` retains local SQLite state, **not Bunny Database**. Direct Bunny Database integration is not implemented.
- Bunny persistent volumes have **no automatic replication or backup**, and separate replicas receive independent volumes. Use one replica and back up offline snapshots with a restore drill.
- Torrent/P2P, multicast/DLNA, inbound network protocols and GStreamer workloads may be limited by Magic Containers sandbox, networking or costs. Not certified.
- Open online source access and media relay require explicit abuse, copyright, credential and SSRF protections. No all-providers-working claim is made.

Read [Security](SECURITY.md), [Architecture](ARCHITECTURE.md), the [Bunny deployment documentation](https://bunny.net/docs/magic-containers/deploy), [Persistent Volumes](https://bunny.net/docs/magic-containers/persistent-volumes), and [Lampac docs](https://docs.lampac.dev/).
