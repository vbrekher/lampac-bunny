# Lampac Bunny — live Bunny acceptance

**LIVE_DEPLOYMENT_VERIFIED = false**  
**LIVE_ACCEPTANCE = BLOCKED**

Tested at **2026-11-03T21:46:50.957538+00:00 UTC** (UTC offset is explicit in the timestamp). Tested source commit: `c2eb9c9d2f8d10f9286a7700e1858a341183d96e`. Starting main: `8deb82073b019b7b138b070519bd14ff0d0c6b23`. The report commit follows the tested source commit; it adds evidence only.

## What actually ran

Saved Bunny credentials authenticated against the real Magic Containers API. The complete application list contained no `lampac-bunny`. The complete regions list reported capacity in **AMS**, a European candidate region. An intentionally invalid API Key received **HTTP 401**; the installer error did not include the key or response body.

Two Python installer attempts using the real account and an actual Bash installer invocation stopped at GHCR preflight. A separate anonymous request to the GHCR token endpoint returned **HTTP 401**. The original one-command public deployment path therefore cannot currently complete. Before and after the two Python attempts, the number of matching Bunny applications was **0**. No application, volume, registry or CDN endpoint was created by these attempts; existing user resources were not modified or removed.

The available GitHub CLI credential lacks `read:packages` (package metadata request returned HTTP 403). No authenticated image pull or package visibility change was performed. HTTP 401 alone cannot prove whether the package is private, missing or restricted by another access policy.

## Image and deployment identity

| Field | Observed value |
| --- | --- |
| Image requested | `ghcr.io/vbrekher/lampac-bunny:v0.1.1` |
| Expected digest | `sha256:ec518a9170c5f4b4373545851f2325f285ee0daa26af6cd4ffa5819200b12adc` |
| Observed digest / architecture | BLOCKED; no manifest retrieved |
| Intended architecture | `linux/amd64` |
| App ID / test deployment ID | None; deployment was not created |
| Deployed region | None; AMS capacity was observed only |
| Public HTTPS URL | None |
| Intended configuration | One shared replica, one EU region, port 9118, 5 GB SQLite volume, generated root password, three health probes |
| Resources charged by this test | No new resources provisioned; unrelated existing account usage is outside this report |

## Live results

`PASS` means checked against real infrastructure. `FAIL` means actually checked and not working. `NOT_TESTED` means not exercised. `BLOCKED` means prerequisites prevented the check. Offline tests below do not count as live PASS.

| Check | Status | Evidence |
| --- | --- | --- |
| Bunny authentication | PASS | Real authenticated application listing |
| EU regional capacity | PASS | AMS in paginated region listing reported capacity |
| Wrong API Key | PASS | Real API returned HTTP 401; secret absent from installer error |
| Anonymous GHCR pull access | FAIL | Anonymous token endpoint returned HTTP 401 |
| Digest and amd64 verification | BLOCKED | Manifest unavailable; expected digest is not observed evidence |
| Container deployment and healthy state | BLOCKED | Image preflight stopped creation |
| `GET /version?type=hash` | BLOCKED | No public deployment URL; no HTTP result fabricated |
| `GET /online.js` and JavaScript validity | BLOCKED | No running deployment |
| HTTPS / TLS | BLOCKED | No deployment endpoint |
| Startup / readiness / liveness | BLOCKED | Payload defines probes; no live probe results |
| Restart / recovery | BLOCKED | No running application to restart |
| Actual SQLite writes retained after restart | BLOCKED | No container or volume |
| Repeat installation of running app | BLOCKED | No initial deployment |
| Repeat failed preflight without new resources | PASS | Matching app count 0 before / 0 after two attempts |
| Unauthorized admin access | BLOCKED | No public endpoint; configured password alone is insufficient evidence |
| Unrestricted public proxy protection | BLOCKED | No live endpoint; API-wide authentication is not provided by the starter configuration |
| .NET exception log review | BLOCKED | No deployed .NET process |
| Real catalogs and Lampa compatibility | NOT_TESTED | No running application or client session |
| Permitted video playback | NOT_TESTED | No playback session; HTTP 200 would not be sufficient |
| Unexpected process termination | NOT_TESTED | No disposable test deployment |

## Changes and local verification

- Raised the shell prerequisite to Python 3.10+, aligning its advertised floor with the union annotation style. The previous `from __future__ import annotations` postpones annotation evaluation; no Python 3.9 execution failure was reproduced here.
- Added the explicit `gitHub` registry type from the official API contract.
- Hash manifest bytes and pass `imageDigest` to Bunny, preventing a mutable tag from selecting a different image after preflight. Reject an explicitly conflicting existing digest.
- Added AMS to preferred European regions, matching the live API's Amsterdam ID.
- Authenticate with a read-only Bunny call before GHCR preflight; invalid keys now get an actionable account error first.
- Added a local process lock, explicit `--redeploy`, a configurable 600-second default startup wait, standard CLI environment-variable support and redacted local I/O failure messages.
- Added failure/retry regression coverage. Updated README, EN/RU/NL instructions, linked ecosystem cards and honest acceptance status. Preserved hero, upstream credits and AGPL-3.0 notice.

Local checks completed: `bash bunny/scripts/preflight.sh`, **16** Python installer tests, `bash bunny/scripts/test-local-acceptance.sh`, shell syntax, Python compilation, agent metadata validation, changed-file credential scanning and `git diff --check`. All passed. Python used: **3.14.3**; execution on Python 3.10 itself was not tested. No .NET source project or Docker image was changed, rebuilt or republished.

Mock coverage includes unavailable capacity, registry failure, GHCR preflight failure with no writes, interrupted deploy retry retaining app/password, matching-app reuse, explicit redeploy, HTTP-error redaction, duplicate-name refusal and endpoint timeout without a success marker. These results are not Bunny certification. The local acceptance regression uses mocked Docker/curl; no actual local media playback was tested.

Three advertised project URLs and the author repository link returned HTTP 200. Official Bunny deployment and persistence links returned HTTP 200. `docs.lampac.dev` returned HTTP 403 to this environment; its contents could not be verified. Local documentation links were checked separately. Mintlify CLI is unavailable; no Mintlify site files were changed.

## Remaining risks and owner action

**High — public API access:** the existing starter configuration disables `accsdb` and does not protect every remaining media/proxy API. Administrative password configuration is not evidence of safe public operation. Keep the endpoint private until live admin/proxy checks and appropriate route controls are in place. No runtime configuration or image security fix is claimed in this PR.

**Medium — concurrency and partial creation:** the lock covers one machine. Bunny name lookup plus application creation is not a cross-machine transaction. Use one provisioning terminal per account. If a creation response or local state write fails, inspect Bunny before retrying; do not remove volumes. A lost local password must be recovered securely from the existing Bunny environment configuration rather than creating another app.

The owner must make the [expected GHCR package](https://github.com/users/vbrekher/packages/container/lampac-bunny/settings) anonymously pullable and confirm that the expected tag exists. This cannot be completed with the currently available package permissions. Then run this single command in a local interactive terminal; the API Key prompt is hidden:

```bash
curl -fsSL https://raw.githubusercontent.com/vbrekher/lampac-bunny/main/bunny/scripts/install-bunny.sh | bash
```

Until this PR is merged, the command uses the existing main installer. To test the PR implementation first, check out the PR branch and run `bash bunny/scripts/install-bunny.sh` from that checkout. Do not paste any key or deployment state file into GitHub or chat.

After provisioning, complete every blocked mandatory check, including actual SQLite writes and post-restart reads, healthy probes, repeat installation, admin/proxy protection, independent HTTPS checks and log inspection. Test crashes only on a separate instance and never delete existing data. Record actual URL, App ID, region and digest in a new dated evidence revision. Media playback requires a real permitted playback session.

**Conclusion:** installation hardening and documentation are prepared, but real deployment and production acceptance are **BLOCKED**. No green live-certified badge is published. The PR must remain unmerged until the required live checks pass.

## Sources and machine-readable evidence

- [Official Magic Containers OpenAPI](https://api-mc.opsbunny.net/docs/public/swagger.json), release `v1.11.1.0`, retrieved during this session; `ContainerRequest.imageDigest` and `ContainerRegistryRequest.type` checked.
- [Official Bunny deployment](https://bunny.net/docs/magic-containers/deploy) and [persistent volumes](https://bunny.net/docs/magic-containers/persistent-volumes).
- [Machine-readable results](live-bunny-results.json).
