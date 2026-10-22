# Pro technical notes

[简体中文](technical-notes.zh-CN.md) · **English** · [日本語](technical-notes.ja.md) · [Project overview](../README_EN.md)

[Source](#source-map) · [Driver](#driver) · [Display and games](#display) · [Voice/agent](#voice-agent) · [Transport](#transport) · [Independent programs](#vision-audio) · [Status/evidence](#implementation-status)

Audit baseline: `d548868`. Current source, configuration, and available records take precedence. The [18-item specification](HIGH_STAGE_SYSTEM_SPEC_18.md) is a historical requirements document, not evidence of completion.

<a id="source-map"></a>

## Modules and source references

| Entry/module | Files | Actual responsibility |
| :--- | :--- | :--- |
| Firmware entry | [main.cc](../firmware-s3/main/main.cc), [CMake](../firmware-s3/main/CMakeLists.txt) | Display, board LED, I2S, USB, APSTA/UDP; defaults to companion 17; opt-in diagnostic entries. |
| Pixel output | [display_hal.cc](../firmware-s3/main/display/display_hal.cc), [matrix_layout.h](../firmware-s3/main/display/matrix_layout.h) | One 256-pixel application buffer, serpentine addressing, brightness, RMT DMA/refresh. |
| Modes/graphics | [display_manager.cc](../firmware-s3/main/display/display_manager.cc), [effect_engine.cc](../firmware-s3/main/display/effect_engine.cc) | Mode initialization, task dispatch, timer, effects, faces, companion. |
| Games/spectrum | [game_engine.cc](../firmware-s3/main/display/game_engine.cc), [spectrum_engine.cc](../firmware-s3/main/display/spectrum_engine.cc) | Games, scores, band rendering, peak hold. |
| Commands/network | [command_dispatcher.cc](../firmware-s3/main/protocol/command_dispatcher.cc), [wifi_manager.cc](../firmware-s3/main/protocol/wifi_manager.cc) | USB text/PCM demultiplexing, audio ring buffer, commands, UDP ACK cache. |
| I2S | [audio_hal.cc](../firmware-s3/main/audio/audio_hal.cc) | INMP441 input, MAX98357A output, PCM conversion, playback mutex, idle clock gating. |
| PC service | [web_server.py](../pc-agent-vision/web_server.py), [light_controller.py](../pc-agent-vision/light_controller.py), [wifi_gateway.py](../pc-agent-vision/wifi_gateway.py) | HTTP/WS, serialized chat, USB audio, acknowledged UDP. |
| Voice/plans | [voice_listener.py](../pc-agent-vision/voice_listener.py), [wake_detector.py](../pc-agent-vision/wake_detector.py), [semantic_control.py](../pc-agent-vision/semantic_control.py) | VAD, KWS, Whisper, effect catalog, argument validation. |
| Chat/synthesis | [kurisu_agent.py](../pc-agent-vision/kurisu_agent.py), [voice_engine.py](../pc-agent-vision/voice_engine.py), [light_tools.py](../pc-agent-vision/light_tools.py) | Short-term conversation, tool execution, bilingual replies, GPT-SoVITS/cache. |
| Clients | [Web JS](../pc-agent-vision/web_app/app.js), [Android Activity](../android-app/src/org/fglab/kurisu/MainActivity.java) | Controls, independent Canvas animation, WebView wrapper. |

The Web service does not launch `vision_gesture.py`, `vision_face.py`, `vision_tracker.py`, or `audio_visualizer.py`. Root `fingertip_tracker.*` is excluded from production CMake, and neither mode 26 nor `track` exists in dispatch/enums. [INTEGRATION](../INTEGRATION.md) is an unimplemented integration proposal.

<a id="driver"></a>

## Single panel, RMT, and scheduling

Current layout is one 16×16 panel: top-left DIN, front-view even rows to the right and odd rows reversed. Out-of-range returns -1; all 2D drawing shares:

```math
i(x,y)=16y+\begin{cases}x,&y\bmod2=0\\15-x,&y\bmod2=1\end{cases},\qquad 0\le x,y<16
```

GPIO17 outputs GRB WS2812 data. `led_strip_new_rmt_device` uses 10 MHz resolution, 128 memory symbols, and `with_dma=true`. It allocates 258 positions: 256 physical pixels followed by two black data positions. These are transmission margin, not two extra physical LEDs. Reset timing depends on the library; comments do not establish a measured 280 μs pulse.

Display task priority 5 runs on Core 1; USB/audio and UDP tasks run on Core 0. Most engines return 33 ms delay after refreshing, spectrum 20 ms, scores 100 ms, plus drawing, transfer, board LED, and scheduling overhead. DMA does not imply zero CPU, and `led_strip_refresh` is not an application frame-swap queue. No Front/Back exchange exists; stable 60 FPS and double buffering are unsupported.

Startup brightness is 20; the protocol accepts 0–60, with channels approximately RGB×brightness/255. Mid's FastLED 5 V/1200 mA estimator is absent. Brightness limits are not hardware current limits. GPIO48 is another RMT device with `with_dma=false`, indicating pairing/listening/thinking/speaking; not every LED is DMA-driven.

A shared recursive mutex serializes rendering, mode/game/spectrum input, brightness and timer operations; it is released before the render task sleeps. Internal game-completion mode changes can re-enter the lock. This is not a single-task command FIFO and ACKs are not global atomic snapshots. Advanced direct-engine access requires caller-managed synchronization.

<a id="display"></a>

## Effects, companion, timer, and games

### Mode catalog

The enum contains 0–25 excluding 18: 25 IDs including off and score screens, not 25 animated effects.

| IDs | Implementation |
| :--- | :--- |
| 0;1/2/3 | Off; red/blue/green. |
| 4–10 | Diagonal HSV rainbow, spatial-sine aurora, two meteors, fourteen lifecycle stars, color wash, random rain, dual radial ripples. |
| 11–14 | Smile/sad/neutral and rotating faces, with preset blinking/eye motion; no user gaze tracking. |
| 15;16/17 | Spectrum; 16 and 17 share the companion renderer. |
| 19/20;21/22 | Snake/score; Tetris/score. |
| 23/24/25 | Random cooling/neighborhood heat propagation; per-column code-rain strips; elapsed-time countdown. |

These are not pixel-identical Mid ports: rainbow, aurora, stars, ripple, and faces have separate current implementations. Fire does not sample Perlin noise; code rain does not draw legible digits. Describe the actual heat array and pixel trails.

### Companion images and color status

Four frames are idle, blink, and two mouths. Speaker-enabled state alternates mouths every 140 ms; otherwise blinking lasts about 160 ms at randomized intervals. I2S clocks stop after about 800 ms idle, so mouths can continue after audible speech. No phoneme, amplitude-envelope, or speech-timestamp alignment exists, nor circadian/yawning/sleep models.

The [generator](../scripts/update_kurisu_sprites.py) separates source RGB, role labels, display overrides, and reference PWM, producing [firmware frames](../firmware-s3/main/display/kurisu_sprites.h). For target channel q at reference brightness B=20:

```math
c=\left\lceil\frac{255q}{20}\right\rceil,\qquad p=\left\lfloor\frac{cB}{255}\right\rfloor
```

This preserves specified integer outputs at the reference level, not measured colorimetry, luminance, or screen matching. Companion scale is currently 100%; `Show` does not enable a second sRGB decode. `srgb_transfer.h` remains optional; an old Gamma table does not mean all production output uses gamma correction.

The independent 256-cell [fixture](../tests/fixtures/kurisu_design_hex.txt) preserves source data. Four skin cells, two unlit cells, and pants matching the coat are user-requested output overrides, not an untouched rendering. The dark-brown outline remains orange; visible flickering led to rejection of four-phase experiments. See the [color history](KURISU_VISUAL_TUNING.md).

### Countdown and worldline sequence

The timer accepts 1–86400 seconds and uses `get_millis()` differences instead of accumulated sleeps. Remaining pixels follow:

```math
N_{\mathrm{on}}=\left\lfloor256\max\left(0,1-\frac{t-t_0}{T}\right)\right\rfloor
```

It adds edge-pixel fading and green/orange/red progress colors. Expiry starts about 1500 ms of full-panel feedback before off; no measured timer error, physical sand, or dedicated completion sound is implemented. Selecting mode 25 alone does not initialize timing; use `countdown`.

“Worldline” is a PC sequence: fire→meteor→matrix→dynamic, with 0.35/0.35/1.2 s delays; the Web page shows fixed 1.048596%. There is no board-side numeric meter, random-number lock, or dedicated crackling effect. Persona text is not a measurement.

### Game mechanisms and limits

Snake retains 256 coordinates, initial length 3, 16×16 wrapping and self-collision. Bounded enumeration selects an unoccupied food cell; growth preserves the old tail, and a full board ends play. The latest direction is applied once per tick and cannot reverse the last committed direction. Speed is clamped to at least 80 ms; arbitrary multi-digit score display remains incomplete.

Tetris retains seven shapes/four rotations, a 16×16 field and ten columns x=3..12, with collision, rotation, locking, line clearing and scoring. The initial 800 ms interval decreases by 30 ms per line and is clamped at 100 ms. Drop moves one cell; hard drop, wall kicks and DDA are absent.

<a id="voice-agent"></a>

## Local audio input and semantic plans

### Wake and single-turn state

I2S_RX uses 16 kHz mono 32-bit slots; `ReadMic` shifts 16 bits to PCM16 for USB upload. PC uses 30 ms/480-sample frames with DC removal, WebRTC VAD2, and adaptive RMS thresholds. Two speech frames start an utterance; standby/command silence gates are 16/36 frames, with optional Silero validation for short clips. Comments mentioning three frames are outdated.

Standby audio first passes Sherpa ONNX Zipformer KWS at 0.50, then unprompted Whisper confirms it. Configured names must begin the utterance; Whisper text without acoustic evidence cannot wake. Whisper prefers CUDA float16 and falls back to CPU int8. Missing KWS disables automatic wake. Ten idle seconds end the command window, while active speech/processing/queued work is protected.

A name plus command can execute immediately; a name alone produces a reply and waits for one command. Incomplete prefixes can span utterances. Processing/playback pauses microphone upload; afterward capture resumes with `is_awake=False`. This is neither continuous conversation nor AEC full duplex.

### Plan checks and conversation

`semantic_control.py` implements effect names, JSON Schema, exact-command routes, explicit numeric-clause parsing, validation, and at most one repair request. Names map to mode numbers in code. Invalid arguments, actions attached to chat, and contradictory timer start/stop are rejected. Competing display requests require clarification; plans contain at most four actions.

`kurisu_agent.py` executes only control plans, never tool-looking persona prose, and deduplicates identical tool/argument pairs within a turn. Success depends on board ACK. Conversation keeps roughly twelve recent complete turns in memory, without Mem0, persistent vectors, or long-term memory. `Modelfile.kurisu` adds persona/sampling settings to `qwen2.5:7b`; it is not LLM training.

Although `light_tools.py` uses MCP naming and function schemas, execution is local Python dispatch, without a complete MCP JSON-RPC discovery/session service. The S3 does not run Mid's XiaoZhi client. A board-side bidirectional XiaoZhi/MCP integration is not established.

### Synthesis and PCM playback

`voice_engine.py` loads external GPT-SoVITS v2Pro checkpoints, BERT/HuBERT, and reference audio; no project training pipeline exists. Chinese/Japanese are synthesized separately, with 180 ms silence when both succeed, then filtering/optional noisereduce/EQ/normalization. It caches 32 kHz WAV and uses `resample_poly` for 16 kHz PCM. Missing models do not fall back to system TTS. A Windows local-playback path exists when board USB is unavailable; cross-platform fallback is not guaranteed.

The board duplicates PCM16 into two 32-bit I2S slots with squared volume mapping, a digital gain rather than sound-pressure measurement:

```math
g=\left\lfloor65536(V/100)^2\right\rfloor,\qquad s_{32}=\mathrm{clip}_{32}(s_{16}g)
```

PC pacing uses cumulative bytes and a monotonic clock with 120 ms target lead:

```math
t_{\mathrm{send}}=t_0+\frac{B_{\mathrm{sent}}}{2\times16000}-0.120
```

A 32 KiB ring buffer is consumed by an 8192-byte-stack playback task. Before/after queries compare `audio_rx/audio_played/audio_dropped/audio_errors`; sample deltas must match with no drops/errors. `audio_played` counts complete I2S writes, not acoustic quality. There is no simultaneous-input/output AEC guarantee or lossless preservation of original audio.

<a id="transport"></a>

## USB, Wi-Fi, and controls

USB microphone frames are `55 AA len_hi len_lo PCM16LE`; playback frames are `AA 55 len_hi len_lo PCM16LE`. Length is big-endian, PCM little-endian. Firmware accepts at most 2048-byte playback payloads without CRC or frame timeout recovery. USB also parses text/JSON, while ordinary PC control forces UDP 8888.

UDP envelopes use `{"request_id":"...","command":"..."}`. PC defaults are 0.6 s timeout and two retries. S3 caches sixteen results for 30 s, keyed by sender IP/ID; a changed command with the same ID conflicts. This bounded cache is not indefinite exactly-once delivery. ACK means dispatch/handling, not optical/acoustic acceptance. STA+SoftAP and roughly 2 s beacons support discovery, with timer-based reconnection.

HTTP 8080 exposes `/api/chat`, `mode`, `volume`, `cmd`, `game`, `status`, and `ceremony`; `/ws` broadcasts chat/mode events. Canvas uses local functions/time: spectra, games, and companion pixels are not board readback. The worldline display is also UI animation, not Three.js, WebGL, or a digital twin.

Android is a Java WebView, loading a configured PC URL and falling back to bundled assets. Bundled JS differs from current Web JS; relative `/api` requests on file pages do not automatically locate the PC. Activity defaults and SDK paths are machine-specific, so installing an APK alone does not establish standalone S3 control. HTTP/UDP have no user authentication and assume a local experimental network.

<a id="vision-audio"></a>

## Independent vision/audio programs

| Program | Actual implementation | Boundary |
| :--- | :--- | :--- |
| [vision_gesture.py](../pc-agent-vision/vision_gesture.py) | MediaPipe single-hand x/y rules; 0 off, 1 red, 2/victory companion, 3 fire, 4 code rain, 5 rainbow. | Changed result and >0.6 s since last trigger, not a 0.6 s pose hold. Still gates sending on Wi-Fi control readiness; no 3D grasp/throw. |
| [vision_face.py](../pc-agent-vision/vision_face.py) | Haar/100×100 grayscale LBPH, S capture/T retrain; ylk red, zzc blue, other names smile; 15 s greeting cooldown. | No liveness/security evaluation; synchronous synthesis may block GUI; not online incremental learning. |
| [vision_tracker.py](../pc-agent-vision/vision_tracker.py) | Face Mesh mouth width/height>2.8 triggers smile, timed dynamic-face return, presence flag. | Geometric heuristic, not emotion/head-pose/gaze/fatigue classification; absence does not activate power saving. |
| [audio_visualizer.py](../pc-agent-vision/audio_visualizer.py) | PyAudio default 16 kHz input, 512-point Hann/rFFT, sixteen averages, peak normalization, log amplitude, low-frequency transients. | PC input, not automatic phone/system-playback capture; separate from Web startup, without MIR fluids. |

Band edges inherit Mid, but rates/constants differ. Peak P starts at 0.05, decays by 0.96 per window, and has floor 0.01. For band means a_i:

```math
P_t=\max(0.96P_{t-1},\max_i a_i,0.01),\qquad
b_i=\left\lfloor15\frac{\ln(1+9a_i/P_t)}{\ln10}\right\rfloor
```

Spectrum rendering retains empirical decay and white peak markers. `last_feed_time_` now enforces a 500 ms stale-input threshold and clears old targets without new packets. This threshold is not an end-to-end latency result.

Old `b 150` in the independent gesture/spectrum scripts is replaced by legal brightness 20 and Wi-Fi readiness. Spectrum startup requires a mode ACK, failure releases capture, and restoration messages follow command results. Vision programs still compete for the camera/modes; uncompiled fingertip sources do not resolve those gaps.

<a id="implementation-status"></a>

## Validation, incomplete work, and next steps

An isolated ESP-IDF 5.5.4 build with public example network configuration succeeds; the image is 874800 bytes. Eleven real C++ engine cases and nine Python control/resource-release cases pass. C++ uses a fake clock/LED HAL; Python does not connect serial, UDP, microphones or models. No flashing, recording, audible output or new hardware acceptance occurred. Historical listening/hardware records do not validate this revision.

Historical [voice recovery](VOICE_CONTROL_RECOVERY.md) records thirty fixed semantic cases, two user-confirmed voice scenarios, and 223360 samples written during silent-output checks. These scopes cannot be combined into accuracy/listening metrics. [Panel validation](MATRIX_16X16_VALIDATION.md) records diagnostic patterns and multimode confirmation; 73/74 hardware-check counts include variable polling and are not identical fixed benchmarks.

The latest color record describes an 873920-byte binary whose local SHA256 matches `pants_match_coat_validation`. Build/flash logs and brightness 20/mode 17/mic-off ACKs can be inspected. This is historical evidence, not a new measurement. Dark brown remains unaccepted; stable numeric rendering is not color calibration.

| Status | Content |
| :--- | :--- |
| Traceable main implementation | Single-board driver, effects/companion/games/timer, UDP ACK, single-turn voice, Web control. |
| Independent or lacking unified acceptance | Three vision programs, PyAudio spectra, Android packaging/offline pages, unintegrated fingertip sources. |
| Future targets | Continuous dialogue, MCP service, persistent memory, gaze/pose/fatigue, grasp/throw, gesture games, DDA, wireless audio, MIR, 3D twin. |
| Remaining limits | Remaining limits include browser/board state mismatch, camera/mode arbitration, arbitrary multi-digit scoring, external models/environments and stale Android bundled pages. New locking, timeout and input behavior still require physical tests. |

`requirements-control.txt` pins pyserial 3.5 for the control clients only; it does not install the complete web/vision/voice stack. Full dependencies are not locked and external models/original-machine paths still need configuration. Maintenance fixes preserve historical records and do not imply authorship of all frameworks, models or assets.

The 2026-10 revision validates spectrum fields/ranges and propagates rejection. After 500 ms without input, targets clear and decay continues; zero values no longer keep bottom pixels/peak markers lit. Snake fixes food exclusion, old-tail growth, full-board completion and once-per-tick direction application with a strict 80 ms speed floor. Tetris has a strict 100 ms floor. Rendering, mode/game/spectrum input, brightness and timer state share a recursive mutex.

Countdown requires its dedicated command with integer duration 1–86400 seconds. Direct modes are 0–24 except 18; selecting 25 without duration is rejected consistently by the PC controller, tool schema and firmware. Independent gesture/spectrum scripts now check Wi-Fi control readiness and restore legal brightness 20, without requiring a USB audio connection. They remain standalone programs without unified camera/mode arbitration.
