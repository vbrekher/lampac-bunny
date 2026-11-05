# Lampac Bunny — deploy to Bunny

## Quick start

Requirements: macOS or Linux, Bash, curl, **Python 3.10+**, and a Bunny account that permits Magic Containers provisioning. Docker, GitHub, VPS and SSH configuration are not required.

```bash
curl -fsSL https://raw.githubusercontent.com/vbrekher/lampac-bunny/main/bunny/scripts/install-bunny.sh | bash
```

Get the **account API Key** in [Bunny Dashboard](https://dash.bunny.net/) → Account → API. Enter it at the hidden prompt. The installer sends it only to Bunny, never stores it, and rejects credential-bearing redirects. Existing `BUNNY_API_KEY` or `BUNNYNET_API_KEY` environment variables are supported for automation; do not put literal secrets in shell history.

**Live acceptance: PASS.** Verified on **2026-11-04 UTC** using real Bunny infrastructure in **AMS** and the pinned **v0.1.3** image. HTTPS, JavaScript/plugin loading, SQLite persistence, restart/crash recovery, repeated installation and protected administrative routes passed. See the [live report](../../docs/acceptance/LIVE_BUNNY_ACCEPTANCE.md) and [JSON evidence](../../docs/acceptance/live-bunny-results.json). Physical TV hardware and every provider were not tested.

Anonymous public GHCR access was verified. The installer selects the public GitHub registry and does not require GitHub credentials.

## Automatic configuration

The installer verifies `ghcr.io/vbrekher/lampac-bunny:v0.1.3`, expected digest `sha256:25353ce71cf3bd5298877fd3b1cd40b2e9cbbeeaa8713fbedc126a02c69e66f2`, and `linux/amd64`. It pins the image digest in Bunny's configuration, selects one available European region (AMS first), connects GHCR, and creates:

- One `lampac-bunny` application with shared runtime and scaling minimum/maximum both set to one.
- One 5 GB persistent volume mounted at `/lampac/database`.
- Internal HTTP port `9118` and a public HTTPS CDN endpoint.
- A random `LAMPAC_ROOT_PASSWORD` and startup/readiness/liveness probes at `/version`.

Bunny bills compute, storage and CDN usage. The installer waits up to 600 seconds for nonempty HTTP 200 responses from `/version?type=hash` and `/online.js`. This is a smoke check, not full acceptance.

## Find the URL and connect

The URL appears in terminal output and **Magic Containers → lampac-bunny → Endpoints**. Add `https://YOUR-ENDPOINT/online.js` in a compatible Lampa client's plugin settings. Test catalogs and playback separately using permitted content; API success is not proof of video playback.

The generated password and deployment metadata are saved at `~/.config/lampac-bunny/deployment.json` (or under `XDG_CONFIG_HOME`) with permissions `0600`. Keep a protected backup. Do not post this file or credentials publicly.

## Reopen, retry and update

Repeat the original command to locate and reuse the matching application without replacing its volumes. A pending or inactive deployment is retried. Conflicting images, duplicate names and inconsistent local state stop the installer for inspection.

```bash
# Redeploy the same pinned image; allow 15 minutes for HTTPS startup.
curl -fsSL https://raw.githubusercontent.com/vbrekher/lampac-bunny/main/bunny/scripts/install-bunny.sh | bash -s -- --redeploy --timeout 900
# Explicit region for a new application, if capacity is available.
curl -fsSL https://raw.githubusercontent.com/vbrekher/lampac-bunny/main/bunny/scripts/install-bunny.sh | bash -s -- --region DE
```

A local lock prevents simultaneous installs on one machine. Do not provision concurrently from multiple machines. After a create timeout, inspect the dashboard before retrying. Do not delete an existing application or volume to recover. Recognized v0.1.1/v0.1.2 deployments are migrated to the reviewed pinned v0.1.3 release, preserving the volume, password, CDN and custom operator configuration. Other images are refused. Published tags are never overwritten.

## Troubleshooting

| Failure | Action |
| --- | --- |
| Bunny 401/403 | Check the account API Key and Magic Containers permissions |
| GHCR inaccessible or digest mismatch | Check public package access; do not bypass digest verification |
| No capacity | Retry later or choose an available European region |
| Endpoint/startup timeout | Inspect container status, probes, CDN endpoint and logs; rerun with a longer timeout |
| Interrupted deployment | Rerun; the installer finds the matching app and retained volume |
| Local state mismatch | Inspect protected local metadata and the Bunny app before changing anything |
| Docker disk is read-only during development | Run `bash bunny/scripts/doctor.sh`; repair Docker storage while preserving volumes |

## Local development and configuration

```bash
bash bunny/scripts/preflight.sh
python3 bunny/scripts/test_deploy_bunny.py
bash bunny/scripts/test-local-acceptance.sh
# Use your own new versioned image tag:
bash bunny/scripts/build-image.sh YOUR-REGISTRY/lampac-bunny:NEW-VERSION --load
```

`--push` publishes after registry authentication. The LIGHT source build uses .NET 10 and excludes Chromium, FFmpeg and GStreamer. Do not enable those tools without a separately tested image. Optional modules such as Sync, TimeCode, TorrServer, JacRed, WebLog and SISI start disabled.

An optional `LAMPAC_BUNNY_CONFIG_B64` can encode a customized `bunny/config/init.conf`. Base64 is not encryption. The runtime override wins over `config/base.conf` and code defaults; keep the internal HTTP listener on `0.0.0.0:9118` and use `listen.scheme="https"` for advertised public URLs. Local HTTP-only development can advertise `http`. The bootstrap validates JSON and listener configuration, not the safety of every module.

## Security and persistence

The root password protects administrative functions, but the starter configuration is not a universal API authentication gateway. Public CDN routes require reviewed access controls, route restrictions and rate limits. Live unauthenticated generic relay checks returned 401/400/404; an authorized synthetic relay decoded successfully. Keep relay tokens private.

Use one replica in one region for SQLite. `/lampac/database` is local SQLite, not Bunny Database. Maintain consistent backups and test restoration; never remove user data for acceptance tests. Restart/recovery, SQLite durability and .NET log inspection were verified in the linked live report. Destructive tests belong on a separate disposable instance.

Read [Security](SECURITY.md), [Architecture](ARCHITECTURE.md), [official deployment](https://bunny.net/docs/magic-containers/deploy), [persistent volumes](https://bunny.net/docs/magic-containers/persistent-volumes), and [Lampac documentation](https://docs.lampac.dev/).
