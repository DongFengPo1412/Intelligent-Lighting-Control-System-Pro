# Phase B3 — 36 remaining targets

Current verified checkpoint: **6/6**, **100/100 registered**. This is software integration, not final product/hardware acceptance.

| Group | IDs | Status |
|---|---|---|
| 1 | 007, 008, 011, 012, 013, 023 | BUILD + INPUT_REPLAY_PASSED |
| 2 | 024, 025, 032, 036, 037, 039 | BUILD + INPUT_REPLAY_PASSED |
| 3 | 046, 047, 048, 049, 050, 056 | BUILD + INPUT_REPLAY_PASSED |
| 4 | 059, 060, 061, 068, 069, 070 | BUILD + INPUT_REPLAY_PASSED |
| 5 | 071, 077, 078, 079, 080, 082 | BUILD + INPUT_REPLAY_PASSED |
| 6 | 089, 090, 091, 096, 099, 100 | BUILD + INPUT_REPLAY_PASSED |

## Evidence boundaries

Each completed group has independent C++ and Python rule implementations, three real difficulty profiles, fixed-size firmware state, action sound events and bounded 16x16 rendering. `BatchCartridge` shares lifecycle/drawing only.

`scripts/solve_phase_b3.py` produces input-only win/loss witnesses at 16667us. Jump planning, legal puzzle solving and feedback controllers may inspect or copy the simulator to plan; they never assign terrain/progress/terminal state to manufacture a victory. `tests/phase_b3_core_test.h` replays the same inputs in production C++ and compares score, lives, state, progress and game-specific key positions/states.

Score/lives/terminal state are exact; continuous key fields allow 0.03 units and HUD progress one percentage point for floating-point rounding. Circular tolerance is restricted to the rotating knife target angle. The original test suites and -Werror remain.

All original pairing/replay, priority audio, power limiter, NVS/OTA layout, non-arcade functions and the inherited 64 cartridges are retained. No flash, APK installation, speaker listening, actual DMA/latency measurement or physical acceptance has been performed. Software checks do not establish human fun, exhaustive seed fairness or final product quality.

Detailed raw logs, builds and final reports are kept outside the repository in the task cache/artifacts. All six software checkpoints are complete. Further physical or product-quality work requires its own acceptance evidence.

## Final software verification

- `tests/`: 2176 tests, 2175 passed and one optional WASM-renderer test skipped. These include inherited tests; the count is not the number of games.
- All 100: manifest/source/registry/transport/CMake consistency, 1800-frame native bounds/lifecycle runs, Python input runs and real HTTP routes on an explicitly simulated server.
- New 36: 216 real-input witnesses (win and loss at all three tiers), production C++ vs Python score/lives/terminal/key-state checks. Each witness resets/pauses/resumes normally.
- JavaScript transport/pairing: 16 passed. Production Java UDP loopback/pairing/retry/lifecycle and C++ NVS/replay/watchdog/audio tests passed.
- Real headless Chromium: 100 registered / 0 planned, all new help/control mappings, Pong and lander independent multi-touch release, acknowledged difficulty and sound settings. This is not Android touchscreen acceptance.
- ESP-IDF 5.5.4 firmware and signed debug APK 2.0.0 (versionCode 12) built. All 14 packaged web assets match source SHA-256.
- Accelerated Python run: 240000 ticks, 200 game switches, 4000.08 simulated seconds. This took seconds of wall time and does not certify physical long-run stability.

## New game rules and tier differences

All rows below have REGISTERED / BUILD_PASSED / UNIT_TEST_PASSED / FULL_ROUND_HOST_PASSED / SIMULATOR_PASSED / HARDWARE_NOT_TESTED. FEATURE_COMPLETE remains unclaimed. Frame bounds and simulator overview inspection are distinct from physical LED readability. Sound event presence does not establish audible quality.

| ID | Game / independent rule | Easy / Normal / Hard | Cartridge sound events | Input-only rounds |
|---|---|---|---|---|
| 007 向下射击 | Fall through a vertical shaft, fire downward with finite ammo, reload on shelves and defeat enemies before landing. | 生命3/2/1；弹药4/3/2 | collision, hit, shot | 3 wins + 3 losses, C++/Python |
| 008 蓄力跳跃 | Charge then release a ballistic jump between elevated platforms; failed landings lose altitude. | 重力8/8.5/9；限时100/80/65s | jump | 3 wins + 3 losses, C++/Python |
| 011 恐龙跑酷 | Automatic running, grounded jump timing, accelerating obstacles and a twelve-obstacle survival milestone. | 初速3/4/5；障碍高度1/2/3 | collision, jump | 3 wins + 3 losses, C++/Python |
| 012 旋盘投刀 | Throw knives into a rotating target while avoiding all already embedded blade angles. | 目标8/10/12刀；转速0.8/1.1/1.5 | collision, hit, shot | 3 wins + 3 losses, C++/Python |
| 013 摆锤投球 | Release a swinging bob with its tangential velocity and land inside three baskets with limited balls. | 篮筐半宽2.5/2/1.5；球数6/5/4 | action, collision, hit | 3 wins + 3 losses, C++/Python |
| 023 空气曲棍球 | Move a two-dimensional paddle, deflect a puck, use a close-range power strike and score three goals against bounded AI. | AI移动0.8/1.3/1.8；回击速度5/6/7 | collision, hit, shot | 3 wins + 3 losses, C++/Python |
| 024 弹珠撞靶 | Aim a finite supply of gravity-driven balls; collide with and remove every peg. | 弹数10/8/6；初速6/7/8 | hit, shot | 3 wins + 3 losses, C++/Python |
| 025 滚珠平衡迷宫 | Tilt acceleration and inertia, wall bounces, lethal pits and a low-speed finish. | 惯性加速度4/5/6；限时100/80/60s | collision | 3 wins + 3 losses, C++/Python |
| 032 横向防卫 | Wraparound horizontal flight and lasers protect four humans from abducting landers. | 下降速度0.45/0.6/0.8；生命3/2/1 | collision, hit, shot | 3 wins + 3 losses, C++/Python |
| 036 地下充气战 | Dig tunnels, aim a held pump at pursuing monsters, maintain inflation until they burst. | 充气时间0.30/0.40/0.50s；追击间隔0.65/0.55/0.45s | collision, hit | 3 wins + 3 losses, C++/Python |
| 037 染色跳格 | Diagonal hops on a triangular pyramid, persistent tile colours and a pursuing chaser. | 追兵间隔1.5/0.9/0.5s；生命3/2/1 | collision, jump | 3 wins + 3 losses, C++/Python |
| 039 迷雾探索迷宫 | A deterministic perfect maze with restricted vision, remembered explored walls and a hidden exit. | 视野半径3/2/1；限时90/70/55s | action | 3 wins + 3 losses, C++/Python |
| 046 合成大西瓜 | Drop circles under gravity; equal levels merge on contact, different levels collide and a high stack overflows. | 重力6/7/8；落球预算32/24/20 | action, hit | 3 wins + 3 losses, C++/Python |
| 047 自由方块消除 | Place a three-piece rack freely on a 6x6 board; clear full rows, columns or 3x3 regions. | 清除目标4/5/6；放置预算36/30/24 | action, hit | 3 wins + 3 losses, C++/Python |
| 048 三合镇 | Place grass; three connected equal objects merge at the placed cell and can cascade into a house. | 岩石格0/2/4；落子预算40/30/20 | action, hit | 3 wins + 3 losses, C++/Python |
| 049 灭灯 | Toggle a lamp and its orthogonal neighbours on a solvable 5x5 board; turn every light off within a move budget. | 打乱操作5/9/13；预算30/24/20 | action | 3 wins + 3 losses, C++/Python |
| 050 四色迷你数独 | Fill four colours under row, column and 2x2 box constraints; checking a conflicting or incomplete board costs an attempt. | 已知格8/6/4；检查机会3/2/1 | action, collision | 3 wins + 3 losses, C++/Python |
| 056 数字华容道 | Slide the empty cell of a legally scrambled 3x3 numbered board back into ordered 1 through 8. | 合法打乱10/18/26步；移动预算90/70/50 | action | 3 wins + 3 losses, C++/Python |
| 059 割绳子 | A rope constrains a swinging candy; cut at the correct time and preserve tangential momentum to feed the target. | 摆速1.2/1.5/1.8；目标半宽1.8/1.3/0.9；机会3/2/1 | action, collision | 3 wins + 3 losses, C++/Python |
| 060 传送门谜题 | Linked floor portals cross a sealed wall; a remote switch unlocks the exit gate. | 移动预算60/45/30；限时90/70/50s | action, hit | 3 wins + 3 losses, C++/Python |
| 061 四子棋 | Seven columns obey gravity; alternating player and tactical AI must connect four before the opponent. | 优先赢棋/赢棋并封堵/增加威胁判断；限时180/150/120s | action | 3 wins + 3 losses, C++/Python |
| 068 颜色密码 | Guess a hidden four-colour code; exact and misplaced matches account for duplicates without double counting. | 猜测预算10/8/6；限时180/150/120s | action, hit | 3 wins + 3 losses, C++/Python |
| 069 取石子 | Choose one heap and a positive take count; alternating normal-play Nim rewards taking the last stone. | 固定取一/异或最优/异或最优；限时120/90/60s | action | 3 wins + 3 losses, C++/Python |
| 070 连通染色 | Recolour the connected top-left region, expanding only across adjacent matching cells within a move limit. | 染色预算20/16/12；限时120/100/80s | action | 3 wins + 3 losses, C++/Python |
| 071 单人孔明棋 | Jump over adjacent pegs into an empty triangle hole, removing the jumped peg; leave exactly one. | 限时240/180/120s；同一可解三角残局 | hit | 3 wins + 3 losses, C++/Python |
| 077 保龄球 | Aim and charge a rolling ball, knock down a rack, and play ten frames with strike/spare bonuses including tenth-frame extra rolls. | 碰撞半径1.1/0.95/0.8；十局目标60/90/120分 | action, hit | 3 wins + 3 losses, C++/Python |
| 078 棒球击打 | A pitched ball approaches the plate; a timed swing earns hits or home runs, while missed pitches accumulate strikes. | 球速5/6/7；命中窗口半宽1.1/0.8/0.55 | collision, hit | 3 wins + 3 losses, C++/Python |
| 079 足球点球 | Aim and charge a shot against a moving goalkeeper; five attempts decide a three-goal challenge. | 门将频率2/3/4；阻挡半宽2/2.5/3 | action, collision, hit | 3 wins + 3 losses, C++/Python |
| 080 光线摩托 | Two continuous riders leave solid trails; turning avoids walls and traps the opponent, with a survival milestone. | 移动间隔0.16/0.13/0.10s；生存目标50/65/80步 | lifecycle only | 3 wins + 3 losses, C++/Python |
| 082 坦克抛物线对轰 | Choose elevation and power, fire a gravity shell over terrain, damage the enemy and deform impact terrain before its return shot. | 敌方瞄准偏差2/1/0.25；限时120/100/80s | action, hit | 3 wins + 3 losses, C++/Python |
| 089 消防灭火 | Fire grows and spreads on a grid; directional hose jets spend water, a station refills it, and the house must be protected. | 传播周期1.5/1.0/0.7s；水量8/6/4 | action, hit | 3 wins + 3 losses, C++/Python |
| 090 传送带工厂 | Rotate belt tiles to route raw products through a processor to a coloured order sink, without wasting three items. | 订单3/4/5；移动周期0.30/0.24/0.18s | action, collision, hit | 3 wins + 3 losses, C++/Python |
| 091 电线迷宫 | Guide an electrical contact along a one-pixel conducting wire; touching a non-wire cell breaks the circuit. | 限时60/40/25s；触离线即失败 | action, collision | 3 wins + 3 losses, C++/Python |
| 096 冰面滑行迷宫 | A directional push slides until a wall, not just one tile; reach the exit at rest before the slide budget expires. | 滑行预算16/12/8；限时90/70/50s | action | 3 wins + 3 losses, C++/Python |
| 099 自动攻击生存 | Move through a pursuing horde while automatically attacking nearby enemies; kills grant a damage or firing-rate upgrade. | 生命5/4/3；敌速0.8/1/1.2；生存30/40/50s | action, collision, hit | 3 wins + 3 losses, C++/Python |
| 100 翻牌配对 | Reveal two hidden cards, remember mismatches, and clear eight pairs before the turn or time budget. | 翻对预算24/20/16；限时180/120/90s | action, collision, hit | 3 wins + 3 losses, C++/Python |

## Deliberate adaptation limits and remaining acceptance

These are small matrix adaptations, not commercial-game reproductions. Suika has four fruit levels and a fourth-level completion goal; Triple Town ends at a third-level house; portal puzzles use a linked pair and a switch; Peg Solitaire uses the 15-hole triangle; Blockudoku uses a 6x6 board with 3x3 regions; Sudoku accepts any valid 4x4 completion, without claiming unique givens. Deterministic seed witnesses prove the supplied challenge paths, not arbitrary levels or all human strategies.

The 64 inherited cartridges were not rewritten or silently given full-round certification. Their existing per-game quality statuses remain in `game_acceptance.csv`. All 100 compile and pass basic integration; this does not establish complete rounds, three-tier sound design or final quality for every inherited game.

No physical ESP32/Android install, flash, microphone/speaker playback, current measurement, NVS power-cycle, real DMA underrun measurement, stack high-water mark, runtime PSRAM/heap, input-to-LED latency or final fun/readability acceptance was performed. App and firmware output remain external artifacts; credentials and generated binaries are not committed.
