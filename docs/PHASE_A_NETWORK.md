# Phase A: paired LAN control and arcade transport

Scope: critical communication, persistence and access-control repairs on
`arcade-100-audit-and-elevation` (2026-11-04). No Phase B game expansion, sound
system, difficulty overhaul, or hardware flashing is included.

## Connection modes

- Android **ESP32 direct**: the packaged page calls the bounded asynchronous native
  UDP client. The 13 registered Target IDs are 001, 009, 010, 020, 021, 026, 033,
  034, 038, 041, 054, 074 and 097. No running PC is needed for this arcade path.
- **PC Web**: the same frontend contract goes through `/api/arcade` and the existing
  Python gateway. Voice, music, vision and model inference still need the PC.
- **Simulator**: explicitly start `web_server.py --simulate --no-audio`. Every
  simulated response is labelled. A missing board never enables simulation.

These are implementation modes, not a claim of physical-device acceptance.

## Pair a board once

The new firmware and new clients must be deployed together. Older unauthenticated
UDP/PCM clients are intentionally rejected. **This task does not flash a board**;
before any later firmware deployment, verify the existing partition layout and
back up NVS, then obtain authorization for the specific safe update procedure.

After that authorized update:

1. Use the board's physical USB serial terminal (close software holding the port).
   Send `{"cmd":"pair"}` as one line. The response contains `control_token`.
   It is a 64-character hex secret, persisted in NVS, not the Wi-Fi password.
   This command does not disclose its key over UDP. Do not commit or publish it.
2. In APK connection settings choose **ESP32 街机直连**. Enter its actual AP or STA
   IPv4 address and the token. The AP default is offered as a preset, not the only
   permitted address. Native settings permit host addresses in 10/8, 172.16/12
   and 192.168/16; DNS names, broadcast endpoints and other ports are rejected.
3. For the PC, set `KURISU_BOARD_IP` and `KURISU_CONTROL_TOKEN`, or save
   `{"control_token":"<your key>"}` as `control-pairing.json` in the runtime data
   directory (`%LOCALAPPDATA%\KurisuPro`, overridable by `KURISU_DATA_DIR`).
   Keep that file private and outside the repository. Discovery beacons never
   replace a selected target or receive credential-bearing broadcast commands.
4. UDP clients obtain the current public boot nonce, then send authenticated
   envelopes. A board reboot returns `boot_changed`; clients invalidate their
   nonce and require a subsequent explicit request, rather than replaying an
   uncertain action across reboot.

NVS initialization failure does not erase data automatically. Display/USB remain
available; persistence/network setup report failure. Resolve storage exhaustion
or incompatible NVS through a separately authorized backup/recovery procedure.
Pairing key creation/commit failure fails closed. No key is printed at boot.

## PC Web, MCP and WebSocket access

Default startup listens on `127.0.0.1`. Local scripts and same-origin localhost
pages remain usable. To allow paired phones on the LAN, explicitly start:

```powershell
python pc-agent-vision/web_server.py --host 0.0.0.0 --no-audio
```

The normal audio-enabled startup is still supported; `--no-audio` above is only
an example for silent administration. No audio gain, model, voice or LED mapping
was changed by this phase.

At CLI startup a persistent `web-access-token` file is created in the runtime data
directory unless `KURISU_ACCESS_TOKEN` (at least 32 characters) is configured.
Read it locally and enter it when the remote webpage asks. This web token is
separate from the board token. Non-browser clients use `Authorization: Bearer ...`.
`POST /api/pair` exchanges that header for an HttpOnly, SameSite=Strict cookie, so
the browser's WebSocket can authenticate without putting secrets in URLs.

- All `/api/`, `/mcp`, `/ws` and `/xiaozhi` routes are guarded, including memory,
  uploads, camera/audio controls and tool execution. WebSocket upgrades must pass
  the same policy. Existing tool-name/schema validation remains in place.
- Origin must match the exact scheme/host/port or an explicit comma-separated
  `KURISU_ALLOWED_ORIGINS` entry. Wildcard CORS is removed. Origin `null` is denied.
- Local anonymous access also checks the Host header against localhost/loopback,
  limiting DNS-rebinding exposure. Forwarded headers are not trusted.
- An existing strong `KURISU_XIAOZHI_TOKEN` (32+ characters) is accepted only for
  `/xiaozhi/v1/`; it does not authorize ordinary Web APIs. That optional adapter
  must still be explicitly enabled and retains its own token check.
- Regular API request bodies are limited to 64 KiB (also for chunked input), music
  uploads to 20 MiB, and reference-document ingestion to 1 MiB so the existing
  100,000-character document feature still works with JSON escaping. WebSocket
  messages are limited to 64 KiB and rate checked after upgrade as well; at most
  32 ordinary WebSocket clients are active. Per-peer accounting stays bounded.
- APK native UDP is available only to its exact packaged page. CSP disallows
  frames/objects; external resources are blocked for the packaged page. Remote
  Web pages cannot use the bridge. Activity epochs reject old-page replies.
  Native targets/commands/lengths are validated, queues/retries/timeouts bounded,
  and callback JSON is encoded with `JSONObject.quote`.
  The all-frame bridge exposure is documented by [Android Developers](https://developer.android.com/privacy-and-security/risks/insecure-webview-native-bridges).

**Protection boundary:** HTTP, UDP and PCM here are plaintext. Pairing is access
control, not confidentiality, cryptographic peer authentication, or protection
against a LAN eavesdropper who steals a bearer token. Use a trusted WPA2-protected
LAN/AP or an appropriately configured secure tunnel/TLS deployment. Do not expose
these ports to the Internet. No cloud identity system was introduced.

## UDP contract and safe input

```json
{"request_id":"123_unique_request_id","client_id":"persistent_client_id","seq":123,
 "boot_id":"current_boot_nonce","token":"private_board_token",
 "command":"{\"cmd\":\"arcade\",\"action\":\"input\",\"down\":18,\"pressed\":16}"}
```

Canonical actions: select/start/pause/resume/reset/exit/input/heartbeat/status;
frame readback uses `{"cmd":"frame"}`. The frontend accepts both action-style
and path-style arcade requests. `stop` is adapted to `exit`.

- Native replies must match the request ID and have `status:"ok"`; arcade state
  and the full 1536-character RGB888 pixel string are validated. `arcade` is
  adapted to frontend `game_status`; source tags remain explicit.
- Retries reuse exactly the same envelope. Firmware uses full SHA-256 command
  digests, peer/client-scoped IDs, a 16-reply fixed cache (2304 bytes per response),
  and replay high-water marks for up to 32 client identities per boot. Different
  payloads/sequence numbers reusing an ID are conflicts. Evicted older requests
  are rejected as stale, never re-executed; full frames are cached untruncated.
  IDs have the form `<seq>_<unique suffix>`, so an old ID cannot be reused with
  a newer sequence after cache eviction. Native callback IDs are restored only
  after their corresponding wire reply has matched exactly.
  Capacity exhaustion is reported rather than silently evicting replay state.
  Clients persist identities; changing many identities/IPs can require a planned
  reboot. This is bounded LAN reliability protection, not an anti-MITM protocol.
- State snapshots share the display mutex with rendering and game lifecycle
  changes. The display task continues to own the physical game update loop.
- A held key is part of a combined bitmask: right + A = 18; releasing A keeps 2.
  Press edges are separate from held state. Input/heartbeat, frame queries and
  lifecycle commands have different bounded retry budgets. No synchronous bridge
  fallback remains. Frame polling has backpressure.
- Leaving the page/backgrounding releases keys and requests pause; old replies
  cannot resume play. On communication failure input is blocked until explicit
  select/start/resume. Firmware clears input after 500 ms and pauses after 1000 ms
  without input/heartbeat. Reconnection alone does not resume the game, including
  Mario's pre-play READY transition.
- NVS writes are buffered in RAM and committed at lifecycle/round boundaries.
  Failed open/read/set/commit preserves dirty records for retry. Static cartridge
  construction does not access NVS. Active-play Mario records now enter the same
  RAM store, so reset/exit cannot silently lose them.
  Storage lifecycle follows the [ESP-IDF 5.5 NVS API](https://docs.espressif.com/projects/esp-idf/en/v5.5/esp32s3/api-reference/storage/nvs_flash.html);
  host adapters below do not replace its physical flash tests.

## Reproduce software checks

Set `PYTHONDONTWRITEBYTECODE=1`, `PYTHONPATH=pc-agent-vision`, `KURISU_TEST_TMP`,
`KURISU_DATA_DIR` and `KURISU_CACHE_DIR` to task-specific directories **outside**
the repository. Use the configured Python environment, not an assumed global one.
The native runner optionally accepts `--json-jar <cache>/json-20240303.jar` to
exercise the production `DeviceUdpClient` on JVM loopback sockets (port 8888 must
be free). This pins the SHA-256 of the upstream [JSON-java 20240303 release](https://github.com/stleary/JSON-java/tree/20240303);
the test-only JAR stays outside Git and is not packaged in the APK. Android's
own `org.json` remains the production runtime, so real phone acceptance is still
required.

```text
python -B -m unittest discover -s tests -p test_*.py
python -B scripts/test_interaction_regressions.py
python -B scripts/test_semantic_control.py
node --check pc-agent-vision/web_app/app.js
node --test tests/phase_a_transport.test.cjs
python -B scripts/test_phase_a_native.py --work-dir <task-cache>/native --idf-path <ESP-IDF> --java-home <JDK>
python -B scripts/test_phase_a_http.py --url http://127.0.0.1:<simulation-port>
```

The native test compiles the actual C++ store, 13 cartridges, manager, protocol
validator and replay cache. Its fault-injectable file-backed **host NVS adapter**
tests startup order, failed writes/commits, concurrent producers and fresh-process
reload; it does not prove physical flash retention. The Java harness tests pure
bridge policy; APK construction is separately required. The HTTP script refuses
to run against a service not explicitly marked simulated.

## Physical acceptance still required

No ESP32 was flashed and no APK installed during Phase A. After a safely planned
deployment, verify AP and STA independently; APK-only control of all 13 IDs;
right + jump and partial release; rapid taps/long holds/touch cancel; page/background
switching; power/Wi-Fi loss and explicit resume; frame/HUD synchronization; NVS
high-score recovery after actual power cycling; and rejection of unpaired UDP,
HTTP/MCP/WebSocket and PCM peers. Confirm lights, pet, voice and music on the
existing hardware/audio baseline. OTA migration, current measurement, complete
game rounds, difficulty and sound design remain outside this Phase A milestone.
