#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game056_1942 : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_PLAYING = 1;
    static constexpr uint8_t STATE_DEAD = 2;
    static constexpr uint8_t STATE_VICTORY = 3;

    static constexpr int MAX_BULLETS = 8;
    static constexpr int MAX_PLANES = 5;

    struct Bullet {
        float x;
        float y;
        float vx;
        float vy;
        bool is_player;
        bool active;
    };

    struct Plane {
        float x;
        float y;
        float vx;
        float vy;
        int type;       // 0: Zero, 1: Red Formation (POW drop), 2: Bomber
        int health;
        bool active;
        float shoot_cooldown;
    };

    Game056_1942();
    ~Game056_1942() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "1942 (1984)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    int GetLives() const { return lives_; }
    int GetLoopsRemaining() const { return loops_remaining_; }
    bool IsLooping() const { return is_looping_; }
    bool HasWingmen() const { return has_wingmen_; }
    bool IsBossActive() const { return boss_active_; }
    int GetBossHealth() const { return boss_health_; }
    float GetPlayerX() const { return player_x_; }
    float GetPlayerY() const { return player_y_; }

    void TriggerLoop();
    void FireBullets();

private:
    void InitStage();
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdatePlanes(float dt);
    void UpdateBoss(float dt);
    void UpdateBullets(float dt);
    void CheckCollisions();

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;
    int lives_;

    float player_x_;
    float player_y_;
    bool is_looping_;
    float loop_timer_;
    int loops_remaining_;
    bool has_wingmen_;

    float scroll_y_;
    int planes_defeated_;

    // Boss Ayako heavy bomber
    bool boss_active_;
    float boss_x_;
    float boss_y_;
    float boss_vx_;
    int boss_health_;
    float boss_shoot_cooldown_;

    Bullet bullets_[MAX_BULLETS];
    Plane planes_[MAX_PLANES];
};

} // namespace arcade
