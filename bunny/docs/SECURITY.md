# Security and production boundaries

This repository packages Lampac NextGen for Bunny Magic Containers; it does not audit or certify every upstream content provider, third-party script, proxy or native multimedia subsystem.

## Default stance

- Root administrative password **required at boot**, at least 16 characters. Never include it in Git, WGTs, `.env` files you commit, telemetry or screenshots.
- Entry point validates JSON and `listen=http://0.0.0.0:9118`, writes config and password with mode 0600, and removes the secrets from the environment before launching .NET.
- Starter configuration disables stateful/high-risk modules, browser automation and open statistics. It does **not** implement an authentication gateway for the remaining Lampac APIs.
- Public Bunny CDN endpoints are publicly reachable. Configure independent authentication/WAF/rate limits/route controls at the edge and review upstream module security *before* publishing.
- Limit the supported public routes to those actually required. Do not expose WebLog, unrestricted `/proxy/*` routes, arbitrary fetch URLs, admin pages or raw SQLite data.

## Stateful use

A separate persistent volume per replica means local SQLite cannot safely be shared among replicas. Stick to one replica/region, disable autoscaling and test backups/restoration. Note that in-place SQLite files need coordinated, consistent backup; stop writes or use the SQLite backup API, **not** a naive `tar` over a live WAL database.

## Media and network limitations

No claim is made that gVisor networking supports all P2P protocols, multicast discovery, loopback dependencies or inbound listener ports. GStreamer, FFmpeg and browser automation may consume substantial CPU/RAM; monitor and cap media relay traffic. Do not assume third-party source terms permit retransmission or caching.

## Configuration override

`LAMPAC_BUNNY_CONFIG_B64` is optional. Base64 is *encoding*, not encryption: treat its source JSON as non-secret. The bootstrap validates only listener settings/JSON syntax, **not** the security of enabled modules. The operator accepts all consequences of custom modules.

## License

The core is sourced from Lampac NextGen and retains **AGPL-3.0**. If you modify and offer the network service, comply with AGPL source availability requirements. This is an independent community deployment variant, not an official Bunny or Lampac distribution.
