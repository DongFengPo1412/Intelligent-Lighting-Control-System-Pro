# Pro implementation and deployment

[简体中文](PRO_FEATURES.md) · **English** · [日本語](PRO_FEATURES.ja.md) · [Overview](../README_EN.md)

Implementation status as of 2026-10-25: source integration, offline checks and build evidence, with limited board communication, audio, gesture and music-following acceptance. **Full-system hardware acceptance remains incomplete.** Each test applies only to its recorded version and conditions; see the [board records](hardware-checks-20261023.en.md).

## Mapping the 18 historical requirements

The [historical SRS](HIGH_STAGE_SYSTEM_SPEC_18.md) is a design reference, not a completion certificate. Unmeasured performance and hardware assumptions are not results.

| Item | Current implementation | Boundary or design difference |
| --- | --- | --- |
| 1 One S3 | `main.cc`: display on Core 1, network/audio on Core 0 | LLM and vision still run on the PC. |
| 2 RMT DMA | Matrix output through `display_hal.cc` | No measured zero-CPU result. |
| 3 Buffers/gamma | Drawing buffer, completed PWM snapshot, display mutex; optional gamma | Not an asynchronous swap queue; gamma defaults off. No verified stable 60 FPS. |
| 4 Effects | Existing modes 0–25, with 18 unused; configurable wiring for one 16×16 panel | Not a claim of frame-by-frame identity with Mid. |
| 5 Local LLM | Ollama, `Modelfile.kurisu`, validated semantic plans | Qwen2.5-based configuration, not newly trained model research. |
| 6 Memory | SQLite facts/preferences/conversation, document chunks, deletable RAG | Default lexical hash vectors; optional local embeddings. Not Mem0. |
| 7 Conversation/MCP/XiaoZhi | Continuous turns, HTTP/WS MCP, separate v1 Opus adapter; optional Wi-Fi duplex/reference echo processing/interruption | Wake detection stays on the PC, not board WakeNet. Duplex has no acoustic acceptance. |
| 8 Countdown | Dedicated 1–86400-second command, pixel progress, completion animation and asynchronous cue | Not granular physics; actual timing/audio require measurement. |
| 9 Worldline | Mode 28: rolling digits settle at `1.048596`, decimal point and cue sequence | A fictional display effect, not an instrument; cues are not sampled electrical sounds. |
| 10 Hand sandbox | Shared camera, 21 landmarks, pinch/grab/throw, relative-z input, gravity/bounce/ripples | Monocular relative depth, not calibrated metric 3D; no >60 FPS measurement. |
| 11 Gaze/head pose | Iris ratios, nine-point affine calibration, approximate solvePnP | Calibration fit error is not independent gaze accuracy; approximate intrinsics. |
| 12 Expression cues | EAR/PERCLOS, mouth/brow geometry, fatigue/frown hints, smile celebration | Heuristic interaction cues, not psychological or medical classifiers. |
| 13 Pet lifecycle | Idle/closed-eye/mouth frames, night/rest/presence/fatigue context | Existing user palette overrides retained; mouth animation is not phoneme synchronization. |
| 14 Wireless music | TCP PCM, local catalog/search, web/voice requests, previous/next, shuffle/repeat, uploads/direct URLs | 16 kHz mono PCM16, separate music gain 0.25; original-source losslessness is not claimed. See the [library guide](LOCAL_MUSIC.en.md). |
| 15 MIR music halo | 1024-point FFT, 16 logarithmic bands, RMS, spectral flux, onset and beat phase drive concentric square rings; optional 16-column spectrum | Stale-input decay and heuristic rhythm estimation. Band distribution is not separate fundamental-frequency extraction from polyphonic songs; no song-library accuracy or objective audiovisual latency result. |
| 16 Motion games | Dwell/debounce hand or calibrated-gaze controls for Snake/Tetris | One camera owner; manual incompatible mode changes pause automatic control. |
| 17 DDA | Manual 0–1 difficulty and bounded adaptive hints from input intervals/expression cues | Speed floors remain; no demonstrated psychological flow-state result. |
| 18 Clients/preview | Pixel editor, completed-frame readback, WebGL, configurable Android host/DNS-SD | Optional real C++ WASM preview. Not a calibrated optical twin; Android not installed/tested. |

Native WakeNet, physical sand, original-format lossless music and physical-light simulation differ from the SRS. Source coverage does not establish performance or subjective quality.

## Services, models and data

On 2026-10-24, fixed squares, endpoint markers and all 16 row starts identified the current panel as left-to-right on every row. Production builds default to `-DPRO_MATRIX_SERPENTINE=OFF`; use `ON` for a physically serpentine panel. This option changes the shared coordinate mapping and frame readback without changing RGB values.

Use Python 3.10 and `pc-agent-vision/requirements-pro.txt` for control/Web/vision/MIR/MCP/Opus. Whisper, KWS, Torch, GPT-SoVITS, model weights and reference audio need their separate [voice-baseline setup](VOICE_CONTROL_RECOVERY.md). Simulation downloads none of them.

The entry remains `pc-agent-vision/web_server.py`. Since 2026-10-25, `/` serves the unified responsive interface; `/pro.html` redirects there. Browser and Android share one frontend using actual APIs and frame readback. [UI guide](UNIFIED_WEB.md).

| Setting | Default and purpose |
| --- | --- |
| `KURISU_DATA_DIR` | `%LOCALAPPDATA%/KurisuPro`: memory, faces, gaze calibration and device address; outside Git. |
| `KURISU_CACHE_DIR` | `~/.codex/cache/tasks/kurisu-runtime-<pid>`: voice cache/diagnostics; explicitly isolate tests. |
| `KURISU_CONTINUOUS` | `1`: listen again after replies; exit after 10 s idle or a closing phrase. `0` selects a single turn. |
| `KURISU_AUDIO_TRANSPORT` | `usb`; `wifi` opts into TCP PCM. Retains the historical USB conversion, 70% board volume and audio baseline. |
| `KURISU_BARGE_IN` | Off; `1` with Wi-Fi enables experimental reference-echo processing and wake interruption, still followed by unprompted ASR confirmation. |
| `KURISU_ECHO_DELAY_MS` | `120`: experimental reference alignment, not a calibrated acoustic delay. |
| `KURISU_AUTO_MEMORY` | `1`: explicit first-person preferences/names/habits may be saved; `记住：…` saves manually. View/delete/clear through the console; `0` disables automatic extraction. |
| `KURISU_EMBED_MODEL` | Unset: lexical hashes; an installed Ollama embedding model enables `/api/embed`. Stored records are re-embedded when the representation changes. |
| `OLLAMA_HOST` | Embeddings default to `http://127.0.0.1:11434`; chat still uses existing `OPENAI_BASE_URL`. |
| `KURISU_RENDERER_WASM` | Optional built `engine.wasm` for simulation; absent means limited static fixtures. |
| `KURISU_NODE_EXE` | `node`, used by the offline renderer process. |

Personal memory, documents, face samples and calibration stay local. Retrieved material is reference context, not an executable lighting plan. Weights and runtime data are not committed.

## Fully offline preview

This path binds to `127.0.0.1` without serial discovery, UDP, model loading, camera/microphone capture or sound.

```powershell
$task = Join-Path $env:USERPROFILE ('.codex\cache\tasks\pro-preview-' + [guid]::NewGuid().ToString('N'))
$env:KURISU_DATA_DIR = Join-Path $task 'data'
$env:KURISU_CACHE_DIR = Join-Path $task 'cache'
python -B pc-agent-vision/web_server.py --simulate --no-audio --port 8086
```

Open `http://127.0.0.1:8086/`. Simulated chat accepts explicit literal lighting commands; it does not imitate arbitrary LLM understanding. For real C++ animation, build using Clang/WebAssembly and a compatible sysroot:

```powershell
python -B scripts/build_offline_renderer.py --clang <clang.exe> --sysroot <wasm-sysroot> --output-dir "$task\engine"
node pc-agent-vision/offline_renderer.js "$task\engine\engine.wasm" --test
$env:KURISU_RENDERER_WASM = "$task\engine\engine.wasm"
python -B pc-agent-vision/web_server.py --simulate --no-audio --port 8086
```

The build uses production Effect/Game/Spectrum/Interaction/Fingertip sources with substitute time/LED/audio interfaces. It does not simulate ESP32 scheduling, I2S, networking or power. Simulated countdown uses a progress fixture rather than the actual timer task. WASM output is not distributed in Git.

## Display, vision, music and games

- Direct modes: **0–31 excluding 18 and 25**. Mode 25 requires a countdown duration. Modes 26–31 are fingertip, sandbox, worldline, canvas, music halo and ambient.
- The teammate fingertip source is registered in CMake, modes, commands and locked display dispatch. See [integration](../INTEGRATION.md); prefer the shared Web camera path to competing standalone programs.
- Vision is off until enabled. Choose 19/21 before gesture/gaze gaming. Gaze gaming requires nine-point calibration; look at each orange point and press Space. Stop capture before changing its index.
- Selecting an incompatible mode/countdown pauses automatic switching; re-enable the visual mode to resume. Local LBPH greetings are not secure identity authentication.
- Face enrollment requires a running camera, a currently detected face and a sample no older than **1 second**. Missing/empty crops and stopped/failed capture invalidate the cache; enrollment uses a detached image under the sample lock. This is an offline-tested freshness guard, not a recognition-accuracy claim.
- Audio upload/direct links are limited to 20 MiB and 30 minutes. Account/DRM/redirect-dependent music services are not universally supported. Failures appear in status; stopping interrupts playback/feature output.
- The halo maps low-to-high bands from inner to outer rings, RMS to overall intensity, attacks to expanding pulses, and beat phase to motion. Analysis follows the actual PCM send-start clock and skips stale windows under slow ACKs. `music.analysis` reports command dispatch statistics, not speaker-to-panel optical latency. Playback pauses an active voice listener and restores only the pause it owns.
- DDA input intervals and facial geometry are hints. Adaptive control can be disabled and difficulty set manually; existing game rules/results remain.

## Protocols

### HTTP and WebSocket

Existing `/api/chat`, `mode`, `volume`, `cmd`, `game`, `status`, `ceremony` and `/ws` remain.

| Route | Contract |
| --- | --- |
| `GET /api/pro/frame` | Completed frame: 1536 hex characters for logical-row-major RGB pixels; `frame_source` labels hardware PWM versus simulation. |
| `POST /api/pro/canvas` | `{"hex":"<256 RGB pixels>"}`; validate/commit the complete frame, then mode 29. |
| `GET /api/pro/status` | Vision, music, continuous-turn and XiaoZhi connection state. |
| `GET/POST/DELETE /api/pro/memory` | List/save/delete by id; POST `{"clear":true}` clears. |
| `POST /api/pro/documents` | `{"text":"..."}`, chunked reference input, at most 100000 characters. |
| `POST /api/pro/vision` | `{"enabled":true,"mode":"pet","camera":0}`; pet/fingertip/sandbox/gesture_game/gaze_game/identity. |
| `POST /api/pro/calibrate` | At least five non-collinear `[iris_x,iris_y,target_x,target_y]` samples. |
| `POST /api/pro/enroll` | `{"name":"..."}`; requires the fresh current face described above. |
| `POST /api/pro/track-calibrate` | x0/y0/x1/y1 and invert_x/invert_y. |
| `POST /api/pro/difficulty` | `{"level":0.5,"adaptive":true}`. |
| `POST /api/pro/music-upload?visual=fluid` | Raw audio bytes, not multipart; `visual=fluid` (default, halo) or `spectrum` (16 columns). |
| `POST /api/pro/music` | `{"url":"...","visual":"fluid"}` or `{"stop":true}`; `visual` also accepts `spectrum`. |
| `GET/POST /api/pro/library`, `POST /api/pro/music` | Catalog configuration/scan/search and ID/query playback, queue and repeat options; see the [library API](LOCAL_MUSIC.en.md). |
| `POST /api/pro/observations` | Synthetic observations, simulation only. |
| `POST /api/pro/device-tool` | Call a connected native XiaoZhi device's advertised MCP tool; validate name/arguments against its schema. |

### MCP

HTTP `/mcp` supports initialize, ping, tools/list, tools/call and session deletion. Initialization returns `Mcp-Session-Id`; later requests return that header. Notifications return 202. Supported JSON-response subsets: 2024-11-05, 2025-03-26 and 2025-06-18; no SSE streaming. `/ws` accepts `{"type":"mcp","payload":{...JSON-RPC...}}`.

Tools include existing lighting/volume/countdown, `self.matrix.set_canvas/get_frame`, `self.game.set_difficulty`, `self.memory.remember/search`, and `self.sensors.get_context`. Sensor context carries enabled/freshness/simulation labels. Schema validation and device ACK participate in success; failures return isError rather than a spoken success claim.

### Two different wireless audio paths

**Pro PCM:** `KURISU_AUDIO_TRANSPORT=wifi`, S3 TCP 8889; `KAP1 + kind(u8) + length(u16BE)`, at most 2048 payload bytes, PCM16LE/16000/mono. Kind 4 handshake is `pcm16le/16000/mono/v1`, 1 playback, 2 microphone, 5 heartbeat. Control remains UDP ACK; playback checks I2S sample counts.

**Native XiaoZhi Opus:** set `KURISU_XIAOZHI_BRIDGE=1` before launch. Connect the native client to `ws://<PC-IP>:8080/xiaozhi/v1/` with `Protocol-Version: 1`, hello Opus/16000/mono and 20/40/60 ms. It adapts listen/start/stop, abort, STT/LLM/TTS, Opus frames and bidirectional MCP discovery. Do not simultaneously start the Pro PC microphone listener.

`KURISU_XIAOZHI_TOKEN` optionally requires a Bearer token. ASR lazily uses existing local Whisper resources, default CPU int8; `KURISU_ASR_MODEL`/`KURISU_ASR_DEVICE` override model/device. Character TTS is retained. This is a server adapter, not an external XiaoZhi firmware rewrite/build/flash; native-client hardware integration is untested.

KAP1 PCM and native Opus are **not interchangeable**. HTTP/UDP/PCM deployment targets a trusted experiment LAN, not direct public exposure.

## Android and builds

Configure the PC host on first Android use or select a discovered `_kurisupro._tcp` service. The address persists; disconnection is reported. Optional zeroconf publishes DNS-SD, still requiring LAN/firewall tests.

The build preserves MainActivity/Manifest/resources/repository assets. Outputs and temporary debug signing material go to explicit external paths. Supply the original aapt2/R8, JDK, android.jar and SDK Build Tools with zipalign/apksigner:

```powershell
python -B android-app/build_apk.py --work-dir "$task\android-build-new" --output "$task\Kurisu-Pro-debug.apk" --build-tools <SDK-build-tools-dir> --java-home <JDK-dir> --android-jar <android.jar>
```

Use new output/work paths. The independently test-signed APK does not replace the old repository v1.0 APK and was not installed. ESP32 builds use ESP-IDF 5.5.4 with `PRO_MATRIX_DIAGNOSTIC` and `PRO_HAIR_CALIBRATION` off. Offline builds use isolated source and public Wi-Fi configuration, without copying private configuration. No flash/monitor is part of these checks.

## Offline verification and remaining hardware work

Test entries: `tests/test_pro_runtime.py`, `tests/test_controller_validation.py`, `tests/test_face_enrollment.py`, `scripts/test_interaction_regressions.py`, `scripts/test_semantic_control.py`, `tests/test_kurisu_palette.py`, `tests/test_display_engines.py` and renderer `--test`. Set `KURISU_TEST_TMP` to an isolated task cache; optionally set `KURISU_TEST_RENDERER_WASM` for the compiled C++ integration. Do not confuse them with similarly named physical-board scripts.

Remaining measurements include wireless audio interruption/quality, AEC/false barge-in, continuous voice, visual thresholds/independent gaze error, brightness/gamma/cues, FPS/CPU/stack, Android installation/discovery and endurance. Source and simulation do not replace those results.

References: [XiaoZhi WebSocket](https://xiaozhi.dev/docs/development/websocket/), [XiaoZhi MCP](https://xiaozhi.dev/docs/development/mcp/protocol/), [Ollama embeddings](https://docs.ollama.com/api/embed), [Android apksigner](https://developer.android.com/tools/apksigner). The locally available XiaoZhi 2.2.4 WebSocket v1 implementation was also consulted.

## 2026-10-24 delivery fixes and limited board records

- A 256-pixel canvas produces a 1631-byte UDP payload after ACK wrapping and needs IPv4 fragment reassembly on a typical 1500-MTU link. `firmware-s3/sdkconfig.defaults` now enables `CONFIG_LWIP_IP4_REASSEMBLY=y`. Defaults do not override an existing `sdkconfig`: enable IPv4 reassembly through `idf.py menuconfig`, confirm the generated build configuration contains this value, then rebuild.
- PC and board PCM sockets enable TCP_NODELAY. The semantic model is warmed before automatic listening, using a 4096-token context and 30-minute keep-alive; failed warmup leaves automatic listening stopped. Generated wake keywords go to `KURISU_CACHE_DIR` instead of the model directory.
- [Limited board records from 2026-10-23](hardware-checks-20261023.en.md) describe the 155 control checks and USB/Wi-Fi audio-sample checks with their limits. This delivery performs only builds and offline regressions, without flashing, recording or playback.
- `tests/test_delivery_regressions.py` uses fake sockets/models for canvas configuration, warmup failure and keyword-cache checks. Physical entries `scripts/test_pro_board.py` and `scripts/test_pro_audio.py` require explicit execution with suitable devices and are not default offline tests.
