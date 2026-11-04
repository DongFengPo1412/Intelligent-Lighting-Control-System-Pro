// game_052_pipe_connect.h —— 目标 #052 管道旋转接水 (Pipe Connect 1989)
// 机制: 5x5 3x3像素管道网络 + 90度顺时针旋转 + 实时连通水色预览 + 放水防漏导流
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

class Game052PipeConnect : public Cartridge {
public:
    static const int kGridSize = 5;
    static const int kNumStages = 3;

    // 端口方向位掩码: Up=1, Right=2, Down=4, Left=8
    static const uint8_t kPortUp    = 1u << 0;
    static const uint8_t kPortRight = 1u << 1;
    static const uint8_t kPortDown  = 1u << 2;
    static const uint8_t kPortLeft  = 1u << 3;

    Game052PipeConnect();
    ~Game052PipeConnect() override = default;

    uint8_t GetId() const override { return 52; }
    const char* GetName() const override { return "管道旋转接水"; }
    const char* GetEnglishName() const override { return "Pipe Connect"; }
    uint16_t GetReleaseYear() const override { return 1989; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    void Init() override;
    void Reset() override;
    void Start() override;
    void Pause() override;
    void Resume() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

    static uint8_t RotateMaskCW(uint8_t mask);

private:
    void LoadStage(int stage_idx);
    void RecomputeWetPreview();
    void StepWaterFlow();
    void AddScore(uint32_t pts);

    CartridgeState state_;
    int stage_;
    int cursor_x_;
    int cursor_y_;
    bool flow_active_;
    float prep_countdown_;
    float flow_timer_;
    float flow_interval_;
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
    float anim_timer_;

    uint8_t masks_[kGridSize][kGridSize];
    bool fixed_[kGridSize][kGridSize];
    bool wet_preview_[kGridSize][kGridSize];
    bool flowing_[kGridSize][kGridSize];
};

} // namespace arcade
