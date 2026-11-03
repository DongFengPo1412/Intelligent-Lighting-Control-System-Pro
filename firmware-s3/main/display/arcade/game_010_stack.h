// game_010_stack.h —— 目标 #010 堆叠大师 16 (Stack Master 16)
// 机制: 平移运动 + 切除悬空缩窄 + 面积梯次衰减 + 彩虹色相律动
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

class Game010Stack : public Cartridge {
public:
    Game010Stack();
    ~Game010Stack() override = default;

    uint8_t GetId() const override { return 10; }
    const char* GetName() const override { return "堆叠大师"; }
    const char* GetEnglishName() const override { return "Stack Master"; }
    uint16_t GetReleaseYear() const override { return 2016; }
    ControlType GetControlType() const override { return CTRL_TAP_SINGLE; }

    void Init() override;
    void Reset() override;
    void Start() override;
    void Pause() override;
    void Resume() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

private:
    void PlaceBlock();
    void GetLayerColor(int layer_idx, uint8_t& r, uint8_t& g, uint8_t& b);

    CartridgeState state_;
    int current_row_;
    float active_x_;
    float active_w_;
    float active_vx_;

    static const int kMaxVisibleLayers = 16;
    StackLayer layers_[kMaxVisibleLayers];
    int layer_count_;

    static const int kMaxDebris = 4;
    FallingDebris debris_[kMaxDebris];

    uint32_t score_;
    uint32_t high_score_;
    int perfect_combo_;
    float perfect_flash_;
    float state_timer_;
    float anim_timer_;
};

} // namespace arcade
