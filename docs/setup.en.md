# Pro setup and operation

[简体中文](setup.zh-CN.md) · **English** · [日本語](setup.ja.md) · [Project overview](../README_EN.md)

[Structure](#structure) · [Hardware](#hardware) · [Firmware](#firmware) · [PC/models](#pc) · [Operation](#operation) · [Checks](#verification)

This guide follows current source. This pass changed documentation and ran offline checks without launching device services or reflashing. Read the [implementation scope](technical-notes.en.md#implementation-status), rather than treating historical requirements as completed deployment.

<a id="structure"></a>

## Repository and external assets

```text
.
├── firmware-s3/
│   ├── CMakeLists.txt
│   ├── sdkconfig.defaults
│   ├── diagnostics/
│   └── main/
│       ├── main.cc
│       ├── CMakeLists.txt
│       ├── idf_component.yml
│       ├── wifi_config.example.h
│       ├── audio/
│       ├── display/
│       └── protocol/
├── pc-agent-vision/
│   ├── web_server.py
│   ├── kurisu_agent.py
│   ├── semantic_control.py
│   ├── voice_listener.py
│   ├── voice_engine.py
│   ├── wake_detector.py
│   ├── light_controller.py
│   ├── wifi_gateway.py
│   ├── Modelfile.kurisu
│   ├── requirements-wake.txt
│   ├── web_app/
│   └── faces/
├── android-app/
├── scripts/
├── tests/
├── docs/
└── INTEGRATION.md
```

This is the main structure; independent vision/spectrum scripts also reside in `pc-agent-vision`. Models, private configuration, `.runtime_deps`, caches, diagnostic recordings, and builds are not distributed. Existing face images are historically tracked assets, not a ready dataset for every user; keep new enrollment local. No such assets were added or removed in this pass.

<a id="hardware"></a>

## Hardware and connections

| Component | Current source configuration | Checks |
| :--- | :--- | :--- |
| Controller | ESP32-S3, USB Serial/JTAG, Wi-Fi APSTA. | Old directory names do not identify the exact module; an 8 MB Flash default is not physical-model evidence. |
| Matrix | One 16×16 WS2812B panel, 256 LEDs, GRB, GPIO17→DIN. | Front top-left DIN, alternating rows. Two extra black data positions do not mean 258 physical LEDs. |
| INMP441 | WS4/SCK5/DIN6, I2S_NUM_1, 16 kHz. | Verify actual module supply, ground, and selected channel. |
| MAX98357A/speaker | DOUT7/BCLK15/LRCK16, I2S_NUM_0, 16 kHz/two 32-bit slots. | Module provides amplification; code does not establish speaker impedance or power capacity. |
| Board RGB | GPIO48, separate RMT, no DMA. | Confirm the actual board has this LED. |
| PC USB | Native USB Serial/JTAG; autodetect 303A:1001, otherwise COM9. | Port may differ. Audio requires a data cable, not power only. |
| Wi-Fi | UDP 8888, simultaneous S3 STA/SoftAP. | Use a reachable network, private settings, and actual logged addresses. |

Matrix supply, level shifting, wiring, voltage drop, and whole-system current lack complete controlled records. Brightness 20/default and 60/limit are not a 5 V/1.2 A current limiter. Design power, common ground, and signal levels for the real hardware; brightness is not supply-capacity assurance.

<a id="firmware"></a>

## Firmware configuration/build

The component declares IDF>=5.0 and `espressif/led_strip:^3.0.2`; recent inspectable builds use **ESP-IDF v5.5.4**. Every version meeting the lower bound has not been tested. Defaults select ESP32-S3, 8 MB Flash, and Octal PSRAM; verify actual hardware. Local sdkconfig/lock files are ignored.

Copy [wifi_config.example.h](../firmware-s3/main/wifi_config.example.h) to same-directory `wifi_config.private.h`, setting STA/AP details locally. `.gitignore` excludes it; do not publish the original machine's network settings.

From the repository root in an activated ESP-IDF terminal:

```powershell
cd firmware-s3
idf.py --version
idf.py menuconfig
idf.py -DPRO_MATRIX_DIAGNOSTIC=OFF -DPRO_HAIR_CALIBRATION=OFF build
idf.py -p COMx flash monitor
```

If a new configuration has not selected ESP32-S3, back up existing configuration before `idf.py set-target esp32s3`. Replace `COMx`; stop PC services holding the port before flashing. Startup selects mode 17, brightness 20, board volume 70.

`PRO_MATRIX_DIAGNOSTIC=ON` replaces the application with a wiring diagnostic without network/audio. `PRO_HAIR_CALIBRATION=ON` selects a separate color experiment rejected for visible flickering. They cannot both be enabled; normal operation requires both OFF. Do not run old color experiments or regenerate frames for ordinary reproduction.

<a id="pc"></a>

## PC environment, models, dependencies

The current local environment is Windows/Python **3.10.20**. ASR has CPU fallback; GPT-SoVITS is configured for CUDA. There is no comprehensive pinned requirements file, so a one-step fresh-environment setup is not guaranteed.

| Function | Dependencies/assets | Source and scope |
| :--- | :--- | :--- |
| Control/Web | pyserial, NumPy, aiohttp; entry also imports Torch/voice modules. | Not a minimal control-only server isolated from model dependencies. |
| ASR/VAD | Torch, faster-whisper, webrtcvad, Whisper `base` resources. | Initial download may require networking; local inference does not mean assets are bundled. |
| Acoustic wake | `sherpa-onnx==1.13.8`, `sherpa-onnx-core==1.13.8`, `models/wake_kws`. | See [wake record](VOICE_CONTROL_RECOVERY.md); models/private dependencies are untracked. |
| Language model | Ollama, `qwen2.5:7b`, `Modelfile.kurisu`. | Local persona configuration, not project-trained LLM. |
| TTS | NumPy/SciPy, GPT-SoVITS environment, BERT/HuBERT, character checkpoints/reference, optional noisereduce. | Requires a compatible Torch/CUDA environment; external models are not distributed. |
| Optional vision | OpenCV contrib, MediaPipe `solutions` APIs, Torch. | Launch separately and check API compatibility; do not mix multiple OpenCV wheels. |
| Optional spectrum | PyAudio, NumPy, accessible audio input. | Not automatic loopback or phone-music input. |

Prepare the language model with these commands, which download rather than train:

```powershell
ollama pull qwen2.5:7b
ollama create kurisu -f pc-agent-vision/Modelfile.kurisu
ollama list
```

Verify Ollama at `http://localhost:11434`. Agent defaults `OPENAI_BASE_URL` to `http://localhost:11434/v1`, but semantic planning explicitly requires the Ollama endpoint. A different compatible chat API does not guarantee full-path support.

Install wake dependencies into the existing isolated layout; prepare models separately:

```powershell
python -m pip install --target pc-agent-vision/.runtime_deps -r pc-agent-vision/requirements-wake.txt
```

`wake_kws` needs `tokens.txt` and epoch-12 INT8 encoder/decoder/joiner names matching `wake_detector.py`. Initialization generates the keyword file. Missing/incompatible assets disable automatic wake instead of falling back to free transcription.

TTS actually searches `models/GPT-SoVITS`, `models/pretrained_models/chinese-roberta-wwm-ext-large`, `chinese-hubert-base`, and `models/kurisu_tts/{kurisu-e15.ckpt,kurisu_e4_s972.pth,prompt_shy.wav}`. The separate root `GPT_SoVITS` directory is not an automatic substitute. Match source assets and dependencies; absent checkpoints do not constitute reproduced synthesis.

<a id="operation"></a>

## Launch and feature operation

Ensure no other service owns the USB port/UDP 8888, and launch only one primary entry. Web startup loads models, initializes hardware, prepares caches, and may play a pairing chime.

```powershell
python pc-agent-vision/web_server.py
```

Use `http://localhost:8080` on the PC, or the logged PC LAN address on a reachable phone. Inspect `/api/status`: `wifi.wifi_online`, `audio_usb_connected`, `board_audio_recent`, `wake_detector_ready`, and errors. Service availability is not board/audio availability; default labels/animations are not hardware evidence.

Operation is wake→reply if needed→one complete command→board acknowledgement→Chinese/Japanese reply→standby. Try colors, stars/ripples, a timer, brightness, or volume. Each next turn requires another wake. Playback pauses microphone upload; listening and speaking are not simultaneous.

Web buttons select modes, raw brightness, volume, timers, and game directions. Firmware brightness is 0–60; the PC wrapper clamps 1–60, and semantic percentages scale to maximum 60. Brightness 20 is not 20%. Supply timer seconds explicitly; selecting mode 25 alone does not start a complete timer. Game S/drop means one cell down.

Android APK/source are under [android-app](../android-app). Configure the PC URL in the WebView source. Build scripts contain original-machine JDK17/Android35 paths that must be adapted. Bundled assets may lag the Web source; offline UI cannot replace PC models/network services. Rebuilding is not a default setup step.

These independent programs occupy camera/audio resources or operate hardware. Run separately after stopping competing programs:

```powershell
python pc-agent-vision/vision_gesture.py
python pc-agent-vision/vision_face.py
python pc-agent-vision/vision_tracker.py
python pc-agent-vision/audio_visualizer.py
```

Do not launch the whole block concurrently. Gesture exits with q/Esc; face uses S/T/Q; tracker/spectrum use Ctrl+C. Face greetings may speak; spectrum needs a PC input device. Old `b 150` commands exceed firmware limits; see [known issues](technical-notes.en.md#vision-audio) rather than trusting restoration messages. Root fingertip scripts are not production modes.

<a id="verification"></a>

## Checks and troubleshooting

These offline commands neither open hardware nor load complete models. Use a compatible environment with NumPy/SciPy:

```powershell
python scripts/test_interaction_regressions.py
python scripts/test_semantic_control.py
python -m unittest discover -s tests -p test_kurisu_palette.py
node --check pc-agent-vision/web_app/app.js
node --check android-app/assets/www/app.js
xtensa-esp32s3-elf-g++ -std=c++14 -fsyntax-only tests/matrix_layout_test.cpp
xtensa-esp32s3-elf-g++ -std=c++14 -fsyntax-only tests/srgb_transfer_test.cpp
```

`test_semantic_control.py --live` calls local Ollama only; `test_board_ack.py --silent` still operates the physical matrix. Other comprehensive scripts can load models, record, change modes, or produce sound: do not batch-run them. Historical flashing/physical acceptance and current offline results are separated in the [technical notes](technical-notes.en.md#implementation-status).

| Symptom | Checks |
| :--- | :--- |
| Web opens without changing LEDs | Reachable UDP address, beacons, ACK/request ID; HTTP success is not board confirmation. |
| Wi-Fi works but voice fails | USB data port, PCM frames, recent board audio, KWS/Whisper/TTS resources. |
| Text says success without execution | Inspect structured plans and tool ACKs; old scripts/copy may not match current protocol. |
| Every command needs another wake | Current single-turn policy; continuous conversation has not been implemented. |
| Browser and physical pixels differ | Canvas is independent, without pixel readback; companion artwork also differs. |
| Colors remain wrong | Check role recipes and physical feedback; generation tests do not establish color acceptance. |
| Capture/playback interfere | Pause ownership, sample deltas, drops/errors, and stack margin; PC write completion is insufficient. |
