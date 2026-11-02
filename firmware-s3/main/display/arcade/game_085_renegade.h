#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game085Renegade : public Cartridge {
public:
    Game085Renegade();
    ~Game085Renegade() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 85; }
    std::string GetName() const override { return "Renegade (1986)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_FIGHT = 0,
        STATE_VICTORY = 1,
        STATE_HERO_DEAD = 2
    };

    enum ActionState {
        ACT_IDLE = 0,
        ACT_FRONT_PUNCH = 1,
        ACT_BACK_ELBOW = 2,
        ACT_GROUND_POUND = 3,
        ACT_JUMP_KICK = 4
    };

    struct Thug {
        float x{12.0f};
        float y{10.0f};
        float vx{-2.0f};
        int hp{3};
        bool is_down{false};
        float down_timer{0.0f};
        bool active{false};
        float respawn_timer{0.0f};
    };

    GameState GetState() const { return state_; }
    int GetScore() const { return score_; }
    int GetHeroHp() const { return hero_hp_; }
    int GetLives() const { return lives_; }
    ActionState GetHeroAction() const { return action_; }
    float GetHeroX() const { return px_; }
    float GetHeroY() const { return py_; }
    int GetThugsDefeated() const { return thugs_defeated_; }

private:
    void ResetFight();
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateThugs(float dt);
    void CheckCombat();

    GameState state_{STATE_FIGHT};
    float state_timer_{0.0f};
    int score_{0};
    int high_score_{22000};
    int lives_{3};
    int hero_hp_{100};
    int thugs_defeated_{0};

    // Hero Kunio (White school uniform)
    float px_{4.0f};
    float py_{10.0f};
    int facing_{1};
    ActionState action_{ACT_IDLE};
    float act_timer_{0.0f};
    int mounted_thug_idx_{-1};

    static constexpr int MAX_THUGS = 3;
    Thug thugs_[MAX_THUGS];

    // Subway train hazard (bottom track at y = 14..15)
    float train_x_{-20.0f};
    float train_speed_{25.0f};
    float train_interval_{10.0f};
};

} // namespace arcade
