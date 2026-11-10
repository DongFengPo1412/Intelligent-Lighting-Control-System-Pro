package org.fglab.kurisu;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.net.nsd.NsdManager;
import android.net.nsd.NsdServiceInfo;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.view.WindowInsets;
import android.webkit.PermissionRequest;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.EditText;
import android.widget.Toast;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;

/** Thin Android host. Browser and APK use exactly the same web_app sources. */
public class MainActivity extends Activity {
    private WebView webView;
    private NsdManager nsd;
    private NsdManager.DiscoveryListener discovery;
    private ValueCallback<Uri[]> fileCallback;
    private volatile String serverOrigin = "";
    private volatile String authenticatedOrigin = "";
    private volatile String candidateOrigin = "";
    private volatile String cameraAuthorizedOrigin = "";
    private volatile boolean bridgeTrusted=false, backgrounded=false, destroyed=false;
    private final java.util.concurrent.atomic.AtomicInteger bridgeEpoch=new java.util.concurrent.atomic.AtomicInteger();
    private final DeviceUdpClient udpClient=new DeviceUdpClient();
    private FrontCameraBridge frontCameraBridge;
    private final DeviceUdpClient readClient=new DeviceUdpClient();
    private final java.util.concurrent.ThreadPoolExecutor readExecutor=new java.util.concurrent.ThreadPoolExecutor(
        1,1,0L,java.util.concurrent.TimeUnit.MILLISECONDS,new java.util.concurrent.ArrayBlockingQueue<Runnable>(1));
    private final java.util.concurrent.ThreadPoolExecutor udpExecutor=new java.util.concurrent.ThreadPoolExecutor(
        1,1,0L,java.util.concurrent.TimeUnit.MILLISECONDS,new java.util.concurrent.ArrayBlockingQueue<Runnable>(64));
    private static final class DeviceTarget {
        final String host,token;
        DeviceTarget(String host,String token) {this.host=host;this.token=token;}
    }
    private volatile DeviceTarget deviceTarget=new DeviceTarget("","");
    private volatile boolean discovering=false;
    private String clientId="";
    private String pendingExport;
    private static final int PICK_FILE = 10, SAVE_CANVAS = 11;
    private static final String OFFLINE = "file:///android_asset/www/index.html";

    @Override protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        webView = findViewById(R.id.webView);
        View root = (View) webView.getParent();
        root.setOnApplyWindowInsetsListener((v, insets) -> {
            if (Build.VERSION.SDK_INT >= 30) {
                android.graphics.Insets bars = insets.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout());
                v.setPadding(bars.left, bars.top, bars.right, bars.bottom);
            } else {
                v.setPadding(insets.getSystemWindowInsetLeft(), insets.getSystemWindowInsetTop(),
                    insets.getSystemWindowInsetRight(), insets.getStableInsetBottom());
            }
            return insets.consumeSystemWindowInsets();
        });
        root.requestApplyInsets();
        deviceTarget=new DeviceTarget(getSharedPreferences("config",MODE_PRIVATE).getString("device_host",""),
            getSharedPreferences("config",MODE_PRIVATE).getString("device_token",""));
        clientId=getSharedPreferences("config",MODE_PRIVATE).getString("device_client",java.util.UUID.randomUUID().toString().replace("-",""));
        getSharedPreferences("config",MODE_PRIVATE).edit().putString("device_client",clientId).apply();
        if (Build.VERSION.SDK_INT >= 23 && checkSelfPermission(android.Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{android.Manifest.permission.CAMERA}, 102);
        }
        frontCameraBridge = new FrontCameraBridge(this, webView);
        initWebSettings();
        webView.loadUrl(OFFLINE);
        autoDiscoverAndConnect(false);
    }

    private void purgeCookiesAndStorage() {
        try {
            android.webkit.CookieManager cm = android.webkit.CookieManager.getInstance();
            cm.removeAllCookies(null);
            cm.flush();
            cm.setAcceptCookie(false);
        } catch (Exception ignored) {}
        try {
            android.webkit.WebStorage.getInstance().deleteAllData();
        } catch (Exception ignored) {}
    }

    private void connectServer(String value) {
        Uri uri = Uri.parse(value.trim());
        if (!("http".equals(uri.getScheme()) || "https".equals(uri.getScheme())) || uri.getHost() == null || uri.getUserInfo() != null) {
            Toast.makeText(this, "请输入完整的 HTTP(S) 服务地址", Toast.LENGTH_LONG).show();
            if (serverOrigin.isEmpty()) webView.loadUrl(OFFLINE);
            return;
        }
        serverOrigin = new Uri.Builder().scheme(uri.getScheme()).encodedAuthority(uri.getEncodedAuthority()).build().toString();
        authenticatedOrigin = serverOrigin;
        android.content.SharedPreferences prefs = getSharedPreferences("config", MODE_PRIVATE);
        prefs.edit().putString("server_url", serverOrigin + "/").apply();
        Toast.makeText(this, "已连接服务 (" + serverOrigin + ")", Toast.LENGTH_SHORT).show();
        String targetUrl = serverOrigin + "/";
        webView.loadUrl(targetUrl);
    }

    private void configureConnection() {
        new AlertDialog.Builder(this).setTitle("连接方式").setItems(new String[]{
            "⚡ 自动搜索并配对连接（推荐）",
            "🎮 灯板街机直连（无需电脑）",
            "💻 电脑服务（语音／音乐／视觉）"
        }, (dialog,which)->{
            if(which==0)autoDiscoverAndConnect(true);
            else if(which==1)configureDevice();
            else configureServer();
        }).show();
    }
    private void configureDevice() {
        android.widget.LinearLayout layout=new android.widget.LinearLayout(this);layout.setOrientation(1);
        DeviceTarget target=deviceTarget;
        EditText host=new EditText(this);host.setHint("ESP32 IPv4（AP 或 STA 地址）");host.setText(target.host.isEmpty()?"192.168.4.1":target.host);
        EditText token=new EditText(this);token.setHint("USB pair 指令返回的 control_token");token.setText(target.token);
        token.setInputType(android.text.InputType.TYPE_CLASS_TEXT|android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD);
        layout.addView(host);layout.addView(token);
        new AlertDialog.Builder(this).setTitle("配对灯板").setView(layout).setPositiveButton("保存直连",(d,w)->{
            String ip=host.getText().toString().trim(),key=token.getText().toString().trim();
            if(!BridgePolicy.privateIpv4(ip)||!BridgePolicy.tokenOrPrivate(ip,key)) {Toast.makeText(this,"需要内网 IPv4（私人热点下凭据可选，或输入 64 位十六进制凭据）",Toast.LENGTH_LONG).show();return;}
            releaseDeviceInput();deviceTarget=new DeviceTarget(ip,key);serverOrigin="";
            getSharedPreferences("config",MODE_PRIVATE).edit().putString("device_host",ip).putString("device_token",key).apply();
            webView.loadUrl(OFFLINE);
        }).setNegativeButton("取消",null).show();
    }
    private void configureServer() {
        configureServer(getSharedPreferences("config", MODE_PRIVATE).getString("server_url", ""));
    }

    private void configureServer(String initialUrl) {
        android.widget.LinearLayout layout = new android.widget.LinearLayout(this);
        layout.setOrientation(android.widget.LinearLayout.VERTICAL);
        layout.setPadding(40, 20, 40, 10);

        EditText urlInput = new EditText(this);
        urlInput.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_VARIATION_URI);
        urlInput.setSingleLine(true);
        urlInput.setHint("http://电脑IP:8080");
        urlInput.setText(initialUrl != null && !initialUrl.isEmpty() ? initialUrl : "http://192.168.");

        EditText tokenInput = new EditText(this);
        tokenInput.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD);
        tokenInput.setSingleLine(true);
        tokenInput.setHint("配对凭据 access_token (可选)");

        layout.addView(urlInput);
        layout.addView(tokenInput);

        new AlertDialog.Builder(this).setTitle("连接电脑服务").setMessage("手机需能访问运行服务的电脑。输入地址与配对凭据可安全配对。")
            .setView(layout).setPositiveButton("连接", (d,w) -> {
                String u = urlInput.getText().toString().trim();
                String tok = tokenInput.getText().toString().trim();
                if (!tok.isEmpty()) {
                    String full = u.contains("?") ? (u + "&pair=" + tok) : (u + "?pair=" + tok);
                    connectServer(full);
                } else {
                    connectServer(u);
                }
            })
            .setNeutralButton("发现服务", (d,w) -> discoverServer()).setNegativeButton("取消", null).show();
    }

    public boolean isPageAuthenticated(WebView view) {
        if (view == null) return false;
        String current = view.getUrl();
        if (current == null || isOfflinePage(current)) return false;
        Uri uri = Uri.parse(current);
        String origin = new Uri.Builder().scheme(uri.getScheme()).encodedAuthority(uri.getEncodedAuthority()).build().toString();
        if (!authenticatedOrigin.isEmpty() && authenticatedOrigin.equalsIgnoreCase(origin)) return true;
        if (!serverOrigin.isEmpty() && serverOrigin.equalsIgnoreCase(origin) && BridgePolicy.privateIpv4(uri.getHost())) return true;
        return false;
    }

    public boolean isPageExplicitlyAuthenticated(WebView view) {
        if (view == null) return false;
        String current = view.getUrl();
        if (current == null || isOfflinePage(current)) return false;
        Uri uri = Uri.parse(current);
        String origin = new Uri.Builder().scheme(uri.getScheme()).encodedAuthority(uri.getEncodedAuthority()).build().toString();
        return !authenticatedOrigin.isEmpty() && authenticatedOrigin.equalsIgnoreCase(origin);
    }

    public boolean isCameraAuthorized(String origin) {
        return origin != null && !cameraAuthorizedOrigin.isEmpty() && cameraAuthorizedOrigin.equalsIgnoreCase(origin);
    }

    private boolean trustedPage(WebView view) {
        String current = view.getUrl();
        if (current == null) return false;
        if (isOfflinePage(current)) return true;
        return isPageAuthenticated(view);
    }

    public static boolean verifyServerIdentity(String candidateOrigin, String savedToken) {
        if (candidateOrigin == null || candidateOrigin.trim().isEmpty() || savedToken == null || savedToken.trim().isEmpty()) {
            return false;
        }
        try {
            byte[] nonceBytes = new byte[16];
            new java.security.SecureRandom().nextBytes(nonceBytes);
            StringBuilder sb = new StringBuilder();
            for (byte b : nonceBytes) sb.append(String.format("%02x", b));
            String clientNonce = sb.toString();

            java.net.URL url = new java.net.URL(candidateOrigin.replaceAll("/+$", "") + "/api/auth/challenge");
            java.net.HttpURLConnection conn = (java.net.HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setRequestProperty("Content-Type", "application/json");
            conn.setConnectTimeout(1500);
            conn.setReadTimeout(1500);
            conn.setDoOutput(true);
            conn.setInstanceFollowRedirects(false);

            org.json.JSONObject req = new org.json.JSONObject();
            req.put("nonce", clientNonce);
            byte[] body = req.toString().getBytes(StandardCharsets.UTF_8);
            try (java.io.OutputStream os = conn.getOutputStream()) {
                os.write(body);
            }

            if (conn.getResponseCode() != 200) {
                return false;
            }

            java.io.ByteArrayOutputStream baos = new java.io.ByteArrayOutputStream();
            try (java.io.InputStream is = conn.getInputStream()) {
                byte[] buf = new byte[1024];
                int n;
                while ((n = is.read(buf)) != -1) baos.write(buf, 0, n);
            }
            String respText = baos.toString("UTF-8");
            org.json.JSONObject resp = new org.json.JSONObject(respText);
            if (!"ok".equals(resp.optString("status"))) return false;
            String serverNonce = resp.optString("server_nonce", "");
            String serverProof = resp.optString("server_proof", "");
            if (serverNonce.isEmpty() || serverProof.isEmpty()) return false;

            javax.crypto.Mac mac = javax.crypto.Mac.getInstance("HmacSHA256");
            javax.crypto.spec.SecretKeySpec keySpec = new javax.crypto.spec.SecretKeySpec(
                savedToken.trim().getBytes(StandardCharsets.UTF_8), "HmacSHA256"
            );
            mac.init(keySpec);
            byte[] rawHmac = mac.doFinal((clientNonce + ":" + serverNonce).getBytes(StandardCharsets.UTF_8));
            StringBuilder expectedProof = new StringBuilder();
            for (byte b : rawHmac) expectedProof.append(String.format("%02x", b));

            return expectedProof.toString().equalsIgnoreCase(serverProof);
        } catch (Exception e) {
            return false;
        }
    }

    private boolean navigate(WebView view, Uri uri) {
        if ("amadeus".equals(uri.getScheme())) {
            if (!trustedPage(view)) return true;
            if ("settings".equals(uri.getHost())) configureConnection();
            if ("pair".equals(uri.getHost())) {
                String ip = uri.getQueryParameter("host"), key = uri.getQueryParameter("token");
                if (BridgePolicy.privateIpv4(ip) && BridgePolicy.token(key)) {
                    releaseDeviceInput();
                    deviceTarget = new DeviceTarget(ip, key);
                    getSharedPreferences("config", MODE_PRIVATE).edit().putString("device_host", ip).putString("device_token", key).apply();
                    Toast.makeText(this, "已同步灯板直连配对参数 (" + ip + ")", Toast.LENGTH_LONG).show();
                }
            }
            if ("export".equals(uri.getHost())) {
                String hex = uri.getQueryParameter("hex");
                if (hex != null && hex.matches("[0-9a-fA-F]{1536}")) {
                    pendingExport = "{\"width\":16,\"height\":16,\"hex\":\"" + hex + "\"}";
                    Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE)
                        .setType("application/json").putExtra(Intent.EXTRA_TITLE, "amadeus-canvas.json");
                    startActivityForResult(intent, SAVE_CANVAS);
                }
            }
            return true;
        }
        if ("file".equals(uri.getScheme())) return !isOfflinePage(uri.toString());
        if (!("http".equals(uri.getScheme()) || "https".equals(uri.getScheme()))) return true;
        String origin = new Uri.Builder().scheme(uri.getScheme()).encodedAuthority(uri.getEncodedAuthority()).build().toString();
        if (serverOrigin.equals(origin)) return false;
        try { startActivity(new Intent(Intent.ACTION_VIEW, uri)); } catch (android.content.ActivityNotFoundException ignored) {}
        return true;
    }

    private void initWebSettings() {
        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(false); // android_asset still works; arbitrary local files do not.
        s.setAllowContentAccess(false);
        s.setAllowFileAccessFromFileURLs(false);
        s.setAllowUniversalAccessFromFileURLs(false);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setUseWideViewPort(true);
        s.setLoadWithOverviewMode(true);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        s.setUserAgentString(s.getUserAgentString() + " AmadeusAndroid/1.1");
        webView.setBackgroundColor(0xff111316);
        webView.addJavascriptInterface(new NativeUdpBridge(), "AmadeusNative");
        webView.setWebViewClient(new WebViewClient() {
            @Override public void onPageStarted(WebView view,String url,android.graphics.Bitmap favicon) {
                if (frontCameraBridge != null) frontCameraBridge.stop();
                if(bridgeTrusted)releaseDeviceInput();
                bridgeTrusted=false;bridgeEpoch.incrementAndGet();udpClient.interrupt();readClient.interrupt();
                if (!isPageAuthenticated(view)) {
                    purgeCookiesAndStorage();
                }
                if (url != null && !isOfflinePage(url)) {
                    Uri u = Uri.parse(url);
                    String curOrig = new Uri.Builder().scheme(u.getScheme()).encodedAuthority(u.getEncodedAuthority()).build().toString();
                    if (!curOrig.equalsIgnoreCase(cameraAuthorizedOrigin)) {
                        cameraAuthorizedOrigin = "";
                    }
                } else {
                    cameraAuthorizedOrigin = "";
                }
                super.onPageStarted(view,url,favicon);
            }
            @Override public void onPageFinished(WebView view,String url) {
                bridgeTrusted=isOfflinePage(url) || isPageAuthenticated(view);super.onPageFinished(view,url);
                if (isPageAuthenticated(view)) {
                    android.content.SharedPreferences prefs = getSharedPreferences("config", MODE_PRIVATE);
                    String tok = prefs.getString("access_token", "");
                    if (tok != null && !tok.isEmpty() && !isOfflinePage(url)) {
                        String js = "try { sessionStorage.setItem('kurisu_access_token', '" + tok + "'); localStorage.setItem('kurisu_access_token', '" + tok + "'); } catch(e){}";
                        view.evaluateJavascript(js, null);
                    }
                }
            }
            @Override public android.webkit.WebResourceResponse shouldInterceptRequest(WebView view,WebResourceRequest request) {
                String url=request.getUrl().toString();
                // The bridge is injected into all frames: packaged pages may load
                // packaged assets only. CSP also prohibits frames/objects entirely.
                if(serverOrigin.isEmpty() && !url.startsWith("file:///android_asset/www/"))
                    return new android.webkit.WebResourceResponse("text/plain","utf-8",new java.io.ByteArrayInputStream(new byte[0]));
                return null;
            }
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                return request.isForMainFrame() && navigate(view, request.getUrl());
            }
            @Override public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (frontCameraBridge != null) frontCameraBridge.stop();
                cameraAuthorizedOrigin = "";
                if (request.isForMainFrame() && !request.getUrl().toString().startsWith("file:")) {
                    serverOrigin = "";
                    authenticatedOrigin = "";
                    purgeCookiesAndStorage();
                    view.loadUrl(OFFLINE);
                    Toast.makeText(MainActivity.this, "已切换至手机直连模式", Toast.LENGTH_SHORT).show();
                }
            }
        });
        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(final PermissionRequest request) {
                runOnUiThread(() -> {
                    if (isFinishing() || destroyed) {
                        request.deny();
                        return;
                    }
                    try {
                        String reqOrigin = request.getOrigin() != null ? request.getOrigin().toString() : "";
                        boolean wantsVideo = false;
                        for (String res : request.getResources()) {
                            if (PermissionRequest.RESOURCE_VIDEO_CAPTURE.equals(res)) {
                                wantsVideo = true;
                                break;
                            }
                        }
                        if (!wantsVideo) {
                            request.deny();
                            return;
                        }
                        final String[] videoOnly = new String[]{PermissionRequest.RESOURCE_VIDEO_CAPTURE};
                        if (isCameraAuthorized(reqOrigin)) {
                            request.grant(videoOnly);
                            return;
                        }
                        new AlertDialog.Builder(MainActivity.this)
                            .setTitle("摄像头权限申请")
                            .setMessage("网页 (" + reqOrigin + ") 申请使用摄像头进行体感与视觉交互。\n\n是否允许？")
                            .setPositiveButton("允许", (d, w) -> {
                                cameraAuthorizedOrigin = reqOrigin;
                                request.grant(videoOnly);
                            })
                            .setNegativeButton("拒绝", (d, w) -> request.deny())
                            .setOnCancelListener(d -> request.deny())
                            .show();
                    } catch (Exception e) {
                        request.deny();
                    }
                });
            }
            @Override public boolean onJsPrompt(WebView view, String url, String message, String defaultValue, final android.webkit.JsPromptResult result) {
                if (isFinishing() || !trustedPage(view)) { result.cancel(); return true; }
                final EditText input = new EditText(MainActivity.this);
                input.setSingleLine(true);
                if (defaultValue != null) input.setText(defaultValue);
                new AlertDialog.Builder(MainActivity.this).setTitle("配对验证").setMessage(message).setView(input)
                    .setPositiveButton("确定", (d, w) -> result.confirm(input.getText().toString()))
                    .setNegativeButton("取消", (d, w) -> result.cancel())
                    .setOnCancelListener(d -> result.cancel()).show();
                return true;
            }
            @Override public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback, FileChooserParams params) {
                if (!trustedPage(view)) return false;
                if (fileCallback != null) fileCallback.onReceiveValue(null);
                fileCallback = callback;
                try { startActivityForResult(params.createIntent(), PICK_FILE); }
                catch (android.content.ActivityNotFoundException error) { fileCallback.onReceiveValue(null); fileCallback=null; return false; }
                return true;
            }
        });
    }

    @Override protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if (request == PICK_FILE && fileCallback != null) {
            fileCallback.onReceiveValue(WebChromeClient.FileChooserParams.parseResult(result, data)); fileCallback=null;
        }
        if (request == SAVE_CANVAS && pendingExport != null) {
            if (result == RESULT_OK && data != null && data.getData() != null) {
                try (OutputStream out = getContentResolver().openOutputStream(data.getData())) {
                    if (out == null) throw new java.io.IOException("No output stream");
                    out.write(pendingExport.getBytes(StandardCharsets.UTF_8));
                    Toast.makeText(this, "画布已保存", Toast.LENGTH_SHORT).show();
                } catch (java.io.IOException error) { Toast.makeText(this, "保存失败，请重试", Toast.LENGTH_LONG).show(); }
            }
            pendingExport=null;
        }
    }

    private static void addSubnetPrefix(java.util.Set<String> prefixes, String ip) {
        if (!BridgePolicy.privateIpv4(ip)) return;
        int dot = ip.lastIndexOf('.');
        if (dot > 0) prefixes.add(ip.substring(0, dot + 1));
    }

    private void autoDiscoverAndConnect(final boolean manual) {
        if (discovering) return;
        discovering = true;
        if (manual) Toast.makeText(this, "正在自动搜索局域网内的电脑服务与灯板…", Toast.LENGTH_SHORT).show();
        new Thread(() -> {
            String foundServerUrl = null, foundAccessToken = null, foundBoardIp = null, foundControlToken = null;
            try (java.net.DatagramSocket sock = new java.net.DatagramSocket()) {
                sock.setBroadcast(true);
                sock.setSoTimeout(45);
                java.util.Set<String> prefixes = new java.util.LinkedHashSet<>();
                try {
                    java.util.Enumeration<java.net.NetworkInterface> ifs = java.net.NetworkInterface.getNetworkInterfaces();
                    while (ifs != null && ifs.hasMoreElements()) {
                        java.net.NetworkInterface nif = ifs.nextElement();
                        if (!nif.isUp() || nif.isLoopback()) continue;
                        java.util.Enumeration<java.net.InetAddress> addrs = nif.getInetAddresses();
                        while (addrs.hasMoreElements()) {
                            String ip = addrs.nextElement().getHostAddress();
                            addSubnetPrefix(prefixes, ip);
                        }
                    }
                } catch (Exception ignored) {}
                addSubnetPrefix(prefixes, deviceTarget.host);
                String savedUrl = getSharedPreferences("config", MODE_PRIVATE).getString("server_url", "");
                if (!savedUrl.isEmpty()) {
                    try { addSubnetPrefix(prefixes, Uri.parse(savedUrl).getHost()); } catch (Exception ignored) {}
                }
                prefixes.add("192.168.186.");
                prefixes.add("192.168.4.");

                byte[] pcProbe = "{\"cmd\":\"kurisu_discover\"}".getBytes(StandardCharsets.UTF_8);
                byte[] boardProbe = "{\"request_id\":\"probe_discover\"}".getBytes(StandardCharsets.UTF_8);
                try {
                    sock.send(new java.net.DatagramPacket(pcProbe, pcProbe.length, java.net.InetAddress.getByName("255.255.255.255"), 8890));
                    sock.send(new java.net.DatagramPacket(boardProbe, boardProbe.length, java.net.InetAddress.getByName("255.255.255.255"), 8888));
                    sock.send(new java.net.DatagramPacket(boardProbe, boardProbe.length, java.net.InetAddress.getByName("192.168.4.1"), 8888));
                    if (BridgePolicy.privateIpv4(deviceTarget.host)) {
                        sock.send(new java.net.DatagramPacket(boardProbe, boardProbe.length, java.net.InetAddress.getByName(deviceTarget.host), 8888));
                    }
                    if (!savedUrl.isEmpty()) {
                        String sHost = Uri.parse(savedUrl).getHost();
                        if (BridgePolicy.privateIpv4(sHost)) {
                            sock.send(new java.net.DatagramPacket(pcProbe, pcProbe.length, java.net.InetAddress.getByName(sHost), 8890));
                        }
                    }
                } catch (Exception ignored) {}

                for (String prefix : prefixes) {
                    try {
                        sock.send(new java.net.DatagramPacket(pcProbe, pcProbe.length, java.net.InetAddress.getByName(prefix + "255"), 8890));
                        sock.send(new java.net.DatagramPacket(boardProbe, boardProbe.length, java.net.InetAddress.getByName(prefix + "255"), 8888));
                    } catch (Exception ignored) {}
                }

                // Phase 1: Fast receive window after broadcast (600ms)
                long deadline = System.nanoTime() + 600_000_000L;
                byte[] buf = new byte[2048];
                while (System.nanoTime() < deadline) {
                    java.net.DatagramPacket pkt = new java.net.DatagramPacket(buf, buf.length);
                    try {
                        sock.receive(pkt);
                    } catch (java.net.SocketTimeoutException timeout) {
                        if (foundServerUrl != null && foundBoardIp != null) break;
                        continue;
                    }
                    String senderIp = pkt.getAddress().getHostAddress();
                    if (!BridgePolicy.privateIpv4(senderIp)) continue;
                    String text = new String(pkt.getData(), 0, pkt.getLength(), StandardCharsets.UTF_8).trim();
                    try {
                        org.json.JSONObject json = new org.json.JSONObject(text);
                        if ("KurisuPro".equals(json.optString("service"))) {
                            int port = json.optInt("port", 8080);
                            String rawUrl = json.optString("server_url", "");
                            if (rawUrl != null && !rawUrl.isEmpty()) {
                                try {
                                    java.net.URI u = new java.net.URI(rawUrl);
                                    if (u.getPort() > 0 && u.getPort() <= 65535) port = u.getPort();
                                } catch (Exception ignored) {}
                            }
                            foundServerUrl = "http://" + senderIp + ":" + port;
                            String bIp = json.optString("board_ip", "");
                            if (BridgePolicy.privateIpv4(bIp)) foundBoardIp = bIp;
                            if (foundBoardIp != null) break;
                        }
                        if (json.has("boot_id") || "Kurisu-Matrix".equals(json.optString("device"))) {
                            String staIp = json.optString("sta_ip", "");
                            foundBoardIp = BridgePolicy.privateIpv4(staIp) ? staIp : senderIp;
                            if (foundServerUrl != null) break;
                        }
                    } catch (Exception ignored) {}
                }

                // Phase 2: If either is missing, do targeted fallback scan
                if (foundServerUrl == null || foundBoardIp == null) {
                    for (String prefix : prefixes) {
                        for (int host = 1; host <= 254; host++) {
                            try {
                                java.net.InetAddress target = java.net.InetAddress.getByName(prefix + host);
                                if (foundServerUrl == null) sock.send(new java.net.DatagramPacket(pcProbe, pcProbe.length, target, 8890));
                                if (foundBoardIp == null) sock.send(new java.net.DatagramPacket(boardProbe, boardProbe.length, target, 8888));
                            } catch (Exception ignored) {}
                        }
                    }
                    deadline = System.nanoTime() + 1_000_000_000L;
                    while (System.nanoTime() < deadline) {
                        java.net.DatagramPacket pkt = new java.net.DatagramPacket(buf, buf.length);
                        try {
                            sock.receive(pkt);
                        } catch (java.net.SocketTimeoutException timeout) {
                            if (foundServerUrl != null && foundBoardIp != null) break;
                            continue;
                        }
                        String senderIp = pkt.getAddress().getHostAddress();
                        if (!BridgePolicy.privateIpv4(senderIp)) continue;
                        String text = new String(pkt.getData(), 0, pkt.getLength(), StandardCharsets.UTF_8).trim();
                        try {
                            org.json.JSONObject json = new org.json.JSONObject(text);
                            if ("KurisuPro".equals(json.optString("service"))) {
                                int port = json.optInt("port", 8080);
                                String rawUrl = json.optString("server_url", "");
                                if (rawUrl != null && !rawUrl.isEmpty()) {
                                    try {
                                        java.net.URI u = new java.net.URI(rawUrl);
                                        if (u.getPort() > 0 && u.getPort() <= 65535) port = u.getPort();
                                    } catch (Exception ignored) {}
                                }
                                foundServerUrl = "http://" + senderIp + ":" + port;
                                String bIp = json.optString("board_ip", "");
                                if (BridgePolicy.privateIpv4(bIp)) foundBoardIp = bIp;
                                if (foundBoardIp != null) break;
                            }
                            if (json.has("boot_id") || "Kurisu-Matrix".equals(json.optString("device"))) {
                                String staIp = json.optString("sta_ip", "");
                                foundBoardIp = BridgePolicy.privateIpv4(staIp) ? staIp : senderIp;
                                if (foundServerUrl != null) break;
                            }
                        } catch (Exception ignored) {}
                    }
                }
            } catch (Exception ignored) {}

            if (foundServerUrl != null) {
                try {
                    java.net.URL healthUrl = new java.net.URL(foundServerUrl + "/api/health");
                    java.net.HttpURLConnection conn = (java.net.HttpURLConnection) healthUrl.openConnection();
                    conn.setInstanceFollowRedirects(false);
                    conn.setConnectTimeout(800);
                    conn.setReadTimeout(800);
                    conn.setRequestMethod("GET");
                    int code = conn.getResponseCode();
                    if (code == 200) {
                        try (java.io.InputStream in = conn.getInputStream();
                             java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream()) {
                            long deadlineRead = System.nanoTime() + 800_000_000L;
                            byte[] buf = new byte[256];
                            int r;
                            boolean rejected = false;
                            while ((r = in.read(buf)) != -1) {
                                if (System.nanoTime() >= deadlineRead) {
                                    rejected = true;
                                    break;
                                }
                                out.write(buf, 0, r);
                                if (out.size() > 16384) {
                                    rejected = true;
                                    break;
                                }
                            }
                            if (rejected) {
                                foundServerUrl = null;
                            } else {
                                String body = out.toString("UTF-8");
                                org.json.JSONObject obj = new org.json.JSONObject(body);
                                if (!"ok".equals(obj.optString("status")) || !"KurisuPro".equals(obj.optString("service"))) {
                                    foundServerUrl = null;
                                }
                            }
                        } catch (Exception e) {
                            foundServerUrl = null;
                        }
                    } else {
                        foundServerUrl = null;
                    }
                    conn.disconnect();
                } catch (Exception e) {
                    foundServerUrl = null;
                }
            }

            final String sUrl = foundServerUrl, bIp = foundBoardIp;
            if (sUrl != null) {
                candidateOrigin = sUrl;
            }
            runOnUiThread(() -> {
                discovering = false;
                if (isFinishing() || destroyed) return;
                android.content.SharedPreferences prefs = getSharedPreferences("config", MODE_PRIVATE);
                android.content.SharedPreferences.Editor ed = prefs.edit();
                String finalBoardIp = bIp != null ? bIp : deviceTarget.host;
                if (BridgePolicy.privateIpv4(finalBoardIp)) {
                    deviceTarget = new DeviceTarget(finalBoardIp, deviceTarget.token);
                    ed.putString("device_host", finalBoardIp);
                }
                if (sUrl != null) {
                    serverOrigin = sUrl;
                    ed.putString("server_url", sUrl + "/").apply();
                    String curUrl = webView.getUrl();
                    if (curUrl == null || curUrl.equals(OFFLINE) || !curUrl.startsWith(sUrl)) {
                        Toast.makeText(MainActivity.this, "已连接电脑服务 (" + sUrl + ")", Toast.LENGTH_SHORT).show();
                        webView.loadUrl(sUrl + "/");
                    }
                } else if (BridgePolicy.privateIpv4(finalBoardIp)) {
                    ed.apply();
                    String curUrl = webView.getUrl();
                    if (curUrl == null || (!isOfflinePage(curUrl) && (serverOrigin == null || serverOrigin.isEmpty()))) {
                        Toast.makeText(MainActivity.this, "已自动直连灯板 (" + finalBoardIp + ")", Toast.LENGTH_SHORT).show();
                        webView.loadUrl(OFFLINE);
                    }
                } else {
                    ed.apply();
                    if (manual) {
                        Toast.makeText(MainActivity.this, "未发现同一局域网下的服务，请确认手机与设备在同一热点/Wi-Fi", Toast.LENGTH_LONG).show();
                        discoverServer();
                    }
                }
            });
        }).start();
    }

    private void discoverServer() {
        autoDiscoverAndConnect(true);
        if (discovery != null) return;
        nsd = (NsdManager) getSystemService(NSD_SERVICE);
        discovery = new NsdManager.DiscoveryListener() {
            public void onDiscoveryStarted(String type) { runOnUiThread(() -> Toast.makeText(MainActivity.this, "正在发现服务；也可手动输入地址", Toast.LENGTH_LONG).show()); }
            public void onServiceFound(NsdServiceInfo service) {
                if (!service.getServiceName().startsWith("KurisuPro")) return;
                nsd.resolveService(service, new NsdManager.ResolveListener() {
                    public void onResolveFailed(NsdServiceInfo s, int code) {}
                    public void onServiceResolved(NsdServiceInfo s) {
                        String host=s.getHost().getHostAddress(); if (host.indexOf(':')>=0) host="["+host+"]";
                        final String url="http://"+host+":"+s.getPort();
                        runOnUiThread(() -> {
                            if (!isFinishing()) {
                                serverOrigin = url;
                                getSharedPreferences("config", MODE_PRIVATE).edit().putString("server_url", url + "/").apply();
                                Toast.makeText(MainActivity.this, "已自动连接电脑服务 (" + url + ")", Toast.LENGTH_SHORT).show();
                                webView.loadUrl(url + "/");
                            }
                        });
                        stopDiscovery();
                    }
                });
            }
            public void onServiceLost(NsdServiceInfo s) {}
            public void onDiscoveryStopped(String type) { discovery=null; }
            public void onStartDiscoveryFailed(String type,int code) { stopDiscovery(); }
            public void onStopDiscoveryFailed(String type,int code) { discovery=null; }
        };
        nsd.discoverServices("_kurisupro._tcp.",NsdManager.PROTOCOL_DNS_SD,discovery);
        webView.postDelayed(this::stopDiscovery,15000);
    }
    private void stopDiscovery() { NsdManager.DiscoveryListener current=discovery;discovery=null;if(nsd!=null&&current!=null)try{nsd.stopServiceDiscovery(current);}catch(IllegalArgumentException ignored){} }
    @Override protected void onPause() {
        if (frontCameraBridge != null) frontCameraBridge.stop();
        backgrounded=true;releaseDeviceInput();
        webView.evaluateJavascript("window.dispatchEvent(new Event('blur'))",null);
        webView.onPause();super.onPause();
    }
    @Override protected void onResume() {
        super.onResume();
        backgrounded=false;
        if(webView!=null)webView.onResume();
        autoDiscoverAndConnect(false);
    }
    @Override protected void onDestroy() { if (frontCameraBridge != null) frontCameraBridge.stop(); releaseDeviceInput();destroyed=true;bridgeTrusted=false;udpExecutor.shutdown();readExecutor.shutdownNow();stopDiscovery();if(fileCallback!=null)fileCallback.onReceiveValue(null);if(webView!=null)webView.destroy();super.onDestroy(); }
    @Override public void onBackPressed() { if(webView.canGoBack())webView.goBack();else super.onBackPressed(); }

    private static boolean isOfflinePage(String url) {
        if(url==null)return false;
        Uri uri=Uri.parse(url);
        return "file".equals(uri.getScheme()) && (uri.getAuthority()==null || uri.getAuthority().isEmpty()) && "/android_asset/www/index.html".equals(uri.getPath());
    }
    private void releaseDeviceInput() {
        bridgeEpoch.incrementAndGet();udpClient.interrupt();readClient.interrupt();
        final DeviceTarget target=deviceTarget;
        if(!BridgePolicy.privateIpv4(target.host)||!BridgePolicy.tokenOrPrivate(target.host,target.token))return;
        final String host=target.host,key=target.token;
        try { udpExecutor.execute(()->{
            for(String command:new String[]{"{\"cmd\":\"arcade\",\"action\":\"input\",\"down\":0,\"pressed\":0}","{\"cmd\":\"arcade\",\"action\":\"pause\"}"}) {
                String id="release_"+java.util.UUID.randomUUID().toString().replace("-","");
                try {
                    org.json.JSONObject envelope=new org.json.JSONObject();envelope.put("request_id",id);envelope.put("command",command);
                    udpClient.request(host,key,clientId,envelope.toString(),200,1,id);
                }catch(Exception ignored){}
            }
        }); } catch(java.util.concurrent.RejectedExecutionException ignored) { /* Board watchdog releases/pause in 500/1000ms. */ }
    }
    public class NativeUdpBridge {
        @android.webkit.JavascriptInterface
        public boolean hasNativeCamera() {
            return true;
        }

        @android.webkit.JavascriptInterface
        public boolean startFrontCamera(final String uploadUrl, final String mode) {
            if (backgrounded || destroyed) return false;
            String curUrl = webView != null ? webView.getUrl() : null;
            if (curUrl == null || isOfflinePage(curUrl)) return false;
            Uri curUri = Uri.parse(curUrl);
            final String curOrigin = new Uri.Builder().scheme(curUri.getScheme()).encodedAuthority(curUri.getEncodedAuthority()).build().toString();

            // Validate caller origin against authenticated serverOrigin
            if (serverOrigin == null || serverOrigin.isEmpty() || !serverOrigin.equalsIgnoreCase(curOrigin)) {
                android.util.Log.w("MainActivity", "Camera rejected: caller origin does not match authenticated serverOrigin");
                return false;
            }

            // Verify Android OS camera permission
            if (android.os.Build.VERSION.SDK_INT >= 23 && checkSelfPermission(android.Manifest.permission.CAMERA) != android.content.pm.PackageManager.PERMISSION_GRANTED) {
                android.util.Log.w("MainActivity", "Camera rejected: OS Camera permission not granted");
                return false;
            }

            if (!isCameraAuthorized(curOrigin)) {
                android.util.Log.i("MainActivity", "Requesting camera authorization for origin: " + curOrigin);
                final java.util.concurrent.CountDownLatch latch = new java.util.concurrent.CountDownLatch(1);
                final boolean[] authorized = new boolean[]{false};
                runOnUiThread(() -> {
                    if (isFinishing() || destroyed) {
                        latch.countDown();
                        return;
                    }
                    new AlertDialog.Builder(MainActivity.this)
                        .setTitle("摄像头权限申请")
                        .setMessage("网页 (" + curOrigin + ") 申请使用摄像头进行体感与视觉交互。\n\n是否允许？")
                        .setPositiveButton("允许", (d, w) -> {
                            cameraAuthorizedOrigin = curOrigin;
                            authorized[0] = true;
                            latch.countDown();
                        })
                        .setNegativeButton("拒绝", (d, w) -> {
                            authorized[0] = false;
                            latch.countDown();
                        })
                        .setOnCancelListener(d -> {
                            authorized[0] = false;
                            latch.countDown();
                        })
                        .show();
                });
                try {
                    boolean completed = latch.await(30, java.util.concurrent.TimeUnit.SECONDS);
                    if (!completed || !authorized[0]) {
                        android.util.Log.w("MainActivity", "Camera permission denied or timed out by user");
                        return false;
                    }
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    return false;
                }
            }
            if (uploadUrl == null || uploadUrl.trim().isEmpty()) return false;
            try {
                Uri parsed = Uri.parse(uploadUrl.trim());
                if (!("http".equalsIgnoreCase(parsed.getScheme()) || "https".equalsIgnoreCase(parsed.getScheme()))) {
                    return false;
                }
                String host = parsed.getHost();
                int port = parsed.getPort() != -1 ? parsed.getPort() : ("https".equalsIgnoreCase(parsed.getScheme()) ? 443 : 80);
                Uri authUri = Uri.parse(curOrigin);
                String authHost = authUri.getHost();
                int authPort = authUri.getPort() != -1 ? authUri.getPort() : ("https".equalsIgnoreCase(authUri.getScheme()) ? 443 : 80);
                if (host == null || !host.equalsIgnoreCase(authHost) || port != authPort) {
                    android.util.Log.w("MainActivity", "Camera upload rejected: target origin does not match authorized server");
                    return false;
                }
                String path = parsed.getPath();
                if (path == null || !(path.equals("/api/vision/phone_frame") || path.equals("/api/pro/vision/frame") || path.equals("/api/pro/camera/frame"))) {
                    android.util.Log.w("MainActivity", "Camera upload rejected: endpoint not whitelisted");
                    return false;
                }
                String sessionId = parsed.getQueryParameter("session_id");
                if (sessionId == null || sessionId.trim().isEmpty()) {
                    android.util.Log.w("MainActivity", "Camera upload rejected: missing session_id");
                    return false;
                }
            } catch (Exception e) {
                return false;
            }
            if (frontCameraBridge != null) {
                return frontCameraBridge.start(uploadUrl, mode, curOrigin);
            }
            return false;
        }

        @android.webkit.JavascriptInterface
        public void stopFrontCamera() {
            if (frontCameraBridge != null) {
                frontCameraBridge.stop();
            }
        }

        @android.webkit.JavascriptInterface
        public void stopFrontCamera(final String sessionId) {
            if (frontCameraBridge != null) {
                frontCameraBridge.stop(sessionId);
            }
        }

        @android.webkit.JavascriptInterface
        public void setCameraRotation(final int rotation) {
            if (frontCameraBridge != null) {
                frontCameraBridge.setRotation(rotation);
            }
        }

        @android.webkit.JavascriptInterface
        public void sendUdpAsync(final String message,final int timeoutMs,final int retries,final String callbackId) {
            if(!BridgePolicy.requestId(callbackId))return;
            final int epoch=bridgeEpoch.get();
            final DeviceTarget target=deviceTarget;
            if(!bridgeTrusted||backgrounded||destroyed||message==null||message.length()>3000) {
                dispatchResult(epoch,callbackId,DeviceUdpClient.error(callbackId,"forbidden_page"));return;
            }
            if(!BridgePolicy.privateIpv4(target.host)) {
                dispatchResult(epoch,callbackId,DeviceUdpClient.error(callbackId,"pairing_required"));return;
            }
            // Each lane is serial with its own stable replay identity. A dropped
            // frame cannot occupy the control socket, or reorder its sequence.
            final boolean readOnly=DeviceUdpClient.isReadOnly(message);
            final DeviceUdpClient client=readOnly?readClient:udpClient;
            final String identity=readOnly?java.util.UUID.nameUUIDFromBytes((clientId+":read").getBytes(StandardCharsets.UTF_8)).toString().replace("-",""):clientId;
            try { (readOnly?readExecutor:udpExecutor).execute(()->{
                if(epoch!=bridgeEpoch.get()||backgrounded||destroyed)return;
                String result=client.request(target.host,target.token,identity,message,readOnly?1200:Math.max(timeoutMs, 1200),readOnly?0:retries,callbackId);
                dispatchResult(epoch,callbackId,result);
            }); } catch(java.util.concurrent.RejectedExecutionException full) {
                dispatchResult(epoch,callbackId,DeviceUdpClient.error(callbackId,"queue_full"));
            }
        }
        private void dispatchResult(final int epoch,final String id,final String raw) {
            if(destroyed||webView==null)return;
            webView.post(()->{
                if(epoch!=bridgeEpoch.get()||!bridgeTrusted||backgrounded||destroyed)return;
                String key=org.json.JSONObject.quote(id),payload=org.json.JSONObject.quote(raw);
                webView.evaluateJavascript("if(window.__amadeusUdpCallbacks&&window.__amadeusUdpCallbacks["+key+"])window.__amadeusUdpCallbacks["+key+"]("+payload+");",null);
            });
        }
    }
}
