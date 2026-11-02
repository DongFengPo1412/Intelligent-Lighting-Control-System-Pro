// game_006_stack.h —— 堆叠大师 16 (Stack It Up 16)
// 编号: #006 | 机制: 平移运动 + 切除悬空缩窄 + 面积梯次衰减 + 彩虹色相律动
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

struct StackLayer {
    float x;
    float w;
    uint8_t r, g, b;
};

struct FallingDebris {
    float x;
    float y;
    float w;
    float vy;
    uint8_t r, g, b;
    bool active;
};

class Game006Stack : public Cartridge {
public:
    Game006Stack();
    ~Game006Stack() override = default;

    uint8_t GetId() const override { return 6; }
    const char* GetName() const override { return "堆叠大师"; }
    const char* GetEnglishName() const override { return "Stack It Up 16"; }
    uint16_t GetReleaseYear() const override { return 2016; }
    ControlType GetControlType() const override { return CTRL_TAP_SINGLE; }

    void Init() override;
    void Reset() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

private:
    void PlaceBlock();
    void GetLayerColor(int layer_idx, uint8_t& r, uint8_t& g, uint8_t& b);

    CartridgeState state_;
    int current_row_;      // 当前正在移动摆放的屏幕行 (从 14 逐渐向上)
    float active_x_;       // 活动方块当前水平位置
    float active_w_;       // 活动方块宽度
    float active_vx_;      // 活动方块水平平移速度 (带正负)

    static const int kMaxVisibleLayers = 16;
    StackLayer layers_[kMaxVisibleLayers];
    int layer_count_;      // 已经成功堆叠的层数

    static const int kMaxDebris = 4;
    FallingDebris debris_[kMaxDebris];

    uint32_t score_;
    uint32_t high_score_;
    int perfect_combo_;
    float perfect_flash_;  // 完美对齐时的全屏高光粒子计时器
    float state_timer_;
};

} // namespace arcade

