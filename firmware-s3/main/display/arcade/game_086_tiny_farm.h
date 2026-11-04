// game_086_tiny_farm.h —— 目标 #086 小农场 (Tiny Harvest)
// 机制: 5x5农田地块(播种->浇水发芽->生长->金黄成熟->逾期枯萎) + 水井补给 + 季节营收配额
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

enum FarmPlotState : uint8_t {
    PLOT_BARREN   = 0,
    PLOT_SEED     = 1,
    PLOT_SPROUT   = 2,
    PLOT_GROWING  = 3,
    PLOT_RIPE     = 4,
    PLOT_WITHERED = 5,
};

struct FarmPlot {
    uint8_t state;
    bool premium;
    bool boost_watered;
    float timer;
};

class Game086TinyFarm : public arcade::Cartridge {
public:
    Game086TinyFarm();
    ~Game086TinyFarm() override = default;

    uint8_t GetId() const override { return 86; }
    const char* GetName() const override { return "小农场"; }
    const char* GetEnglishName() const override { return "Tiny Harvest"; }
    uint16_t GetReleaseYear() const override { return 1996; }
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
    void SetupMatch(CartridgeState new_state);
    void HandleSmartActionA();
    void HandleActionB();
    void AddScore(uint32_t pts);

    static const int kGridSize = 5;
    static const int kMaxWater = 6;
    static const uint32_t kTargetQuota = 500;

    CartridgeState state_;
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
    float anim_timer_;
    float season_timer_;
    int cursor_col_;
    int cursor_row_;
    int water_;
    int combo_;
    float combo_timer_;
    float move_cooldown_;
    FarmPlot plots_[kGridSize][kGridSize];
};

} // namespace arcade
