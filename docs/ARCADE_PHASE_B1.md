# Phase B1: shared infrastructure and four-game quality batch

This milestone retains 59 registered target cartridges; the remaining 41 are
not added here. It does not certify all 59 as finished products.

## Time ownership

The display task remains the only game-logic/render owner under DisplayLock.
Every cartridge advances through `FixedStepClock` at 16667 microseconds per step
(approximately 60 Hz), driven by actual monotonic elapsed time. Render sleep
subtracts work already spent from its approximately 33ms frame budget.

At most four logic steps are run per rendered frame. Additional whole steps are
discarded and counted; the fractional remainder is retained. This prevents an
unbounded recovery loop after a long stall. Mode changes reset the accumulator.
Watchdog release/pause still use real monotonic time, independently of game dt.
`timing_dropped_ms` is a cumulative diagnostic, not a measured FPS promise.
Python's explicit simulator uses the same integer step/catch-up contract.

## Shared sound

`arcade_sound.h` defines a fixed-capacity event bus and synthesized tone profiles
for menu/start/pause/score/hurt/win/loss/action/beat/hit/jump/shot/collision.
Game Update only tries to enqueue; it never sleeps, waits on I2S or allocates a
PCM buffer. Busy/full/too-frequent events are dropped. Events older than 180ms,
or from an invalidated selection/pause/exit generation, are discarded.

One low-priority `arcade_sfx` worker renders small 16kHz PCM chunks through the
existing AudioHAL output. Game playback attempts the existing mutex and I2S write
without waiting. External PCM reception/playback reserves priority for 500ms;
active microphone streaming also mutes game audio. A game event preempted by
speech/music/capture is dropped, not resumed later. The existing speech PCM,
USB/Wi-Fi transports, master volume/gain and voice model are unchanged.

All 59 cartridges have common lifecycle/score/life/terminal event hooks.
The selected batch additionally connects rhythm beat/hit, lemming skill action
and fruit hit/combo events. Event enum availability does not mean every individual
action in all 59 games is already hooked. Jump/shot/collision hooks for the
remaining games are part of later per-game acceptance.

`sound_played` counts complete tones submitted to I2S, not acoustic acceptance.

No audible test was run here. Queue/synthesis/priority policy tests and firmware
construction do not establish I2S listening quality, acoustic echo performance,
speaker loudness or exact preemption latency on hardware.

## Settings protocol

Authenticated arcade command, across APK UDP and PC Web:

```json
{"cmd":"arcade","action":"config","sound_enabled":true,"sound_volume":25,"difficulty":2}
```

`sound_enabled` is boolean; `sound_volume` is integer 0..100. Optional integer
`difficulty` is 0=Easy, 1=Normal, 2=Hard. Only 017/085/092/095 support difficulty
in this milestone. Other games reject a supplied difficulty rather than pretending
to apply it. Omit difficulty to change sound alone. Invalid settings or changed
difficulty during PLAYING/PAUSED are rejected without partially changing settings.
Apply difficulty from title/terminal state; it resets the round. Settings are RAM
state, not NVS persistence. Per-cartridge difficulty survives a reset/selection
within the running process. Reboot starts at Normal. The device response's
`difficulty_supported`, `difficulty`, `sound_enabled`, `sound_volume` are authoritative.
Android 1.3.0 displays these controls; active rounds lock the difficulty selector.
The older global difficulty slider still controls the older engine, not these
cartridges. The new per-cartridge controls are explicitly separate.

## Selected quality batch

| Target | Actual difficulty changes | Software full-round acceptance |
|---|---|---|
| 017 Rhythm Lanes | Beat interval .50/.40/.32s, travel exactly three beats, judge window 2.0/1.8/1.4 pixels, max misses 10/8/5 | 64 notes through actual lane presses at each tier, no-input loss, hit/beat events, restart/pause |
| 085 Lemmings | Rescue 2/3/4 of five, stage limit 70/55/45s | All three authored stages via cursor/skill presses at each tier; no rewritten terrain or rescue counters |
| 092 Fruit Slice | Lives 5/3/2, hit radius 1.9/1.65/1.4, different spawn intervals | Slice at least 40 while avoiding bombs at each tier; no-input loss; slash animation enforces repeat cooldown |
| 095 Super Hexagon | Initial shrink 3.0/3.8/4.3 and cap 4.0/5.0/5.5 | Reach 30 walls or 45 seconds via directional input at each tier; no-input loss and restart |

`tests/test_phase_b_gameplay.py` and `tests/phase_b_core_test.h` exercise both
Python and the actual production C++ games. Winning scripts read game state to
choose inputs; they do not force progress, move enemies or overwrite terrain.
These deterministic policies establish solvability/terminal behavior for the
authored scenarios, not human fun, universal seed fairness or physical readability.
All 59 also receive variable-frame fixed-step regression, including bounded stalls.

Real phone/ESP32 testing, listening, long wall-clock stress, power/NVS cycling,
and additional per-game tuning remain pending. Do not flash without a separately
authorized backup/recovery plan. Phase A pairing and replay protection remain.
