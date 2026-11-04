# Phase B2 — audio hardening and one five-game batch

This milestone adds formal targets **035, 057, 058, 081, 098**. Registry: **64/100**;
36 remain unregistered. This is a software milestone, not product or physical acceptance.
Historical B1 checks and the existing 59 cartridges are retained.

## Audio contract

The ESP-IDF 5.5.4 implementation of `i2s_channel_write` can return an accepted
prefix together with a timeout. B1 discarded the rest of the event on any short
write. `GameAudioStream` now tracks accepted **mono source samples**, corresponding
to complete stereo-int32 frames (8 bytes). It resumes at the unwritten suffix;
it never replays the prefix. Misaligned or oversized write results are faults.

Each worker poll makes at most one write attempt (up to 160 samples). Playback
mutex acquisition and I2S writes remain zero-wait. The low-priority task yields
one RTOS tick; sample offsets determine the next write deadline, replacing the
unconditional additional 10ms sleep after every write. More than 25ms without
progress, or nominal tone duration + 40ms, drops the tone. It does not accumulate
an unbounded retry backlog. These budgets are dropout policies, not a guarantee
of continuous physical sound.

Speech/music's existing 500ms reservation and microphone capture gate are checked
on every attempted write. Preempted suffixes are discarded. A new event can play
after the priority window/capture ends; no old tone resumes. Muting or changing
the game invalidates pending/in-flight events. Speaker power transitions still
use the existing AudioHAL/SDK path; actual wake and DMA latency are unmeasured.
No voice model, master volume, Wi-Fi PCM authentication or music path was changed.

Fresh gameplay events no longer share a blanket 30–45ms enum cooldown. Distinct
rapid hits/chords/actions are accepted until the bounded queue fills. Producers
may supply a nonzero operation identity for local duplicate suppression, keyed
by operation, kind, game, detail and session generation. The 16-identity history
is bounded and is **not** a replacement for authenticated UDP replay protection:
replayed network commands still return their cached ACK without redispatch.

Device arcade status exposes `sound_busy`, `sound_short_writes` (includes zero
progress), `sound_late`, `sound_faults`, `sound_duplicates`, plus existing
played/dropped/preempted counts. PC Web forwards these counters; APK receives the
same raw device state. `sound_played` means all samples were submitted, not heard.
Queue-full/old events can still be deliberately dropped; this is not lossless audio.

Host tests exercise the same production stream and byte-to-sample conversion
used by AudioHAL: busy/partial writes, exact accepted PCM sequence, zero-progress
timeout, 10ms jitter, larger scheduling stalls, malformed results, rapid distinct
events, identity duplicates, mute, external-PCM priority and capture recovery.
They do not emulate ESP32 DMA timing or certify acoustic performance.

## Actual game scope

| Target | Independent rules and goal | Easy / Normal / Hard |
|---|---|---|
| 035 Boulder Dash | Dig dirt, collect eight gems, horizontally push rocks, falling/rolling rocks crush the player; leave through the unlocked exit. One authored cave. | Rock tick .18/.14/.10s; time 90/65/45s |
| 057 Rush Hour | A/B select seven fixed-axis vehicles; directions translate the selected car; free the red target at the right edge. One authored 6×6 board, solved by legal-state BFS. | 50/30/16 actual moves; time 120/90/60s |
| 058 Program Robot | Queue relative forward/turn/wait commands before execution; a switch opens a gate on the route to the goal. Collision or a program ending away from the goal loses an attempt; three failures lose. One authored board. | Buffer 20/17/14 commands; execution .30/.24/.18s; time 100/75/50s |
| 081 Qix | Move on safe ground, arm drawing with A, close a vulnerable trail; flood-fill captures the side without the moving enemy. Enemy or self-trail contact loses. | Capture 50/60/70%; enemy tick .10/.08/.06s; time 90/70/55s |
| 098 Lunar Lander | Rotate and thrust with limited fuel in continuous 2D gravity/wind; land slowly and upright on the green pad. Wrong ground, unsafe speed/attitude, bounds or timeout loses. | Pad half-width 3/2/1; fuel 45/35/25; downward limit 1.4/1.1/.8; horizontal limit .7/.55/.4; gravity/wind differ |

All five provide C++ production cartridges, independent Python simulators,
title/play/pause/resume/terminal/restart flow, scoring, bounded RGB frames,
meaningful difficulty and action events. They reuse only lifecycle/drawing helpers;
none is an existing game renamed. This batch uses original synthesized sounds and
code-drawn pixels; it does not import commercial game artwork or recordings.
`release_year=2026` describes these project adaptations, not the original titles.

Difficulty uses the existing authoritative `config` protocol and is locked while
playing/paused. Nine cartridges now support that setting (B1's four plus these five).
Settings remain RAM state. Reset/selection retains the tier; reboot defaults to Normal.
The LED render target remains approximately **30FPS**, with approximately **60Hz
logic**. No unmeasured claim about button-to-LED latency is made.

## Existing complex-game acceptance: 055 Mirror Laser

All four authored optical boards are replayed through cursor/rotation/fire input.
Intermediate mirror arrangements previously started a 0.45s bomb timer during
editing. This made a spatial puzzle depend on unrealistically quick cursor input.
A now rotates and enters safe preview; B explicitly fires/stops. A bad preview
does not consume a life, while firing into a bomb still does. SELECT resets the
current board; the existing top-level restart resets the whole round. A top-right
cyan/orange pixel distinguishes preview/fire. Phone labels/help match this rule.
Both languages test wrong-fire failure and slow editing plus all four-stage wins.

## Evidence and limits

- `scripts/solve_phase_b2.py --output <explicit path>` independently searches legal
  Rush Hour moves, plans Qix cuts by replaying the real rules, and drives a feedback
  lander controller. It generates input-only witnesses without modifying terrain,
  enemies, counters or terminal state to win.
- `tests/fixtures/phase_b2_input_paths.json` freezes 15 three-tier wins plus the
  four-stage Mirror Laser round, with a 16667us input timestep.
- Python and the production C++ host harness independently replay those exact
  inputs. Separate controlled collision fixtures test rock crush/push, blocked
  cars/move exhaustion, program capacity/gate/failures, Qix collisions and unsafe
  landing. Test fixtures are not used to manufacture full-round success.
- All 64 receive variable-frame/canary regression; original pairing/replay,
  lifecycle, Pong mode and independent multi-touch release checks are retained.
- Real aiohttp HTTP/WS tests cover all 64. Actual Chrome checks new control
  descriptions, Pong 36→4→0 and Lander 18→2→0 touches. APK 1.4.0 packages the same
  web files. These are simulator/browser/loopback integrations, not phone/ESP32 tests.

Full-round software checks prove the frozen authored scenarios can be completed
and fail correctly. They do not establish human fun, universal seed fairness,
physical LED readability, real audio continuity, physical input latency, power/NVS
cycling or long wall-clock stress. No board was flashed, no APK installed and no
audible test run. Those checks remain pending with a backup/recovery plan.

This task stops after this single five-game batch. Remaining 36 targets and other
games' full-round/difficulty/action-audio acceptance are future batches.
