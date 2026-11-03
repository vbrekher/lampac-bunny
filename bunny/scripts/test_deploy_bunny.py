#!/usr/bin/env python3
"""Offline tests for one-key Bunny Magic Containers deployment, no real resources."""
import importlib.util
import json
import os
from pathlib import Path
import stat
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
        self.registries = []
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
            self.registries.append({"id": 42, "hostName": "ghcr.io"})
            return {"status": "saved", "id": 42}
        if method == "POST" and path == "/apps":
            self.created = body
            self.app = {"name": m.APP_NAME, "id": "mock-app-id"}
            return {"id": "mock-app-id"}
        if method == "POST" and path.endswith("/deploy"):
            return {}
        if method == "GET" and path.startswith("/apps/"):
            return {
                "id": "mock-app-id", "name": m.APP_NAME,
                "containerTemplates": [{
                    "name": m.CONTAINER_NAME, "imageName": "lampac-bunny",
                    "imageNamespace": "vbrekher", "imageTag": "v0.1.1",
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
        self.assertEqual(c["probes"]["readiness"]["httpGet"]["request"]["path"], "/version?type=hash")
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
            self.assertEqual(api.created["containerTemplates"][0]["imageTag"], "v0.1.1")
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
            m.BunnyAPI("my-secret-key\\nnewline")

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
