# Project workflow

- Repository: https://github.com/DongFengPo1412/Intelligent-Lighting-Control-System-Pro
- Branch policy: Always work directly on `main` (Owner directive). Do not create, switch to, or retain secondary branches. All changes are verified and committed directly to `main`, then pushed to `origin/main`.
- Preserve inherited changes and hardware/system configurations. Label standalone experiments accurately; do not present unintegrated code as a working feature.
- Hardware Pinout & Peripherals:
  - ESP32-S3 Core 1: 60 FPS matrix physical rendering (FastLED linear grading, GPIO 17 WS2812 16×16 matrix).
  - ESP32-S3 Core 0: Real-time command dispatcher, Wi-Fi UDP 8888, USB-Serial-JTAG, and Jetson UART1.
  - Jetson Nano Hardware UART1: RX=GPIO8, TX=GPIO9, 115200 8N1, no flow control.
  - Audio: INMP441 Microphone (WS=4, SCK=5, DIN=6) + MAX98357A Speaker (DOUT=7, BCLK=15, LRCK=16).
  - Onboard Indicator LED: GPIO 48.
- Jetson Nano UART & Universal Canvas Protocol:
  - JSON commands and raw binary frames (`0x55 0xAA 0x43 0x46`) supported on UART1.
  - Universal 16×16 RGB canvas (Mode 29) supports single pixel updates, chunked JSON with CRC16, and high-speed binary frame streaming.
  - Automatic game key release watchdog (500ms inactivity timeout) protects against runaway inputs.
- Keep network credentials, API keys, generated recordings, caches, model weights, private runtime dependencies, and build outputs out of commits.
- Announce audible tests or parameter comparisons before running them, and use the user's listening feedback to select settings.
- Flashing, partition migration, NVS erasure, and APK installation require the owner's explicit authorization.
