#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game042MarioBros : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_PLAYING = 1;
    static constexpr uint8_t STATE_DEAD = 2;
    static constexpr uint8_t STATE_VICTORY = 3;

    static constexpr int MAX_ENEMIES = 4;

    struct Enemy {
        float x;
        float y;
        float vx;
        float vy;
        bool active;
        bool is_flipped;
        float flip_timer;
        bool is_enraged;
    };

    Game042MarioBros();
    ~Game042MarioBros() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "Mario Bros. (1983)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    int GetLives() const { return lives_; }
    int GetPowHitsRemaining() const { return pow_hits_; }
    int GetEnemiesRemaining() const;

    float GetPlayerX() const { return player_x_; }
    float GetPlayerY() const { return player_y_; }

    void SetPlayerPos(float x, float y) { player_x_ = x; player_y_ = y; }
    void HitPowBlock();
    void BumpCeiling(float x, float y);

private:
    void InitArena();
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateEnemies(float dt);
    void CheckCollisions();

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;
    int lives_;
    int pow_hits_;
    int enemies_defeated_;
    int total_wave_enemies_;

    float player_x_;
    float player_y_;
    float player_vx_;
    float player_vy_;
    int player_facing_;
    bool is_grounded_;

    float pow_shake_timer_;

    Enemy enemies_[MAX_ENEMIES];
    uint8_t platform_grid_[16][16]; // 0: Air, 1: Pipe, 2: Solid Platform, 3: POW block
};

} // namespace arcade
