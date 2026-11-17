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
    private volatile int mRotation = 270; // Default: 270 degrees clockwise for Android front camera upright orientation
    private volatile String mAuthorizedOrigin = null;
    private volatile String mCurrentSessionId = null;
    private volatile String mVisionToken = "";
    private final java.util.concurrent.atomic.AtomicLong sessionEpoch = new java.util.concurrent.atomic.AtomicLong(0);
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

    public long getSessionEpoch() {
        return sessionEpoch.get();
    }

    public String getCurrentSessionId() {
        return mCurrentSessionId;
    }

    public boolean isRunning() {
        return mRunning;
    }

    private void emitStatus(final long expectedEpoch, final String sessionId, final String state, final String detail) {
        activity.runOnUiThread(() -> {
            if (sessionEpoch.get() != expectedEpoch) return;
            try {
                org.json.JSONObject obj = new org.json.JSONObject();
                obj.put("session_id", sessionId != null ? sessionId : "");
                obj.put("epoch", expectedEpoch);
                obj.put("state", state);
                if (detail != null) obj.put("detail", detail);
                webView.evaluateJavascript("if(window.onNativeCameraStatus)window.onNativeCameraStatus(" + obj.toString() + ");", null);
            } catch (Exception ignored) {}
        });
    }

    public synchronized boolean start(final String uploadUrl, final String mode) {
        return start(uploadUrl, mode, null, "");
    }

    public synchronized boolean start(final String uploadUrl, final String mode, final String authorizedOrigin) {
        return start(uploadUrl, mode, authorizedOrigin, "");
    }

    public synchronized boolean start(final String uploadUrl, final String mode, final String authorizedOrigin, final String visionToken) {
        stop();
        if (authorizedOrigin == null || authorizedOrigin.trim().isEmpty() || uploadUrl == null || uploadUrl.trim().isEmpty()) {
            return false;
        }
        final String parsedSessionId;
        try {
            android.net.Uri targetUri = android.net.Uri.parse(uploadUrl.trim());
            String targetOrigin = new android.net.Uri.Builder().scheme(targetUri.getScheme()).encodedAuthority(targetUri.getEncodedAuthority()).build().toString();
            android.net.Uri authUri = android.net.Uri.parse(authorizedOrigin.trim());
            String expectedOrigin = new android.net.Uri.Builder().scheme(authUri.getScheme()).encodedAuthority(authUri.getEncodedAuthority()).build().toString();
            if (!expectedOrigin.equalsIgnoreCase(targetOrigin)) {
                return false;
            }
            String sess = targetUri.getQueryParameter("session_id");
            if (sess == null || sess.trim().isEmpty()) {
                return false;
            }
            parsedSessionId = sess.trim();
        } catch (Exception e) {
            return false;
        }
        final long myEpoch = sessionEpoch.incrementAndGet();
        final String myMode = (mode != null && !mode.trim().isEmpty()) ? mode.trim() : "fingertip";
        final String myVisionToken = visionToken != null ? visionToken.trim() : "";
        this.mCurrentSessionId = parsedSessionId;
        this.mAuthorizedOrigin = authorizedOrigin.trim();
        this.mVisionToken = myVisionToken;
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

            // Resolve optional explicit access token safely from SharedPreferences (never from URL)
            String tok = activity.getSharedPreferences("config", Activity.MODE_PRIVATE).getString("access_token", "");
            final String authToken = tok != null ? tok.trim() : "";
            final String finalUploadUrl = uploadUrl.replaceAll("([?&])token=[^&]*", "$1").replaceAll("[?&]$", "");

            mSurface = new SurfaceTexture(10);
            mCamera.setPreviewTexture(mSurface);
            mRunning = true;
            emitStatus(myEpoch, parsedSessionId, "camera_opened", null);
            mCamera.setPreviewCallback((data, camera) -> {
                if (!mRunning || sessionEpoch.get() != myEpoch) return;
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
                    if (!mRunning || sessionEpoch.get() != myEpoch) return;
                    final byte[] finalJpeg = jpeg;
                    final String b64 = Base64.encodeToString(finalJpeg, Base64.NO_WRAP);
                    final String sidArg = org.json.JSONObject.quote(parsedSessionId);

                    // Post frame to WebView for local live preview window, strictly gated by epoch
                    activity.runOnUiThread(() -> {
                        if (!mRunning || sessionEpoch.get() != myEpoch) return;
                        webView.evaluateJavascript("if(window.onNativeCameraFrame)window.onNativeCameraFrame('" + b64 + "'," + sidArg + "," + myEpoch + ");", null);
                    });

                    // Upload frame to PC server in background thread (single-slot concurrency guard)
                    if (!mUploading && finalUploadUrl != null && !finalUploadUrl.isEmpty()) {
                        mUploading = true;
                        uploadExecutor.execute(() -> {
                            HttpURLConnection conn = null;
                            try {
                                if (!mRunning || sessionEpoch.get() != myEpoch) return;
                                URL u = new URL(finalUploadUrl);
                                conn = (HttpURLConnection) u.openConnection();
                                conn.setInstanceFollowRedirects(false); // Security: prohibit following cross-origin redirects
                                conn.setRequestMethod("POST");
                                conn.setDoOutput(true);
                                conn.setRequestProperty("Content-Type", "image/jpeg");
                                conn.setRequestProperty("X-Vision-Mode", myMode);
                                conn.setRequestProperty("X-Vision-Session", parsedSessionId);
                                conn.setRequestProperty("X-Camera-Rotation", String.valueOf(rot));
                                conn.setRequestProperty("X-Camera-Mirrored", "true");
                                if (!myVisionToken.isEmpty()) {
                                    conn.setRequestProperty("X-Vision-Token", myVisionToken);
                                }
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
                                if (!mRunning || sessionEpoch.get() != myEpoch) {
                                    return;
                                }
                                if (responseCode >= 300 && responseCode < 400) {
                                    emitStatus(myEpoch, parsedSessionId, "upload_error", "redirect_rejected");
                                    return;
                                }
                                if (responseCode == 200) {
                                    InputStream is = conn.getInputStream();
                                    ByteArrayOutputStream resp = new ByteArrayOutputStream();
                                    byte[] buf = new byte[1024];
                                    int len;
                                    while ((len = is.read(buf)) != -1) resp.write(buf, 0, len);
                                    is.close();
                                    if (!mRunning || sessionEpoch.get() != myEpoch) return;
                                    final String json = resp.toString("UTF-8");
                                    activity.runOnUiThread(() -> {
                                        if (!mRunning || sessionEpoch.get() != myEpoch) return;
                                        webView.evaluateJavascript("if(window.onNativeCameraObservation)window.onNativeCameraObservation(" + json + "," + sidArg + "," + myEpoch + ");", null);
                                    });
                                } else {
                                    emitStatus(myEpoch, parsedSessionId, "upload_error", "http_" + responseCode);
                                }
                            } catch (Exception uploadErr) {
                                if (mRunning && sessionEpoch.get() == myEpoch) {
                                    emitStatus(myEpoch, parsedSessionId, "upload_error", uploadErr.getMessage());
                                }
                            } finally {
                                if (conn != null) conn.disconnect();
                                mUploading = false;
                            }
                        });
                    }
                } catch (Exception frameErr) {
                    if (mRunning && sessionEpoch.get() == myEpoch) {
                        emitStatus(myEpoch, parsedSessionId, "local_error", frameErr.getMessage());
                    }
                }
            });
            mCamera.startPreview();
            return true;
        } catch (Exception e) {
            stop();
            return false;
        }
    }

    public synchronized void stop(final String sessionId) {
        if (sessionId != null && !sessionId.trim().isEmpty()) {
            if (mCurrentSessionId != null && !mCurrentSessionId.equals(sessionId.trim())) {
                // Ignore stale stop request belonging to an older session
                return;
            }
        }
        stop();
    }

    public synchronized void stop() {
        sessionEpoch.incrementAndGet();
        mRunning = false;
        mCurrentSessionId = null;
        mVisionToken = "";
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
