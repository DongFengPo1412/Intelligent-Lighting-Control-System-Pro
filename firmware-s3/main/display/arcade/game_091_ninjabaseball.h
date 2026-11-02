#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game091NinjaBaseball : public Cartridge {
public:
    Game091NinjaBaseball();
    ~Game091NinjaBaseball() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 91; }
    std::string GetName() const override { return "Ninja Baseball Bat Man (1993)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_INNING = 0,
        STATE_HERO_HIT = 1,
        STATE_STAGE_CLEAR = 2,
        STATE_GAME_OVER = 3
    };

    enum ActionState {
        ACTION_IDLE = 0,
        ACTION_SWING = 1,
        ACTION_BUNT = 2,
        ACTION_HOMERUN = 3,
        ACTION_SLIDE = 4
    };

    struct Thug {
        float x{0.0f};
        float y{0.0f};
        float vx{-1.5f};
        float vy{0.0f};
        int hp{2};
        bool is_airborne{false};
        bool is_homerun_flying{false};
        bool active{false};
        float respawn_timer{0.0f};
    };

    static constexpr int MAX_THUGS = 3;

    GameState GetState() const { return state_; }
    int GetScore() const { return score_; }
    int GetLives() const { return lives_; }
    ActionState GetActionState() const { return action_state_; }
    int GetHomeRuns() const { return home_runs_; }
    float GetPlayerX() const { return px_; }
    float GetPlayerY() const { return py_; }
    int GetThugsDefeated() const { return thugs_defeated_; }

    const Thug& GetThug(int i) const { return thugs_[i]; }

private:
    void ResetInning(bool hard_reset);
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateThugs(float dt);
    void CheckBatCombat();

    GameState state_{STATE_INNING};
    float state_timer_{0.0f};
    int score_{0};
    int lives_{3};
    int inning_{1};
    int home_runs_{0};
    int thugs_defeated_{0};

    // Ninja Batter (Captain Jose)
    float px_{3.0f};
    float py_{12.0f};
    int facing_{1};
    ActionState action_state_{ACTION_IDLE};
    float action_timer_{0.0f};

    Thug thugs_[MAX_THUGS];
};

} // namespace arcade
