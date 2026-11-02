#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game051Shinobi : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_PLAYING = 1;
    static constexpr uint8_t STATE_DEAD = 2;
    static constexpr uint8_t STATE_VICTORY = 3;

    static constexpr int MAX_ENEMIES = 4;
    static constexpr int MAX_SHURIKENS = 3;
    static constexpr int MAX_HOSTAGES = 2;

    struct Enemy {
        float x;
        int tier;       // 0: Upper (y=7), 1: Lower (y=13)
        float vx;
        int health;
        bool active;
        float shoot_cooldown;
    };

    struct Shuriken {
        float x;
        int tier;
        float vx;
        bool is_gunshot;
        bool active;
    };

    struct Hostage {
        float x;
        int tier;
        bool rescued;
    };

    Game051Shinobi();
    ~Game051Shinobi() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "Shinobi (1987)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    int GetLives() const { return lives_; }
    int GetTier() const { return player_tier_; }
    int GetHostagesRemaining() const;
    bool HasGunUpgrade() const { return has_gun_upgrade_; }
    bool HasNinjutsu() const { return has_ninjutsu_; }

    float GetPlayerX() const { return player_x_; }
    void SetPlayerPos(float x, int tier) { player_x_ = x; player_tier_ = tier; }

    void ThrowShuriken();
    void TriggerNinjutsu();

private:
    void InitStage();
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateEnemies(float dt);
    void UpdateShurikens(float dt);
    void CheckCollisions();

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;
    int lives_;
    int hostages_rescued_;
    int enemies_defeated_;
    int total_enemies_;

    float player_x_;
    int player_tier_;       // 0: Upper (y=7), 1: Lower (y=13)
    int player_facing_;     // +1 (right) or -1 (left)
    bool is_crouching_;
    bool is_leaping_tier_;
    float leap_progress_;
    bool is_melee_slashing_;
    float melee_timer_;

    bool has_gun_upgrade_;
    bool has_ninjutsu_;
    float ninjutsu_flash_timer_;

    Enemy enemies_[MAX_ENEMIES];
    Shuriken shurikens_[MAX_SHURIKENS];
    Hostage hostages_[MAX_HOSTAGES];
};

} // namespace arcade
