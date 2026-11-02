# Architecture: independent Lampac Bunny

```text
                          Compatible clients (any Lampa instance, browser, API)
                                               |
                                           HTTPS (CDN)
                                               |
                              Bunny Magic Containers (1 region, 1 replica)
                                               |
                                   HTTP 0.0.0.0:9118
                                               |
                                Lampac NextGen (.NET 10)
                                 /                   \
                         /lampac/database       /lampac/cache
                           SQLite volume         cache volume
```

- **Source of code:** full preserved Lampac NextGen fork in this repository, compiled by the lightweight `bunny/Dockerfile` using official .NET 10 images; Chromium, GStreamer and FFmpeg are not installed in the default runtime. The base upstream `Dockerfile` remains available and unchanged.
- **Runtime:** one service listening on HTTP/9118. Bunny terminates HTTPS at the CDN endpoint; Dockerfile health and Bunny readiness check `/version?type=hash`.
- **Config:** `/opt/lampac-bunny/init.conf` is the immutable starter template. `bunny/docker-entrypoint.sh` writes `/lampac/init.conf` and `/lampac/passwd` from environment on every start; these are in the ephemeral application directory. Overriding requires `LAMPAC_BUNNY_CONFIG_B64` with valid JSON.
- **State:** Lampac's own SQLite and files under `/lampac/database`, optional `/lampac/cache`. No Bunny Database, Bunny Storage or Scripting connection is made implicitly.
- **Plugins:** `/online.js` is the main client integration path. No Lampa Multilingual build, WGT, source import or compile dependency exists.
- **Optional modules:** can be enabled with a validated custom JSON after network/security compatibility review. Embedded TorrServer and JacRed are **not** part of the default operational profile.
- **Networking:** HTTP APIs are the only tested design target. P2P, DLNA, multicast and transcoding are experiment-only until proven in the live Bunny sandbox.

## Release evidence required before production claims

1. Offline bootstrap preflight PASS (local).
2. Real docker image build PASS (`linux/amd64`; not available in every environment).
3. Local container HTTP smoke PASS; check startup root credential and persistence across restart.
4. Bunny deploy one region/replica with real volume, external HTTPS health PASS.
5. Private authenticated client workflow PASS, media provider terms checked.
6. Backup and restore test of any SQLite state; no unverified multi-region or auto-scaling claims.
