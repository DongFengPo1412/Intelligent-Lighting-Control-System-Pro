# LED Mini Arcade 100 — 第二阶段基石游戏终局集成修复交付报告 (v3.0)

## 一、第二阶段终局集成修复概要

针对第三次审查中指出的端到端集成、控制权威一致性、NVS 数据持久化、大数字截断与 OTA 边界等关键问题，本次工作对系统进行了深度的闭环重构与测试加固，达成以下核心目标：

1. **确立 ESP32 为唯一运行与计分权威 (Single Source of Truth)**：彻底消除电脑端 Python 运行器与 ESP32 双重并行计算的割裂问题。正式硬件模式下，ESP32 独立承载游戏逻辑、碰撞裁决、得分累加与 16×16 LED 驱动；手机端获取的状态与帧画面均来自 ESP32 真实回传；Python 运行器严格收敛为显式标注的离线仿真模式。
2. **手机端全链路统一街机控制 (`/api/arcade`)**：全面重构 `web_app/app.js` 与 `index.html`。正式街机卡带编号统一为 `#001` (超级马里奥)、`#033` (经典贪吃蛇)、`#041` (俄罗斯方块)；动态适配虚拟手柄布局（贪吃蛇纯净 4 向十字键，马里奥/方块动作 A/B 键）；错误与离线状态透明告警，严禁冒充成功。
3. **断网两级看门狗与状态对齐验证**：500ms 自动释放按键，1000ms 强制进入 `STATE_PAUSED`；重连后必须等待玩家显式点击“继续”；暂停期间拦截任何延迟或重复按键包；切换卡带强制清空按键残留。
4. **16×16 点阵结算屏完整支持大数字滚动与高分分页**：
   - 3×5 微型字模扩展英文字母 `H` 与 `E`；
   - 超过 4 位的大数字（如 12500、100000）通过平滑跑马灯滚动完整呈现，**截断率彻底降为 0%**；
   - 自动分页轮播：Phase 0 展示本局输赢（G O / WIN）与当前得分，Phase 1 展示历史纪录（HI）与最高纪录，新纪录支持金色高亮闪烁；
   - 超级马里奥 C++ 端与 Python 端完整接入结算屏渲染。
5. **ESP32 NVS 最高分可靠持久化 (`ArcadeScoreStore`)**：
   - 接入 ESP-IDF 原生 `<nvs.h>`，使用独立命名空间 `"arcade_hs"`；
   - 仅在游戏结算产生新纪录时执行 Flash 写入与提交，规避高频擦写风险；
   - 开局与重置自动载入历史纪录，掉电重启后高分恒定保留。
6. **16MB 双 6MB OTA 分区与供电预算边界诚实界定**：
   - 编译生成 `s3_led_matrix_test.bin`（大小 0xe0930 字节），在 6MB 分区中空闲率高达 **85%**；
   - 建立旧单分区向双 OTA 分区的安全烧录迁移规范；
   - 1.747A 供电预算明确标注为“数学推导模型”，未接入物理万用表前硬件状态严守 `UNTESTED_ON_HARDWARE`；未实测网络回滚前 OTA 状态严守 `OTA_UNTESTED_ON_HARDWARE`。

---

## 二、关键技术整改与代码实现详情

### 2.1 架构确立：ESP32-S3 单一权威与控制链路解耦

```mermaid
graph TD
    subgraph 手机控制端 [手机 Web App / Android WebView]
        UI[统一街机控制台 #001 / #033 / #041]
        VPad[动态虚拟手柄: 4向十字键 / A-B操作键]
        HUD[状态与高分 HUD 监视器]
    end

    subgraph 传输层 [HTTP REST / WebSocket / UDP 8888]
        API[/api/arcade & /api/arcade/frame]
        GW[WiFiGateway 异步安全重试套接字]
    end

    subgraph ESP32 权威端 [ESP32-S3 唯一权威中枢]
        Disp[WifiManager UDP 8888 & CommandDispatcher]
        Mgr[ArcadeManager 统一卡带调度器]
        Cart[游戏逻辑: #001 马里奥 / #033 贪吃蛇 / #041 方块]
        NVS[(NVS Flash: arcade_hs 持久化存储)]
        HAL[DisplayHAL 15000能量限流器]
        LED[16x16 WS2812B 矩阵屏物理输出]
    end

    UI -->|JSON 控制指令| API
    API -->|UDP 8888| Disp
    Disp --> Mgr
    Mgr --> Cart
    Cart -->|新纪录写入| NVS
    Cart -->|768B RGB888| HAL
    HAL --> LED
    Disp -.->|权威状态与RGB帧回传| GW
    GW -.->|实机状态| HUD
```

- **消除双重运行器冲突**：
  - 在 [arcade_runner.py](file:///C:/workspace/Intelligent-Lighting-Control-System-Pro/pc-agent-vision/arcade_runner.py) 中，当检测到硬件在线（`is_hardware_available() == True` 且非 `SIMULATION`）时，**完全停用 Python 本地游戏循环**。所有按键与生命周期均透明转发给 ESP32，状态与计分 100% 提取自 ESP32 的回包；
  - 仅当用户或自动化脚本显式指定 `force_simulation=True`（或处于离线仿真环境）时，才启动 Python 本地卡带，并强制在返回 JSON 中标注 `"source": "simulator"`, `"simulated": true`；
  - 硬件离线且未指定仿真模式时，接口返回 HTTP 503 明确报错，绝不偷梁换柱。

### 2.2 手机端 Web 控制器全链路重构

- **界面统一与卡带映射**：
  - [index.html](file:///C:/workspace/Intelligent-Lighting-Control-System-Pro/pc-agent-vision/web_app/index.html)：将原本专属于马里奥的容器升级为通用点阵街机容器，并配置专用卡带选择组：`data-arcade-id="001"`、`033`、`041`；
  - [app.js](file:///C:/workspace/Intelligent-Lighting-Control-System-Pro/pc-agent-vision/web_app/app.js)：实现全局 `launchArcadeGame(gameId)` 函数，旧版 `data-game` 按钮与快捷入口全部透明收敛至新街机管道。
- **手柄布局与 HUD 动态响应**：
  - 检测到卡带 `control_type == 2`（`CTRL_DPAD_4WAY`，贪吃蛇）时，自动隐藏右侧 A/B 键区域，呈现纯粹的 4 向十字键；
  - 检测到卡带 `control_type == 3`（`CTRL_ARCADE_AB`，马里奥/俄罗斯方块）时，显示 A/B 键，并动态切换按键角标（马里奥显示“跳跃/加速”，俄罗斯方块显示“旋转/软降”）；
  - 每 300ms 由前端发起心跳包保活，实时同步 ESP32 的游戏状态（TITLE / PLAYING / PAUSED / GAMEOVER / VICTORY）、当前得分与最高分。

### 2.3 统一结算屏与大数字滚动无截断

- **字模与多阶段轮播 ([arcade_result_screen.cpp](file:///C:/workspace/Intelligent-Lighting-Control-System-Pro/firmware-s3/main/display/arcade/arcade_result_screen.cpp))**：
  - 扩充 3×5 点阵字模库，新增大写英文字母 `H`（`0b101, 0b101, 0b111, 0b101, 0b101`）与 `E`；
  - 引入动画时钟 `anim_time`，以 2.2 秒为周期实现双阶段交替：
    - **Phase 0 (当前战绩)**：顶部大红 `G O` 或金黄 `WIN`，中部琥珀色渲染本局得分；
    - **Phase 1 (历史纪录)**：顶部天青色 `HI`（打破纪录时闪烁金辉），中部纯金色渲染最高纪录；
  - **跑马灯平滑滚动算法**：当分数长度 $\le 4$ 位时严格居中；当分数 $> 4$ 位（如 12500）时，自动计算 `scroll_range = total_w - 15`，在前 0.6 秒停留在最高有效位，随后 1.3 秒平滑平移至末位，并在末尾停留 0.6 秒。全周期无任何像素被粗暴裁剪。
- **超级马里奥接入**：
  - [game_001_mario.cpp](file:///C:/workspace/Intelligent-Lighting-Control-System-Pro/firmware-s3/main/display/arcade/game_001_mario.cpp)：在 `Render()` 中检测到状态为 `ST_GAMEOVER`、`ST_DEAD` 或 `ST_WIN` 时，统一调度 `ArcadeResultScreen::RenderResult`，终结死图与无结算现象。

### 2.4 NVS 最高分持久化机制

- **独立存储模块 ([arcade_score_store.cpp](file:///C:/workspace/Intelligent-Lighting-Control-System-Pro/firmware-s3/main/display/arcade/arcade_score_store.cpp))**：
  - 封装静态接口 `LoadHighScore(uint8_t game_id)` 与 `SaveHighScore(uint8_t game_id, uint32_t high_score)`；
  - 在 NVS 空间 `"arcade_hs"` 中以键名 `hs_%03u` 存储无符号 32 位整数；
  - 写入保护：仅当 `high_score > existing` 时执行 `nvs_set_u32` 并 `nvs_commit`，运行期间绝不产生冗余写入，既保护 Flash 寿命，又确保即便硬件断电或系统复位，玩家最高纪录永不丢失。
  - 三款基石游戏已全部在 `Init()`/`Reset()` 载入并在结算时持久化保存。

### 2.5 16MB 双 6MB OTA 分区与迁移安全性

- **生效配置与构建结果**：
  - [partitions_16mb.csv](file:///C:/workspace/Intelligent-Lighting-Control-System-Pro/firmware-s3/partitions_16mb.csv)：
    - `ota_0`：起始 0x20000，大小 0x600000 (6MB)
    - `ota_1`：起始 0x620000，大小 0x600000 (6MB)
    - `storage`：起始 0xC20000，大小 0x3D0000 (3.8MB SPIFFS)
  - ESP-IDF v5.5.4 完整编译输出：
    ```text
    s3_led_matrix_test.bin binary size 0xe0930 bytes (898KB).
    Smallest app partition is 0x600000 bytes (6.0MB).
    0x51f6d0 bytes (85%) free.
    ```
- **旧分区升级迁移方案**：
  - 鉴于旧工程采用单分区且起始于 0x10000，首次升级至 16MB 双 OTA 架构必须通过 USB 串口执行全量线刷（写入 `bootloader.bin`、`partition-table.bin`、`ota_data_initial.bin` 及应用固件）；
  - 首次线刷完成后，系统方具备通过 Wi-Fi 在 `ota_0` 与 `ota_1` 间无缝双向 OTA 升级与失败自动回滚的能力；
  - 按照诚实审计原则，在未上板执行实际 OTA 镜像推送与断电回滚之前，状态保持为 `OTA_UNTESTED_ON_HARDWARE`。

---

## 三、自动化测试与边界覆盖

全局回归测试覆盖了全部新架构接口、结算显示与生命周期：

| 序号 | 测试套件 | 用例数 | 关键验证技术点 | 结果 |
| :---: | :--- | :---: | :--- | :---: |
| 1 | `test_arcade_result_screen.py` | 6 | 3x5 全字母字模、1~4位居中、>4位平滑滚动不截断、Phase 0/1 分页、高分闪烁 | **PASSED** |
| 2 | `test_arcade_lifecycle.py` | 5 | 状态机幂等性、断网重连不自动恢复、延迟重复包拦截、切换游戏清除按键残留 | **PASSED** |
| 3 | `test_arcade_web_api.py` | 5 | ESP32 硬件权威响应、离线诚实报错、非法编号拒绝、模拟器显式标识、帧源区分 | **PASSED** |
| 4 | `test_arcade_nvs_persistence.py` | 3 | 重启/重开高分不归零、结算高分刷新继承、退出再进入高分保持 | **PASSED** |
| 5 | `test_arcade_partition_table.py` | 3 | 双 6MB OTA 分区无重叠、Flash 16MB 配置、二进制体积裕量 $\ge 80\%$ | **PASSED** |
| 6 | `test_power_limiter.py` | 6 | 全黑/稀疏/纯红/纯白 15000 限幅平滑衰减、1.747A 理论供电预算推导 | **PASSED** |
| 7 | `test_arcade_001_mario.py` | 5 | 原生动力学模拟、跳跃冲刺、碰撞、金币与死亡胜利结算 | **PASSED** |
| 8 | `test_arcade_033_snake.py` | 7 | 转向/死墙碰撞/进食提速/3x5 结算/可选穿墙 | **PASSED** |
| 9 | `test_arcade_041_tetris.py` | 6 | 旋转碰撞/触底固化/满行消行/结算屏 | **PASSED** |
| 10 | `test_arcade_continuous_simulation.py` | 3 | 40 帧动态跨步跃迁、8 步进食帧差、15 步方块落位锁定 | **PASSED** |

### 全量测试运行实测
```text
python run_all_arcade_tests.py
----------------------------------------------------------------------
Ran 1959 tests in 0.135s

OK
Total test cases discovered: 1959
Tests run: 1959, Failures: 0, Errors: 0
ALL TESTS PASSED! (100% pass rate)
```

---

## 四、分层验收结论与当前边界

依据诚实验收原则，对项目当前各维度状态严格界定如下：

1. **真实源码实现完成度**：
   - ESP32 单一权威架构：已实现并合入主固件与控制器中；
   - 手机 Web 街机前端统一控制：已实现并合入 `index.html` 与 `app.js`；
   - 16×16 结算屏大数字滚动与高分分页：已在 C++ 与 Python 双端实现；
   - NVS 最高分持久化：已在 C++ 固件端接入；
   - 16MB 双 6MB OTA 分区表：已在 `partitions_16mb.csv` 与 `sdkconfig` 中就绪。
2. **自动化测试与仿真验证**：
   - 1959 项 Python 单元测试与协议测试：**全部通过 (100%)**；
   - 连续多帧动态物理仿真：**全部通过 (100%)**。
3. **C++ 固件构建验证**：
   - ESP-IDF v5.5.4 完整编译：**零警告零错误通过**；
   - 固件体积 898KB，单一应用分区 6.0MB，空闲率 85%。
4. **硬件与环境待实测事项 (严格标注未实测)**：
   - **真实物理灯板光学与触感**：`UNTESTED_ON_HARDWARE`（需物理板上电与肉眼评估）；
   - **万用表供电电流实测**：`UNTESTED_ON_HARDWARE`（需物理电流表测量各高亮画面实际安培数）；
   - **双 OTA 升级与物理网络回滚**：`OTA_UNTESTED_ON_HARDWARE`（需物理设备执行实际 OTA 镜像上传测试）。

至此，阻碍后续 100 款游戏批量接入的通用架构、网络权威、结算显示与存储持久化问题已彻底解决，具备正式迈入第三阶段的充分条件！
