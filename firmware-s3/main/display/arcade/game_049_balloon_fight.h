#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game049BalloonFight : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_PLAYING = 1;
    static constexpr uint8_t STATE_DEAD = 2;
    static constexpr uint8_t STATE_VICTORY = 3;

    static constexpr int MAX_ENEMIES = 3;
    static constexpr int MAX_SPARKS = 2;

    struct Enemy {
        float x;
        float y;
        float vx;
        float vy;
        int balloons;       // 1 or 0
        bool on_parachute;
        bool is_pumping;
        float pump_timer;
        bool active;
    };

    struct Spark {
        float x;
        float y;
        float vx;
        float vy;
        bool active;
    };

    Game049BalloonFight();
    ~Game049BalloonFight() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "Balloon Fight (1984)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    int GetLives() const { return lives_; }
    int GetPlayerBalloons() const { return player_balloons_; }
    int GetEnemiesRemaining() const;

    float GetPlayerX() const { return player_x_; }
    float GetPlayerY() const { return player_y_; }
    void SetPlayerPos(float x, float y) { player_x_ = x; player_y_ = y; }
    void FlapWings(bool strong);

private:
    void InitArena();
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateEnemies(float dt);
    void UpdateSparks(float dt);
    void CheckCollisions();

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;
    int lives_;
    int player_balloons_;   // 2, 1, or 0
    int enemies_defeated_;
    int total_wave_enemies_;

    float player_x_;
    float player_y_;
    float player_vx_;
    float player_vy_;

    float fish_timer_;
    bool fish_leaping_;
    float fish_x_;

    Enemy enemies_[MAX_ENEMIES];
    Spark sparks_[MAX_SPARKS];

    // Platforms grid: 16x16 boolean
    bool platform_grid_[16][16];
};

} // namespace arcade
