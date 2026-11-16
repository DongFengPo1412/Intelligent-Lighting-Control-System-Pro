package org.fglab.kurisu;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.InetSocketAddress;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.Locale;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * JVM unit & loopback contract tests for Round 1 Android bridge, origin/health verification,
 * and camera epoch isolation (no Android device or UI runtime required).
 */
public final class AndroidRound1ContractsTest {

    private static void check(boolean cond, String msg) {
        if (!cond) {
            throw new AssertionError("FAILED: " + msg);
        }
    }

    // Mirrors MainActivity.normalizeOrigin
    private static String normalizeOrigin(String rawUrl) {
        if (rawUrl == null || rawUrl.trim().isEmpty()) {
            return "";
        }
        try {
            URI uri = URI.create(rawUrl.trim());
            String scheme = uri.getScheme();
            String host = uri.getHost();
            if (scheme == null || host == null) {
                return "";
            }
            scheme = scheme.toLowerCase(Locale.ROOT);
            host = host.toLowerCase(Locale.ROOT);
            int port = uri.getPort();
            if (port < 0) {
                port = "https".equals(scheme) ? 443 : 80;
            }
            if (("http".equals(scheme) && port == 80) || ("https".equals(scheme) && port == 443)) {
                return scheme + "://" + host;
            }
            return scheme + "://" + host + ":" + port;
        } catch (Exception e) {
            return "";
        }
    }

    // Mirrors MainActivity.verifyServerHealth
    private static boolean verifyServerHealth(String origin, int timeoutMs) {
        String normalized = normalizeOrigin(origin);
        if (normalized.isEmpty()) {
            return false;
        }
        HttpURLConnection conn = null;
        try {
            URI healthUri = URI.create(normalized + "/api/health");
            conn = (HttpURLConnection) healthUri.toURL().openConnection();
            conn.setRequestMethod("GET");
            conn.setConnectTimeout(timeoutMs);
            conn.setReadTimeout(timeoutMs);
            conn.setUseCaches(false);
            if (conn.getResponseCode() != 200) {
                return false;
            }
            StringBuilder body = new StringBuilder();
            try (InputStream is = conn.getInputStream()) {
                byte[] buf = new byte[1024];
                int n;
                while ((n = is.read(buf)) > 0 && body.length() < 4096) {
                    body.append(new String(buf, 0, n, StandardCharsets.UTF_8));
                }
            }
            String text = body.toString();
            Matcher m = Pattern.compile("\"status\"\\s*:\\s*\"([^\"]+)\"").matcher(text);
            if (!m.find()) {
                return false;
            }
            String st = m.group(1);
            return "ok".equalsIgnoreCase(st) || "ready".equalsIgnoreCase(st);
        } catch (Exception e) {
            System.err.println("verifyServerHealth error for " + origin + ": " + e);
            return false;
        } finally {
            if (conn != null) {
                conn.disconnect();
            }
        }
    }

    public static void main(String[] args) throws Exception {
        // 1. BridgePolicy unit validation (including subnet & token rules)
        check(BridgePolicy.privateIpv4("192.168.186.12"), "192.168.186.12 valid private IPv4");
        check(BridgePolicy.privateIpv4("172.20.10.4"), "172.20.10.4 iOS/Android hotspot valid private IPv4");
        check(BridgePolicy.privateIpv4("10.42.0.55"), "10.42.0.55 Linux/Ubuntu hotspot valid private IPv4");
        check(!BridgePolicy.privateIpv4("127.0.0.1"), "loopback must not be treated as remote private IPv4");
        check(!BridgePolicy.privateIpv4("8.8.8.8"), "public IPv4 rejected");
        check(!BridgePolicy.privateIpv4("192.168.1.255"), "broadcast host rejected");

        String validTok = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
        check(BridgePolicy.tokenOrPrivate("172.20.10.4", null), "hotspot private host allowed without token");
        check(BridgePolicy.tokenOrPrivate("172.20.10.4", validTok), "hotspot private host allowed with valid token");
        check(!BridgePolicy.tokenOrPrivate("203.0.113.5", ""), "non-private host requires valid 64-hex token");
        check(BridgePolicy.tokenOrPrivate("203.0.113.5", validTok), "non-private host accepted with valid token");
        check(BridgePolicy.requestId("req_round1-001"), "valid request id accepted");
        check(!BridgePolicy.requestId("bad id;drop"), "malicious request id rejected");

        // 2. Origin canonicalization & duplicate reload suppression contract
        check("http://172.20.10.3:8080".equals(normalizeOrigin("HTTP://172.20.10.3:8080/api/pro/status")),
                "canonical origin strips path and lowercases");
        check("http://172.20.10.3".equals(normalizeOrigin("http://172.20.10.3:80/")),
                "canonical origin omits default port 80");
        check("https://example.local".equals(normalizeOrigin("https://example.local:443/app")),
                "canonical origin omits default port 443");
        check("".equals(normalizeOrigin("javascript:alert(1)")),
                "non-http scheme produces empty normalized origin");

        // 3. Loopback HTTP health probe checks (/api/health -> 200 ok vs 503 vs bogus body)
        final AtomicInteger mode = new AtomicInteger(0);
        HttpServer healthServer = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        healthServer.createContext("/api/health", new HttpHandler() {
            @Override
            public void handle(HttpExchange exchange) throws IOException {
                int m = mode.get();
                byte[] resp;
                int code = 200;
                if (m == 0) {
                    resp = "{\"status\":\"ok\",\"version\":\"pro\"}".getBytes(StandardCharsets.UTF_8);
                } else if (m == 1) {
                    resp = "{\"status\":\"ready\"}".getBytes(StandardCharsets.UTF_8);
                } else if (m == 2) {
                    code = 503;
                    resp = "{\"status\":\"starting\"}".getBytes(StandardCharsets.UTF_8);
                } else {
                    resp = "<html><body>Not Kurisu</body></html>".getBytes(StandardCharsets.UTF_8);
                }
                exchange.getResponseHeaders().set("Content-Type", "application/json");
                exchange.sendResponseHeaders(code, resp.length);
                try (OutputStream os = exchange.getResponseBody()) {
                    os.write(resp);
                }
            }
        });
        healthServer.start();
        try {
            String origin = "http://127.0.0.1:" + healthServer.getAddress().getPort();
            mode.set(0);
            check(verifyServerHealth(origin, 1500), "health status=ok must pass");
            mode.set(1);
            check(verifyServerHealth(origin, 1500), "health status=ready must pass");
            mode.set(2);
            check(!verifyServerHealth(origin, 1500), "health HTTP 503 must be rejected");
            mode.set(3);
            check(!verifyServerHealth(origin, 1500), "non-JSON captive portal HTML must be rejected");
            check(!verifyServerHealth("http://127.0.0.1:1", 250), "unreachable port must return false");
        } finally {
            healthServer.stop(0);
        }

        // 4. Epoch & sessionId isolation model matching FrontCameraBridge
        class EpochStateModel {
            long currentEpoch = 0;
            String currentSessionId = "";
            boolean running = false;
            String lastEvent = "";

            synchronized long start(String sessionId) {
                currentEpoch++;
                currentSessionId = sessionId;
                running = true;
                lastEvent = "camera_opened:" + currentEpoch;
                return currentEpoch;
            }

            synchronized void onUploadResult(long epoch, String status) {
                if (epoch != currentEpoch || !running) {
                    return; // Stale callback dropped!
                }
                lastEvent = status + ":" + epoch;
            }

            synchronized void stop(String sessionId, long expectedEpoch) {
                if (expectedEpoch > 0 && expectedEpoch != currentEpoch) {
                    return; // Stale epoch stop ignored!
                }
                if (sessionId != null && !sessionId.isEmpty() && !currentSessionId.equals(sessionId)) {
                    return; // Mismatched session stop ignored!
                }
                running = false;
                lastEvent = "stopped:" + currentEpoch;
            }
        }

        EpochStateModel cam = new EpochStateModel();
        long ep1 = cam.start("sess_1");
        long ep2 = cam.start("sess_2");
        check(ep2 > ep1 && cam.running, "epoch must advance strictly");
        cam.onUploadResult(ep1, "upload_error");
        check("camera_opened:2".equals(cam.lastEvent), "stale epoch upload_error must not clobber active epoch");
        cam.stop("sess_1", 0);
        check(cam.running, "stale session stop must not stop sess_2");
        cam.stop("sess_2", ep1);
        check(cam.running, "stale expectedEpoch stop must not stop ep2");
        cam.onUploadResult(ep2, "upload_accepted");
        check("upload_accepted:2".equals(cam.lastEvent), "active epoch upload_accepted must record");
        cam.stop("sess_2", ep2);
        check(!cam.running && "stopped:2".equals(cam.lastEvent), "matching epoch+session stop shuts down cleanly");

        System.out.println("PASS: AndroidRound1ContractsTest (BridgePolicy, health probe, origin normalization, epoch isolation)");
    }
}
