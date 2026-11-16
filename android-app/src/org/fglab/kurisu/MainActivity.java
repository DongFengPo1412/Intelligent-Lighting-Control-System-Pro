package org.fglab.kurisu;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.net.NetworkRequest;
import android.net.Uri;
import android.net.nsd.NsdManager;
import android.net.nsd.NsdServiceInfo;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
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
    private volatile String mainFrameOrigin = "";
    private volatile String mainFrameUrl = "";
    private volatile boolean bridgeTrusted=false, backgrounded=false, destroyed=false;
    private final java.util.concurrent.atomic.AtomicInteger bridgeEpoch=new java.util.concurrent.atomic.AtomicInteger();
    private final java.util.concurrent.atomic.AtomicInteger pageNavigationEpoch=new java.util.concurrent.atomic.AtomicInteger();
    private final java.util.concurrent.atomic.AtomicInteger discoveryGen=new java.util.concurrent.atomic.AtomicInteger();
    private final java.util.concurrent.atomic.AtomicReference<String> activeCameraRequestId=new java.util.concurrent.atomic.AtomicReference<>("");
    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private AlertDialog activeCameraDialog = null;
    private Runnable activeCameraTimeout = null;
    private static final class PendingCameraRequest {
        final String requestId;
        final String uploadUrl;
        final String mode;
        final String visionToken;
        final int navEpoch;
        PendingCameraRequest(String requestId, String uploadUrl, String mode, String visionToken, int navEpoch) {
            this.requestId = requestId;
            this.uploadUrl = uploadUrl;
            this.mode = mode;
            this.visionToken = visionToken;
            this.navEpoch = navEpoch;
        }
    }
    private volatile PendingCameraRequest pendingOsCameraRequest = null;
    private volatile boolean awaitingOsCameraPermission = false;
    private volatile int discoveryRetryCount = 0;
    private volatile int consecutiveHealthFailures = 0;
    private ConnectivityManager connectivityManager = null;
    private ConnectivityManager.NetworkCallback networkCallback = null;
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
        frontCameraBridge = new FrontCameraBridge(this, webView);
        initWebSettings();
        webView.loadUrl(OFFLINE);
        registerNetworkCallback();
        autoDiscoverAndConnect(false);
        scheduleHealthCheck(8000L);
    }

    private void registerNetworkCallback() {
        try {
            connectivityManager = (ConnectivityManager) getSystemService(CONNECTIVITY_SERVICE);
            if (connectivityManager == null) return;
            NetworkRequest req = new NetworkRequest.Builder()
                .addTransportType(NetworkCapabilities.TRANSPORT_WIFI)
                .build();
            networkCallback = new ConnectivityManager.NetworkCallback() {
                @Override public void onAvailable(Network network) {
                    if (destroyed) return;
                    discoveryRetryCount = 0;
                    consecutiveHealthFailures = 0;
                    mainHandler.post(() -> {
                        if (!destroyed && !isFinishing() && !backgrounded) {
                            autoDiscoverAndConnect(false);
                        }
                    });
                }
                @Override public void onLost(Network network) {
                    if (destroyed) return;
                    consecutiveHealthFailures = 0;
                    mainHandler.post(() -> {
                        if (!destroyed && !isFinishing() && !backgrounded) {
                            scheduleDiscoveryRetry(1200L);
                        }
                    });
                }
            };
            connectivityManager.registerNetworkCallback(req, networkCallback);
        } catch (Exception ignored) {}
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
                cancelPendingCameraRequest("navigation");
                if (frontCameraBridge != null) frontCameraBridge.stop();
                if(bridgeTrusted)releaseDeviceInput();
                bridgeTrusted=false;bridgeEpoch.incrementAndGet();pageNavigationEpoch.incrementAndGet();udpClient.interrupt();readClient.interrupt();
                mainFrameUrl = url != null ? url : "";
                mainFrameOrigin = extractOrigin(url);
                if (!isPageAuthenticated(view)) {
                    purgeCookiesAndStorage();
                }
                if (url != null && !isOfflinePage(url)) {
                    String curOrig = mainFrameOrigin;
                    if (!curOrig.equalsIgnoreCase(cameraAuthorizedOrigin)) {
                        cameraAuthorizedOrigin = "";
                    }
                } else {
                    cameraAuthorizedOrigin = "";
                }
                super.onPageStarted(view,url,favicon);
            }
            @Override public void onPageFinished(WebView view,String url) {
                mainFrameUrl = url != null ? url : "";
                mainFrameOrigin = extractOrigin(url);
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

    private static String extractOrigin(String rawUrl) {
        if (rawUrl == null || rawUrl.trim().isEmpty() || rawUrl.startsWith("file:")) return "";
        try {
            Uri uri = Uri.parse(rawUrl.trim());
            if (uri.getScheme() == null || uri.getEncodedAuthority() == null) return "";
            return new Uri.Builder().scheme(uri.getScheme()).encodedAuthority(uri.getEncodedAuthority()).build().toString();
        } catch (Exception ignored) {
            return "";
        }
    }

    private static boolean verifyServerHealth(String candidateUrl) {
        if (candidateUrl == null || candidateUrl.trim().isEmpty()) return false;
        java.net.HttpURLConnection conn = null;
        try {
            java.net.URL healthUrl = new java.net.URL(candidateUrl.replaceAll("/+$", "") + "/api/health");
            conn = (java.net.HttpURLConnection) healthUrl.openConnection();
            conn.setInstanceFollowRedirects(false);
            conn.setConnectTimeout(800);
            conn.setReadTimeout(800);
            conn.setRequestMethod("GET");
            if (conn.getResponseCode() != 200) return false;
            try (java.io.InputStream in = conn.getInputStream();
                 java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream()) {
                long deadlineRead = System.nanoTime() + 800_000_000L;
                byte[] buf = new byte[256];
                int r;
                while ((r = in.read(buf)) != -1) {
                    if (System.nanoTime() >= deadlineRead) return false;
                    out.write(buf, 0, r);
                    if (out.size() > 16384) return false;
                }
                org.json.JSONObject obj = new org.json.JSONObject(out.toString("UTF-8"));
                return "ok".equals(obj.optString("status")) && "KurisuPro".equals(obj.optString("service"));
            }
        } catch (Exception e) {
            return false;
        } finally {
            if (conn != null) conn.disconnect();
        }
    }

    private final Runnable discoveryRetryRunnable = () -> {
        if (!destroyed && !isFinishing() && !backgrounded) {
            autoDiscoverAndConnect(false);
        }
    };

    private final Runnable healthCheckRunnable = () -> {
        if (destroyed || isFinishing() || backgrounded) return;
        final String curOrigin = serverOrigin;
        if (curOrigin != null && !curOrigin.isEmpty()) {
            new Thread(() -> {
                if (destroyed) return;
                boolean ok = verifyServerHealth(curOrigin);
                mainHandler.post(() -> {
                    if (destroyed || isFinishing() || backgrounded) return;
                    if (!curOrigin.equals(serverOrigin)) return;
                    if (ok) {
                        consecutiveHealthFailures = 0;
                        discoveryRetryCount = 0;
                    } else {
                        consecutiveHealthFailures++;
                        if (consecutiveHealthFailures >= 2) {
                            consecutiveHealthFailures = 0;
                            serverOrigin = "";
                            authenticatedOrigin = "";
                            cameraAuthorizedOrigin = "";
                            if (frontCameraBridge != null) frontCameraBridge.stop();
                            autoDiscoverAndConnect(false);
                        }
                    }
                    scheduleHealthCheck(12000L);
                });
            }).start();
        } else {
            scheduleHealthCheck(12000L);
        }
    };

    private void scheduleDiscoveryRetry(long delayMs) {
        if (destroyed || isFinishing() || backgrounded) return;
        mainHandler.removeCallbacks(discoveryRetryRunnable);
        mainHandler.postDelayed(discoveryRetryRunnable, delayMs);
    }

    private void scheduleHealthCheck(long delayMs) {
        if (destroyed || isFinishing() || backgrounded) return;
        mainHandler.removeCallbacks(healthCheckRunnable);
        mainHandler.postDelayed(healthCheckRunnable, delayMs);
    }

    private void cancelPendingCameraRequest(String reason) {
        final String cancelledId = activeCameraRequestId.getAndSet("");
        awaitingOsCameraPermission = false;
        pendingOsCameraRequest = null;
        mainHandler.post(() -> {
            if (activeCameraTimeout != null) {
                mainHandler.removeCallbacks(activeCameraTimeout);
                activeCameraTimeout = null;
            }
            if (activeCameraDialog != null) {
                try { activeCameraDialog.dismiss(); } catch (Exception ignored) {}
                activeCameraDialog = null;
            }
            if (cancelledId != null && !cancelledId.isEmpty() && webView != null && !destroyed) {
                emitCameraStatusJson(cancelledId, "cancelled", reason, "", 0L);
            }
        });
    }

    private void emitCameraStatusJson(String requestId, String status, String reason, String sessionId, long epoch) {
        if (destroyed || webView == null) return;
        try {
            org.json.JSONObject obj = new org.json.JSONObject();
            obj.put("request_id", requestId != null ? requestId : "");
            obj.put("status", status != null ? status : "failed");
            if (reason != null && !reason.isEmpty()) obj.put("reason", reason);
            if (sessionId != null && !sessionId.isEmpty()) obj.put("session_id", sessionId);
            if (epoch > 0) obj.put("epoch", epoch);
            final String js = "if(window.onNativeCameraStatus)window.onNativeCameraStatus(" + obj.toString() + ");";
            mainHandler.post(() -> {
                if (!destroyed && webView != null) {
                    webView.evaluateJavascript(js, null);
                }
            });
        } catch (Exception ignored) {}
    }

    private void applyDiscoveredEndpoints(final String sUrl, final String bIp, final boolean manual) {
        mainHandler.post(() -> {
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
                candidateOrigin = sUrl;
                boolean alreadySameOrigin = sUrl.equalsIgnoreCase(serverOrigin) && sUrl.equalsIgnoreCase(mainFrameOrigin);
                serverOrigin = sUrl;
                consecutiveHealthFailures = 0;
                discoveryRetryCount = 0;
                ed.putString("server_url", sUrl + "/").apply();
                String curUrl = webView != null ? webView.getUrl() : null;
                if (!alreadySameOrigin && (curUrl == null || curUrl.equals(OFFLINE) || !sUrl.equalsIgnoreCase(extractOrigin(curUrl)))) {
                    Toast.makeText(MainActivity.this, "已连接电脑服务 (" + sUrl + ")", Toast.LENGTH_SHORT).show();
                    if (webView != null) webView.loadUrl(sUrl + "/");
                }
            } else if (BridgePolicy.privateIpv4(finalBoardIp)) {
                ed.apply();
                String curUrl = webView != null ? webView.getUrl() : null;
                if (curUrl == null || (!isOfflinePage(curUrl) && (serverOrigin == null || serverOrigin.isEmpty()))) {
                    Toast.makeText(MainActivity.this, "已自动直连灯板 (" + finalBoardIp + ")", Toast.LENGTH_SHORT).show();
                    if (webView != null) webView.loadUrl(OFFLINE);
                }
                if (!backgrounded && discoveryRetryCount < 8) {
                    long backoff = Math.min(30000L, 2000L << Math.min(discoveryRetryCount, 4));
                    discoveryRetryCount++;
                    scheduleDiscoveryRetry(backoff);
                }
            } else {
                ed.apply();
                if (!backgrounded && discoveryRetryCount < 8) {
                    long backoff = Math.min(30000L, 2000L << Math.min(discoveryRetryCount, 4));
                    discoveryRetryCount++;
                    scheduleDiscoveryRetry(backoff);
                }
                if (manual) {
                    Toast.makeText(MainActivity.this, "未发现同一局域网下的服务，请确认手机与设备在同一热点/Wi-Fi", Toast.LENGTH_LONG).show();
                    discoverServer();
                }
            }
        });
    }

    private void autoDiscoverAndConnect(final boolean manual) {
        if (discovering || destroyed || isFinishing()) return;
        discovering = true;
        final int myGen = discoveryGen.incrementAndGet();
        if (manual) {
            discoveryRetryCount = 0;
            Toast.makeText(this, "正在自动搜索局域网内的电脑服务与灯板…", Toast.LENGTH_SHORT).show();
        }
        new Thread(() -> {
            String foundServerUrl = null, foundBoardIp = null;
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
                while (System.nanoTime() < deadline && discoveryGen.get() == myGen) {
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
                if ((foundServerUrl == null || foundBoardIp == null) && discoveryGen.get() == myGen) {
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
                    while (System.nanoTime() < deadline && discoveryGen.get() == myGen) {
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

            if (foundServerUrl != null && !verifyServerHealth(foundServerUrl)) {
                foundServerUrl = null;
            }
            if (discoveryGen.get() != myGen) {
                discovering = false;
                return;
            }
            applyDiscoveredEndpoints(foundServerUrl, foundBoardIp, manual);
        }).start();
    }

    private void discoverServer() {
        autoDiscoverAndConnect(true);
        if (discovery != null || destroyed || isFinishing()) return;
        nsd = (NsdManager) getSystemService(NSD_SERVICE);
        if (nsd == null) return;
        discovery = new NsdManager.DiscoveryListener() {
            public void onDiscoveryStarted(String type) { runOnUiThread(() -> { if (!isFinishing() && !destroyed) Toast.makeText(MainActivity.this, "正在发现服务；也可手动输入地址", Toast.LENGTH_LONG).show(); }); }
            public void onServiceFound(NsdServiceInfo service) {
                if (destroyed || !service.getServiceName().startsWith("KurisuPro")) return;
                nsd.resolveService(service, new NsdManager.ResolveListener() {
                    public void onResolveFailed(NsdServiceInfo s, int code) {}
                    public void onServiceResolved(NsdServiceInfo s) {
                        if (destroyed || s.getHost() == null) return;
                        String host = s.getHost().getHostAddress();
                        if (!BridgePolicy.privateIpv4(host)) return;
                        final String url = "http://" + host + ":" + s.getPort();
                        new Thread(() -> {
                            if (destroyed || !verifyServerHealth(url)) return;
                            applyDiscoveredEndpoints(url, null, false);
                            mainHandler.post(() -> stopDiscovery());
                        }).start();
                    }
                });
            }
            public void onServiceLost(NsdServiceInfo s) {}
            public void onDiscoveryStopped(String type) { discovery=null; }
            public void onStartDiscoveryFailed(String type,int code) { stopDiscovery(); }
            public void onStopDiscoveryFailed(String type,int code) { discovery=null; }
        };
        nsd.discoverServices("_kurisupro._tcp.",NsdManager.PROTOCOL_DNS_SD,discovery);
        mainHandler.postDelayed(this::stopDiscovery,15000);
    }
    private void stopDiscovery() { NsdManager.DiscoveryListener current=discovery;discovery=null;if(nsd!=null&&current!=null)try{nsd.stopServiceDiscovery(current);}catch(IllegalArgumentException ignored){} }
    @Override protected void onPause() {
        if (!awaitingOsCameraPermission) {
            cancelPendingCameraRequest("backgrounded");
            if (frontCameraBridge != null) frontCameraBridge.stop();
        }
        backgrounded=true;releaseDeviceInput();
        mainHandler.removeCallbacks(discoveryRetryRunnable);
        mainHandler.removeCallbacks(healthCheckRunnable);
        stopDiscovery();
        if (webView != null) {
            webView.evaluateJavascript("window.dispatchEvent(new Event('blur'))",null);
            webView.onPause();
        }
        super.onPause();
    }
    @Override protected void onResume() {
        super.onResume();
        backgrounded=false;
        discoveryRetryCount = 0;
        if(webView!=null)webView.onResume();
        autoDiscoverAndConnect(false);
        scheduleHealthCheck(8000L);
    }
    @Override public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode != 102) {
            return;
        }
        awaitingOsCameraPermission = false;
        final PendingCameraRequest pending = pendingOsCameraRequest;
        pendingOsCameraRequest = null;
        if (pending == null || destroyed || isFinishing()) {
            return;
        }
        String sessId = "";
        try {
            sessId = pending.uploadUrl != null ? Uri.parse(pending.uploadUrl.trim()).getQueryParameter("session_id") : "";
        } catch (Exception ignored) {}
        final String reqSessId = sessId != null ? sessId : "";
        boolean granted = grantResults != null && grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED;
        if (!granted) {
            if (activeCameraTimeout != null) {
                mainHandler.removeCallbacks(activeCameraTimeout);
                activeCameraTimeout = null;
            }
            activeCameraRequestId.compareAndSet(pending.requestId, "");
            emitCameraStatusJson(pending.requestId, "denied", "os_camera_permission_denied", reqSessId, 0L);
            return;
        }
        mainHandler.post(() -> {
            backgrounded = false;
            proceedWithFrontCameraAuthorization(pending.requestId, pending.uploadUrl, pending.mode, pending.visionToken, pending.navEpoch);
        });
    }
    @Override protected void onDestroy() {
        cancelPendingCameraRequest("destroyed");
        if (frontCameraBridge != null) frontCameraBridge.stop();
        releaseDeviceInput();
        destroyed=true;
        bridgeTrusted=false;
        mainHandler.removeCallbacksAndMessages(null);
        if (connectivityManager != null && networkCallback != null) {
            try { connectivityManager.unregisterNetworkCallback(networkCallback); } catch (Exception ignored) {}
            networkCallback = null;
        }
        udpExecutor.shutdown();readExecutor.shutdownNow();stopDiscovery();
        if(fileCallback!=null)fileCallback.onReceiveValue(null);
        if(webView!=null)webView.destroy();
        super.onDestroy();
    }
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
    private boolean validateUploadTarget(String uploadUrl, String expectedOrigin) {
        if (uploadUrl == null || uploadUrl.trim().isEmpty() || expectedOrigin == null || expectedOrigin.isEmpty()) return false;
        try {
            Uri parsed = Uri.parse(uploadUrl.trim());
            if (!("http".equalsIgnoreCase(parsed.getScheme()) || "https".equalsIgnoreCase(parsed.getScheme()))) return false;
            String host = parsed.getHost();
            int port = parsed.getPort() != -1 ? parsed.getPort() : ("https".equalsIgnoreCase(parsed.getScheme()) ? 443 : 80);
            Uri authUri = Uri.parse(expectedOrigin);
            String authHost = authUri.getHost();
            int authPort = authUri.getPort() != -1 ? authUri.getPort() : ("https".equalsIgnoreCase(authUri.getScheme()) ? 443 : 80);
            if (host == null || !host.equalsIgnoreCase(authHost) || port != authPort) return false;
            String path = parsed.getPath();
            if (path == null || !(path.equals("/api/vision/phone_frame") || path.equals("/api/pro/vision/frame") || path.equals("/api/pro/camera/frame"))) {
                return false;
            }
            String sessionId = parsed.getQueryParameter("session_id");
            return sessionId != null && !sessionId.trim().isEmpty();
        } catch (Exception e) {
            return false;
        }
    }

    private void proceedWithFrontCameraAuthorization(final String requestId, final String uploadUrl, final String mode, final String visionToken, final int startNavEpoch) {
            if (destroyed || isFinishing() || backgrounded || !requestId.equals(activeCameraRequestId.get()) || pageNavigationEpoch.get() != startNavEpoch) {
                emitCameraStatusJson(requestId, "cancelled", "stale_lifecycle", "", 0L);
                return;
            }
            // WebView.getUrl() MUST only be accessed on the UI / WebView thread.
            String curUrl = webView != null ? webView.getUrl() : null;
            if (curUrl == null || isOfflinePage(curUrl)) {
                activeCameraRequestId.compareAndSet(requestId, "");
                emitCameraStatusJson(requestId, "failed", "offline_or_untrusted_page", "", 0L);
                return;
            }
            final String curOrigin = extractOrigin(curUrl);
            if (serverOrigin == null || serverOrigin.isEmpty() || !serverOrigin.equalsIgnoreCase(curOrigin) || !BridgePolicy.privateIpv4(Uri.parse(curUrl).getHost())) {
                activeCameraRequestId.compareAndSet(requestId, "");
                emitCameraStatusJson(requestId, "denied", "origin_mismatch", "", 0L);
                return;
            }
            if (!validateUploadTarget(uploadUrl, curOrigin)) {
                activeCameraRequestId.compareAndSet(requestId, "");
                emitCameraStatusJson(requestId, "denied", "invalid_upload_target", "", 0L);
                return;
            }
            final String reqSessId = Uri.parse(uploadUrl.trim()).getQueryParameter("session_id");
            if (isCameraAuthorized(curOrigin)) {
                if (activeCameraTimeout != null) {
                    mainHandler.removeCallbacks(activeCameraTimeout);
                    activeCameraTimeout = null;
                }
                activeCameraRequestId.compareAndSet(requestId, "");
                boolean ok = frontCameraBridge != null && frontCameraBridge.start(uploadUrl, mode, curOrigin, visionToken);
                emitCameraStatusJson(requestId, ok ? "started" : "failed", ok ? "" : "camera_open_failed", reqSessId, frontCameraBridge != null ? frontCameraBridge.getSessionEpoch() : 0L);
                return;
            }
            if (activeCameraDialog != null) {
                try { activeCameraDialog.dismiss(); } catch (Exception ignored) {}
                activeCameraDialog = null;
            }
            if (activeCameraTimeout != null) {
                mainHandler.removeCallbacks(activeCameraTimeout);
            }
            final Runnable timeoutTask = () -> {
                if (activeCameraRequestId.compareAndSet(requestId, "")) {
                    awaitingOsCameraPermission = false;
                    pendingOsCameraRequest = null;
                    if (activeCameraDialog != null) {
                        try { activeCameraDialog.dismiss(); } catch (Exception ignored) {}
                        activeCameraDialog = null;
                    }
                    emitCameraStatusJson(requestId, "timeout", "authorization_timeout", reqSessId, 0L);
                }
            };
            activeCameraTimeout = timeoutTask;
            mainHandler.postDelayed(timeoutTask, 30000L);
            activeCameraDialog = new AlertDialog.Builder(MainActivity.this)
                .setTitle("摄像头权限申请")
                .setMessage("网页 (" + curOrigin + ") 申请使用摄像头进行体感与视觉交互。\n\n是否允许？")
                .setPositiveButton("允许", (d, w) -> {
                    mainHandler.removeCallbacks(timeoutTask);
                    activeCameraDialog = null;
                    if (!activeCameraRequestId.compareAndSet(requestId, "") || destroyed || isFinishing() || backgrounded || pageNavigationEpoch.get() != startNavEpoch) {
                        emitCameraStatusJson(requestId, "cancelled", "stale_lifecycle", reqSessId, 0L);
                        return;
                    }
                    cameraAuthorizedOrigin = curOrigin;
                    boolean ok = frontCameraBridge != null && frontCameraBridge.start(uploadUrl, mode, curOrigin, visionToken);
                    emitCameraStatusJson(requestId, ok ? "started" : "failed", ok ? "" : "camera_open_failed", reqSessId, frontCameraBridge != null ? frontCameraBridge.getSessionEpoch() : 0L);
                })
                .setNegativeButton("拒绝", (d, w) -> {
                    mainHandler.removeCallbacks(timeoutTask);
                    activeCameraDialog = null;
                    activeCameraRequestId.compareAndSet(requestId, "");
                    emitCameraStatusJson(requestId, "denied", "user_denied", reqSessId, 0L);
                })
                .setOnCancelListener(d -> {
                    mainHandler.removeCallbacks(timeoutTask);
                    activeCameraDialog = null;
                    activeCameraRequestId.compareAndSet(requestId, "");
                    emitCameraStatusJson(requestId, "denied", "user_cancelled", reqSessId, 0L);
                })
                .show();
    }

    public class NativeUdpBridge {
        @android.webkit.JavascriptInterface
        public boolean hasNativeCamera() {
            return true;
        }

        @android.webkit.JavascriptInterface
        public String requestFrontCamera(final String requestId, final String uploadUrl, final String mode, final String visionToken) {
            if (!BridgePolicy.requestId(requestId) || backgrounded || destroyed) {
                emitCameraStatusJson(requestId, "failed", "unavailable", "", 0L);
                return "{\"status\":\"failed\",\"reason\":\"unavailable\"}";
            }
            activeCameraRequestId.set(requestId);
            final int startNavEpoch = pageNavigationEpoch.get();
            if (android.os.Build.VERSION.SDK_INT >= 23 && checkSelfPermission(android.Manifest.permission.CAMERA) != android.content.pm.PackageManager.PERMISSION_GRANTED) {
                pendingOsCameraRequest = new PendingCameraRequest(requestId, uploadUrl, mode, visionToken, startNavEpoch);
                awaitingOsCameraPermission = true;
                mainHandler.post(() -> {
                    if (destroyed || isFinishing() || !requestId.equals(activeCameraRequestId.get()) || pageNavigationEpoch.get() != startNavEpoch) {
                        awaitingOsCameraPermission = false;
                        pendingOsCameraRequest = null;
                        emitCameraStatusJson(requestId, "cancelled", "stale_lifecycle", "", 0L);
                        return;
                    }
                    requestPermissions(new String[]{android.Manifest.permission.CAMERA}, 102);
                });
                return "{\"status\":\"pending\",\"request_id\":" + org.json.JSONObject.quote(requestId) + "}";
            }
            mainHandler.post(() -> proceedWithFrontCameraAuthorization(requestId, uploadUrl, mode, visionToken, startNavEpoch));
            return "{\"status\":\"pending\",\"request_id\":" + org.json.JSONObject.quote(requestId) + "}";
        }

        @android.webkit.JavascriptInterface
        public boolean startFrontCamera(final String uploadUrl, final String mode) {
            if (backgrounded || destroyed) return false;
            final String curOrigin = mainFrameOrigin;
            if (curOrigin == null || curOrigin.isEmpty()) return false;
            if (serverOrigin == null || serverOrigin.isEmpty() || !serverOrigin.equalsIgnoreCase(curOrigin)) {
                return false;
            }
            if (android.os.Build.VERSION.SDK_INT >= 23 && checkSelfPermission(android.Manifest.permission.CAMERA) != android.content.pm.PackageManager.PERMISSION_GRANTED) {
                return false;
            }
            if (!validateUploadTarget(uploadUrl, curOrigin)) {
                return false;
            }
            if (!isCameraAuthorized(curOrigin)) {
                // Non-blocking fallback: trigger async dialog cleanly instead of blocking JavaBridge thread.
                requestFrontCamera("legacy_" + System.currentTimeMillis(), uploadUrl, mode, "");
                return false;
            }
            return frontCameraBridge != null && frontCameraBridge.start(uploadUrl, mode, curOrigin, "");
        }

        @android.webkit.JavascriptInterface
        public void stopFrontCamera() {
            cancelPendingCameraRequest("stopped");
            if (frontCameraBridge != null) {
                frontCameraBridge.stop();
            }
        }

        @android.webkit.JavascriptInterface
        public void stopFrontCamera(final String sessionId) {
            cancelPendingCameraRequest("stopped");
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
