# Android host

There is one frontend source: `../pc-agent-vision/web_app/`. `build_apk.py` copies it into the APK at build time; do not maintain another `assets/www` source tree. `/pro.html` is a compatibility redirect to `/`.

The native host provides saved server selection, DNS-SD discovery, system insets, explicit file selection and canvas export. Voice and camera processing remain on the PC / ESP32. The app requests no phone camera or microphone permission. A bundled offline shell is clearly disconnected and does not simulate an online board.

Build a debug APK outside the repository:

```powershell
python -B android-app/build_apk.py `
  --work-dir "$env:USERPROFILE\.codex\cache\tasks\YOUR-TASK\android-build" `
  --output "$env:USERPROFILE\.codex\artifacts\YOUR-TASK\Amadeus-debug.apk" `
  --build-tools "PATH-TO-ANDROID-BUILD-TOOLS"
```

Requires JDK 17, Android SDK platform 35, `tools/aapt2.exe`, `tools/r8.jar`, Build Tools `zipalign.exe` and `lib/apksigner.jar`. Private SDK tools and build outputs are not committed. Each build currently creates a disposable debug signing key: updating an existing installation signed by a different key requires uninstalling it first (which clears app preferences), or building with the original signing setup. This is not a production release signing workflow. Use a current Android System WebView (Chromium 105+); OS minimum 24 alone does not guarantee support for modern web APIs.

The old tracked v1.0 APKs are historical artifacts; they are not automatically updated by source changes and are not linked from the unified frontend. New APKs are delivered outside the repository. Compilation and signature verification do not establish physical phone acceptance.
