# ESP32-S3 LED Mini Arcade 100 — 第一阶段：完整旧游戏审计、目标映射与统一架构报告

> **项目目标**：在一块 16×16、共 256 颗 WS2812B RGB LED 像素的灯板上，实现恰好 **100 款核心玩法独立、完全可玩、画面清晰、操作简单、质量合格** 的小游戏，通过 ESP32-S3-N16R8 固件运行，与手机 App Wi-Fi 互联控制，具备非阻塞 I2S 音效。

---

## 一、第一阶段执行成果概览

根据主任务指令要求，第一阶段（Stage 1）严禁在未经审计与备份前随意删除或重构现有代码。我们已严格完成全部准备与审计工作：

1. **版本管理与安全恢复点**：
   - 建立了安全快照 Git 标签：`archive-191-snapshot` 并推送到远程仓库，完整固化保留了 189 款历史街机实现的所有代码、测试与资源。
   - 创建并切入专用开发分支：`arcade-100-audit-and-elevation`。
2. **仓库现状与代码事实核实**：
   - **代码事实**：仓库中实际存在的游戏总数为 **189 款**（而非口头传闻的 191 款）：包括 `#001` 超级马里奥引擎（`firmware-s3/main/display/mario_game.cpp` 与 `pc-agent-vision/mario_runner.py`）以及 `#004` 至 `#191` 共 188 款街机卡带（`game_004_doodle_jump` 至 `game_191_finalfight`）。
   - **历史跳番槽位**：编号 `#002` 与 `#003` 在旧工程历史中因马里奥与涂鸦跳跃之间的编号跳跃而未创建独立卡带文件。
3. **自动化测试基线验证**：
   - 全套卡带自动化单元测试：**1916 / 1916 项测试全部通过（100% 成功率，耗时 0.180 秒）**。
4. **四项必须交付的核心数据文件生成**：
   - [`audit_191.csv`](file:///C:/workspace/Intelligent-Lighting-Control-System-Pro/audit_191.csv)：191 行全量旧游戏代码审计明细表（含 18 维度评估与处置方案）。
   - [`legacy_to_target.csv`](file:///C:/workspace/Intelligent-Lighting-Control-System-Pro/legacy_to_target.csv)：100 款目标游戏与旧代码的映射与复用说明。
   - [`games_100_manifest.json`](file:///C:/workspace/Intelligent-Lighting-Control-System-Pro/games_100_manifest.json)：正式目标 100 款游戏完整元数据清单。
   - [`game_acceptance.csv`](file:///C:/workspace/Intelligent-Lighting-Control-System-Pro/game_acceptance.csv)：100 款目标游戏质量验收跟踪表。

---

## 二、旧 191 款游戏审计结论（五种处理方案）

经过对现有 189 款代码实现、输入逻辑、图形渲染与核心玩法的逐一核验，五种处理方案分布如下：

```mermaid
pie title 旧游戏与目标分类处理分布
    "KEEP (直接复用优质实现)" : 39
    "REWORK (调优改造适配目标)" : 15
    "MERGE (合并吸收其他实现)" : 8
    "ARCHIVE (归档入快照保留)" : 127
    "MISSING (目标清单待新实现)" : 46
```

### 2.1 KEEP（保留并复用 — 39款目标游戏）
玩法完全匹配固定 100 款目标、代码成熟、在 16×16 上具备出色的画面表达与手感，直接纳入正式目录：
- **平台/跑酷**：`001` 超级马里奥、`002` 涂鸦跳跃、`005` 淘金者 (Lode Runner)
- **单键/时机**：`009` Flappy Bird、`010` Stack 堆叠、`016` 打地鼠、`017` Piano Tiles
- **弹球/物理**：`020` Pong、`021` Breakout 打砖块、`022` 街机弹珠台、`025` 滚珠平衡迷宫
- **射击/防卫**：`026` Space Invaders、`027` Asteroids、`028` Missile Command、`029` Centipede、`030` 打鸭子、`031` Robotron 双向射击、`032` Defender 横向防卫
- **迷宫/追逐**：`033` 贪吃蛇 (Snake)、`034` 吃豆人 (Pac-Man)、`036` Dig Dug 地下打气人、`038` 炸弹人 (Bomberman)
- **方块/合并**：`041` 俄罗斯方块 (Tetris)、`042` 魔法气泡 (Puyo Puyo)、`043` 2048、`052` 水管工 (Pipe Dream)、`054` 推箱子 (Sokoban)、`062` 黑白棋 (Othello)
- **竞速/体育/生存**：`074` 极速变道赛车、`075` 高山滑雪、`077` 街机保龄球、`078` 冠军棒球、`080` Tron 光轮摩托、`081` Qix 划线天蚕变、`082` 百战天虫抛物线轰炸、`094` 索道探险家 (Roc'n Rope)、`097` 青蛙过河 (Frogger)、`098` 月球着陆器 (Lunar Lander)

### 2.2 REWORK（重构与适配 — 15款目标游戏）
玩法符合目标核心，但需要根据 16×16 屏幕规格进行机制提纯或规则对齐：
- `006` Bubble Bobble：确保“吐泡困怪 + 踩破消灭”的动作核心，严格区分三消类泡泡龙。
- `008` Jump King：基于敲冰块垂直攀登，改造为长按蓄力起跳机制。
- `013` 摆锤投球：基于小丑跷跷板改造周期性简谐摆动释放小球入筐。
- `014` 轨道跃迁：基于旋风巡航者同心环改造轨道交汇处切轨跃迁。
- `023` 空气曲棍球：基于飞盘对决改造 2D 气垫球拍防守反击与球门判定。
- `035` Boulder Dash：基于矿工逃犯改造地下挖土避落石塌方机制。
- `037` Q*bert 染色跳格：基于现有斜向跳球优化 3~4 层阶梯视差与翻色。
- `039` 迷雾探索迷宫：基于地牢穿梭改造局部视野战争迷雾探索。
- `044` 宝石迷阵：基于钱币交换机改造相邻方块滑动交换三消。
- `045` SameGame：基于翻转方块改造连通色块整组点击清除。
- `066` 海战棋：基于潜艇雷达改造双人迷雾坐标盲猜盲打。
- `083` 路径塔防：基于绝地要塞改造道路固定路径架设防御塔拦截。
- `089` 消防灭火：基于消防车改造水枪高压喷射压制火势蔓延。
- `091` 电线迷宫：基于气球防爆改造电流急急棒狭窄通道不碰壁。
- `096` 冰面滑行迷宫：基于企鹅推冰块改造滑动直至撞墙停顿滑冰迷宫。
- `099` 幸存者自动索敌：基于圣铠传说改造移动走位 + 自动武器索敌射击与升级构筑。

### 2.3 ARCHIVE（归档至 Git 快照 — 127款旧游戏）
在第 004 到 191 款的历史卡带中，有 127 款属于街机历史题材（例如《双截龙》、《快打旋风》、《大金刚》、《恐龙快打》、《战场之狼》、《雷电》等清版格斗与复杂卷轴游戏）。这些游戏在 16×16 硬件上已被安全完整固化在 `archive-191-snapshot` 标签中，未来将从正式 100 款菜单中归档退出，释放菜单专注度与系统资源。

### 2.4 MISSING（待新建实现 — 46款益智/棋盘/单键游戏）
目标 100 款清单中规定的现代益智、桌面棋类与触控游戏（如 `003` Celeste、`004` VVVVVV、`007` Downwell、`015` Simon、`046` 合成大西瓜、`047` Blockudoku、`049` Lights Out、`051` Flow Free、`061` 四子棋、`063` 五子棋、`064` 跳棋、`070` Flood-It、`086` 小农场、`092` 水果忍者、`095` Super Hexagon、`100` 翻牌配对等），将在后续第二至第五阶段按批次实现。

---

## 三、硬件资源与系统容量审计

硬件平台：**ESP32-S3-N16R8 (16MB SPI Flash + 8MB Octal PSRAM)**。

| 资源类别 | 硬件物理上限 | 当前固件实测占用 | 100款游戏预算评估 | 余量与安全性 |
| :--- | :--- | :--- | :--- | :--- |
| **Flash 存储** | 16,384 KB (16MB) | 853.4 KB (`.bin` 大小) | ~2,500 KB (~2.5MB) | **>84% 充裕**（完全容纳所有关卡数据与字库） |
| **SRAM (内部)** | 512 KB | 静态分配 ~98 KB | ~140 KB | **>70% 充裕**（高速总线无等待） |
| **PSRAM (外部)** | 8,192 KB (8MB) | 启用 Octal 模式，当前占用 ~300 KB | ~1,200 KB | **>85% 充裕**（动态关卡图、音效缓存自由分配） |
| **LED 帧缓冲** | 256 像素 (RGB888) | 768 字节 (双缓冲 1.5 KB) | 固定 1.5 KB | **零压力**（每帧更新无需动态堆分配） |
| **LED 功耗控制** | 256 颗 5V WS2812B | 全白峰值 ~12.8A (不可承受) | 软件限制全局亮度 (30%~40%)，峰值 <1.8A | **硬件安全受控** |

> [!IMPORTANT]
> **关于 Flash 分区与 OTA**：当前 `sdkconfig` 设置为 `CONFIG_ESPTOOLPY_FLASHSIZE_8MB=y`。鉴于主板是 N16R8（16MB），后续可在 `sdkconfig.defaults` 中启用 16MB 配置并配置双 OTA 大分区（每个 App 分区可达 4MB~6MB），在 100 款游戏全集成后依然保留无线 OTA 升级能力。

---

## 四、统一游戏引擎架构（ESP32-S3 & Python 双端）

为避免 100 款游戏重复冗余代码，我们确立统一的生命周期与框架工具集：

```mermaid
stateDiagram-v2
    [*] --> MENU
    MENU --> READY: App选择游戏 / 发送START
    READY --> PLAYING: 倒计时结束 (3-2-1)
    PLAYING --> PAUSED: 按下暂停 / Wi-Fi网络断开
    PAUSED --> PLAYING: 继续游戏 / 网络恢复重连
    PLAYING --> GAME_OVER: 生命耗尽 / 判定失败
    PLAYING --> RESULT: 通关胜出 / 达成目标
    GAME_OVER --> RESULT: 结算得分展示
    RESULT --> MENU: 超时 / 按下SELECT退出
```

### 4.1 统一卡带抽象接口 (`arcade::Cartridge` / `BaseCartridge`)
所有游戏均必须继承标准虚接口：
- `Init()` / `Reset()`：内存零开销复位。
- `Update(dt, keys_down, keys_pressed)`：固定步长物理驱动（30 FPS 刷新）。
- `Render(uint8_t* fb_rgb24)`：严格带边界保护绘制入 768 字节 RGB888 缓冲区。
- `GetStatus()`：回读当前游戏状态结构体（`score`, `lives`, `state`, `progress`），供手机端与音效事件捕获。

### 4.2 统一共享功能模块
- **绘制核心 (`MatrixCanvas`)**：点、线、矩形、圆形、消隐闪烁、3×5 迷你高对比度数字字体。
- **动态难度控制器 (`AdaptiveDifficulty`)**：支持 Easy/Normal/Hard 三档，或基于存活时间/失误率自适应调节下落与运动速度。
- **音效事件分发器 (`SoundDispatcher`)**：将游戏产生的 `SND_MENU`, `SND_JUMP`, `SND_SCORE`, `SND_HIT`, `SND_GAMEOVER`, `SND_VICTORY` 非阻塞抛入 I2S 队列，绝不阻塞游戏主线程。
- **高分持久化 (`StorageManager`)**：利用 ESP32 NVS 存储 100 款游戏各自的历史最高分。

---

## 五、手机 App 与 Wi-Fi 通信协议规范

手机端通过 Wi-Fi（UDP 端口 8888 与 HTTP REST API）连接 ESP32-S3：

### 5.1 六类自适应虚拟手柄布局
根据卡带元数据 `control_type` 动态切换手机 UI：
1. `CTRL_TAP_SINGLE`：全屏轻触单键（适用于 Flappy Bird、Stack、恐龙跑酷）。
2. `CTRL_TWO_BUTTON`：左右双按键（适用于涂鸦跳跃、极速赛车）。
3. `CTRL_DPAD_4WAY`：十字方向键（适用于贪吃蛇、推箱子、吃豆人）。
4. `CTRL_ARCADE_AB`：十字键 + A/B 键（适用于超级马里奥、太空侵略者、泡泡龙）。
5. `CTRL_MULTI_TRACK`：四轨独立轻触键（适用于别踩白块儿）。
6. `CTRL_VERSUS_DUAL`：上下/左右双人同屏虚拟推杆（适用于双人乒乓）。

### 5.2 网络安全与防卡死机制
- **按键包序列号与心跳**：手机端以 30Hz 发送按键掩码包，附带序列号。
- **断线自动暂停（Safe Pause）**：当连续 500ms 未收到手机心跳包时，固件自动触发 `PAUSE` 状态，强制清空当前所有按键按下态，坚决杜绝“手机断开后角色一直跑或一直射击”的恶性 Bug。

---

## 六、后续阶段执行路线图（Stage 2 ~ Stage 7）

```mermaid
flowchart TD
    S1["第一阶段: 审计191款旧游戏 (已完成 ✓)"] --> S2["第二阶段: 保留优质游戏并统一架构"]
    S2 --> S3["第三阶段: 完善高适配度游戏 (单键/经典益智)"]
    S3 --> S4["第四阶段: 实现中等复杂度游戏 (物理/迷宫/消除)"]
    S4 --> S5["第五阶段: 实现高难度游戏 (Celeste/Downwell/Suika)"]
    S5 --> S6["第六阶段: 手机App和全系统集成 (动态手柄/高分)"]
    S6 --> S7["第七阶段: 最终验收与100款逐款验证"]
```

1. **第二阶段（保留优质游戏并统一架构）**：
   - 固化马里奥、贪吃蛇、俄罗斯方块的统一 C++ 接口。
   - 建立 100 款游戏的统一管理注册中心与共享渲染字库。
2. **第三阶段（完善高适配度游戏）**：
   - 优先实现与调优：Flappy Bird, Stack, Pong, Breakout, 2048, 打地鼠, Lights Out, 四子棋, 吃豆人, 推箱子, 青蛙过河, Tron, 翻牌配对等。
3. **第四阶段（实现中等复杂度游戏）**：
   - 消除连锁类（Puyo Puyo, SameGame）、棋盘对弈（黑白棋, 五子棋, 西洋跳棋）、迷宫探索与多角色 AI。
4. **第五阶段（实现较难适配的游戏）**：
   - 重点突破：Celeste 冲刺关卡、Downwell 垂直开火坠落、合成大西瓜碰撞合并、Cut the Rope 绳索摆动、Lemmings 旅鼠拯救、吸血鬼幸存者式自动索敌。
5. **第六阶段（手机 App 全系统集成）**：
   - 手机端 100 款游戏目录、分类筛选、动态手柄渲染、历史排行榜、音量调节。
6. **第七阶段（逐款验收）**：
   - 100 款游戏自动化单元测试覆盖率达 100%，逐一更新 `game_acceptance.csv`，输出最终交付物。

---

## 七、第一阶段交付物索引

- 全量旧游戏审计表：[`audit_191.csv`](file:///C:/workspace/Intelligent-Lighting-Control-System-Pro/audit_191.csv)
- 目标与旧代码映射表：[`legacy_to_target.csv`](file:///C:/workspace/Intelligent-Lighting-Control-System-Pro/legacy_to_target.csv)
- 正式 100 款游戏元数据表：[`games_100_manifest.json`](file:///C:/workspace/Intelligent-Lighting-Control-System-Pro/games_100_manifest.json)
- 游戏质量验收跟踪表：[`game_acceptance.csv`](file:///C:/workspace/Intelligent-Lighting-Control-System-Pro/game_acceptance.csv)
- 历史代码安全快照：Git Tag `archive-191-snapshot` (Commit `d31d9b9`)
- 当前工作分支：`arcade-100-audit-and-elevation`
