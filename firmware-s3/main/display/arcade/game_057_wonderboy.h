#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game057WonderBoy : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_PLAYING = 1;
    static constexpr uint8_t STATE_DEAD = 2;
    static constexpr uint8_t STATE_VICTORY = 3;

    static constexpr int MAX_AXES = 3;
    static constexpr int MAX_MONSTERS = 4;
    static constexpr int MAX_FRUITS = 3;

    struct Axe {
        float x;
        float y;
        float vx;
        float vy;
        bool active;
    };

    struct Monster {
        float x;
        float y;
        float vx;
        int type;       // 0: Snail, 1: Octopus, 2: Rolling Boulder
        int health;
        bool active;
    };

    struct Fruit {
        float x;
        float y;
        int type;       // 0: Banana, 1: Apple, 2: Skateboard Egg
        bool active;
    };

    Game057WonderBoy();
    ~Game057WonderBoy() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "Wonder Boy (1986)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    int GetLives() const { return lives_; }
    int GetVitality() const { return vitality_; }
    bool HasSkateboard() const { return has_skateboard_; }
    bool HasFairy() const { return has_fairy_; }
    float GetPlayerX() const { return player_x_; }
    float GetPlayerY() const { return player_y_; }
    float GetStageProgress() const { return stage_progress_; }

    void ThrowAxe();
    void SetVitality(int v) { vitality_ = v; }
    void GiveSkateboard() { has_skateboard_ = true; }

private:
    void InitStage();
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateAxes(float dt);
    void UpdateMonsters(float dt);
    void CheckCollisions();

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;
    int lives_;

    float player_x_;
    float player_y_;
    float player_vx_;
    float player_vy_;
    int player_facing_;
    bool is_jumping_;

    int vitality_;          // 0 to 16
    float vitality_timer_;

    bool has_skateboard_;
    bool has_fairy_;
    float fairy_timer_;

    float stage_progress_;  // 0.0 to 60.0 km
    float scroll_speed_;

    Axe axes_[MAX_AXES];
    Monster monsters_[MAX_MONSTERS];
    Fruit fruits_[MAX_FRUITS];
};

} // namespace arcade
