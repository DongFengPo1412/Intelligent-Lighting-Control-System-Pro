#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game094CrashBoys : public Cartridge {
public:
    Game094CrashBoys();
    ~Game094CrashBoys() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 94; }
    std::string GetName() const override { return "Crash 'n' the Boys (1992)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_RUNNING = 0,
        STATE_VAULTING = 1,
        STATE_AIRBORNE = 2,
        STATE_HERO_FALL = 3,
        STATE_STAGE_CLEAR = 4,
        STATE_GAME_OVER = 5
    };

    struct Rival {
        float x{0.0f};
        float y{13.0f};
        float vx{4.5f};
        bool active{false};
        bool knocked_down{false};
    };

    struct RooftopGap {
        float start_dist{80.0f};
        float end_dist{110.0f};
    };

    static constexpr int MAX_RIVALS = 2;

    GameState GetState() const { return state_; }
    int GetScore() const { return score_; }
    int GetLives() const { return lives_; }
    float GetPlayerX() const { return px_; }
    float GetPlayerY() const { return py_; }
    float GetRunSpeed() const { return run_speed_; }
    float GetPoleFlex() const { return pole_flex_; }
    bool IsDropkicking() const { return is_dropkicking_; }
    float GetDistance() const { return distance_; }
    int GetRivalsDefeated() const { return rivals_defeated_; }

    const Rival& GetRival(int i) const { return rivals_[i]; }

private:
    void ResetEvent(bool hard_reset);
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateRivals(float dt);
    void CheckAirCombat();

    GameState state_{STATE_RUNNING};
    float state_timer_{0.0f};
    int score_{0};
    int lives_{3};
    int round_{1};
    int rivals_defeated_{0};

    // Kunio / Crash Athlete
    float px_{3.0f};
    float py_{13.0f};
    float run_speed_{6.0f};
    float pole_flex_{0.0f}; // 0.0 to 1.0 (pole bend power)
    float air_vx_{0.0f};
    float air_vy_{0.0f};
    bool is_dropkicking_{false};

    // Rooftop progression & Gaps
    float distance_{0.0f};
    float stage_length_{400.0f};
    float next_gap_dist_{60.0f};
    float gap_width_{18.0f};

    Rival rivals_[MAX_RIVALS];
};

} // namespace arcade
