"""LAN access policy shared by HTTP, MCP and WebSocket upgrade routes.

Local scripts and same-origin loopback pages remain usable without pairing.
Remote clients need a bearer token or a same-site session established with it.
This policy does not encrypt HTTP; use TLS or a trusted isolated LAN.
"""
import hmac
import ipaddress
import os
import re
import secrets
import socket
import subprocess
import sys
import threading
import time
from urllib.parse import urlsplit
from aiohttp import web


REVOKED_TOKENS = frozenset({
    "dPBYG-Ew4zA8U3rMAAS5tX6sA0_fWrbsWTrr1IjBMZk",
})

_VIRTUAL_IFACE_PATTERN = re.compile(
    r"(?:vpn|radmin|wireguard|openvpn|tailscale|zerotier|hamachi|"
    r"vethernet|hyper-v|vmware|virtualbox|vbox|wsl|docker|virbr|vmnet|"
    r"loopback|teredo|isatap|clash|mihomo|sing-box|nekobox|utun|\btun\d|\btap\d)",
    re.IGNORECASE,
)

_SUBNET_CACHE_LOCK = threading.Lock()
_SUBNET_CACHE = {"ts": 0.0, "subnets": ()}


def resolve_trust_private(trust_private=None) -> bool:
    """Single source of truth for whether trusted hotspot zero-config mode is enabled."""
    if trust_private is not None:
        return bool(trust_private)
    return os.environ.get("KURISU_TRUST_PRIVATE", "1") == "1"


def invalidate_subnet_cache():
    with _SUBNET_CACHE_LOCK:
        _SUBNET_CACHE["ts"] = 0.0
        _SUBNET_CACHE["subnets"] = ()


def _is_usable_lan_network(net: ipaddress.IPv4Network) -> bool:
    if net.prefixlen < 16 or net.prefixlen > 30:
        return False
    ip = net.network_address
    return ip.is_private and not ip.is_loopback and not ip.is_link_local and not ip.is_multicast


def _parse_windows_ipconfig(text: str):
    subnets = []
    current_adapter = ""
    is_virtual = False
    media_disconnected = False
    cur_ip = None
    cur_mask = None

    def flush():
        nonlocal cur_ip, cur_mask
        if cur_ip and cur_mask and not is_virtual and not media_disconnected:
            try:
                addr = ipaddress.IPv4Address(cur_ip)
                if addr.is_private and not addr.is_loopback and not addr.is_link_local:
                    net = ipaddress.IPv4Network(f"{cur_ip}/{cur_mask}", strict=False)
                    if _is_usable_lan_network(net) and net not in subnets:
                        subnets.append(net)
            except ValueError:
                pass
        cur_ip = None
        cur_mask = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line:
            continue
        if not line[0].isspace() and line.endswith(":"):
            flush()
            current_adapter = line[:-1].strip()
            is_virtual = bool(_VIRTUAL_IFACE_PATTERN.search(current_adapter))
            media_disconnected = False
            continue
        if re.search(r"Media disconnected|媒体已断开连接", line, re.IGNORECASE):
            media_disconnected = True
            continue
        m_ip = re.search(r"(?:IPv4\s*Address|IPv4\s*地址)[^:]*:\s*([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)", line, re.IGNORECASE)
        if m_ip:
            cur_ip = m_ip.group(1)
            continue
        m_mask = re.search(r"(?:Subnet\s*Mask|子网掩码)[^:]*:\s*([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)", line, re.IGNORECASE)
        if m_mask:
            cur_mask = m_mask.group(1)
            continue
    flush()
    return subnets


def _parse_posix_ip_addr(text: str):
    subnets = []
    for raw_line in text.splitlines():
        m = re.match(r"^\d+:\s+([^\s:]+)\s+inet\s+([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+/\d+)", raw_line.strip())
        if not m:
            continue
        iface, cidr = m.group(1), m.group(2)
        if _VIRTUAL_IFACE_PATTERN.search(iface) or iface == "lo":
            continue
        try:
            iface_ip = ipaddress.IPv4Interface(cidr)
            addr = iface_ip.ip
            if addr.is_private and not addr.is_loopback and not addr.is_link_local:
                net = iface_ip.network
                if _is_usable_lan_network(net) and net not in subnets:
                    subnets.append(net)
        except ValueError:
            continue
    return subnets


def detect_active_local_subnets(max_age: float = 2.0):
    """Detect active non-VPN/non-virtual local IPv4 interface subnets dynamically."""
    now = time.monotonic()
    with _SUBNET_CACHE_LOCK:
        if max_age > 0 and (now - _SUBNET_CACHE["ts"]) < max_age and _SUBNET_CACHE["subnets"]:
            return list(_SUBNET_CACHE["subnets"])

    subnets = []
    try:
        if sys.platform == "win32":
            out = subprocess.check_output(
                ["ipconfig"],
                stderr=subprocess.DEVNULL,
                timeout=2.0,
            ).decode("mbcs", errors="replace")
            subnets.extend(_parse_windows_ipconfig(out))
        else:
            out = subprocess.check_output(
                ["ip", "-4", "-o", "addr", "show", "up"],
                stderr=subprocess.DEVNULL,
                timeout=2.0,
            ).decode("utf-8", errors="replace")
            subnets.extend(_parse_posix_ip_addr(out))
    except Exception:
        pass

    if not subnets:
        # Lightweight stdlib route fallback if OS command is unavailable in a minimal container.
        for probe_target in ("192.168.4.1", "8.8.8.8"):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                try:
                    sock.connect((probe_target, 80))
                    local_ip = sock.getsockname()[0]
                finally:
                    sock.close()
                addr = ipaddress.IPv4Address(local_ip)
                if addr.is_private and not addr.is_loopback and not addr.is_link_local:
                    net = ipaddress.IPv4Network(f"{local_ip}/24", strict=False)
                    if net not in subnets:
                        subnets.append(net)
            except Exception:
                continue

    with _SUBNET_CACHE_LOCK:
        _SUBNET_CACHE["ts"] = now
        _SUBNET_CACHE["subnets"] = tuple(subnets)
    return subnets


# Explicit safe unauthenticated LAN endpoints (Default-Deny policy).
# Only safe telemetry, basic lighting controls, chat, local library browsing & playback control,
# and user-initiated vision mode start/stop are permitted from verified active hotspot subnets
# when trust_private is enabled.
# ALL sensitive endpoints (camera live feeds/frames without scoped vision capability, face enroll,
# memory, documents, library root/scan writes, music-upload, device tools, MCP, settings, restart,
# dynamic/unlisted actions) strictly require valid admin token/cookie or localhost loopback.
SAFE_UNAUTHENTICATED_LAN_ENDPOINTS = frozenset({
    "/api/health",
    "/api/auth/challenge",
    "/api/pair",
    "/api/status",
    "/api/pro/status",
    "/api/state",
    "/api/preview",
    "/api/display/frame",
    "/api/game/mario/frame",
    "/api/arcade/frame",
    "/api/command",
    "/api/mode",
    "/api/brightness",
    "/api/volume",
    "/api/cmd",
    "/api/game",
    "/api/arcade",
    "/api/ceremony",
    "/api/chat",
    "/api/pro/chat",
    "/api/pro/music",
    "/api/pro/vision",
    "/api/pro/canvas",
    "/api/pro/difficulty",
    "/api/retry_warmup",
    "/ws",
})

# Method-specific ordinary paths allowed on trusted hotspot (GET only, POST mutates config/disk)
SAFE_UNAUTHENTICATED_LAN_GET_ENDPOINTS = frozenset({
    "/api/pro/library",
})

# Paths that may use a short-lived, single-session, peer-bound vision capability credential
SCOPED_VISION_FRAME_PATHS = frozenset({
    "/api/pro/camera/frame",
    "/api/pro/vision/frame",
})

SCOPED_VISION_FEED_PATHS = frozenset({
    "/api/pro/camera/feed",
    "/api/pro/camera/frame",
})

SCOPED_VISION_CALIBRATE_PATHS = frozenset({
    "/api/pro/calibrate",
})

# Sensitive endpoints strictly requiring admin token/cookie pairing, localhost loopback,
# or (for camera frames/calibration) an active scoped vision capability credential.
SENSITIVE_ENDPOINTS = (
    "/api/pro/documents",
    "/api/pro/memories",
    "/api/pro/memory",
    "/api/pro/face",
    "/api/pro/enroll",
    "/api/pro/camera",
    "/api/pro/device-tool",
    "/api/pro/library",
    "/api/pro/calibrate",
    "/api/pro/music-upload",
    "/api/pro/observations",
    "/api/config",
    "/api/restart",
    "/api/pro/settings",
    "/mcp",
)


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
        self.trust_private = resolve_trust_private(trust_private)
        self._vision_caps = {}
        self._vision_lock = threading.Lock()

    @classmethod
    def get_trusted_subnets(cls):
        subnets = []
        custom = os.environ.get("KURISU_HOTSPOT_SUBNET", "").strip()
        if custom:
            for item in custom.split(","):
                item = item.strip()
                if not item:
                    continue
                try:
                    subnets.append(ipaddress.ip_network(item, strict=False))
                except ValueError:
                    pass
        for detected in detect_active_local_subnets():
            if detected not in subnets:
                subnets.append(detected)
        return subnets

    @classmethod
    def is_trusted_peer(cls, remote):
        try:
            addr = ipaddress.ip_address(remote)
            if addr.is_loopback:
                # Loopback is governed exclusively by AccessPolicy.local(request), never LAN trust.
                return False
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
        if origin == "null":
            return False
        if request.headers.get('Sec-Fetch-Site') == 'cross-site':
            return False
        return not origin or origin == f"{request.scheme}://{request.host}" or origin in self.origins

    def issue_vision_capability(self, session_id: str, peer_ip: str, source: str = "remote", ttl_seconds: float = 600.0) -> str:
        """Issue an unguessable, short-lived capability token bound to one vision session and peer IP."""
        if not session_id or not peer_ip:
            raise ValueError("session_id and peer_ip required for vision capability")
        cap_token = secrets.token_urlsafe(32)
        now = time.monotonic()
        with self._vision_lock:
            # Prune expired entries boundedly
            self._vision_caps = {
                k: v for k, v in self._vision_caps.items()
                if not v["revoked"] and v["expires_at"] > now
            }
            # Revoke previous caps for different sessions from this hub so old tokens die cleanly
            for meta in self._vision_caps.values():
                if meta["session_id"] != session_id:
                    meta["revoked"] = True
            self._vision_caps[cap_token] = {
                "session_id": session_id,
                "peer_ip": peer_ip,
                "source": source,
                "expires_at": now + float(ttl_seconds),
                "revoked": False,
            }
        return cap_token

    def revoke_vision_capability(self, session_id: str = None):
        with self._vision_lock:
            for meta in self._vision_caps.values():
                if session_id is None or meta["session_id"] == session_id:
                    meta["revoked"] = True

    def _has_valid_vision_capability(self, request, required_session_id=None) -> bool:
        headers = getattr(request, "headers", {}) or {}
        query = getattr(request, "query", {}) or {}
        cookies = getattr(request, "cookies", {}) or {}
        supplied = headers.get("Authorization", "")
        bearer = supplied[7:] if supplied.startswith("Bearer ") else ""
        cap_candidate = (
            headers.get("X-Vision-Token", "")
            or bearer
            or cookies.get("kurisu_vision_session", "")
        )
        if not cap_candidate or cap_candidate in REVOKED_TOKENS:
            return False
        req_session = required_session_id or headers.get("X-Vision-Session") or query.get("session_id") or ""
        peer_ip = getattr(request, "remote", "") or ""
        now = time.monotonic()
        with self._vision_lock:
            meta = self._vision_caps.get(cap_candidate)
            if not meta or meta["revoked"] or meta["expires_at"] <= now:
                return False
            if meta["peer_ip"] != peer_ip:
                return False
            if meta["source"] == "remote":
                if not req_session or meta["session_id"] != req_session:
                    return False
            meta["expires_at"] = max(meta["expires_at"], now + 300.0)
            return True

    def has_admin_auth(self, request) -> bool:
        """True only for full master pairing credential or verified localhost loopback."""
        supplied = request.headers.get("Authorization", "")
        bearer = supplied[7:] if supplied.startswith("Bearer ") else ""
        query_token = request.query.get("token", "")
        header_token = request.headers.get("X-Access-Token", "")
        token_candidate = bearer or query_token or header_token
        cookie = request.cookies.get("kurisu_session", "")
        if token_candidate in REVOKED_TOKENS or cookie in REVOKED_TOKENS:
            return False
        return bool(
            (token_candidate and hmac.compare_digest(token_candidate.encode('utf-8'), self.token.encode('utf-8'))) or
            (cookie and hmac.compare_digest(cookie.encode('utf-8'), self.token.encode('utf-8'))) or
            self.local(request)
        )

    def authorized(self, request):
        supplied = request.headers.get("Authorization", "")
        bearer = supplied[7:] if supplied.startswith("Bearer ") else ""
        # 1. Explicit master token / session cookie authentication or localhost loopback has full authorization
        if self.has_admin_auth(request):
            return True

        if request.path == '/xiaozhi/v1/' and len(self.xiaozhi_token) >= 32 and hmac.compare_digest(
                bearer.encode('utf-8'), self.xiaozhi_token.encode('utf-8')):
            return True # Scoped compatibility with the existing optional native adapter.

        path = getattr(request, "path", "")
        norm_path = path.rstrip("/") if path != "/" else "/"
        method = str(getattr(request, "method", "GET") or "GET").upper()

        # 2. Scoped single-session vision capability (active on trusted hotspot or paired peer)
        if self.trust_private and self.is_trusted_peer(request.remote or ""):
            if norm_path in SCOPED_VISION_FRAME_PATHS and method == "POST":
                if self._has_valid_vision_capability(request):
                    return True
            if norm_path == "/api/pro/camera/feed" and method == "GET":
                if self._has_valid_vision_capability(request):
                    return True
            if norm_path in SCOPED_VISION_CALIBRATE_PATHS and method == "POST":
                if self._has_valid_vision_capability(request):
                    return True

            # 3. Strict Default-Deny LAN security policy for ordinary controls:
            if norm_path in SAFE_UNAUTHENTICATED_LAN_ENDPOINTS:
                return True
            if norm_path in SAFE_UNAUTHENTICATED_LAN_GET_ENDPOINTS and method == "GET":
                return True
            return False

        return False

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
