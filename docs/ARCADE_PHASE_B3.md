# Phase B3 — 36 remaining targets

Current verified checkpoint: **1/6**, **70/100 registered**. This is software integration, not final product/hardware acceptance.

| Group | IDs | Status |
|---|---|---|
| 1 | 007, 008, 011, 012, 013, 023 | BUILD + INPUT_REPLAY_PASSED |
| 2 | 024, 025, 032, 036, 037, 039 | PENDING |
| 3 | 046, 047, 048, 049, 050, 056 | PENDING |
| 4 | 059, 060, 061, 068, 069, 070 | PENDING |
| 5 | 071, 077, 078, 079, 080, 082 | PENDING |
| 6 | 089, 090, 091, 096, 099, 100 | PENDING |

## Evidence boundaries

Each completed group has independent C++ and Python rule implementations, three real difficulty profiles, fixed-size firmware state, action sound events and bounded 16x16 rendering. `BatchCartridge` shares lifecycle/drawing only.

`scripts/solve_phase_b3.py` produces input-only win/loss witnesses at 16667us. Jump planning, legal puzzle solving and feedback controllers may inspect or copy the simulator to plan; they never assign terrain/progress/terminal state to manufacture a victory. `tests/phase_b3_core_test.h` replays the same inputs in production C++ and compares score, lives, state, progress and game-specific key positions/states.

Score/lives/terminal state are exact; continuous key fields allow 0.03 units and HUD progress one percentage point for floating-point rounding. Circular tolerance is restricted to the rotating knife target angle. The original test suites and -Werror remain.

All original pairing/replay, priority audio, power limiter, NVS/OTA layout, non-arcade functions and the inherited 64 cartridges are retained. No flash, APK installation, speaker listening, actual DMA/latency measurement or physical acceptance has been performed. Software checks do not establish human fun, exhaustive seed fairness or final product quality.

Detailed raw logs, builds and final reports are kept outside the repository in the task cache/artifacts. Remaining checkpoints continue automatically within the same task.
