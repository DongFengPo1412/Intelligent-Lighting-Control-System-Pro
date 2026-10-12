"""
Android APK 构建工具箱: 未来道具研究所 · 牧濑红莉栖具身交互客户端
无需安装庞大臃肿的完整 Android Studio，直接利用 OpenJDK 17 + aapt2 + D8
全自动化编译生成经过数字签名的 release APK 安装包
"""

import os
import sys
import shutil
import subprocess
import zipfile

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from PIL import Image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.join(BASE_DIR, "tools")
JAVA_HOME = r"E:\Android\openjdk\jdk-17.0.12"
ANDROID_JAR = r"E:\Android\android-sdk\platforms\android-35\android.jar"

AAPT2 = os.path.join(TOOLS_DIR, "aapt2.exe")
R8_JAR = os.path.join(TOOLS_DIR, "r8.jar")
JAVAC = os.path.join(JAVA_HOME, "bin", "javac.exe")
KEYTOOL = os.path.join(JAVA_HOME, "bin", "keytool.exe")
JARSIGNER = os.path.join(JAVA_HOME, "bin", "jarsigner.exe")
JAVA = os.path.join(JAVA_HOME, "bin", "java.exe")

SRC_DIR = os.path.join(BASE_DIR, "src")
RES_DIR = os.path.join(BASE_DIR, "res")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
BIN_DIR = os.path.join(BASE_DIR, "bin")
GEN_DIR = os.path.join(BASE_DIR, "gen")
OUTPUT_APK = os.path.join(BASE_DIR, "Kurisu_Amadeus_v1.0.apk")

PACKAGE_NAME = "org.fglab.kurisu"

def run_cmd(cmd_list, desc=""):
    print(f"\n[执行步骤] {desc}...")
    cmd_str = " ".join([f'"{c}"' if " " in c else c for c in cmd_list])
    res = subprocess.run(cmd_str, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"❌ 失败: {desc}")
        print("STDOUT:", res.stdout)
        print("STDERR:", res.stderr)
        sys.exit(1)
    else:
        print(f"✓ 成功: {desc}")
    return res

def setup_project():
    os.makedirs(SRC_DIR, exist_ok=True)
    os.makedirs(RES_DIR, exist_ok=True)
    os.makedirs(ASSETS_DIR, exist_ok=True)
    os.makedirs(BIN_DIR, exist_ok=True)
    os.makedirs(GEN_DIR, exist_ok=True)

    # 1. 复制 Web 资源到 assets/www (排除自身递归的 apk)
    www_dir = os.path.join(ASSETS_DIR, "www")
    if os.path.exists(www_dir):
        shutil.rmtree(www_dir)
    web_src = os.path.join(os.path.dirname(BASE_DIR), "pc-agent-vision", "web_app")
    shutil.copytree(web_src, www_dir, ignore=shutil.ignore_patterns("*.apk"))
    print("✓ Web 核心资源已嵌入 assets/www")

    # 2. 生成多分辨率高清图标
    icon_src = os.path.join(web_src, "assets", "icon.png")
    if os.path.exists(icon_src):
        icon_img = Image.open(icon_src)
        mipmap_configs = [
            ("mipmap-mdpi", 48),
            ("mipmap-hdpi", 72),
            ("mipmap-xhdpi", 96),
            ("mipmap-xxhdpi", 144),
            ("mipmap-xxxhdpi", 192)
        ]
        for folder, sz in mipmap_configs:
            f_path = os.path.join(RES_DIR, folder)
            os.makedirs(f_path, exist_ok=True)
            resized = icon_img.resize((sz, sz), Image.Resampling.LANCZOS)
            resized.save(os.path.join(f_path, "ic_launcher.png"))
            resized.save(os.path.join(f_path, "ic_launcher_round.png"))
        print("✓ Android 各级高清应用图标已生成完毕")

    # 3. 准备 res/values
    val_dir = os.path.join(RES_DIR, "values")
    os.makedirs(val_dir, exist_ok=True)

    with open(os.path.join(val_dir, "strings.xml"), "w", encoding="utf-8") as f:
        f.write('''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">牧濑红莉栖 · 具身交互中枢</string>
</resources>''')

    with open(os.path.join(val_dir, "styles.xml"), "w", encoding="utf-8") as f:
        f.write('''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <style name="AppTheme" parent="android:Theme.Material.NoActionBar.Fullscreen">
        <item name="android:windowBackground">#060a0f</item>
        <item name="android:statusBarColor">#060a0f</item>
        <item name="android:navigationBarColor">#060a0f</item>
    </style>
</resources>''')

    # 4. 准备 res/layout/activity_main.xml
    layout_dir = os.path.join(RES_DIR, "layout")
    os.makedirs(layout_dir, exist_ok=True)
    with open(os.path.join(layout_dir, "activity_main.xml"), "w", encoding="utf-8") as f:
        f.write('''<?xml version="1.0" encoding="utf-8"?>
<FrameLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:background="#060a0f">

    <WebView
        android:id="@+id/webView"
        android:layout_width="match_parent"
        android:layout_height="match_parent" />

</FrameLayout>''')

    # 5. 准备 AndroidManifest.xml
    manifest_path = os.path.join(BASE_DIR, "AndroidManifest.xml")
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(f'''<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="{PACKAGE_NAME}"
    android:versionCode="1"
    android:versionName="1.0.0">

    <uses-sdk android:minSdkVersion="24" android:targetSdkVersion="35" />

    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
    <uses-permission android:name="android.permission.ACCESS_WIFI_STATE" />
    <uses-permission android:name="android.permission.RECORD_AUDIO" />
    <uses-permission android:name="android.permission.MODIFY_AUDIO_SETTINGS" />
    <uses-permission android:name="android.permission.VIBRATE" />

    <application
        android:label="@string/app_name"
        android:icon="@mipmap/ic_launcher"
        android:roundIcon="@mipmap/ic_launcher_round"
        android:theme="@style/AppTheme"
        android:usesCleartextTraffic="true"
        android:hardwareAccelerated="true">

        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:configChanges="orientation|screenSize|keyboardHidden"
            android:windowSoftInputMode="adjustResize">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>''')

    # 6. 编写原生 Java 主逻辑
    pkg_dir = os.path.join(SRC_DIR, "org", "fglab", "kurisu")
    os.makedirs(pkg_dir, exist_ok=True)
    java_file = os.path.join(pkg_dir, "MainActivity.java")
    with open(java_file, "w", encoding="utf-8") as f:
        f.write('''package org.fglab.kurisu;

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
''')
    print("✓ Android 源码与配置文件生成完毕")

def build_apk():
    # 步骤 1: 编译 Android 资源
    compiled_res = os.path.join(BIN_DIR, "compiled_res.zip")
    run_cmd([AAPT2, "compile", "--dir", RES_DIR, "-o", compiled_res], "AAPT2 编译资源")

    # 步骤 2: 链接资源，生成 R.java 与基础 base.apk
    manifest_path = os.path.join(BASE_DIR, "AndroidManifest.xml")
    base_apk = os.path.join(BIN_DIR, "base.apk")
    run_cmd([
        AAPT2, "link",
        "-I", ANDROID_JAR,
        "-A", ASSETS_DIR,
        "--manifest", manifest_path,
        "-o", base_apk,
        "--java", GEN_DIR,
        "--auto-add-overlay",
        compiled_res
    ], "AAPT2 资源链接与生成 R.java")

    # 步骤 3: 编译 Java 源码
    r_java = os.path.join(GEN_DIR, "org", "fglab", "kurisu", "R.java")
    main_java = os.path.join(SRC_DIR, "org", "fglab", "kurisu", "MainActivity.java")
    classes_dir = os.path.join(BIN_DIR, "classes")
    os.makedirs(classes_dir, exist_ok=True)

    run_cmd([
        JAVAC,
        "-encoding", "utf-8",
        "-cp", ANDROID_JAR,
        "-d", classes_dir,
        r_java, main_java
    ], "Javac 编译 Java 字节码")

    # 步骤 4: D8 编译成 classes.dex
    dex_dir = os.path.join(BIN_DIR, "dex")
    os.makedirs(dex_dir, exist_ok=True)
    class_files = []
    for root, _, files in os.walk(classes_dir):
        for f in files:
            if f.endswith(".class"):
                class_files.append(os.path.join(root, f))

    d8_cmd = [
        JAVA, "-cp", R8_JAR,
        "com.android.tools.r8.D8",
        "--lib", ANDROID_JAR,
        "--output", dex_dir
    ] + class_files
    run_cmd(d8_cmd, "D8 转换为 Android Dalvik DEX 字节码")

    # 步骤 5: 将 classes.dex 注入 base.apk
    dex_file = os.path.join(dex_dir, "classes.dex")
    unaligned_apk = os.path.join(BIN_DIR, "unaligned.apk")
    shutil.copyfile(base_apk, unaligned_apk)

    with zipfile.ZipFile(unaligned_apk, 'a') as z:
        z.write(dex_file, "classes.dex")
    print("✓ classes.dex 已成功注入 APK 归档")

    # 步骤 6: 生成签名密钥 (若不存在)
    keystore = os.path.join(BASE_DIR, "kurisu_release.keystore")
    if not os.path.exists(keystore):
        run_cmd([
            KEYTOOL, "-genkeypair", "-v",
            "-keystore", keystore,
            "-storepass", "steinsgate",
            "-keypass", "steinsgate",
            "-alias", "kurisu",
            "-keyalg", "RSA",
            "-keysize", "2048",
            "-validity", "10000",
            "-dname", "CN=MakiseKurisu, OU=FutureGadgetLab, O=Amadeus, L=Akihabara, ST=Tokyo, C=JP"
        ], "生成未来道具研究所专用数字证书")

    # 步骤 7: 对 APK 进行数字签名
    shutil.copyfile(unaligned_apk, OUTPUT_APK)
    run_cmd([
        JARSIGNER,
        "-keystore", keystore,
        "-storepass", "steinsgate",
        "-keypass", "steinsgate",
        OUTPUT_APK,
        "kurisu"
    ], "Jarsigner 签署 Android 发布包")

    size_mb = os.path.getsize(OUTPUT_APK) / (1024 * 1024)
    print("\n" + "="*60)
    print(f"🎉 牧濑红莉栖手机 APK 安装包构建大成功！")
    print(f"📦 输出路径: {OUTPUT_APK}")
    print(f"📊 文件大小: {size_mb:.2f} MB")
    print(f"📱 支持设备: Android 7.0 ~ Android 15 (API 24 - 35)")
    print("="*60 + "\n")

if __name__ == "__main__":
    setup_project()
    build_apk()
