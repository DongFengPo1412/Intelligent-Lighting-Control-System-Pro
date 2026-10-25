package org.fglab.kurisu;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
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
    private String serverOrigin = "";
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
        initWebSettings();
        String saved = getSharedPreferences("config", MODE_PRIVATE).getString("server_url", "");
        if (saved.isEmpty()) { webView.loadUrl(OFFLINE); configureServer(); }
        else connectServer(saved);
    }

    private void connectServer(String value) {
        Uri uri = Uri.parse(value.trim());
        if (!("http".equals(uri.getScheme()) || "https".equals(uri.getScheme())) || uri.getHost() == null || uri.getUserInfo() != null) {
            Toast.makeText(this, "请输入完整的 HTTP(S) 服务地址", Toast.LENGTH_LONG).show();
            if (serverOrigin.isEmpty()) webView.loadUrl(OFFLINE);
            return;
        }
        serverOrigin = new Uri.Builder().scheme(uri.getScheme()).encodedAuthority(uri.getEncodedAuthority()).build().toString();
        getSharedPreferences("config", MODE_PRIVATE).edit().putString("server_url", serverOrigin + "/").apply();
        webView.loadUrl(serverOrigin + "/");
    }

    private void configureServer() {
        EditText input = new EditText(this);
        input.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_VARIATION_URI);
        input.setSingleLine(true);
        input.setText(getSharedPreferences("config", MODE_PRIVATE).getString("server_url", ""));
        input.setHint("http://电脑局域网IP:8080");
        new AlertDialog.Builder(this).setTitle("连接光影实验室").setMessage("手机需能访问运行服务的电脑。")
            .setView(input).setPositiveButton("连接", (d,w) -> connectServer(input.getText().toString()))
            .setNeutralButton("发现服务", (d,w) -> discoverServer()).setNegativeButton("取消", null).show();
    }

    private boolean trustedPage(WebView view) {
        String current = view.getUrl();
        if (current == null) return false;
        if (current.startsWith(OFFLINE)) return true;
        Uri uri = Uri.parse(current);
        String origin = new Uri.Builder().scheme(uri.getScheme()).encodedAuthority(uri.getEncodedAuthority()).build().toString();
        return !serverOrigin.isEmpty() && serverOrigin.equals(origin);
    }

    private boolean navigate(WebView view, Uri uri) {
        if ("amadeus".equals(uri.getScheme())) {
            if (!trustedPage(view)) return true;
            if ("settings".equals(uri.getHost())) configureServer();
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
        if ("file".equals(uri.getScheme())) return !uri.toString().startsWith(OFFLINE);
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
        s.setAllowFileAccess(true);
        s.setAllowContentAccess(true);
        s.setAllowFileAccessFromFileURLs(false);
        s.setAllowUniversalAccessFromFileURLs(false);
        s.setMediaPlaybackRequiresUserGesture(true);
        s.setUseWideViewPort(true);
        s.setLoadWithOverviewMode(true);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        s.setUserAgentString(s.getUserAgentString() + " AmadeusAndroid/1.1");
        webView.setBackgroundColor(0xff111316);
        webView.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                return request.isForMainFrame() && navigate(view, request.getUrl());
            }
            @Override public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame() && !request.getUrl().toString().startsWith("file:")) {
                    Toast.makeText(MainActivity.this, "电脑服务暂不可达，请检查连接设置", Toast.LENGTH_LONG).show();
                    view.loadUrl(OFFLINE);
                }
            }
        });
        webView.setWebChromeClient(new WebChromeClient() {
            @Override public void onPermissionRequest(PermissionRequest request) { runOnUiThread(request::deny); }
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

    private void discoverServer() {
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
                        runOnUiThread(() -> { if (!isFinishing()) new AlertDialog.Builder(MainActivity.this).setTitle("发现光影实验室")
                            .setMessage(url).setPositiveButton("连接",(d,w)->connectServer(url)).setNegativeButton("取消",null).show(); });
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
    @Override protected void onPause() { webView.onPause();super.onPause(); }
    @Override protected void onResume() { super.onResume();if(webView!=null)webView.onResume(); }
    @Override protected void onDestroy() { stopDiscovery();if(fileCallback!=null)fileCallback.onReceiveValue(null);if(webView!=null)webView.destroy();super.onDestroy(); }
    @Override public void onBackPressed() { if(webView.canGoBack())webView.goBack();else super.onBackPressed(); }
}
