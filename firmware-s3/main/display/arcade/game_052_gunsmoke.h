#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game052GunSmoke : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_PLAYING = 1;
    static constexpr uint8_t STATE_DEAD = 2;
    static constexpr uint8_t STATE_VICTORY = 3;

    static constexpr int MAX_BULLETS = 6;
    static constexpr int MAX_BANDITS = 4;
    static constexpr int MAX_BARRELS = 2;

    struct Bullet {
        float x;
        float y;
        float vx;
        float vy;
        bool is_player;
        bool active;
    };

    struct Bandit {
        float x;
        float y;
        float vx;
        int health;
        bool active;
        float shoot_cooldown;
    };

    struct Barrel {
        float x;
        float y;
        bool has_horse;
        bool active;
    };

    Game052GunSmoke();
    ~Game052GunSmoke() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "Gun.Smoke (1985)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    int GetLives() const { return lives_; }
    bool HasHorse() const { return has_horse_; }
    int GetHorseArmor() const { return horse_armor_; }
    float GetScrollDistance() const { return scroll_dist_; }
    bool IsBossActive() const { return boss_active_; }
    int GetBossHealth() const { return boss_health_; }

    void Shoot(int direction); // -1: Left (A), 0: Center (A+B), +1: Right (B)

private:
    void InitStage();
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateBullets(float dt);
    void UpdateBandits(float dt);
    void UpdateBoss(float dt);
    void CheckCollisions();

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;
    int lives_;

    float player_x_;
    float player_y_;
    bool has_horse_;
    int horse_armor_;

    float scroll_dist_;
    float scroll_speed_;

    bool boss_active_;
    float boss_x_;
    float boss_y_;
    float boss_vx_;
    int boss_health_;
    float boss_shoot_cooldown_;

    Bullet bullets_[MAX_BULLETS];
    Bandit bandits_[MAX_BANDITS];
    Barrel barrels_[MAX_BARRELS];
};

} // namespace arcade
