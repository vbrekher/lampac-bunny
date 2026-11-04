#!/usr/bin/env python3
"""Lampac Bunny one-command Bunny Magic Containers installer.

Uses the official Magic Containers v3 OpenAPI contract:
https://api.bunny.net/mc (GET /regions, /registries, /apps; POST /registries,
POST /apps, POST /apps/{appId}/deploy). No Docker/Node/third-party Python deps.
"""
from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sys
import time
import warnings
from urllib import error, parse, request

API_BASE = "https://api.bunny.net/mc"
IMAGE_TAG = "v0.1.3"
IMAGE = "ghcr.io/vbrekher/lampac-bunny:" + IMAGE_TAG
LEGACY_IMAGE = "ghcr.io/vbrekher/lampac-bunny:v0.1.1"
LEGACY_DIGEST = "sha256:ec518a9170c5f4b4373545851f2325f285ee0daa26af6cd4ffa5819200b12adc"
IMAGE_DIGEST = "sha256:25353ce71cf3bd5298877fd3b1cd40b2e9cbbeeaa8713fbedc126a02c69e66f2"
PREVIOUS_IMAGE = "ghcr.io/vbrekher/lampac-bunny:v0.1.2"
PREVIOUS_DIGEST = "sha256:70b2e61d9c764e0b3d7f8afa42ad7aac5afcea34a3bfabf542d5c9cfb8a2b54b"
APP_NAME = "lampac-bunny"
CONTAINER_NAME = "lampac"
VOLUME_NAME = "lampac-database"
VOLUME_GB = 5
PORT = 9118
PREFERRED_REGIONS = ("AMS", "NL", "DE", "PL", "FR", "UK")
STATE_DIR = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "lampac-bunny"
STATE_FILE = STATE_DIR / "deployment.json"


class InstallerError(Exception):
    pass


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


# Bunny credentials must never be forwarded to another host by an HTTP redirect.
NO_REDIRECT_OPENER = request.build_opener(NoRedirect)


class BunnyAPI:
    def __init__(self, key: str):
        if not key or any(c in key for c in "\r\n"):
            raise InstallerError("Bunny API Key is empty or contains invalid characters")
        self.key = key

    def call(self, method: str, path: str, body: dict | None = None) -> dict:
        if not path.startswith("/") or "://" in path:
            raise InstallerError("Invalid Bunny API path")
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = request.Request(
            API_BASE + path,
            data=data,
            method=method,
            headers={
                "AccessKey": self.key,
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "lampac-bunny-installer/0.1.3",
            },
        )
        try:
            with NO_REDIRECT_OPENER.open(req, timeout=35) as res:
                raw = res.read(2_000_000)
                if not raw:
                    return {}
                try:
                    return json.loads(raw)
                except (UnicodeError, ValueError):
                    # Deploy endpoint may return a plain success message on HTTP 200.
                    if method == "POST" and path.endswith(("/deploy", "/restart")):
                        return {}
                    raise InstallerError("Unexpected non-JSON Bunny API response")
        except error.HTTPError as exc:
            if exc.code in (401, 403):
                raise InstallerError(
                    f"Bunny API: HTTP {exc.code}. Check your account API Key and Magic Containers permissions."
                ) from None
            # Do not print response bodies: API errors can echo submitted secrets.
            raise InstallerError(f"Bunny API {method} {path.split('?')[0]} returned HTTP {exc.code}") from None
        except (error.URLError, TimeoutError, OSError) as exc:
            raise InstallerError(
                f"Bunny API connection failed during {method} {path.split('?')[0]}; "
                "network error or timeout. Re-run the installer safely."
            ) from None
        except (ValueError, UnicodeError) as exc:
            raise InstallerError("Unexpected non-JSON Bunny API response") from None

    def items(self, path: str) -> list:
        result = []
        cursor = None
        for _ in range(20):
            joiner = "&" if "?" in path else "?"
            route = path + (joiner + "nextCursor=" + parse.quote(cursor, safe="") if cursor else "")
            data = self.call("GET", route)
            if not isinstance(data, dict) or not isinstance(data.get("items"), list):
                raise InstallerError(f"Invalid Bunny API list response for {path}")
            result.extend(data["items"])
            cursor = data.get("cursor")
            if not cursor:
                return result
        raise InstallerError(f"Bunny API pagination exceeded safe limit for {path}")


def verify_public_image() -> None:
    """Require anonymous GHCR access and the exact locally accepted digest."""
    token_url = (
        "https://ghcr.io/token?"
        + parse.urlencode({"scope": "repository:vbrekher/lampac-bunny:pull", "service": "ghcr.io"})
    )
    try:
        with request.urlopen(token_url, timeout=20) as res:
            token = json.load(res).get("token")
        if not isinstance(token, str) or not token:
            raise InstallerError("GHCR did not issue an anonymous pull token")
        req = request.Request(
            "https://ghcr.io/v2/vbrekher/lampac-bunny/manifests/" + IMAGE_TAG,
            headers={
                "Authorization": "Bearer " + token,
                "Accept": (
                    "application/vnd.oci.image.index.v1+json, "
                    "application/vnd.docker.distribution.manifest.list.v2+json, "
                    "application/vnd.oci.image.manifest.v1+json"
                ),
            },
        )
        with request.urlopen(req, timeout=25) as res:
            raw = res.read(2_000_000)
            digest = "sha256:" + hashlib.sha256(raw).hexdigest()
        if digest.lower() != IMAGE_DIGEST:
            raise InstallerError("GHCR tag digest mismatch: refusing an unexpected image")
        index = json.loads(raw)
        manifests = index.get("manifests", [])
        if not any(
            item.get("platform", {}).get("os") == "linux"
            and item.get("platform", {}).get("architecture") == "amd64"
            for item in manifests
        ):
            raise InstallerError("GHCR manifest has no linux/amd64 image")
    except InstallerError:
        raise
    except error.HTTPError as exc:
        if exc.code in (401, 403, 404):
            raise InstallerError(
                "GHCR image is not publicly pullable. In GitHub Packages → lampac-bunny → "
                "Package settings, change visibility to Public, then retry."
            ) from None
        raise InstallerError(f"GHCR verification failed with HTTP {exc.code}") from None
    except (error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise InstallerError("Could not verify GHCR image (network/registry error); retry later") from None


def read_state(path: Path = STATE_FILE) -> dict | None:
    if not path.exists():
        return None
    if path.is_symlink():
        raise InstallerError("Refusing symbolic-link deployment state file")
    if os.name == "posix" and (path.stat().st_mode & 0o077):
        raise InstallerError(f"Unsafe deployment state permissions: chmod 600 {path}")
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise InstallerError("Invalid deployment state; do not delete it until manually inspected") from None
    if not isinstance(state, dict) or state.get("image") not in (IMAGE, LEGACY_IMAGE, PREVIOUS_IMAGE) or not state.get("appId"):
        raise InstallerError("Deployment state does not match the expected Lampac Bunny image")
    return state


def save_state(state: dict, path: Path = STATE_FILE) -> None:
    directory = path.parent
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink():
        raise InstallerError("Refusing symbolic-link deployment state file")
    temp_path = directory / (".deployment." + secrets.token_hex(12))
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(temp_path, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(state, out, indent=2)
            out.write("\n")
        os.replace(temp_path, path)
        os.chmod(path, 0o600)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def select_region(regions: list, override: str | None = None) -> dict:
    available = [x for x in regions if isinstance(x, dict) and x.get("id") and x.get("hasCapacity") is not False]
    if not available:
        raise InstallerError("No Magic Containers region has available capacity")
    if override:
        found = next((r for r in available if r["id"].upper() == override.upper()), None)
        if not found:
            raise InstallerError("Requested region is unavailable. Regions with capacity: " +
                                 ", ".join(r["id"] for r in available))
        return found
    for choice in PREFERRED_REGIONS:
        found = next((r for r in available if r["id"].upper() == choice), None)
        if found:
            return found
    raise InstallerError(
        "No preferred European region available. Choose explicitly with --region REGION. "
        "Available: " + ", ".join(r["id"] for r in available)
    )


def find_app(api: BunnyAPI) -> dict | None:
    found = [a for a in api.items("/apps?limit=100") if str(a.get("name", "")).casefold() == APP_NAME.casefold()]
    if len(found) > 1:
        raise InstallerError("Multiple apps named lampac-bunny already exist; refusing an ambiguous change")
    return found[0] if found else None


def validate_existing(app: dict) -> None:
    containers = app.get("containerTemplates") or []
    if len(containers) != 1:
        raise InstallerError("An app named lampac-bunny already exists with different containers")
    item = containers[0]
    expected_digest = {"v0.1.1": LEGACY_DIGEST, "v0.1.2": PREVIOUS_DIGEST, IMAGE_TAG: IMAGE_DIGEST}.get(item.get("imageTag"))
    if item.get("imageDigest") not in (None, "", expected_digest):
        raise InstallerError("Existing app image digest differs; refusing to overwrite")
    if (item.get("name"), item.get("imageNamespace"), item.get("imageName")) != (
        CONTAINER_NAME, "vbrekher", "lampac-bunny"
    ) or item.get("imageTag") not in ("v0.1.1", "v0.1.2", IMAGE_TAG):
        raise InstallerError("App named lampac-bunny exists but uses another image; refusing to overwrite")


def ensure_registry(api: BunnyAPI) -> str:
    registries = api.items("/registries")
    existing = next((r for r in registries if str(r.get("hostName", "")).lower() == "ghcr.io" and r.get("isPublic") is True), None)
    if existing:
        return str(existing["id"])
    print("Connecting public GHCR registry to your Bunny account...")
    result = api.call("POST", "/registries", {"displayName": "ghcr.io", "type": "gitHub"})
    if result.get("status") != "saved" or not result.get("id"):
        # Collision or registry timing may leave a matching record visible.
        again = api.items("/registries")
        existing = next((r for r in again if str(r.get("hostName", "")).lower() == "ghcr.io" and r.get("isPublic") is True), None)
        if not existing:
            raise InstallerError("Bunny could not connect public GHCR registry")
        return str(existing["id"])
    return str(result["id"])


def create_payload(region_id: str, registry_id: str, password: str) -> dict:
    probe = {
        "initialDelaySeconds": 15,
        "periodSeconds": 10,
        "timeoutSeconds": 7,
        "failureThreshold": 12,
        "httpGet": {
            "request": {"path": "/version", "portNumber": PORT},
            "response": {"expectedStatusCode": "ok"},
        },
    }
    return {
        "name": APP_NAME,
        "runtimeType": "shared",
        "autoScaling": {"min": 1, "max": 1},
        "regionSettings": {
            "allowedRegionIds": [region_id],
            "requiredRegionIds": [region_id],
            "maxAllowedRegions": 1,
        },
        "containerTemplates": [{
            "name": CONTAINER_NAME,
            "image": IMAGE,
            "imageName": "lampac-bunny",
            "imageNamespace": "vbrekher",
            "imageTag": IMAGE_TAG,
            "imageDigest": IMAGE_DIGEST,
            "imageRegistryId": registry_id,
            "imagePullPolicy": "always",
            "environmentVariables": [{"name": "LAMPAC_ROOT_PASSWORD", "value": password}],
            "endpoints": [{
                "displayName": "lampac-http",
                "cdn": {
                    "isSslEnabled": True,
                    "portMappings": [{"containerPort": PORT, "exposedPort": 443}],
                },
            }],
            "volumeMounts": [{"name": VOLUME_NAME, "mountPath": "/lampac/database"}],
            "probes": {"startup": dict(probe, failureThreshold=60), "readiness": probe, "liveness": probe},
        }],
        "volumes": [{"name": VOLUME_NAME, "size": VOLUME_GB}],
    }


def endpoint_url(api: BunnyAPI, app_id: str) -> str | None:
    app = api.call("GET", "/apps/" + parse.quote(app_id, safe=""))
    address = (app.get("displayEndpoint") or {}).get("address")
    if not address:
        try:
            endpoints = api.items("/apps/" + parse.quote(app_id, safe="") + "/endpoints")
            address = next(
                (x.get("publicHost") for x in endpoints if x.get("type") == "cdn" and x.get("publicHost")),
                None,
            )
        except InstallerError:
            return None
    if not isinstance(address, str):
        return None
    if address.startswith("https://"):
        url = address.rstrip("/")
    elif re.fullmatch(r"[a-zA-Z0-9.-]+", address):
        url = "https://" + address
    else:
        return None
    return url if url.startswith("https://") else None


def check_http(url: str) -> bool:
    for path in ("/version?type=hash", "/online.js"):
        try:
            with request.urlopen(url + path, timeout=10) as res:
                if res.status != 200 or not res.read(1):
                    return False
        except (error.HTTPError, error.URLError, TimeoutError, OSError):
            return False
    return True


def pod_names(api: BunnyAPI, app_id: str) -> set:
    overview = api.call("GET", "/apps/" + parse.quote(app_id, safe="") + "/overview")
    return {p.get("name") for r in overview.get("regions", []) for p in r.get("pods", []) if p.get("name")}


def deployment_ready(api: BunnyAPI, app_id: str, previous_pods: set | None = None) -> bool:
    overview = api.call("GET", "/apps/" + parse.quote(app_id, safe="") + "/overview")
    if str(overview.get("status", "")).lower() != "active":
        return False
    return any(
        p.get("status") == "ready" and (not previous_pods or p.get("name") not in previous_pods)
        and any(c.get("name") == CONTAINER_NAME and c.get("status") == "ready"
                and IMAGE_DIGEST in str(c.get("image", "")) for c in p.get("containers", []))
        for r in overview.get("regions", []) for p in r.get("pods", [])
    )


def install(api: BunnyAPI, *, region: str | None, state_path: Path = STATE_FILE,
            verify_image: bool = True, poll: bool = True,
            timeout: int = 600, redeploy: bool = False) -> str:
    print("Lampac Bunny — automatic Bunny Magic Containers deployment")
    print("Image:", IMAGE)
    print("Configuration: one instance, HTTP 9118 / CDN HTTPS, 5 GB persistent database volume")
    # Validate account permissions before registry checks; GET cannot create resources.
    existing = find_app(api)
    if verify_image:
        verify_public_image()
        print("PASS: GHCR image is publicly pullable with verified digest and linux/amd64 platform")

    saved = read_state(state_path)
    previous_pods = None
    if saved and existing and saved["appId"] != existing["id"]:
        raise InstallerError("Local app ID differs from Bunny app of same name; refusing changes")
    if saved and not existing:
        raise InstallerError("Local state references an app absent from Bunny. Inspect account before retry")
    if existing:
        app_id = existing["id"]
        full = api.call("GET", "/apps/" + parse.quote(app_id, safe=""))
        validate_existing(full)
        registry_id = ensure_registry(api)
        container = full["containerTemplates"][0]
        desired = create_payload("unused", registry_id, "unused")["containerTemplates"][0]
        startup = (container.get("probes") or {}).get("startup") or {}
        configuration_changed = any(container.get(k) != desired[k] for k in (
            "imageTag", "imageDigest", "imageRegistryId"
        )) or (startup.get("httpGet") or {}).get("request", {}).get("path") != "/version"
        if configuration_changed:
            previous_pods = pod_names(api, app_id) if poll else None
            if not container.get("id"):
                raise InstallerError("Existing container has no ID; cannot repair configuration safely")
            # Full app patch applies one revision. Keep the container ID, environment,
            # entrypoint, mounts and existing CDN pull zone; never replace volumes.
            updated = {k: container[k] for k in (
                "id", "name", "imageName", "imageNamespace", "environmentVariables",
                "entryPoint", "volumeMounts", "imagePullPolicy"
            ) if k in container}
            updated.update({k: desired[k] for k in (
                "image", "imageTag", "imageDigest", "imageRegistryId", "probes"
            )})
            endpoints = container.get("endpoints") or []
            if any(e.get("type", "").lower() != "cdn" or not e.get("pullZoneId") for e in endpoints):
                raise InstallerError("Existing non-CDN endpoint needs manual review before image upgrade")
            updated["endpoints"] = [{"displayName": e["displayName"], "cdn": {
                "isSslEnabled": e.get("isSslEnabled", True), "pullZoneId": int(e["pullZoneId"]),
                "portMappings": [{"containerPort": p["containerPort"], "exposedPort": p.get("exposedPort") or 443}
                                 for p in e["portMappings"]],
            }} for e in endpoints]
            api.call("PATCH", "/apps/" + parse.quote(app_id, safe=""), {"containerTemplates": [updated]})
            print("Updated matching container to the pinned release and public GHCR registry; volume retained.")
            if saved:
                saved.update(image=IMAGE, imageDigest=IMAGE_DIGEST)
                save_state(saved, state_path)
        if saved and saved.get("image") != IMAGE:
            saved.update(image=IMAGE, imageDigest=IMAGE_DIGEST)
            save_state(saved, state_path)
        print("Existing Lampac Bunny found; no duplicate will be created.")
        if not saved:
            print("Note: this computer has no saved admin password for the existing app.")
        should_deploy = bool(
            redeploy or (saved and saved.get("deployed") is False)
            or full.get("status") in ("inactive", "failing", "unknown")
        )
    else:
        chosen = select_region(api.items("/regions?limit=100"), region)
        print(f"Region: {chosen.get('name') or chosen['id']} ({chosen['id']})")
        registry_id = ensure_registry(api)
        password = saved.get("password") if saved else None
        if not password:
            password = secrets.token_urlsafe(36)
        print("Creating Magic Containers app and volume...")
        created = api.call("POST", "/apps", create_payload(chosen["id"], registry_id, password))
        app_id = created.get("id")
        if not isinstance(app_id, str) or not app_id:
            raise InstallerError("Bunny returned no app ID. Re-run; installer will check for duplicates.")
        save_state({
            "appId": app_id, "image": IMAGE, "imageDigest": IMAGE_DIGEST,
            "password": password, "region": chosen["id"], "deployed": False,
        }, state_path)
        print("Created app ID:", app_id)
        print("Root password stored locally with mode 0600 at:", state_path)
        should_deploy = True

    if should_deploy:
        print("Starting deployment...")
        if existing and redeploy and previous_pods is None and poll:
            previous_pods = pod_names(api, app_id)
        route = "/restart" if existing and full.get("status") == "active" else "/deploy"
        # An app PATCH already starts the active deployment's new revision.
        if not (existing and configuration_changed and full.get("status") == "active"):
            api.call("POST", "/apps/" + parse.quote(app_id, safe="") + route)
        if not existing:
            local_state = read_state(state_path)
            local_state["deployed"] = True
            save_state(local_state, state_path)
        elif saved:
            saved["deployed"] = True
            save_state(saved, state_path)

    print("Bunny app ID:", app_id)
    if not poll:
        return app_id
    deadline = time.monotonic() + timeout
    attempt = 0
    while time.monotonic() < deadline:
        url = endpoint_url(api, app_id)
        if url and deployment_ready(api, app_id, previous_pods) and check_http(url):
            print("PASS: HTTPS health endpoint and online.js respond with HTTP 200")
            print("Your Lampac Bunny URL:", url)
            print("LAMPAC_BUNNY_BUNNY_DEPLOY_PASS")
            return app_id
        if attempt in (0, 9, 19):
            print("Waiting for Bunny deployment and CDN endpoint...")
        attempt += 1
        time.sleep(min(5, max(0, deadline - time.monotonic())))
    url = endpoint_url(api, app_id)
    if url:
        print("Endpoint:", url)
    raise InstallerError(
        "Bunny app was created, but its public HTTP checks are not yet ready. "
        "Do not create another app; re-run this installer or inspect Magic Containers logs."
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Deploy Lampac Bunny to Bunny Magic Containers using only your account API Key."
    )
    parser.add_argument("--region", help="Bunny region ID; default AMS, NL, DE, PL, FR, UK if available")
    parser.add_argument("--timeout", type=int, default=600, help="HTTPS startup wait in seconds (default 600)")
    parser.add_argument("--redeploy", action="store_true", help="Redeploy the matching app without replacing volumes")
    args = parser.parse_args()
    if args.timeout < 1:
        parser.error("--timeout must be positive")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            key = os.environ.get("BUNNY_API_KEY") or os.environ.get("BUNNYNET_API_KEY") or getpass.getpass(
                "Enter Bunny account API Key (hidden): "
            ).strip()
    except (EOFError, KeyboardInterrupt, getpass.GetPassWarning):
        print("Bunny API Key input cancelled. Run from an interactive terminal.", file=sys.stderr)
        return 2
    try:
        # Serialize installers on this machine; lock is released even after a crash.
        import fcntl
        STATE_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
        flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
        with os.fdopen(os.open(STATE_DIR / "install.lock", flags, 0o600), "w") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise InstallerError("Another installer is running on this machine; wait and retry") from None
            install(BunnyAPI(key), region=args.region, timeout=args.timeout, redeploy=args.redeploy)
        return 0
    except (InstallerError, OSError) as exc:
        message = str(exc) if isinstance(exc, InstallerError) else "Local state/lock I/O failed; inspect permissions and disk space before retrying"
        print("LAMPAC_BUNNY_BUNNY_DEPLOY_FAIL:", message, file=sys.stderr)
        return 1
    finally:
        key = ""


if __name__ == "__main__":
    sys.exit(main())
