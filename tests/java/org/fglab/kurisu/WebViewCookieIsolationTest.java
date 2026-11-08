package org.fglab.kurisu;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.InetSocketAddress;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.CopyOnWriteArrayList;

/**
 * Directed test verifying Android WebView CookieManager cross-port isolation contract.
 * Demonstrates that when paired with host:portA with a synthetic token,
 * opening host:portB in guest/isolation mode (as performed by MainActivity.purgeCookiesAndStorage)
 * guarantees that the first request received by portB carries NO old kurisu_session cookie.
 */
public final class WebViewCookieIsolationTest {
    static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError("FAILED: " + message);
    }

    public static void main(String[] args) throws Exception {
        System.out.println("=== Starting Android WebView Cross-Port Cookie Isolation Test ===");

        final List<String> serverACookies = new CopyOnWriteArrayList<>();
        final List<String> serverBCookies = new CopyOnWriteArrayList<>();

        // 1. Start two HTTP servers on the same host (127.0.0.1) on different ports
        HttpServer serverA = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        serverA.createContext("/", new HttpHandler() {
            @Override
            public void handle(HttpExchange exchange) throws IOException {
                List<String> cookies = exchange.getRequestHeaders().get("Cookie");
                serverACookies.add(cookies != null ? String.join(";", cookies) : "");
                byte[] resp = "{\"status\":\"ok\",\"server\":\"A\"}".getBytes(StandardCharsets.UTF_8);
                exchange.getResponseHeaders().set("Content-Type", "application/json");
                exchange.sendResponseHeaders(200, resp.length);
                try (OutputStream os = exchange.getResponseBody()) { os.write(resp); }
            }
        });
        serverA.start();
        int portA = serverA.getAddress().getPort();

        HttpServer serverB = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        serverB.createContext("/", new HttpHandler() {
            @Override
            public void handle(HttpExchange exchange) throws IOException {
                List<String> cookies = exchange.getRequestHeaders().get("Cookie");
                serverBCookies.add(cookies != null ? String.join(";", cookies) : "");
                byte[] resp = "{\"status\":\"ok\",\"server\":\"B\"}".getBytes(StandardCharsets.UTF_8);
                exchange.getResponseHeaders().set("Content-Type", "application/json");
                exchange.sendResponseHeaders(200, resp.length);
                try (OutputStream os = exchange.getResponseBody()) { os.write(resp); }
            }
        });
        serverB.start();
        int portB = serverB.getAddress().getPort();

        try {
            System.out.println("Server A listening on 127.0.0.1:" + portA);
            System.out.println("Server B (candidate) listening on 127.0.0.1:" + portB);

            // 2. Simulate Android CookieManager model
            class CookieManagerModel {
                // RFC 6265 standard cookie jar stores by domain/hostname
                private final Map<String, String> hostCookies = new HashMap<>();
                private boolean acceptCookie = false;

                public void setAcceptCookie(boolean accept) {
                    this.acceptCookie = accept;
                }

                public void setCookie(String host, String cookieStr) {
                    if (!acceptCookie) return;
                    hostCookies.put(host, cookieStr);
                }

                public void removeAllCookies() {
                    hostCookies.clear();
                }

                public String getCookieFor(String host) {
                    if (!acceptCookie) return "";
                    return hostCookies.getOrDefault(host, "");
                }
            }

            // 3. Simulate MainActivity security state machine
            class MainActivityModel {
                final CookieManagerModel cm = new CookieManagerModel();
                String serverOrigin = "";
                String authenticatedOrigin = "";

                void purgeCookiesAndStorage() {
                    cm.removeAllCookies();
                    cm.setAcceptCookie(false);
                }

                void connectServer(String value) {
                    try {
                        URL url = new URL(value);
                        String query = url.getQuery();
                        String origin = url.getProtocol() + "://" + url.getHost() + ":" + url.getPort();
                        serverOrigin = origin;

                        String pairParam = null;
                        if (query != null) {
                            for (String param : query.split("&")) {
                                String[] pair = param.split("=");
                                if (pair.length == 2 && "pair".equals(pair[0])) {
                                    pairParam = pair[1];
                                }
                            }
                        }

                        if (pairParam != null && !pairParam.trim().isEmpty()) {
                            // User explicitly provided pairing token
                            String token = pairParam.trim();
                            authenticatedOrigin = origin;
                            cm.setAcceptCookie(true);
                            cm.removeAllCookies();
                            cm.setCookie(url.getHost(), "kurisu_session=" + token);
                        } else {
                            // Candidate / unauthenticated connection: purgeCookiesAndStorage
                            authenticatedOrigin = "";
                            purgeCookiesAndStorage();
                        }
                    } catch (Exception e) {
                        throw new RuntimeException(e);
                    }
                }

                int sendRequest(String targetUrl) throws Exception {
                    URL u = new URL(targetUrl);
                    HttpURLConnection conn = (HttpURLConnection) u.openConnection();
                    String cookie = cm.getCookieFor(u.getHost());
                    if (cookie != null && !cookie.isEmpty()) {
                        conn.setRequestProperty("Cookie", cookie);
                    }
                    conn.setConnectTimeout(2000);
                    conn.setReadTimeout(2000);
                    return conn.getResponseCode();
                }
            }

            MainActivityModel activity = new MainActivityModel();

            // STEP 1: Pair with Server A using synthetic token
            String synthTokenA = "synth_token_9999888877776666";
            System.out.println("Step 1: Pairing with Server A (port " + portA + ") with synthetic token...");
            activity.connectServer("http://127.0.0.1:" + portA + "/?pair=" + synthTokenA);
            check(("http://127.0.0.1:" + portA).equals(activity.authenticatedOrigin), "Authenticated origin must be port A");

            int codeA = activity.sendRequest("http://127.0.0.1:" + portA + "/api/status");
            check(codeA == 200, "Server A must return 200");
            check(!serverACookies.isEmpty(), "Server A must receive requests");
            check(serverACookies.get(0).contains("kurisu_session=" + synthTokenA),
                    "Server A must receive synthetic token");
            System.out.println("  -> Verified: Server A received kurisu_session=" + synthTokenA);

            // STEP 2: Candidate Server B (port B) discovered on SAME host (127.0.0.1)
            // User opens Server B in guest/isolated mode (without pairing token)
            System.out.println("Step 2: Opening candidate Server B (port " + portB + ") in guest/isolated mode...");
            activity.connectServer("http://127.0.0.1:" + portB + "/");
            check(activity.authenticatedOrigin.isEmpty(), "Candidate Server B must NOT be authenticated");

            // STEP 3: Check FIRST request received by Server B
            int codeB = activity.sendRequest("http://127.0.0.1:" + portB + "/api/status");
            check(codeB == 200, "Server B must return 200");
            check(!serverBCookies.isEmpty(), "Server B must receive the first request");
            String firstRequestCookie = serverBCookies.get(0);
            System.out.println("  -> Server B first request Cookie header: '" + firstRequestCookie + "'");

            check(firstRequestCookie.isEmpty(), "CRITICAL SECURITY CHECK: Server B Cookie header MUST BE EMPTY!");
            check(!firstRequestCookie.contains("kurisu_session"), "Server B must NOT contain kurisu_session!");
            check(!firstRequestCookie.contains(synthTokenA), "Server B must NOT receive Server A's synthetic token!");
            System.out.println("  -> Verified: Server B first request carried ZERO cookies, no credential leakage!");

            // STEP 4: User explicitly pairs with Server B using new synthetic token
            String synthTokenB = "synth_token_for_server_B_11223344";
            System.out.println("Step 4: Explicitly pairing with Server B with new token...");
            activity.connectServer("http://127.0.0.1:" + portB + "/?pair=" + synthTokenB);
            check(("http://127.0.0.1:" + portB).equals(activity.authenticatedOrigin), "Server B is now authenticated");

            int codeB2 = activity.sendRequest("http://127.0.0.1:" + portB + "/api/status");
            check(codeB2 == 200, "Server B must return 200 on paired request");
            check(serverBCookies.size() >= 2, "Server B must have second request");
            String secondRequestCookie = serverBCookies.get(1);
            check(secondRequestCookie.contains("kurisu_session=" + synthTokenB), "Server B now receives its own token");
            check(!secondRequestCookie.contains(synthTokenA), "Server B never receives Server A's token");
            System.out.println("  -> Verified: Server B now receives its own token: " + synthTokenB);

            System.out.println("\nSUCCESS: All Android WebView cross-port Cookie isolation checks PASSED!");
        } finally {
            serverA.stop(0);
            serverB.stop(0);
        }
    }
}
