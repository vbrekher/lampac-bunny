# Lampac Bunny — live Bunny acceptance

**LIVE_DEPLOYMENT_VERIFIED = true**

**LIVE_ACCEPTANCE = PASS**

Verified at **2026-11-04T00:41:32.557951+00:00 UTC** against real Bunny Magic Containers. All mandatory checks below passed. Optional limits remain explicit.

| Identity | Verified value |
| --- | --- |
| Tested installer source | `661cee831b9d35b6d8b94043346a17683f073a91` |
| Runtime image source | `183366c0a6604658204e9dbf762c03ec5a30b894` (also reported by `/version?type=build`) |
| Image | `ghcr.io/vbrekher/lampac-bunny:v0.1.3` |
| OCI index digest | `sha256:25353ce71cf3bd5298877fd3b1cd40b2e9cbbeeaa8713fbedc126a02c69e66f2` |
| Architecture / runtime | `linux/amd64`, observed `linux-x64`, `.NET 10.0.14` |
| Bunny app ID | `Q3pUflMpyF4frwM` |
| Region / replicas | AMS, one shared replica, scaling min=1 / max=1 |
| Public URL | [https://mc-eggpu5qyvc.bunny.run](https://mc-eggpu5qyvc.bunny.run) |
| Persistent volume | `e7caca4b-e1e6-42b6-8553-7f1a1be9a067`, 5 GB at `/lampac/database` |
| Network | Internal HTTP 9118, public CDN HTTPS |
| Final state | App active; one pod and one Lampac container ready; one CDN endpoint |

## Results

`PASS` means actually checked on real infrastructure; `FAIL` means observed failure; `NOT_TESTED` means not exercised; `BLOCKED` means missing prerequisites. Local/mock tests do not count as live PASS.

| Check | Status | Evidence |
| --- | --- | --- |
| anonymous ghcr pull | PASS | Anonymous v0.1.1 and v0.1.3 manifests retrieved; exact OCI index digest and linux/amd64 verified. |
| container deployment | PASS | Real Bunny application created and upgraded; current pinned v0.1.3 is active. |
| container healthy | PASS | One ready pod, one ready Lampac container, exact expected image digest. |
| version http | PASS | HTTP 200 with a nonempty 32-byte build hash. |
| online js | PASS | HTTP 200 application/javascript, Node syntax check and browser Lampa plugin loading; HTTPS server URLs. |
| https tls | PASS | Default certificate-chain and hostname validation succeeded; TLS 1.3. |
| startup readiness liveness | PASS | All three HTTP probes configured on /version port 9118; active/ready runtime observed after cold starts. |
| restart recovery | PASS | Real API restart recovered in 53.1 seconds with unchanged SQLite response; CLI redeploy waited 51.4 seconds for a new healthy pod. |
| sqlite persistence | PASS | Actual TimeCode API write, direct SQLite marker count=1, PRAGMA integrity_check=ok, unchanged record after restart and repeated installer runs. |
| repeat installation | PASS | Repeated real shell installation kept one app, one original 5 GB volume, one endpoint and the same root password. |
| wrong api key | PASS | Real shell installer returned failure with HTTP 401; supplied invalid key was absent from output. |
| unauthorized admin access | PASS | Final admin/config/database/log routes return 404. Temporary stats control: no cookie 404, wrong cookie 404, valid root cookie 200. |
| unrestricted public proxy | PASS | Unauthenticated /media and /corseu return 401; raw/invalid proxy routes return 400 or 404; authorized synthetic relay actually decoded. |
| unexpected process recovery | PASS | Separate disposable v0.1.3 app: induced exit 137, automatic restart count=1, ready state and identical SQLite response; test app deleted. |
| dotnet log review | PASS | One pre-fix ArgumentOutOfRangeException reproduced on v0.1.1; fixed in v0.1.2+. Instrumented post-fix checks added no unhandled .NET exceptions. |
| lampa browser catalogs | PASS | Bundled Lampa web client rendered CUB home/catalog sections and plugin connected notice. |
| permitted media playback | PASS | Owned synthetic testsrc2 video relayed over HTTPS and decoded by FFmpeg: exit 0, 72 frames, 2.958333 seconds of reported output time. |
| physical tv clients | NOT_TESTED | No physical Samsung/Tizen/other TV hardware was tested. |
| all third party providers | NOT_TESTED | Individual provider catalogs, subscriptions, content rights and all formats are outside this acceptance scope. |
| cross machine concurrent install | NOT_TESTED | Local lock tested by design; no distributed account-wide create transaction is claimed. |
| cloud failure injection | NOT_TESTED | Regional exhaustion and CDN provisioning failures were not forcibly injected into the live account; offline failure/recovery tests and real successful provisioning were completed. |

## HTTP and TLS observations

`GET /version?type=hash` returned HTTP 200 and the 32-byte value `452f519c2941c30e71c8eea4c5ce9cb0`. `/online.js` returned HTTP 200, JavaScript content type, valid Node syntax and HTTPS server URLs. A forged unauthenticated `xscheme: http` header did not downgrade those URLs. CORS allowed the compatible client origin. Python's default TLS chain and hostname validation succeeded using TLS 1.3.

Final anonymous requests to `/adminpanel`, `/adminpanel/api/init`, `/adminpanel/api/current`, `/database-editor/api/summary`, `/stats/gc`, `/weblog`, `/passwd`, `/init.conf`, `/current.conf`, `/users.json`, database files and log files were denied with 404. Generic `/media` and `/corseu` requests without a token returned 401; raw/invalid proxy requests returned 400/404. The short DASH request now returns 400 instead of 500.

The default administrative modules are closed. A temporary stats authorization control gave **404 without a cookie, 404 with an incorrect cookie, 200 with the valid root cookie** during the v0.1.2 diagnostic phase; that authorization code is unchanged in v0.1.3. No password, account key, token or authenticated configuration response is included here.

## Actual SQLite and restart evidence

A uniquely identified synthetic record was written through the real TimeCode API. An authenticated temporary diagnostic container read `/lampac/database/TimeCode.sql` with SQLite and observed the `timecodes` table, **one marker row** and **`PRAGMA integrity_check = ok`**.

The HTTP response hash before restart was `90988ab8b85d6ef4a803c6ec21e71856e7faa74c39ce2f6426bbfe392e6e4b6f`. It was unchanged after a real Bunny restart, which recovered in **53.1 seconds**. The record also survived image/pod replacements. Two further runs of the actual shell installer were followed by actual TimeCode reads and returned the same record bytes. The original volume ID and root password remained unchanged.

The final real shell checks included two ordinary installations and `--redeploy`; the last waited **51.4 seconds** for a new healthy pod running the pinned digest. All exited 0 with the deployment success marker. The account retained exactly one `lampac-bunny` app, one original 5 GB volume and one endpoint. A real invalid-key invocation failed with HTTP 401 and did not echo the supplied key.

Sync/TimeCode and diagnostic settings were enabled only for acceptance. The published image defaults, disabled stateful modules and root-password-only environment were restored afterward. Test data was not removed from the main volume.

## Controlled crash on a separate instance

Disposable app `D4E91nnJfqgbr2i` used v0.1.3, a separate 1 GB volume and synthetic data only. A one-time SIGKILL terminated the .NET child with **exit 137**. Bunny automatically restarted it (**restart count 1**) and reached ready state. SQLite response hashes before and after were identical: `414f954fd3a8d2264610f596ea5e3133283b3f398988c690508b290d5104bb98`.

The first failed state was observed at 107.3 seconds and the recovered ready state at 189.8 seconds after test monitoring began. The app and its test resources were deleted afterward; its API lookup now returns 404. No existing user deployment or volume was used for the destructive test.

## Client and real media decoding

The bundled Lampa browser client loaded its CUB home/catalog sections and displayed a plugin-connected notice. This verifies the actual web client, not every TV platform or every provider.

A generated **320×180, 24 fps testsrc2 video** was hosted temporarily and relayed through authenticated `/media` into the encrypted HTTPS `/proxy` route. FFmpeg exited **0**, decoded **72 frames**, and reported **2.958333 seconds** of output time for a three-second run. This is actual decoding beyond an HTTP 200 check. The temporary media token and diagnostic endpoint were removed.

![Lampa catalog in the verified deployment](lampa-live.png)

## Bugs fixed

- Recover a missing CDN endpoint on an existing app without replacing the container ID or volume (offline regression); regional exhaustion/CDN control-plane failures were not forcibly injected into the live account.
- Select an anonymous public GHCR registry instead of reusing unrelated private credentials; private account registries were unchanged.
- Pin the verified OCI digest, hash manifest bytes, use the current AMS region ID, and preserve IDs, credentials, CDN and volume mounts during known-release upgrades.
- Reject short DASH tokens before slicing the input, eliminating the reproduced `ArgumentOutOfRangeException` / HTTP 500.
- Advertise HTTPS client URLs while Kestrel continues to listen on internal HTTP 9118; restrict `xscheme` overrides to authenticated internal requests.
- Use the query-free `/version` health probe and allow a ten-minute startup budget for cold module compilation.
- Wait for an active/ready runtime with the exact image digest and, after restart, a new pod; an old responding instance cannot certify a redeploy.
- Align the Python requirement to 3.10+, reject unmasked key prompts, add local installer locking, timeout control, explicit restart/redeploy and safe state migration.

A pre-fix .NET exception at `2026-11-03T23:56:29.118Z` was retained as evidence. Instrumented post-fix checks produced no additional unhandled .NET exceptions. No v0.1.1, v0.1.2 or v0.1.3 tag was silently overwritten.

## Local validation and scope

Passed: `bash bunny/scripts/preflight.sh`, **22** Python installer tests, `bash bunny/scripts/test-local-acceptance.sh`, shell/Python syntax, source builds of Core and Shared for Linux x64, agent metadata, link checks, credential scans and `git diff --check`. The local acceptance regression uses mocked Docker/curl and is not live evidence. Python used: 3.14.3.

Physical Samsung/Tizen devices, all upstream providers, all media formats and cross-machine concurrent provisioning were not tested. The inherited application version label is `bunny-preview`; the verified release is identified by its versioned image, digest and reported source commit. This acceptance provides no availability SLA or provider-wide security guarantee. Use consistent SQLite backups and one replica in one region.

The main app was initially created through the installer and then repaired/upgraded through the API. Final real shell reuse/redeploy was checked, and the current v0.1.3 template was also created on the separate recovery app. No second empty production app was provisioned merely to repeat the first-install path.

## Resources and reproduction

Remaining paid resources: **one shared Lampac replica, one 5 GB volume and one CDN endpoint**. Temporary diagnostic container/CDN and the separate 1 GB recovery test app were removed. Existing user applications, data, volumes and registry credentials were not modified or deleted.

```bash
curl -fsSL https://raw.githubusercontent.com/vbrekher/lampac-bunny/main/bunny/scripts/install-bunny.sh | bash
```

Enter the Bunny account API Key at the hidden prompt. Repeating the command reuses the matching deployment. Use `bash -s -- --redeploy --timeout 900` to restart and wait longer. Recognized v0.1.1/v0.1.2 deployments can migrate to the pinned release while retaining their data and credentials. Custom operator configuration is preserved and must advertise HTTPS URLs for HTTPS clients.

[Machine-readable results](live-bunny-results.json) contain the HTTP observations, pod/restart evidence and hashes without secrets. The [official Magic Containers OpenAPI](https://api-mc.opsbunny.net/docs/public/swagger.json), [deployment guide](https://bunny.net/docs/magic-containers/deploy) and [persistent-volume guide](https://bunny.net/docs/magic-containers/persistent-volumes) informed the API configuration.

**Conclusion: all mandatory live acceptance checks PASS for this pinned deployment and tested scope.**
