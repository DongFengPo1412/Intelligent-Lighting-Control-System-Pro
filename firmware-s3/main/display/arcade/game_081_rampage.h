#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game081Rampage : public Cartridge {
public:
    Game081Rampage();
    ~Game081Rampage() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 81; }
    std::string GetName() const override { return "Rampage (1986)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_PLAYING = 0,
        STATE_STAGE_CLEAR = 1,
        STATE_MONSTER_DEAD = 2
    };

    struct Building {
        float x_left{0.0f};
        float x_right{0.0f};
        int height{12}; // blocks high from ground y=14
        int hp{10};     // damage to collapse
        bool collapsed{false};
    };

    struct Helicopter {
        float x{15.0f};
        float y{4.0f};
        float vx{-3.0f};
        bool active{true};
        float respawn_timer{0.0f};
    };

    GameState GetState() const { return state_; }
    int GetScore() const { return score_; }
    int GetHp() const { return monster_hp_; }
    int GetLives() const { return lives_; }
    float GetMonsterX() const { return mx_; }
    float GetMonsterY() const { return my_; }
    bool IsOnWall() const { return on_wall_; }

private:
    void ResetCity();
    void UpdateMonster(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateHelicopter(float dt);
    void CheckPunch();

    GameState state_{STATE_PLAYING};
    float state_timer_{0.0f};
    int score_{0};
    int high_score_{16000};
    int lives_{3};
    int monster_hp_{100};
    int days_survived_{1};

    // Monster (George the Gorilla)
    float mx_{2.0f};
    float my_{14.0f};
    float mvy_{0.0f};
    bool on_ground_{true};
    bool on_wall_{false};
    int current_building_{-1};
    int facing_{1};
    float punch_timer_{0.0f};

    static constexpr int NUM_BUILDINGS = 3;
    Building buildings_[NUM_BUILDINGS];

    Helicopter heli_;
};

} // namespace arcade
