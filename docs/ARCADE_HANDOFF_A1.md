# Arcade handoff and Phase A.1

Development branch: `arcade-100-audit-and-elevation`. Do not merge into `main`
as part of this milestone. The target catalogue contains 100 designs; the
integrated registry currently contains **59**, including the original 13 and
46 cartridges inherited from Antigravity. The remaining **41 are not registered**.
Archived games with similar numbers are not substitutes for these target IDs.

`pc-agent-vision/arcade/registered_games.json` records the integrated classes.
`tests/test_arcade_handoff.py` checks it against C++, CMake, Python, Java and JS.
Unavailable cards are disabled in the UI and rejected by the protocol.

## Transport behavior

- Inputs, heartbeat and lifecycle actions keep an ordered control lane.
- Frame/status queries use a bounded disposable readback lane. Android and Python
  use a second, stable authenticated client identity and independent replay
  sequence. They share the existing token/boot challenge, not an unauthenticated
  bypass. Frame loss cannot hold the control socket or its send/state lock.
- Late readback cannot overwrite a newer acknowledged control result. A frame
  failure does not clear held keys. Actual control failures clear input, attempt
  release/pause and require an explicit resume. Board watchdogs still release at
  500 ms and pause at 1000 ms; heartbeat/readback never implicitly resume play.
- Firmware queues up to 32 press edges without per-input heap allocation, consumes
  one per game tick and clears the queue on pause/reset/selection/exit/watchdog.
  Overload returns failure and pauses instead of silently losing press edges.
- UDP retries retain the exact request identity/payload. Readback does not weaken
  boot, sequence, digest or request-ID checks. The protocol remains plaintext
  local-network pairing, not encrypted transport.

## Pong

`{"cmd":"arcade","action":"players","count":1}` selects AI; `count:2`
selects local two-player. Other values/types and other cartridges are rejected.
The reply's `arcade.player_count` is authoritative. Selection clears held keys,
preserves lifecycle/scores and survives reset/restart; selecting the cartridge
afresh defaults to AI. P1 uses UP/DOWN, P2 A/B. START retains its existing role.
Mode changes while paused do not resume the match.

## First Web pairing

`paired_http.js` shares one pairing operation across concurrent explicit 401
rejections. A successful `/api/pair` is checked before saving the token and
retrying each rejected operation once, including uploads. The server's auth
middleware rejects these requests before their business handler runs.
Timeouts/network failures are uncertain outcomes: mutations are not replayed;
status is queried first and the UI asks the user to confirm before repeating.
An invalid/cancelled token does not start an automatic prompt loop. Connection
settings allow a new explicit attempt.

## Verification boundaries

The host harness compiles the actual 59 production C++ cartridges and runs 1800
input/update/render ticks per cartridge with buffer canaries. Python exercises
the same registry and lifecycle. This is not 30 minutes of wall-clock device
stress, visual acceptance or proof of complete rounds for every game.

New explicit full-round checks solve both authored Hanoi levels and all four
mirror-maze levels through actual game input. The existing first-batch gameplay
suite remains separate. Other newly integrated games require deeper game-specific
complete-round, fairness and difficulty acceptance. Shared game audio and uniform
difficulty are not certified by this handoff.

No firmware flashing, phone installation, physical LED/voice/audio/power tests
or real NVS power-cycle tests are performed here. Follow the deployment/backup
and pairing guidance in [PHASE_A_NETWORK.md](PHASE_A_NETWORK.md) before a separately
authorized physical test. Android 1.2.1 builds the same web assets as the PC UI.
