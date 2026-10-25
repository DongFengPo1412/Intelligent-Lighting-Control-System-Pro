# Limited board verification records

[简体中文](hardware-checks-20261023.zh-CN.md) · [English](hardware-checks-20261023.en.md) · [日本語](hardware-checks-20261023.ja.md)

Summarized on 2026-10-24 from existing 2026-10-23 logs for the locally fixed build. These are not a fresh flashing session or complete acceptance.

## Recorded checks

| Item | Evidence and scope |
| --- | --- |
| Control | The earlier canvas command timed out waiting for ACK. With IPv4 reassembly enabled, 155 checks passed, including valid/invalid commands, full canvas, frame reads and countdown request deduplication. |
| Playback samples | USB and Wi-Fi each received/played 111680 samples, with zero recorded drops or write errors. |
| Microphone samples | 99600 USB and 84000 Wi-Fi samples, with zero recorded clipped samples; not recognition, listening-quality or end-to-end latency tests. |

After newline normalization, 37 comparable firmware source/header/build files match the delivered application sources. Configuration and image identity are separate; no byte-identical binary claim is made. Two diagnostic files excluded from the production entry were absent from the earlier test copy.

These records do not establish endurance, subjective audio acceptance, AEC/false wakes, all visual modes, gaze accuracy, DDA effectiveness, Android installation or discovery. A control ACK confirms command handling, not optical output from every LED.

Physical entry: `scripts/test_pro_board.py --output-dir <task-cache>`; the audio script requires either `--playback` or `--microphone`. These entries change device state. Announce playback/sampling first and stop conflicting services; direct outputs to a new task cache outside the repository.

## 2026-10-24 follow-up: startup and wiring

- Ollama started from a stopped state; model and parsing-prompt warmup completed before listening. The first metaphorical planning request correctly selected aurora in about 3.55 seconds externally, without executing a display or speaking.
- A local DNS-SD client found `192.168.178.90:8080`; this is not Android discovery acceptance.
- Camera index 0 returned a nearly black image; index 1 produced real hand observations and mode-26 board ACKs. No photos or videos were saved. Before the wiring correction, the user reported a split cursor and a stationary square also split; fingertip appearance failed acceptance at that stage.
- The board application descriptor matched the last image flashed on 10-23. Human observations of RGB endpoints and all 16 row starts established that the current physical panel runs left-to-right on every row, unlike the previous serpentine output.
- Added `PRO_MATRIX_SERPENTINE`, default `OFF` for this panel, with `ON` retaining serpentine support. Full addressing compile checks passed for both settings. The 889152-byte production image was flashed and verified; 155 silent physical checks passed again.
- The user confirmed that the corrected 2×2 square was intact, then accepted rightward/upward fingertip following and stability after stopping as all normal. On camera 1, 23 of 24 sampled observations contained a hand and the board remained in mode 26. This is not a formal end-to-end latency or long-term tracking-loss measurement.
- The user also accepted sandbox grabbing and release as normal. A 20-second sample contained 46 observations, including 10 camera pinch states; actual PWM frames contained the pink grabbed point in 12 samples and the pale released point in 34, with mode 27 maintained. This is limited-scenario acceptance, not physical-accuracy or metric-depth validation.
- At fixed medium difficulty with adaptation disabled, the user accepted all four Tetris gesture directions. Board logs recorded 9 left, 13 right, 24 rotate and 4 drop commands, followed by score mode 22. Adaptive-difficulty experience was not established by this test.

## 2026-10-25 follow-up: music and panel fault isolation

- The same eight-second melody compared the original field, 16-column FFT and new music halo. The halo uses all 16 bands, RMS, onsets and phase for deterministic concentric expansion. The user accepted its layers, visual effect and natural following. Full songs remain untested; no best-possible effect or separate fundamental-frequency accuracy claim is made.
- Audible halo playback received/played 128000 samples each, with zero drops/write errors. It dispatched 232 feature frames, skipped 17 stale windows and recorded approximately 93 ms maximum command dispatch lag; final silent frames were black. This is not an objective audiovisual latency measurement.
- With 16-band argument validation, 162 silent board control checks passed. The music image is 890576 bytes, SHA-256 `cbc167d7153b35c0ebe204f7e1c0aafe758f442013b372415e05ad22c547fbe9`.
- The original panel's last-row pixel eight (index 247) had an update delay. Off, fixed red and a white locator worked, but uniform cycling and slow three-pixel blue-to-white transitions lagged despite equal software frame values. Raising RMT DMA symbols from 128 to 2040 did not help; a task-cache-only SPI DMA image was also used for comparison. The user replaced the panel and confirmed normal behavior, closing this as an original-panel hardware issue without identifying a specific failed component. At the user's request, testing ended and the production RMT image above was restored. The SPI diagnostic is not a delivered implementation.
- The music adapter also updates offline WASM interface sources. That WASM has not been rebuilt; old binaries do not validate the new halo preview.
- After panel replacement and production RMT restoration, the same eight-second melody was replayed at 70% volume with the halo. The user accepted sound, natural following, final silent decay and pixel-eight synchronization. Receive/play counts were 128000 each, with zero drops/errors; 235 feature frames, 13 skipped stale windows, approximately 215 ms maximum command dispatch lag and a final black halo frame were recorded. This accepts a short melody, not full songs or objective audiovisual latency.

## 2026-10-25 local library integration

- Read-only indexing found 2236 tracks (2234 MP3, two FLAC); title/artist tags and web search were checked. Songs were neither moved nor uploaded, and private paths/tag caches remain outside Git. This milestone changes PC code only; firmware was not modified/flashed. See the [guide](LOCAL_MUSIC.en.md).
- Initial web playback of an Alone excerpt followed the music visually but sounded severely distorted to the user. The first 30 seconds had mono RMS about 0.211 versus 0.0228 for the earlier melody. With board volume fixed at 70% and microphone off, eight-second original-level and 0.25-level excerpts each received/played 128000 samples with zero drops/errors. The user judged the original distorted and the attenuated version very good. Default music-only gain is now 0.25; MIR input and speech level are unchanged. The exact hardware distortion mechanism is not established.
- Real ASR errors for Jay Chou/Qi Li Xiang failed matching initially. Added homophone matching, bounded pronunciation scoring/margins and frequent-artist spelling hints after waking. Ambiguities require selection; both observed errors are offline regressions.
- The user then accepted real voice song requests, wake during music, next and stop, with sound restored. Logs show Qi Li Xiang playing and next selecting San Nian Er Ban, plus the stop command. The broader pronunciation fallback/hints were subsequently checked offline, not across arbitrary accents.
- Whole-song counter completion, every-file compatibility, endurance and music false-wake rates remain unmeasured. Excerpt and limited-operation acceptance do not establish whole-library or acoustic AEC acceptance.
