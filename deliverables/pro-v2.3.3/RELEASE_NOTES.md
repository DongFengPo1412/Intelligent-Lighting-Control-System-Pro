# Intelligent Lighting Control System Pro (`pro-v2.3.3` Pre-release)

## Summary of Fixes & Deliverables

1. **Zero-Config Phone Hotspot Auth & LED Matrix Preview (`pc-agent-vision/access_control.py`)**
   - Added `"/api/pro/frame"` to `SAFE_UNAUTHENTICATED_LAN_GET_ENDPOINTS` (`GET` only), stopping `401 pairing_required` popups (`请输入电脑服务的配对令牌`) and unblocking the phone LED matrix preview on trusted hotspot clients (`192.168.8.146 -> 192.168.8.90:8080`).

2. **Hotspot Latency Resilience & Android Discovery (`pc-agent-vision`, `android-app`)**
   - Increased `WiFiGateway.request()` readback tolerances (`KURISU_STATUS_TIMEOUT=0.9`, `KURISU_STATUS_RETRIES=1`, `KURISU_FRAME_TIMEOUT=0.85`).
   - Kept `/api/status` `is_connected=True` on transient `telemetry_busy` / `ack_timeout` when `wifi_online=True`, avoiding false `"正在重连设备"` banners.
   - Bumped `android-app` (`versionName="2.2.2"`, `versionCode="32"`) timeouts and discovery reliability (`verifyServerHealth=1800ms`, redundant Phase 1 broadcast probes `350ms` apart with `1500ms` window, `1800ms` Phase 2 probes, `sendUdpAsync` `1600ms` + retry).

3. **PCM Playback & Voice Startup Reliability (`firmware-s3` + `pc-agent-vision/network_audio.py`)**
   - Allowed `FlushLocked()` partial-frame tolerance up to `5000ms` (`PcmTxQueue::Flush(..., max_age_ms=5000)`) while keeping host unit-test `1500ms` default.
   - Aligned ESP32 TCP 8889 `SO_RCVTIMEO` to `{6, 0}` matching the `6000ms` idle budget so transient hotspot stalls do not abort mid-stream `read_all()`.
   - Added `WiFiPcmClient.play_stream()` `status` pre-check retry and single transient `OSError` reconnect recovery on non-cancelled playback.

4. **Deliverable Checksums & Verification**
   - Firmware (`ota_0` `0x20000`, readback SHA-256 verified): `s3_led_matrix_test_pro-v2.3.3.bin` (`1,619,120` bytes, SHA-256 `955C9073A49B4D422FBB81F0E645811B4DC2309B64A917EE270C8669F3F130B1`).
   - Android APK (`v2.2.2`, `versionCode=32`, v2+v3 cert `EC:BF:63:8D:...`): `Kurisu_Amadeus_Pro_v2.2.2_vc32.apk` (`2,865,633` bytes, SHA-256 `E3608E1BECE2DA7C868A0E3D6EF8EDC60CF12C6DE9777E1D093F8BA281717EF0`).
   - Native C++ tests (`11/11` PASS) and 11 Python regression suites (`219 passed, 1 skipped, 3 deselected (-k "not F17F18"), 116 subtests passed`) verified after final edits.
