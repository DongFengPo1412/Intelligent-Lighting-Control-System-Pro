// game_051_flow_free.h —— 目标 #051 同色连线 (Flow Free 2012)
// 机制: 6x6 网格四色端点配对 + 非交叉导线逐步延伸/回退/截断 + 满格奖励通关
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

struct FlowPoint {
    int x;
    int y;
};

class Game051FlowFree : public Cartridge {
public:
    static const int kGridSize = 6;
    static const int kGridCells = kGridSize * kGridSize;
    static const int kNumColors = 4;
    static const int kNumStages = 4;

    Game051FlowFree();
    ~Game051FlowFree() override = default;

    uint8_t GetId() const override { return 51; }
    const char* GetName() const override { return "同色连线"; }
    const char* GetEnglishName() const override { return "Flow Free"; }
    uint16_t GetReleaseYear() const override { return 2012; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    void Init() override;
    void Reset() override;
    void Start() override;
    void Pause() override;
    void Resume() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

private:
    void LoadStage(int stage_idx);
    int EndpointColorAt(int x, int y) const;
    int WireColorAt(int x, int y, int* out_seg_idx) const;
    bool IsColorConnected(int color) const;
    int CountConnectedColors() const;
    int CountCoveredCells() const;
    void CheckStageClear();
    void AddScore(uint32_t pts);

    CartridgeState state_;
    int stage_;
    int cursor_x_;
    int cursor_y_;
    int active_color_;
    bool drawing_;
    uint32_t moves_;
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
    float anim_timer_;

    FlowPoint endpoints_[kNumColors][2];
    FlowPoint paths_[kNumColors][kGridCells];
    int path_len_[kNumColors];
};

} // namespace arcade
