#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game047DoubleDragon : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_PLAYING = 1;
    static constexpr uint8_t STATE_DEAD = 2;
    static constexpr uint8_t STATE_VICTORY = 3;

    static constexpr int MAX_ENEMIES = 3;

    struct Enemy {
        float x;
        float y;
        float vx;
        float vy;
        int health;
        bool active;
        bool is_knocked_down;
        float knockdown_timer;
        float attack_cooldown;
        bool is_attacking;
    };

    struct Weapon {
        float x;
        float y;
        bool on_ground;
    };

    Game047DoubleDragon();
    ~Game047DoubleDragon() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "Double Dragon (1987)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    int GetPlayerHealth() const { return player_health_; }
    int GetEnemiesRemaining() const;
    bool HasWeapon() const { return has_weapon_; }

    float GetPlayerX() const { return player_x_; }
    float GetPlayerY() const { return player_y_; }
    void SetPlayerPos(float x, float y) { player_x_ = x; player_y_ = y; }

    void AttackPunch();
    void AttackKick();
    void AttackElbow();

private:
    void InitArena();
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateEnemies(float dt);
    void CheckHitboxes();

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;
    int player_health_;
    int enemies_defeated_;
    int total_wave_enemies_;

    float player_x_;
    float player_y_;
    int player_facing_;     // +1 (right) or -1 (left)
    bool has_weapon_;

    int attack_type_;       // 0: None, 1: Punch, 2: Kick, 3: Elbow
    float attack_timer_;
    float attack_duration_;

    Enemy enemies_[MAX_ENEMIES];
    Weapon weapon_;
};

} // namespace arcade
