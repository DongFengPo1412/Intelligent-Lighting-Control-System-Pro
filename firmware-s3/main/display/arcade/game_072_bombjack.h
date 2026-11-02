#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game072BombJack : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_PLAYING = 1;
    static constexpr uint8_t STATE_DEAD = 2;
    static constexpr uint8_t STATE_VICTORY = 3;

    static constexpr int MAX_BOMBS = 8;
    static constexpr int MAX_ENEMIES = 3;

    struct Bomb {
        float x;
        float y;
        bool is_lit;       // Burning sparking fuse
        bool active;
    };

    struct Enemy {
        float x;
        float y;
        float vx;
        float vy;
        int type;          // 0: Flying bird, 1: Mummy, 2: Mechanical sphere
        bool is_frozen;    // Frozen into bonus coin during Power Ball active
        bool active;
    };

    Game072BombJack();
    ~Game072BombJack() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "Bomb Jack (1984)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    int GetLives() const { return lives_; }
    float GetPlayerX() const { return px_; }
    float GetPlayerY() const { return py_; }
    int GetBombsRemaining() const;
    int GetLitBombsCollected() const { return lit_bombs_collected_; }
    bool IsPowerBallActive() const { return power_ball_timer_ > 0.0f; }

    void Jump();
    void GlideBrake();
    void DiveStomp();

private:
    void InitStage();
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateEnemies(float dt);
    void UpdatePowerBall(float dt);
    void CheckCollisions();
    void LightNextBomb();

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;
    int lives_;

    // Jack superhero state
    float px_;
    float py_;
    float pvy_;
    bool on_ground_;
    bool is_gliding_;
    int facing_;

    // Sequential lit fuse
    int lit_bombs_collected_;
    int combo_multiplier_;

    // Power Ball "P"
    bool power_ball_spawned_;
    float pb_x_;
    float pb_y_;
    float pb_vy_;
    float power_ball_timer_;

    Bomb bombs_[MAX_BOMBS];
    Enemy enemies_[MAX_ENEMIES];
};

} // namespace arcade
