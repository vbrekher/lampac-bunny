<p align="center"><img src="bunny/assets/hero.svg" alt="Lampac Bunny — media backend for Bunny Magic Containers" width="100%"></p>

<h1 align="center">Lampac Bunny</h1>
<p align="center"><strong>Your Lampac backend. One command. Bunny Magic Containers.</strong></p>
<p align="center">A source-built .NET 10 media backend for Lampa and other compatible clients, with automatic Bunny provisioning, a generated admin password and persistent SQLite storage.</p>

<p align="center">
  <a href="bunny/docs/DEPLOY.en.md">English</a> · <a href="bunny/docs/DEPLOY.ru.md">Русский</a> · <a href="bunny/docs/DEPLOY.nl.md">Nederlands</a> · <a href="docs/acceptance/LIVE_BUNNY_ACCEPTANCE.md">Live acceptance</a> · <a href="bunny/docs/SECURITY.md">Security</a>
</p>
<p align="center">
  <img alt="Bunny Magic Containers" src="https://img.shields.io/badge/Bunny-Magic_Containers-f59e0b">
  <img alt="linux amd64" src="https://img.shields.io/badge/image-linux%2Famd64-2563eb">
  <a href="docs/acceptance/LIVE_BUNNY_ACCEPTANCE.md"><img alt="Live acceptance blocked" src="https://img.shields.io/badge/live_acceptance-BLOCKED-eab308"></a>
  <a href="LICENSE"><img alt="AGPL-3.0" src="https://img.shields.io/badge/license-AGPL--3.0-64748b"></a>
</p>

**Live acceptance: BLOCKED — anonymous GHCR access is unavailable.** Real Bunny API access and European capacity were checked; deployment could not proceed through the public-image preflight. See the [dated evidence and remaining checks](docs/acceptance/LIVE_BUNNY_ACCEPTANCE.md). No production certification is claimed.

## Quick start

Requires **Python 3.10+**, Bash, curl, and a Bunny account with paid Magic Containers access. No Docker, GitHub account, VPS or SSH setup is required on the user's computer.

```bash
curl -fsSL https://raw.githubusercontent.com/vbrekher/lampac-bunny/main/bunny/scripts/install-bunny.sh | bash
```

Get your **account API Key** from [Bunny Dashboard](https://dash.bunny.net/) → Account → API. Enter it at the hidden terminal prompt. Never paste credentials into an issue or chat.

**Current prerequisite for the package owner:** make `ghcr.io/vbrekher/lampac-bunny` publicly pullable in [GitHub package settings](https://github.com/users/vbrekher/packages/container/lampac-bunny/settings). Then rerun the command. The installer refuses unavailable images before creating billable resources. Public access alone does not establish that the expected digest exists; the installer also checks the manifest bytes and `linux/amd64` platform.

## What the installer configures

| Component | Configuration |
| --- | --- |
| Application | `lampac-bunny`, one shared instance, one available European region |
| Image | `ghcr.io/vbrekher/lampac-bunny:v0.1.1`, pinned to the expected digest |
| Network | Internal HTTP `9118`, public HTTPS CDN endpoint |
| Storage | One 5 GB persistent volume at `/lampac/database` |
| Credentials | Random `LAMPAC_ROOT_PASSWORD`; API Key is never saved |
| Health | Startup, readiness and liveness probes on `/version?type=hash` |

The expected image digest is `sha256:ec518a9170c5f4b4373545851f2325f285ee0daa26af6cd4ffa5819200b12adc`; its availability is currently blocked by GHCR access. The LIGHT image excludes Chromium, FFmpeg and GStreamer. Optional stateful modules start disabled.

Compute, storage and CDN usage are billed by Bunny. The installer reports the HTTPS URL only after `/version?type=hash` and `/online.js` return nonempty HTTP 200 responses. These smoke checks do not certify playback, persistence or security.

## Connect, reopen and update

Add `https://YOUR-ENDPOINT/online.js` through your Lampa client's plugin settings. Other compatible clients can use Lampac's native API. Provider availability and client playback require separate testing with content you are entitled to use.

Find the server URL in the installer output or **Bunny Dashboard → Magic Containers → lampac-bunny → Endpoints**. Repeating the same command finds the matching application and preserves its volumes. The local password and deployment metadata are stored in `~/.config/lampac-bunny/deployment.json` with mode `0600` (or under `XDG_CONFIG_HOME`). Treat that file as a secret and keep a protected backup.

To redeploy the same pinned release, with a longer startup wait:

```bash
curl -fsSL https://raw.githubusercontent.com/vbrekher/lampac-bunny/main/bunny/scripts/install-bunny.sh | bash -s -- --redeploy --timeout 900
```

This does not upgrade to an arbitrary newer image. Future image upgrades require a reviewed release with a new version and digest. Never silently overwrite `v0.1.1`.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| Bunny HTTP 401/403 | Use the account API Key; check Magic Containers permissions |
| GHCR unavailable/private | Package owner enables public pulls; retry later for registry outages |
| No preferred region capacity | Retry later, or use `bash -s -- --region DE` when DE has capacity |
| HTTPS startup timeout | Inspect deployment, endpoint and logs in Bunny; rerun with `--timeout 900` |
| Interrupted deployment | Rerun the installer; it finds the existing app and retries a pending deployment |
| Conflicting app or local state | Inspect the named app and protected state file; do not delete volumes |
| Another installer running | Wait for it to finish; avoid simultaneous installs from different machines |

The local process lock prevents concurrent installers on one computer. Cross-machine concurrent provisioning is not an atomic operation; use one provisioning terminal per Bunny account. If a create request times out, inspect Bunny before retrying. Existing incompatible applications are rejected instead of overwritten.

## Development and operations

```bash
bash bunny/scripts/preflight.sh
python3 bunny/scripts/test_deploy_bunny.py
bash bunny/scripts/test-local-acceptance.sh
```

Build your own new image tag with `bash bunny/scripts/build-image.sh YOUR-REGISTRY/lampac-bunny:NEW-VERSION --load` or `--push`. For Docker disk diagnostics use `bash bunny/scripts/doctor.sh`; preserve existing volumes.

Read the deployment guides: [English](bunny/docs/DEPLOY.en.md) · [Русский](bunny/docs/DEPLOY.ru.md) · [Nederlands](bunny/docs/DEPLOY.nl.md). Also see [Architecture](bunny/docs/ARCHITECTURE.md), [Security](bunny/docs/SECURITY.md), [Bunny deployment](https://bunny.net/docs/magic-containers/deploy) and [Persistent volumes](https://bunny.net/docs/magic-containers/persistent-volumes).

## Deployment boundaries

- SQLite requires **one replica in one region**. Persistent volumes need separate backup and restore drills; Bunny Database is not a drop-in replacement.
- A public CDN endpoint is not an authentication boundary. The generated root password does not protect every media API. Review route restrictions, authentication and rate limits before sharing the URL. Unrestricted proxy protection remains unverified.
- Catalogs, providers, actual Lampa playback, restart recovery and SQLite durability are **not live-verified**. HTTP 200 alone cannot establish media playback.
- Torrent/P2P, DLNA, browser automation and enhanced media tools require separate images or platform validation.

## Explore Our Other Open-Source Projects

Tools across the Smart TV, Lampa, streaming and Bunny ecosystem:

<table>
<tr><td><h3><a href="https://github.com/vbrekher/lampa-multilingual-edition">🌍 Lampa Multilingual</a></h3><p>Multilingual Lampa experience with 21 languages, personalization and Samsung Tizen tooling.</p></td></tr>
<tr><td><h3><a href="https://github.com/vbrekher/TorrServer-bunny">🐰 TorrServer Bunny</a></h3><p>Self-hosted TorrServer deployment designed for Bunny Magic Containers, offering an alternative to renting a VPS.</p></td></tr>
<tr><td><h3><a href="https://github.com/vbrekher/iptv">📺 IPTV HUB</a></h3><p>IPTV playlist catalog, country-based collections, M3U resources and Bunny CDN workflows for compatible players.</p></td></tr>
</table>

**[Discover more projects by @vbrekher →](https://github.com/vbrekher?tab=repositories)**

## Credits & License

Thank you to the creators and contributors of [Lampac NextGen](https://github.com/lampac-nextgen/lampac) for the backend, and the original Lampa developers for the client ecosystem. Lampac Bunny is a community deployment variant, unaffiliated with Bunny.net or the upstream team.

Lampac source retains **[AGPL-3.0](LICENSE)**. Preserve upstream notices and provide corresponding source as required for modified network services. Check provider terms before making content available.
