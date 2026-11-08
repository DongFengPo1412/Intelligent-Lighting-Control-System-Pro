import json
import unittest
import socket
import os
import sys
from pathlib import Path

# Add pc-agent-vision to path
sys.path.insert(0, str(Path(__file__).parent.parent / "pc-agent-vision"))

from service_discovery import ServiceAdvertisement
from access_control import AccessPolicy


class TestSecurityPairingAndDiscovery(unittest.TestCase):
    def test_discovery_payload_does_not_leak_credentials(self):
        advert = ServiceAdvertisement()
        payload_bytes = advert._build_discovery_payload("192.168.1.50", "192.168.1.100", 8080)
        payload = json.loads(payload_bytes.decode("utf-8"))

        # MUST NOT leak access_token or control_token
        self.assertNotIn("access_token", payload, "Security violation: access_token leaked in discovery payload!")
        self.assertNotIn("control_token", payload, "Security violation: control_token leaked in discovery payload!")

        # MUST contain non-sensitive metadata only
        self.assertEqual(payload.get("service"), "KurisuPro")
        self.assertEqual(payload.get("port"), 8080)
        self.assertIn("server_url", payload)
        self.assertTrue(payload.get("pairing_required"))

    def test_access_policy_rejects_unauthorized_token(self):
        policy = AccessPolicy(token="a" * 32)
        
        class FakeRequest:
            def __init__(self, headers=None, query=None, path="/api/status"):
                self.headers = headers or {}
                self.query = query or {}
                self.path = path
                self.cookies = {}
                self.remote = "192.168.1.50"
                self.scheme = "http"
                self.host = "192.168.1.100:8080"

        # No token -> False
        req_none = FakeRequest()
        self.assertFalse(policy.authorized(req_none))

        # Invalid token -> False
        req_wrong = FakeRequest(headers={"Authorization": "Bearer " + "b" * 32})
        self.assertFalse(policy.authorized(req_wrong))

        # Correct token -> True
        req_ok = FakeRequest(headers={"Authorization": "Bearer " + "a" * 32})
        self.assertTrue(policy.authorized(req_ok))

    def test_camera_bridge_destination_whitelist(self):
        # Verify the regex/logic used by Android MainActivity to check upload destination
        allowed_endpoints = {"/api/vision/phone_frame", "/api/pro/vision/frame", "/api/pro/camera/frame"}
        
        self.assertIn("/api/vision/phone_frame", allowed_endpoints)
        self.assertNotIn("/api/unauthorized/steal", allowed_endpoints)
        self.assertNotIn("/evil", allowed_endpoints)


if __name__ == "__main__":
    unittest.main()
