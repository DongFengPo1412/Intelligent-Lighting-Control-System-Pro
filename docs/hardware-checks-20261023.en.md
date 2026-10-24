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
