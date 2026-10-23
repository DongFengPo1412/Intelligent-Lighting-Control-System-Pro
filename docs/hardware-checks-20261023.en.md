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
