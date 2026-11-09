#!/usr/bin/env python3
"""Offline tests for one-key Bunny Magic Containers deployment, no real resources."""
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
from unittest import mock

MODULE = Path(__file__).resolve().parent / "deploy_bunny.py"
spec = importlib.util.spec_from_file_location("lampac_bunny_deploy", MODULE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class FakeAPI:
    def __init__(self, *, app=None):
        self.calls = []
        self.app = app
        self.registries = [{"id": 42, "hostName": "ghcr.io", "isPublic": True}]
        self.regions = [
            {"id": "NL", "name": "Amsterdam", "hasCapacity": True},
            {"id": "DE", "name": "Frankfurt", "hasCapacity": True},
        ]
        self.created = None

    def items(self, path):
        self.calls.append(("GET ITEMS", path))
        if path.startswith("/regions"):
            return self.regions
        if path.startswith("/registries"):
            return self.registries
        if path.startswith("/apps?"):
            return [self.app] if self.app else []
        if path.endswith("/endpoints"):
            return [{"type": "cdn", "publicHost": "mc-mock.bunny.run"}]
        raise AssertionError("Unexpected list endpoint: " + path)

    def call(self, method, path, body=None):
        self.calls.append((method, path, body))
        if method == "POST" and path == "/registries":
            self.registries.append({"id": 42, "hostName": "ghcr.io", "isPublic": True})
            return {"status": "saved", "id": 42}
        if method == "POST" and path == "/apps":
            self.created = body
            self.app = {"name": m.APP_NAME, "id": "mock-app-id"}
            return {"id": "mock-app-id"}
        if method == "POST" and path.endswith("/deploy"):
            return {}
        if method == "GET" and path.endswith("/overview"):
            return {"status": "active", "regions": [{"pods": [{"name": "mock-pod", "status": "ready", "containers": [{
                "name": m.CONTAINER_NAME, "status": "ready", "image": m.IMAGE + "@" + m.IMAGE_DIGEST
            }]}]}]}
        if method == "GET" and path.startswith("/apps/"):
            return {
                "id": "mock-app-id", "name": m.APP_NAME,
                "containerTemplates": [{
                    "id": "container-id", "imageRegistryId": "42",
                    "name": m.CONTAINER_NAME, "imageName": "lampac-bunny",
                    "imageNamespace": "vbrekher", "imageTag": m.IMAGE_TAG, "imageDigest": m.IMAGE_DIGEST,
                    "probes": m.create_payload("AMS", "42", "test")["containerTemplates"][0]["probes"],
                    "endpoints": [{"displayName": "lampac-http", "type": "cdn", "pullZoneId": "88", "isSslEnabled": True, "portMappings": [{"containerPort": 9118, "exposedPort": None}]}],
                }],
                "displayEndpoint": {"address": "mc-mock.bunny.run"},
            }
        raise AssertionError("Unexpected request: " + repr((method, path)))


class InstallerTests(unittest.TestCase):
    def test_default_region_priority_and_full_payload(self):
        chosen = m.select_region([{"id": "DE"}, {"id": "NL", "hasCapacity": True}])
        self.assertEqual(chosen["id"], "NL")
        p = m.create_payload("NL", "42", "test-root-password-at-least-16-characters")
        self.assertEqual(p["runtimeType"], "shared")
        self.assertEqual(p["autoScaling"], {"min": 1, "max": 1})
        self.assertEqual(p["regionSettings"]["requiredRegionIds"], ["NL"])
        self.assertEqual(p["volumes"], [{"name": m.VOLUME_NAME, "size": 5}])
        c = p["containerTemplates"][0]
        self.assertEqual(c["volumeMounts"], [{"name": m.VOLUME_NAME, "mountPath": "/lampac/database"}])
        self.assertEqual(c["endpoints"][0]["cdn"]["portMappings"][0]["containerPort"], 9118)
        self.assertEqual(c["probes"]["readiness"]["httpGet"]["request"]["path"], "/version")
        self.assertEqual(c["imageRegistryId"], "42")

    def test_no_non_european_fallback(self):
        with self.assertRaises(m.InstallerError):
            m.select_region([{"id": "US", "hasCapacity": True}])

    def test_existing_image_refused(self):
        with self.assertRaises(m.InstallerError):
            m.validate_existing({"containerTemplates": [{
                "name": "lampac", "imageNamespace": "someone", "imageName": "different",
                "imageTag": "latest",
            }]})

    @mock.patch.object(m, "verify_public_image", return_value=None)
    @mock.patch.object(m, "check_http", return_value=True)
    def test_create_deploy_state_permissions_and_retry_no_duplicates(self, _check, _verify):
        with tempfile.TemporaryDirectory() as d:
            state_path = Path(d) / "safe" / "deployment.json"
            api = FakeAPI()
            app_id = m.install(api, region=None, state_path=state_path)
            self.assertEqual(app_id, "mock-app-id")
            self.assertEqual(api.created["containerTemplates"][0]["imageTag"], m.IMAGE_TAG)
            state = json.loads(state_path.read_text())
            self.assertEqual(state["appId"], "mock-app-id")
            self.assertTrue(state["deployed"])
            self.assertTrue(len(state["password"]) >= 32)
            self.assertNotIn("api-key", state_path.read_text())
            if os.name == "posix":
                self.assertEqual(stat.S_IMODE(state_path.stat().st_mode), 0o600)
            previous = len([x for x in api.calls if x[0] == "POST" and x[1] == "/apps"])
            m.install(api, region=None, state_path=state_path)
            self.assertEqual(len([x for x in api.calls if x[0] == "POST" and x[1] == "/apps"]), previous)
            self.assertEqual(len([x for x in api.calls if x[0] == "POST" and x[1].endswith("/deploy")]), 1)

    def test_failed_api_does_not_echo_token(self):
        with self.assertRaises(m.InstallerError):
            m.BunnyAPI("my-secret-key\nnewline")

    def test_current_bunny_amsterdam_region(self):
        self.assertEqual(m.select_region([{"id": "AMS", "group": "EU", "hasCapacity": True}])["id"], "AMS")

    def test_no_capacity(self):
        with self.assertRaises(m.InstallerError):
            m.select_region([{"id": "AMS", "hasCapacity": False}])

    def test_registry_type_and_digest_pin(self):
        api = FakeAPI()
        api.registries = []
        m.ensure_registry(api)
        body = next(c[2] for c in api.calls if c[:2] == ("POST", "/registries"))
        self.assertEqual(body["type"], "gitHub")
        self.assertEqual(m.create_payload("AMS", "42", "test-password")["containerTemplates"][0]["imageDigest"], m.IMAGE_DIGEST)

    def test_registry_failure_prevents_app_creation(self):
        api = FakeAPI()
        api.registries = []
        api.call = mock.Mock(side_effect=m.InstallerError("registry unavailable"))
        with tempfile.TemporaryDirectory() as d, self.assertRaises(m.InstallerError):
            m.install(api, region=None, state_path=Path(d) / "state.json", verify_image=False)
        self.assertIsNone(api.created)

    def test_ghcr_failure_has_no_mutations(self):
        api = FakeAPI()
        with tempfile.TemporaryDirectory() as d, mock.patch.object(
            m, "verify_public_image", side_effect=m.InstallerError("GHCR unavailable")
        ), self.assertRaises(m.InstallerError):
            m.install(api, region=None, state_path=Path(d) / "state.json")
        self.assertFalse(any(c[0] == "POST" for c in api.calls))

    def test_partial_deploy_reuses_app_and_password(self):
        api = FakeAPI()
        original = api.call
        def fail_deploy(method, path, body=None):
            if path.endswith("/deploy"):
                raise m.InstallerError("network timeout")
            return original(method, path, body)
        api.call = fail_deploy
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "state.json"
            with self.assertRaises(m.InstallerError):
                m.install(api, region=None, state_path=path, verify_image=False, poll=False)
            before = m.read_state(path)
            self.assertFalse(before["deployed"])
            api.call = original
            m.install(api, region=None, state_path=path, verify_image=False, poll=False)
            after = m.read_state(path)
            self.assertTrue(after["deployed"])
            self.assertEqual(before["password"], after["password"])
            self.assertEqual(sum(c[:2] == ("POST", "/apps") for c in api.calls), 1)

    def test_http_error_redacts_response_and_key(self):
        from urllib.error import HTTPError
        from io import BytesIO
        secret = "test-secret-do-not-echo"
        with mock.patch.object(m.NO_REDIRECT_OPENER, "open", side_effect=HTTPError(
            "https://api.bunny.net/mc/apps", 401, "unauthorized", {}, BytesIO(secret.encode())
        )):
            with self.assertRaises(m.InstallerError) as result:
                m.BunnyAPI(secret).call("GET", "/apps")
        self.assertNotIn(secret, str(result.exception))
        self.assertIn("401", str(result.exception))

    def test_public_registry_selected_over_private_credentials(self):
        api = FakeAPI()
        api.registries.insert(0, {"id": 99, "hostName": "ghcr.io", "isPublic": False})
        self.assertEqual(m.ensure_registry(api), "42")
        self.assertFalse(any(c[0] == "POST" for c in api.calls))

    def test_startup_probe_allows_cold_module_compilation(self):
        c = m.create_payload("AMS", "42", "offline-test-password")["containerTemplates"][0]
        self.assertGreaterEqual(c["probes"]["startup"]["failureThreshold"] * c["probes"]["startup"]["periodSeconds"], 600)

    def test_legacy_upgrade_retains_credentials_and_cdn_volume_mount(self):
        api = FakeAPI(app={"name": m.APP_NAME, "id": "existing"})
        container = m.create_payload("AMS", "42", "test-existing-root-password")["containerTemplates"][0]
        container.update(id="existing-container", imageTag="v0.1.1", imageDigest=m.LEGACY_DIGEST)
        container["endpoints"] = [{"displayName": "lampac-http", "type": "cdn", "pullZoneId": "88", "isSslEnabled": True,
                                   "portMappings": [{"containerPort": 9118, "exposedPort": None}]}]
        calls = []
        def call(method, path, body=None):
            calls.append((method, path, body))
            if method == "GET": return {"id": "existing", "status": "active", "containerTemplates": [container]}
            if method == "PATCH": return {"id": "existing"}
            raise AssertionError("Upgrade must not create resources or issue a second deployment")
        api.call = call
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "state.json"
            m.save_state({"appId": "existing", "image": m.LEGACY_IMAGE, "password": "test-existing-root-password", "deployed": True}, path)
            m.install(api, region=None, state_path=path, verify_image=False, poll=False)
            state = m.read_state(path)
            self.assertEqual(state["image"], m.IMAGE)
            self.assertEqual(state["password"], "test-existing-root-password")
        changed = next(c[2]["containerTemplates"][0] for c in calls if c[0] == "PATCH")
        self.assertEqual(changed["id"], "existing-container")
        self.assertEqual(changed["endpoints"][0]["cdn"]["pullZoneId"], 88)
        self.assertEqual(changed["environmentVariables"], container["environmentVariables"])
        self.assertEqual(changed["volumeMounts"], container["volumeMounts"])
        self.assertEqual(changed["imageDigest"], m.IMAGE_DIGEST)

    def test_unmasked_key_prompt_is_refused(self):
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(m.sys, "argv", ["deploy_bunny.py"]), \
             mock.patch.object(m.getpass, "getpass", side_effect=m.getpass.GetPassWarning("cannot hide input")), \
             mock.patch.object(m, "install") as install:
            self.assertEqual(m.main(), 2)
            install.assert_not_called()

    def test_ready_requires_target_digest_and_new_pod_after_restart(self):
        api = FakeAPI()
        self.assertTrue(m.deployment_ready(api, "mock-app-id"))
        self.assertFalse(m.deployment_ready(api, "mock-app-id", {"mock-pod"}))
        self.assertTrue(m.deployment_ready(api, "mock-app-id", {"old-pod"}))
        api.call = lambda *args: {"status": "active", "regions": [{"pods": [{"name": "old-pod", "status": "ready", "containers": [{
            "name": m.CONTAINER_NAME, "status": "ready", "image": m.LEGACY_IMAGE + "@" + m.LEGACY_DIGEST
        }]}]}]}
        self.assertFalse(m.deployment_ready(api, "mock-app-id"))

    def test_partial_app_missing_cdn_is_repaired_without_new_app_or_volume(self):
        api = FakeAPI(app={"id": "existing", "name": m.APP_NAME})
        c = m.create_payload("AMS", "42", "test-existing-password")["containerTemplates"][0]
        c.update(id="container-existing", endpoints=[])
        changes = []
        def call(method, path, body=None):
            if method == "GET": return {"id": "existing", "status": "active", "containerTemplates": [c]}
            if method == "PATCH": changes.append(body);return {"id": "existing"}
            raise AssertionError("CDN recovery must not create another app or volume")
        api.call = call
        with tempfile.TemporaryDirectory() as d:
            m.install(api, region=None, state_path=Path(d) / "state.json", verify_image=False, poll=False)
        self.assertEqual(len(changes), 1)
        patch = changes[0]
        self.assertNotIn("volumes", patch)
        repaired = patch["containerTemplates"][0]
        self.assertEqual(repaired["id"], "container-existing")
        self.assertEqual(repaired["volumeMounts"], c["volumeMounts"])
        self.assertTrue(repaired["endpoints"][0]["cdn"]["isSslEnabled"])
        self.assertEqual(repaired["endpoints"][0]["cdn"]["portMappings"][0]["containerPort"], 9118)

    def test_piped_bash_download_path_and_arguments(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); binpath = root / "bin"; binpath.mkdir()
            python = binpath / "python3"
            python.write_text('#!/bin/sh\n[ "$1" = "-c" ] && exit 0\nprintf "%s\\n" "$*" > "$MOCK_INSTALL_PYTHON"\n')
            curl = binpath / "curl"
            curl.write_text('#!/bin/sh\nprintf "%s\\n" "$*" > "$MOCK_INSTALL_CURL"\nwhile [ "$#" -gt 0 ]; do\n if [ "$1" = "-o" ]; then shift; printf "# downloaded test fixture\\n" > "$1"; exit 0; fi\n shift\ndone\nexit 1\n')
            python.chmod(0o755);curl.chmod(0o755)
            env = os.environ.copy();env.update(PATH=str(binpath)+os.pathsep+env["PATH"], MOCK_INSTALL_PYTHON=str(root/"python.out"), MOCK_INSTALL_CURL=str(root/"curl.out"))
            body = (MODULE.parent / "install-bunny.sh").read_text()
            result = subprocess.run(["bash", "-s", "--", "--timeout", "900"], input=body, env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("--timeout 900", (root/"python.out").read_text())
            self.assertIn("661cee831b9d35b6d8b94043346a17683f073a91", (root/"curl.out").read_text())

    def test_ambiguous_apps_refused(self):
        api = FakeAPI()
        api.items = lambda _: [{"name": m.APP_NAME, "id": "a"}, {"name": m.APP_NAME, "id": "b"}]
        with self.assertRaises(m.InstallerError):
            m.find_app(api)

    def test_endpoint_timeout_does_not_report_success(self):
        api = FakeAPI(app={"name": m.APP_NAME, "id": "mock-app-id"})
        with tempfile.TemporaryDirectory() as d, mock.patch.object(
            m, "endpoint_url", return_value=None
        ), mock.patch.object(m.time, "monotonic", side_effect=[0, 2]), self.assertRaises(m.InstallerError):
            m.install(api, region=None, state_path=Path(d) / "state.json", verify_image=False, timeout=1)
        self.assertFalse(any(c[0] == "POST" for c in api.calls))

    def test_explicit_redeploy_preserves_app(self):
        api = FakeAPI(app={"name": m.APP_NAME, "id": "mock-app-id"})
        with tempfile.TemporaryDirectory() as d:
            m.install(api, region=None, state_path=Path(d) / "state.json", verify_image=False, poll=False, redeploy=True)
        self.assertEqual(sum(c[:2] == ("POST", "/apps/mock-app-id/deploy") for c in api.calls), 1)
        self.assertFalse(any(c[:2] == ("POST", "/apps") for c in api.calls))

    def test_existing_conflicting_app_no_write(self):
        api = FakeAPI(app={"name": m.APP_NAME, "id": "existing"})
        api.call = lambda *a, **kw: {
            "containerTemplates": [{"name": "lampac", "imageNamespace": "other",
                                    "imageName": "other", "imageTag": "v2"}]
        }
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(m, "verify_public_image", return_value=None):
                with self.assertRaises(m.InstallerError):
                    m.install(api, region=None, state_path=Path(d) / "state.json", poll=False)


if __name__ == "__main__":
    unittest.main(verbosity=2)
