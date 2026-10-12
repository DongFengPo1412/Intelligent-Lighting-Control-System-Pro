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

public class MainActivity extends Activity {
    private WebView webView;
    private static final String DEFAULT_HOST = "http://192.168.0.181:8080/";

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

        webView.loadUrl(serverUrl);
    }

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
                    view.loadUrl("file:///android_asset/www/index.html");
                }
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(final PermissionRequest request) {
                // 自动授权麦克风与声学媒体采集权限，确保 Web Speech 正常录音
                runOnUiThread(() -> request.grant(request.getResources()));
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
