"""LAN access policy shared by HTTP, MCP and WebSocket upgrade routes.

Local scripts and same-origin loopback pages remain usable without pairing.
Remote clients need a bearer token or a same-site session established with it.
This policy does not encrypt HTTP; use TLS or a trusted isolated LAN.
"""
import hmac
import ipaddress
import os
import secrets
import time
from urllib.parse import urlsplit
from aiohttp import web


REVOKED_TOKENS = frozenset({
    "dPBYG-Ew4zA8U3rMAAS5tX6sA0_fWrbsWTrr1IjBMZk",
})


def load_access_token():
    token = os.environ.get("KURISU_ACCESS_TOKEN", "").strip()
    if token:
        if len(token) < 32:
            raise ValueError("KURISU_ACCESS_TOKEN must contain at least 32 characters")
        return token
    from pro_paths import data_dir
    path = data_dir() / "web-access-token"
    try:
        with path.open("x", encoding="ascii") as stream:
            token = secrets.token_urlsafe(32)
            stream.write(token + "\n")
        path.chmod(0o600)
    except FileExistsError:
        token = path.read_text(encoding="ascii").strip()
    if len(token) < 32:
        raise ValueError("Invalid web-access-token file")
    return token


class AccessPolicy:
    def __init__(self, token=None, origins=(), trust_private=None):
        if token and len(token) < 32:
            raise ValueError("KURISU_ACCESS_TOKEN must contain at least 32 characters")
        self.token = token or load_access_token()
        self.xiaozhi_token = os.environ.get('KURISU_XIAOZHI_TOKEN','')
        self.origins = frozenset(origins)
        self.buckets = {}
        if trust_private is None:
            self.trust_private = os.environ.get("KURISU_TRUST_PRIVATE") == "1"
        else:
            self.trust_private = bool(trust_private)

    @classmethod
    def get_trusted_subnets(cls):
        subnets = [
            ipaddress.ip_network("127.0.0.0/8"),
            ipaddress.ip_network("192.168.186.0/24"),
        ]
        custom = os.environ.get("KURISU_HOTSPOT_SUBNET")
        if custom:
            try:
                subnets.append(ipaddress.ip_network(custom, strict=False))
            except ValueError:
                pass
        return subnets

    @classmethod
    def is_trusted_peer(cls, remote):
        try:
            addr = ipaddress.ip_address(remote)
            if addr.is_loopback:
                return True
            for net in cls.get_trusted_subnets():
                if addr in net:
                    return True
            return False
        except (ValueError, TypeError):
            return False

    @staticmethod
    def local(request):
        try:
            return (ipaddress.ip_address(request.remote).is_loopback and
                    urlsplit("//" + request.host).hostname in {"localhost", "127.0.0.1", "::1"})
        except (ValueError, TypeError):
            return False

    def permitted_origin(self, request):
        origin = request.headers.get("Origin")
        if not origin and request.headers.get('Sec-Fetch-Site') == 'cross-site':
            return False
        return not origin or origin == f"{request.scheme}://{request.host}" or origin in self.origins

    def authorized(self, request):
        supplied = request.headers.get("Authorization", "")
        bearer = supplied[7:] if supplied.startswith("Bearer ") else ""
        query_token = request.query.get("token", "")
        header_token = request.headers.get("X-Access-Token", "")
        token_candidate = bearer or query_token or header_token
        cookie = request.cookies.get("kurisu_session", "")
        if token_candidate in REVOKED_TOKENS or cookie in REVOKED_TOKENS:
            return False
        if self.trust_private and self.is_trusted_peer(request.remote or ""):
            return True
        if request.path == '/xiaozhi/v1/' and len(self.xiaozhi_token) >= 32 and hmac.compare_digest(
                bearer.encode('utf-8'),self.xiaozhi_token.encode('utf-8')):
            return True # Scoped compatibility with the existing optional native adapter.
        return (hmac.compare_digest(token_candidate.encode('utf-8'), self.token.encode('utf-8')) or
                hmac.compare_digest(cookie.encode('utf-8'), self.token.encode('utf-8')) or self.local(request))

    def allow_rate(self, peer):
        now = time.monotonic()
        if peer not in self.buckets and len(self.buckets) >= 256:
            self.buckets = {key:value for key,value in self.buckets.items() if now-value[1] < 60}
            if len(self.buckets) >= 256:
                return False
        credit, previous = self.buckets.get(peer, (240., now))
        credit = min(240., credit + (now-previous)*120.)
        self.buckets[peer] = (max(0., credit-1), now)
        return credit >= 1


@web.middleware
async def access_middleware(request, handler):
    policy = request.app["access_policy"]
    controlled = request.path.startswith(("/api/", "/mcp", "/ws", "/xiaozhi"))
    if controlled:
        if not policy.permitted_origin(request):
            return web.json_response({"status":"error", "error":"origin_forbidden"}, status=403)
        if not policy.allow_rate(request.remote or "unknown"):
            return web.json_response({"status":"error", "error":"rate_limited"}, status=429)
        if request.method == "OPTIONS":
            response = web.Response(status=204)
            origin = request.headers.get("Origin")
            if origin:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Vary"] = "Origin"
                response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, MCP-Protocol-Version, Mcp-Session-Id"
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
            return response
        if not policy.authorized(request) and request.path not in ("/api/auth/challenge", "/api/health"):
            return web.json_response({"status":"error", "error":"pairing_required"}, status=401)
        limit = (20*1024*1024 if request.path in ("/api/pro/music-upload", "/api/pro/camera/frame", "/api/pro/vision/frame") else
                 1024*1024 if request.path == "/api/pro/documents" else 64*1024)
        if request.content_length and request.content_length > limit:
            raise web.HTTPRequestEntityTooLarge(max_size=limit, actual_size=request.content_length)
        if request.can_read_body:
            # Enforce the limit for chunked bodies as well as Content-Length.
            raw = bytearray()
            while not request.content.at_eof() and len(raw) <= limit:
                chunk = await request.content.read(min(65536,limit+1-len(raw)))
                if not chunk:
                    break
                raw.extend(chunk)
            if len(raw) > limit:
                raise web.HTTPRequestEntityTooLarge(max_size=limit, actual_size=len(raw))
            request._read_bytes = bytes(raw)
    response = await handler(request)
    if controlled:
        response.headers["Cache-Control"] = "no-store"
        origin = request.headers.get('Origin')
        if origin and not response.prepared:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Vary'] = 'Origin'
            response.headers['Access-Control-Expose-Headers'] = 'Mcp-Session-Id, MCP-Protocol-Version'
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    return response


async def pair(request):
    # A remote client must supply the token, even if it already has a cookie.
    policy = request.app["access_policy"]
    supplied = request.headers.get("Authorization", "")
    if not hmac.compare_digest(supplied.encode('utf-8'), ("Bearer " + policy.token).encode('utf-8')):
        return web.json_response({"status":"error", "error":"pairing_required"}, status=401)
    response = web.json_response({"status":"ok"})
    response.set_cookie("kurisu_session", policy.token, httponly=True, samesite="Strict", secure=request.secure)
    return response


async def auth_challenge(request):
    """Zero-knowledge server identity verification: proves this server holds the shared token."""
    try:
        data = await request.json() if request.can_read_body else {}
    except Exception:
        data = {}
    client_nonce = str(data.get("nonce", "")).strip()
    if not client_nonce or len(client_nonce) < 8 or len(client_nonce) > 128:
        return web.json_response({"status": "error", "error": "invalid_nonce"}, status=400)
    policy = request.app["access_policy"]
    server_nonce = secrets.token_hex(16)
    message = f"{client_nonce}:{server_nonce}".encode("utf-8")
    server_proof = hmac.new(policy.token.encode("utf-8"), message, "sha256").hexdigest()
    return web.json_response({
        "status": "ok",
        "service": "KurisuPro",
        "server_nonce": server_nonce,
        "server_proof": server_proof,
    })
