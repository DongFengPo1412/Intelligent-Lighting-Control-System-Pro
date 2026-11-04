// arcade_cartridge.h —— ESP32-S3 16x16 街机卡带统一抽象接口
// 版权所有: 未来道具研究所 · PixelArcade Core
#pragma once

#include <stdint.h>
#include <stddef.h>

namespace arcade {

static const int kMatrixWidth = 16;
static const int kMatrixHeight = 16;
static const int kFrameBufferSize = kMatrixWidth * kMatrixHeight * 3; // 768 字节 RGB888

// 统一按键定义
enum ArcadeKeyBits : uint16_t {
    KEY_LEFT   = 1u << 0,
    KEY_RIGHT  = 1u << 1,
    KEY_UP     = 1u << 2,
    KEY_DOWN   = 1u << 3,
    KEY_A      = 1u << 4,   // 主动作 / 跳跃 / 射击
    KEY_B      = 1u << 5,   // 次动作 / 冲刺 / 炸弹
    KEY_START  = 1u << 6,   // 开始 / 暂停
    KEY_SELECT = 1u << 7,   // 选项 / 退出
};

// 虚拟手柄类型（通知手机端呈现对应的触控界面）
enum ControlType : uint8_t {
    CTRL_TAP_SINGLE   = 0, // 全屏单键轻触 (如: 飞翔小鸟, 堆叠大师)
    CTRL_TWO_BUTTON   = 1, // 左右双键 (如: 涂鸦跳跃, 赛车躲避)
    CTRL_DPAD_4WAY    = 2, // 四向十字键 (如: 贪吃蛇, 推箱子)
    CTRL_ARCADE_AB    = 3, // 十字键 + A/B 键 (如: 超级马里奥, 太空射击)
    CTRL_MULTI_TRACK  = 4, // 四轨按键 (如: 别踩白块儿)
    CTRL_VERSUS_DUAL  = 5, // 双人同屏对战 (如: 乒乓对决)
};

// 游戏运行状态
enum CartridgeState : uint8_t {
    STATE_TITLE = 0,
    STATE_PLAYING = 1,
    STATE_PAUSED = 2,
    STATE_GAMEOVER = 3,
    STATE_VICTORY = 4,
};

// 游戏 HUD 状态回读
struct CartridgeStatus {
    uint8_t player_count = 0; // 0: not applicable, Pong: 1 AI / 2 local players.
    uint32_t score = 0;
    uint32_t high_score = 0;
    uint8_t lives = 1;
    uint8_t state = 0;
    uint8_t progress = 0;
};

// 抽象卡带接口
class Cartridge {
public:
    virtual ~Cartridge() = default;

    virtual uint8_t GetId() const = 0;
    virtual const char* GetName() const = 0;
    virtual const char* GetEnglishName() const = 0;
    virtual uint16_t GetReleaseYear() const = 0;
    virtual ControlType GetControlType() const = 0;

    virtual void Init() = 0;
    virtual void Reset() = 0;
    virtual void Start() = 0;
    virtual void Pause() = 0;
    virtual void Resume() = 0;
    virtual void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) = 0;
    virtual void Render(uint8_t* fb_rgb24) = 0;
    virtual CartridgeStatus GetStatus() const = 0;
};

} // namespace arcade

