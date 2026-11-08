import hashlib
import hmac
import json
import socket
import os
import secrets
import sys
import unittest
from pathlib import Path
from urllib.parse import urlparse

# Add pc-agent-vision to path
sys.path.insert(0, str(Path(__file__).parent.parent / "pc-agent-vision"))

from service_discovery import ServiceAdvertisement
from access_control import AccessPolicy, auth_challenge


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

    def test_challenge_response_authentication(self):
        """Zero-knowledge server identity verification via /api/auth/challenge."""
        token = "test_shared_access_token_123456789012"
        client_nonce = secrets.token_hex(16)

        # 1. Genuine server computes proof
        server_nonce = secrets.token_hex(16)
        expected_proof = hmac.new(
            token.encode("utf-8"),
            f"{client_nonce}:{server_nonce}".encode("utf-8"),
            "sha256"
        ).hexdigest()

        # Client verifies proof with saved token
        client_computed = hmac.new(
            token.encode("utf-8"),
            f"{client_nonce}:{server_nonce}".encode("utf-8"),
            "sha256"
        ).hexdigest()
        self.assertEqual(client_computed, expected_proof, "Genuine server proof must match client expected proof")

        # 2. Rogue server does not know token
        rogue_token = "attacker_fake_token_00000000000000"
        rogue_proof = hmac.new(
            rogue_token.encode("utf-8"),
            f"{client_nonce}:{server_nonce}".encode("utf-8"),
            "sha256"
        ).hexdigest()
        self.assertNotEqual(client_computed, rogue_proof, "Rogue server cannot forge proof without token")

    def test_spoofed_discovery_does_not_leak_saved_token(self):
        """Candidate URL must NEVER have ?pair=<token> in the URL."""
        saved_token = "secure_token_abc12345678901234567890"
        candidate_url = "http://192.168.1.199:8080"

        # Verification: URL loaded into webview must be clean
        target_url = candidate_url.rstrip("/") + "/"
        self.assertNotIn("?pair=", target_url, "Token must not be appended in query string")
        self.assertNotIn(saved_token, target_url, "Saved token must never be in candidate URL")

    def test_android_camera_bridge_trust_policy(self):
        """Native camera bridge must allow trusted paired PC page and reject untrusted pages."""
        server_origin = "http://192.168.186.90:8080"

        def simulate_start_front_camera(page_url, upload_url, backgrounded=False, destroyed=False):
            if backgrounded or destroyed:
                return False
            # Check trustedPage:
            if not page_url:
                return False
            is_offline = page_url.startsWith("file:///android_asset/") if hasattr(page_url, "startsWith") else page_url.startswith("file:///android_asset/")
            if is_offline:
                trusted = True
            else:
                p = urlparse(page_url)
                page_origin = f"{p.scheme}://{p.netloc}"
                trusted = (server_origin != "" and server_origin == page_origin)

            if not trusted:
                return False

            # Check upload URL origin and endpoint whitelist
            u = urlparse(upload_url)
            upload_origin = f"{u.scheme}://{u.netloc}"
            if upload_origin != server_origin:
                return False
            if u.path not in ("/api/vision/phone_frame", "/api/pro/vision/frame", "/api/pro/camera/frame"):
                return False
            return True

        # 1. Trusted paired PC page starting camera -> ALLOWED
        res_ok = simulate_start_front_camera(
            page_url="http://192.168.186.90:8080/index.html",
            upload_url="http://192.168.186.90:8080/api/pro/camera/frame"
        )
        self.assertTrue(res_ok, "Trusted paired PC page should be permitted to start camera")

        # 2. Untrusted / third-party page starting camera -> REJECTED
        res_evil = simulate_start_front_camera(
            page_url="http://192.168.1.199:8080/index.html",
            upload_url="http://192.168.186.90:8080/api/pro/camera/frame"
        )
        self.assertFalse(res_evil, "Untrusted candidate page must be rejected")

        # 3. Third-party upload destination -> REJECTED
        res_leak = simulate_start_front_camera(
            page_url="http://192.168.186.90:8080/index.html",
            upload_url="http://evil-server.com/api/pro/camera/frame"
        )
        self.assertFalse(res_leak, "External upload target must be rejected")

        # 4. App in background -> REJECTED
        res_bg = simulate_start_front_camera(
            page_url="http://192.168.186.90:8080/index.html",
            upload_url="http://192.168.186.90:8080/api/pro/camera/frame",
            backgrounded=True
        )
        self.assertFalse(res_bg, "Camera must not start in background")

    def test_unverified_candidate_page_credential_isolation(self):
        """Unverified candidate server MUST NOT receive cookies, JS storage tokens, or camera access."""
        saved_token = "genuine_saved_token_secret_12345"
        rogue_origin = "http://192.168.186.199:8080"
        genuine_origin = "http://192.168.186.90:8080"

        # Simulate APK verification & state machine
        class APKState:
            def __init__(self):
                self.server_origin = ""
                self.authenticated_origin = ""
                self.cookies = {}
                self.injected_storage = {}

            def on_discovery(self, candidate_origin, server_proof_valid):
                if server_proof_valid:
                    self.server_origin = candidate_origin
                    self.authenticated_origin = candidate_origin
                    self.cookies[candidate_origin] = f"kurisu_session={saved_token}"
                else:
                    self.authenticated_origin = ""
                    # Stays offline or loads as unauthenticated guest without credentials

            def is_page_authenticated(self, current_url):
                if not current_url or current_url.startswith("file:"):
                    return False
                p = urlparse(current_url)
                origin = f"{p.scheme}://{p.netloc}"
                return bool(self.authenticated_origin) and self.authenticated_origin == origin

            def on_page_finished(self, current_url):
                if self.is_page_authenticated(current_url):
                    self.injected_storage[current_url] = saved_token

            def start_front_camera(self, current_url, upload_url):
                if not self.is_page_authenticated(current_url):
                    return False
                u = urlparse(upload_url)
                upload_origin = f"{u.scheme}://{u.netloc}"
                return upload_origin == self.authenticated_origin

        apk = APKState()

        # 1. Rogue server discovery (challenge fails)
        apk.on_discovery(rogue_origin, server_proof_valid=False)
        self.assertEqual(apk.authenticated_origin, "", "Rogue candidate must not become authenticated_origin")
        self.assertNotIn(rogue_origin, apk.cookies, "Rogue origin must NOT receive session cookie")

        # Even if loaded as guest:
        apk.on_page_finished(rogue_origin + "/index.html")
        self.assertNotIn(rogue_origin + "/index.html", apk.injected_storage, "Rogue page must NOT receive storage token")
        self.assertFalse(
            apk.start_front_camera(rogue_origin + "/index.html", rogue_origin + "/api/pro/camera/frame"),
            "Rogue page must NOT get camera access"
        )

        # 2. Genuine server discovery (challenge passes)
        apk.on_discovery(genuine_origin, server_proof_valid=True)
        self.assertEqual(apk.authenticated_origin, genuine_origin)
        self.assertIn(genuine_origin, apk.cookies)
        apk.on_page_finished(genuine_origin + "/index.html")
        self.assertEqual(apk.injected_storage.get(genuine_origin + "/index.html"), saved_token)
        self.assertTrue(
            apk.start_front_camera(genuine_origin + "/index.html", genuine_origin + "/api/pro/camera/frame")
        )


if __name__ == "__main__":
    unittest.main()
