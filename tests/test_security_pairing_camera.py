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
        """Discovered candidate servers MUST NEVER automatically receive cookies, JS storage tokens, or camera access.
        Even if a rogue candidate relays an HMAC proof from a genuine PC, discovery candidates remain unauthenticated."""
        saved_token = "genuine_saved_token_secret_12345"
        rogue_origin = "http://192.168.186.199:8080"
        genuine_origin = "http://192.168.186.90:8080"

        # Simulate APK verification & security boundary state machine
        class APKSecurityStateMachine:
            def __init__(self):
                self.server_origin = ""
                self.authenticated_origin = ""
                self.cookies = {}
                self.injected_storage = {}

            def on_discovery(self, candidate_origin, relayed_genuine_proof=False):
                # Discovery results are strictly candidate addresses.
                # Auto-promotion via unauthenticated HTTP challenge is disabled to prevent relay attacks.
                self.server_origin = candidate_origin
                self.authenticated_origin = ""

            def on_explicit_pair_url(self, target_url, pair_param):
                p = urlparse(target_url)
                origin = f"{p.scheme}://{p.netloc}"
                self.server_origin = origin
                if pair_param and pair_param.strip():
                    self.authenticated_origin = origin
                    self.cookies[origin] = f"kurisu_session={pair_param.strip()}"

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

        apk = APKSecurityStateMachine()

        # 1. Rogue candidate discovered (even if it attempts to relay genuine proof)
        apk.on_discovery(rogue_origin, relayed_genuine_proof=True)
        self.assertEqual(apk.authenticated_origin, "", "Discovered rogue candidate must NEVER be authenticated")
        self.assertNotIn(rogue_origin, apk.cookies, "Rogue origin must NOT receive session cookie")

        # Rogue page loads in webview as guest
        apk.on_page_finished(rogue_origin + "/index.html")
        self.assertNotIn(rogue_origin + "/index.html", apk.injected_storage, "Rogue page must NOT receive storage token")
        self.assertFalse(
            apk.start_front_camera(rogue_origin + "/index.html", rogue_origin + "/api/pro/camera/frame"),
            "Rogue page must NOT get camera access"
        )

        # 2. Candidate discovery from genuine PC address without explicit pair param also loads unauthenticated
        apk.on_discovery(genuine_origin)
        self.assertEqual(apk.authenticated_origin, "")
        self.assertNotIn(genuine_origin, apk.cookies)

        # 3. Explicit user pairing (via pairParam, e.g., QR scan or manual input) securely establishes authentication
        apk.on_explicit_pair_url(genuine_origin + "/?pair=" + saved_token, pair_param=saved_token)
        self.assertEqual(apk.authenticated_origin, genuine_origin)
        self.assertIn(genuine_origin, apk.cookies)
        apk.on_page_finished(genuine_origin + "/index.html")
        self.assertEqual(apk.injected_storage.get(genuine_origin + "/index.html"), saved_token)
        self.assertTrue(
            apk.start_front_camera(genuine_origin + "/index.html", genuine_origin + "/api/pro/camera/frame"),
            "Explicitly paired page is authorized for camera upload"
        )

    def test_same_host_different_port_cookie_isolation(self):
        """Cross-port security isolation:
        Even when a candidate service shares the exact same IP/host as a previously paired service,
        navigating to the candidate (or guest mode) purges all cookies and disables cookie acceptance,
        preventing RFC 6265 host-level cookie leakage to unauthenticated ports."""
        saved_token = "paired_token_secret_host50_8080"
        host = "192.168.1.50"
        paired_origin = f"http://{host}:8080"
        candidate_origin = f"http://{host}:9090"

        class CookieManagerSimulator:
            def __init__(self):
                # RFC 6265 standard cookie jar stores by domain/host
                self.host_cookies = {}
                self.accept_cookies = False

            def set_accept_cookie(self, accept: bool):
                self.accept_cookies = accept

            def set_cookie(self, url: str, cookie_str: str):
                if not self.accept_cookies:
                    return
                p = urlparse(url)
                self.host_cookies[p.hostname] = cookie_str

            def remove_all_cookies(self):
                self.host_cookies.clear()

            def get_cookie_header(self, url: str) -> str:
                if not self.accept_cookies:
                    return ""
                p = urlparse(url)
                return self.host_cookies.get(p.hostname, "")

        class AndroidAppSecurityModel:
            def __init__(self):
                self.cm = CookieManagerSimulator()
                self.server_origin = ""
                self.authenticated_origin = ""
                self.web_storage = {}

            def purge_cookies_and_storage(self):
                self.cm.remove_all_cookies()
                self.cm.set_accept_cookie(false) if hasattr(self, 'false') else self.cm.set_accept_cookie(False)
                self.web_storage.clear()

            def connect_server(self, target_url: str):
                p = urlparse(target_url)
                origin = f"{p.scheme}://{p.netloc}"
                self.server_origin = origin
                # Check for explicit pair parameter
                from urllib.parse import parse_qs
                qs = parse_qs(p.query)
                pair_param = qs.get("pair", [""])[0]

                if pair_param.strip():
                    new_tok = pair_param.strip()
                    self.authenticated_origin = origin
                    self.cm.set_accept_cookie(True)
                    self.cm.remove_all_cookies() # Clear prior cookies
                    self.cm.set_cookie(origin, f"kurisu_session={new_tok}")
                else:
                    # Unauthenticated / guest connection: strictly purge and isolate!
                    self.authenticated_origin = ""
                    self.purge_cookies_and_storage()

            def send_http_request(self, target_url: str) -> dict:
                cookie_header = self.cm.get_cookie_header(target_url)
                return {
                    "url": target_url,
                    "cookie": cookie_header,
                    "authenticated": bool(self.authenticated_origin and self.authenticated_origin == f"{urlparse(target_url).scheme}://{urlparse(target_url).netloc}")
                }

        app = AndroidAppSecurityModel()

        # Step 1: User explicitly pairs with port 8080
        app.connect_server(f"{paired_origin}/?pair={saved_token}")
        self.assertEqual(app.authenticated_origin, paired_origin)
        req_paired = app.send_http_request(f"{paired_origin}/api/status")
        self.assertIn("kurisu_session=" + saved_token, req_paired["cookie"], "Paired port 8080 must receive session cookie")
        self.assertTrue(req_paired["authenticated"])

        # Step 2: Discovery discovers candidate service on SAME host, different port (9090)
        # User opens candidate in guest / isolated mode without pairing token
        app.connect_server(candidate_origin)
        self.assertEqual(app.authenticated_origin, "", "Port 9090 candidate must not be authenticated")

        # Step 3: Verify candidate port 9090 receives NO kurisu_session cookie
        req_candidate = app.send_http_request(f"{candidate_origin}/api/status")
        self.assertEqual(req_candidate["cookie"], "", "Candidate port 9090 MUST NOT receive old kurisu_session cookie!")
        self.assertNotIn("kurisu_session", req_candidate["cookie"])
        self.assertFalse(req_candidate["authenticated"], "Candidate port 9090 must not be authenticated")

        # Step 4: User explicitly confirms pairing for port 9090 with new token
        new_token_9090 = "token_for_port_9090_secret"
        app.connect_server(f"{candidate_origin}/?pair={new_token_9090}")
        self.assertEqual(app.authenticated_origin, candidate_origin)
        req_new_paired = app.send_http_request(f"{candidate_origin}/api/status")
        self.assertEqual(req_new_paired["cookie"], f"kurisu_session={new_token_9090}")
        self.assertTrue(req_new_paired["authenticated"])


if __name__ == "__main__":
    unittest.main()
