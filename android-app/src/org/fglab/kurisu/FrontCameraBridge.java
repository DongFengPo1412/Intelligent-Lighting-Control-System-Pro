package org.fglab.kurisu;

import android.app.Activity;
import android.graphics.ImageFormat;
import android.graphics.Rect;
import android.graphics.SurfaceTexture;
import android.graphics.YuvImage;
import android.hardware.Camera;
import android.util.Base64;
import android.webkit.WebView;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Direct hardware front-camera bridge for Android APK.
 * Bypasses Chromium insecure-origin (HTTP) restrictions on getUserMedia,
 * allowing instant live preview and frame streaming to PC vision engine.
 */
public class FrontCameraBridge {
    private final Activity activity;
    private final WebView webView;
    private Camera mCamera;
    private SurfaceTexture mSurface;
    private volatile boolean mRunning = false;
    private volatile boolean mUploading = false;
    private volatile int mRotation = 90; // Default: 90 degrees clockwise as requested
    private volatile String mAuthorizedOrigin = null;
    private long lastFrameTime = 0;
    private final ExecutorService uploadExecutor = Executors.newSingleThreadExecutor();

    public FrontCameraBridge(Activity activity, WebView webView) {
        this.activity = activity;
        this.webView = webView;
    }

    public void setRotation(int deg) {
        this.mRotation = (deg % 360 + 360) % 360;
    }

    public int getRotation() {
        return mRotation;
    }

    public synchronized boolean start(final String uploadUrl, final String mode) {
        return start(uploadUrl, mode, null);
    }

    public synchronized boolean start(final String uploadUrl, final String mode, final String authorizedOrigin) {
        stop();
        if (authorizedOrigin == null || authorizedOrigin.trim().isEmpty() || uploadUrl == null || uploadUrl.trim().isEmpty()) {
            return false;
        }
        try {
            android.net.Uri targetUri = android.net.Uri.parse(uploadUrl.trim());
            String targetOrigin = new android.net.Uri.Builder().scheme(targetUri.getScheme()).encodedAuthority(targetUri.getEncodedAuthority()).build().toString();
            android.net.Uri authUri = android.net.Uri.parse(authorizedOrigin.trim());
            String expectedOrigin = new android.net.Uri.Builder().scheme(authUri.getScheme()).encodedAuthority(authUri.getEncodedAuthority()).build().toString();
            if (!expectedOrigin.equalsIgnoreCase(targetOrigin)) {
                return false;
            }
        } catch (Exception e) {
            return false;
        }
        this.mAuthorizedOrigin = authorizedOrigin.trim();
        try {
            int camId = -1;
            int count = Camera.getNumberOfCameras();
            for (int i = 0; i < count; i++) {
                Camera.CameraInfo info = new Camera.CameraInfo();
                Camera.getCameraInfo(i, info);
                if (info.facing == Camera.CameraInfo.CAMERA_FACING_FRONT) {
                    camId = i;
                    break;
                }
            }
            if (camId == -1) camId = 0;
            mCamera = Camera.open(camId);
            Camera.Parameters params = mCamera.getParameters();
            Camera.Size best = null;
            for (Camera.Size s : params.getSupportedPreviewSizes()) {
                if (s.width <= 640 && s.height <= 480) {
                    if (best == null || (s.width * s.height > best.width * best.height)) {
                        best = s;
                    }
                }
            }
            if (best == null) {
                for (Camera.Size s : params.getSupportedPreviewSizes()) {
                    if (best == null || (s.width * s.height < best.width * best.height)) {
                        best = s;
                    }
                }
            }
            if (best != null) {
                params.setPreviewSize(best.width, best.height);
            }
            mCamera.setParameters(params);

            // Resolve access token securely from SharedPreferences
            String tok = activity.getSharedPreferences("config", Activity.MODE_PRIVATE).getString("access_token", "");
            final String authToken = tok != null ? tok.trim() : "";
            // Strip any sensitive token parameter from URL to prevent query parameter exposure
            final String finalUploadUrl = uploadUrl.replaceAll("([?&])token=[^&]*", "$1").replaceAll("[?&]$", "");

            mSurface = new SurfaceTexture(10);
            mCamera.setPreviewTexture(mSurface);
            mRunning = true;
            mCamera.setPreviewCallback((data, camera) -> {
                if (!mRunning) return;
                long now = System.currentTimeMillis();
                if (now - lastFrameTime < 65) return; // ~15 FPS
                lastFrameTime = now;
                try {
                    Camera.Size sz = camera.getParameters().getPreviewSize();
                    YuvImage yuv = new YuvImage(data, ImageFormat.NV21, sz.width, sz.height, null);
                    ByteArrayOutputStream out = new ByteArrayOutputStream();
                    yuv.compressToJpeg(new Rect(0, 0, sz.width, sz.height), 60, out);
                    byte[] jpeg = out.toByteArray();

                    final int rot = mRotation;
                    if (rot != 0) {
                        try {
                            android.graphics.Bitmap src = android.graphics.BitmapFactory.decodeByteArray(jpeg, 0, jpeg.length);
                            if (src != null) {
                                android.graphics.Matrix matrix = new android.graphics.Matrix();
                                matrix.postRotate(rot);
                                android.graphics.Bitmap rotated = android.graphics.Bitmap.createBitmap(src, 0, 0, src.getWidth(), src.getHeight(), matrix, true);
                                ByteArrayOutputStream rotOut = new ByteArrayOutputStream();
                                rotated.compress(android.graphics.Bitmap.CompressFormat.JPEG, 60, rotOut);
                                jpeg = rotOut.toByteArray();
                                src.recycle();
                                if (rotated != src) rotated.recycle();
                            }
                        } catch (Exception ignored) {}
                    }
                    final byte[] finalJpeg = jpeg;
                    final String b64 = Base64.encodeToString(finalJpeg, Base64.NO_WRAP);

                    // Post frame to WebView for local live preview window
                    activity.runOnUiThread(() -> {
                        if (!mRunning) return;
                        webView.evaluateJavascript("if(window.onNativeCameraFrame)window.onNativeCameraFrame('" + b64 + "');", null);
                    });

                    // Upload frame to PC server in background thread
                    if (!mUploading && finalUploadUrl != null && !finalUploadUrl.isEmpty()) {
                        mUploading = true;
                        uploadExecutor.execute(() -> {
                            try {
                                URL u = new URL(finalUploadUrl);
                                HttpURLConnection conn = (HttpURLConnection) u.openConnection();
                                conn.setInstanceFollowRedirects(false); // Security: prohibit following cross-origin redirects
                                conn.setRequestMethod("POST");
                                conn.setDoOutput(true);
                                conn.setRequestProperty("Content-Type", "image/jpeg");
                                conn.setRequestProperty("X-Vision-Mode", mode != null ? mode : "fingertip");
                                if (!authToken.isEmpty()) {
                                    conn.setRequestProperty("Authorization", "Bearer " + authToken);
                                    conn.setRequestProperty("X-Access-Token", authToken);
                                }
                                conn.setConnectTimeout(1500);
                                conn.setReadTimeout(1500);
                                OutputStream os = conn.getOutputStream();
                                os.write(finalJpeg);
                                os.flush();
                                os.close();
                                int responseCode = conn.getResponseCode();
                                if (responseCode >= 300 && responseCode < 400) {
                                    // Security: reject redirects, do not leak frames or credentials
                                    conn.disconnect();
                                    return;
                                }
                                if (responseCode == 200) {
                                    InputStream is = conn.getInputStream();
                                    ByteArrayOutputStream resp = new ByteArrayOutputStream();
                                    byte[] buf = new byte[1024];
                                    int len;
                                    while ((len = is.read(buf)) != -1) resp.write(buf, 0, len);
                                    is.close();
                                    final String json = resp.toString("UTF-8");
                                    activity.runOnUiThread(() -> {
                                        if (!mRunning) return;
                                        webView.evaluateJavascript("if(window.onNativeCameraObservation)window.onNativeCameraObservation(" + json + ");", null);
                                    });
                                }
                                conn.disconnect();
                            } catch (Exception ignored) {
                            } finally {
                                mUploading = false;
                            }
                        });
                    }
                } catch (Exception ignored) {}
            });
            mCamera.startPreview();
            return true;
        } catch (Exception e) {
            stop();
            return false;
        }
    }

    public synchronized void stop() {
        mRunning = false;
        if (mCamera != null) {
            try {
                mCamera.setPreviewCallback(null);
                mCamera.stopPreview();
                mCamera.release();
            } catch (Exception ignored) {}
            mCamera = null;
        }
        if (mSurface != null) {
            try { mSurface.release(); } catch (Exception ignored) {}
            mSurface = null;
        }
    }
}
