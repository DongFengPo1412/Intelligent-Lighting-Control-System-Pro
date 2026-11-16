# Intelligent Lighting Control System Pro (`pro-v2.3.2` Pre-release)

## Summary of P0 Fixes & Deliverables

1. **Wi-Fi TCP 8889 PCM Resilience (`firmware-s3` + `pc-agent-vision`)**
   - Increased lwIP TCP send/receive window (`16384` bytes, RX mbox `16`) in `firmware-s3/sdkconfig.defaults` and heartbeat tolerance (`6000ms`) in `firmware-s3/main/protocol/network_audio.cc`.
   - Added `PcmTxQueue::DropExpiredMic()` in `firmware-s3/main/protocol/pcm_tx_queue.h` so phone-hotspot stalls drop stale unsent mic packets instead of tearing down TCP 8889 (`errno=116`), preserving `PcmTxQueue` unit-test expiry semantics.
   - Bumped `WiFiPcmClient` socket buffer (`SO_RCVBUF=262144`), `0.5s` heartbeat, `LightController.audio_connected` Wi-Fi isolation, and hotspot-latency-tolerant `wait_for_control(timeout=0.8, retries=1)`.
   - Verified 10.52s continuous live ESP32-S3 INMP441 mic streaming over `HONOR 90 Pro` hotspot (`699 chunks`, `335,520 bytes`, `ac_rms=6168.65`, `mic_tx_drop=0`, `pcm_tx_busy=0`, `pcm_tx_err=0`).

2. **Zero-Config USB Pairing Bootstrap (`pc-agent-vision/wifi_gateway.py`, `light_controller.py`)**
   - Added non-resetting USB CDC serial open (`dtr=False, rts=False` before `.open()`) and `WiFiGateway.bootstrap_usb_pairing()` to fetch `control_token` once over physical USB into local `control-pairing.json` when missing/stale, without logging tokens or storing credentials in the repo.

3. **GPIO48 Status LED Fix & Local Ollama/Voice Recovery (`pc-agent-vision`)**
   - Fixed `voice_listener.py` teardown setting `"green"` (`SOLID_GREEN`) -> `"off"`.
   - Added `finally:` board LED restoration across `VoiceEngine` speech/translation paths and `web_server.background_model_warmup()` failure/cancel/unstarted branches.
   - Increased Ollama warmup timeout (`30.0s -> 90.0s`) to accommodate cold `kurisu:latest` (7.6B Q4_K_M) loading (~36.8s cold, ~0.25–2.1s warm).
   - Added one-click demo launcher [`scripts/start_pro_demo.ps1`](../../scripts/start_pro_demo.ps1).

4. **Formal Deliverables & Verification Scope**
   - Firmware (`ota_0` App-only `0x20000`, readback SHA-256 verified): `s3_led_matrix_test_pro-v2.3.2.bin` (`1,619,104` bytes, SHA-256 `CADF3B153F5DEF8015CD634E566D28FAEAEF608022B8FAAACC65D0BC5850DC60`).
   - Android Pro APK (`versionName="2.2.1"`, `versionCode="31"`): `Kurisu_Amadeus_Pro_v2.2.1_vc31.apk` (`2,861,537` bytes, SHA-256 `ED215BAA6CC9144CBBF9E153A61FB0E83DBDB2B6012CBC2A1B7B2BB354DBE8FB`, v2+v3 signed with matching `v2.2.0` cert `EC:BF:63:8D:...`).
   - Marked **Pre-release** because physical MAX98357A speaker audible playback, interactive human acoustic wakeup, and real-phone APK UI tap tests remain `NOT_TESTED` pending interactive user readiness.
