package org.fglab.kurisu;

import android.app.Activity;
import android.os.Bundle;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.webkit.PermissionRequest;
import android.view.KeyEvent;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.widget.Toast;
import android.content.SharedPreferences;
import android.app.AlertDialog;
import android.widget.EditText;
import android.widget.Button;
import android.widget.FrameLayout;
import android.view.Gravity;
import android.net.nsd.NsdManager;
import android.net.nsd.NsdServiceInfo;
import android.net.Uri;

public class MainActivity extends Activity {
    private WebView webView;
    private static final String DEFAULT_HOST = "";
    private NsdManager nsd;
    private NsdManager.DiscoveryListener discovery;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // 全屏沉浸式无边框
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        getWindow().setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN,
                WindowManager.LayoutParams.FLAG_FULLSCREEN);

        setContentView(R.layout.activity_main);

        webView = findViewById(R.id.webView);
        initWebSettings();

        // 默认加载局域网直连地址，若脱机则平滑降级至内置 assets 演示页
        SharedPreferences sp = getSharedPreferences("config", MODE_PRIVATE);
        String serverUrl = sp.getString("server_url", DEFAULT_HOST);

        Button settings = new Button(this);
        settings.setText("服务器");
        FrameLayout.LayoutParams position = new FrameLayout.LayoutParams(-2, -2, Gravity.TOP | Gravity.RIGHT);
        ((FrameLayout) webView.getParent()).addView(settings, position);
        settings.setOnClickListener(v -> configureServer());
        if (serverUrl.isEmpty()) configureServer(); else webView.loadUrl(serverUrl);
    }

    private void connectServer(String value) {
        Uri uri = Uri.parse(value.trim());
        if (!("http".equals(uri.getScheme()) || "https".equals(uri.getScheme())) || uri.getHost() == null) {
            Toast.makeText(this, "请输入完整的 http(s) 服务器地址", Toast.LENGTH_LONG).show(); return;
        }
        String url = new Uri.Builder().scheme(uri.getScheme()).encodedAuthority(uri.getEncodedAuthority()).path("/pro.html").build().toString();
        getSharedPreferences("config", MODE_PRIVATE).edit().putString("server_url", url).apply();
        webView.loadUrl(url);
    }

    private void configureServer() {
        EditText input = new EditText(this);
        String saved = getSharedPreferences("config", MODE_PRIVATE).getString("server_url", "");
        input.setText(saved.replaceAll("/pro.html$", ""));
        input.setHint("http://电脑局域网IP:8080");
        new AlertDialog.Builder(this).setTitle("连接 Pro 服务（同一局域网）").setView(input)
            .setPositiveButton("连接", (d,w) -> connectServer(input.getText().toString()))
            .setNeutralButton("发现服务", (d,w) -> discoverServer()).setNegativeButton("取消", null).show();
    }

    private void discoverServer() {
        if (discovery != null) return;
        nsd = (NsdManager) getSystemService(NSD_SERVICE);
        discovery = new NsdManager.DiscoveryListener() {
            public void onDiscoveryStarted(String t) { runOnUiThread(() -> Toast.makeText(MainActivity.this, "发现中；找不到时请手动输入地址", Toast.LENGTH_LONG).show()); }
            public void onServiceFound(NsdServiceInfo service) {
                if (!service.getServiceName().startsWith("KurisuPro")) return;
                nsd.resolveService(service, new NsdManager.ResolveListener() {
                    public void onResolveFailed(NsdServiceInfo s, int code) {}
                    public void onServiceResolved(NsdServiceInfo s) {
                        String host = s.getHost().getHostAddress();
                        if (host.indexOf(':') >= 0) host = "[" + host + "]";
                        final String url = "http://" + host + ":" + s.getPort();
                        runOnUiThread(() -> new AlertDialog.Builder(MainActivity.this).setTitle("发现 Pro 服务")
                            .setMessage(url).setPositiveButton("连接", (d,w) -> connectServer(url)).setNegativeButton("取消", null).show());
                        stopDiscovery();
                    }
                });
            }
            public void onServiceLost(NsdServiceInfo s) {}
            public void onDiscoveryStopped(String t) { discovery = null; }
            public void onStartDiscoveryFailed(String t, int code) { stopDiscovery(); }
            public void onStopDiscoveryFailed(String t, int code) { discovery = null; }
        };
        nsd.discoverServices("_kurisupro._tcp.", NsdManager.PROTOCOL_DNS_SD, discovery);
        webView.postDelayed(() -> stopDiscovery(), 15000);
    }

    private void stopDiscovery() {
        NsdManager.DiscoveryListener listener = discovery; discovery = null;
        if (nsd != null && listener != null) try { nsd.stopServiceDiscovery(listener); } catch (IllegalArgumentException ignored) {}
    }

    @Override protected void onDestroy() { stopDiscovery(); if (webView != null) webView.destroy(); super.onDestroy(); }

    private void initWebSettings() {
        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setAllowFileAccess(true);
        s.setAllowContentAccess(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setUseWideViewPort(true);
        s.setLoadWithOverviewMode(true);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public void onReceivedError(WebView view, int errorCode, String description, String failingUrl) {
                // 网络连接受阻时，加载打包在本地 APK 内部的离线兜底 UI
                if (!failingUrl.startsWith("file:///android_asset/")) {
                    Toast.makeText(MainActivity.this, "未能连接局域网主机，已自动切换为本地离线模式", Toast.LENGTH_SHORT).show();
                    view.loadData("<h2>无法连接 Pro 服务</h2><p>点击右上角服务器设置，检查电脑 IP、端口与局域网连接。离线时无法控制灯板。</p>", "text/html; charset=utf-8", "UTF-8");
                }
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(final PermissionRequest request) {
                // 自动授权麦克风与声学媒体采集权限，确保 Web Speech 正常录音
                runOnUiThread(() -> request.deny()); // Voice input is owned by the PC/ESP32 service.
            }
        });
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_BACK && webView.canGoBack()) {
            webView.goBack();
            return true;
        }
        return super.onKeyDown(keyCode, event);
    }
}
