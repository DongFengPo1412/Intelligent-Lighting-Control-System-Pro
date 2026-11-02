#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game067SnowBros : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_PLAYING = 1;
    static constexpr uint8_t STATE_DEAD = 2;
    static constexpr uint8_t STATE_VICTORY = 3;

    static constexpr int MAX_SHOTS = 3;
    static constexpr int MAX_ENEMIES = 4;
    static constexpr int MAX_POTIONS = 2;

    // Enemy snow coating stages
    static constexpr int SNOW_NONE = 0;
    static constexpr int SNOW_LIGHT = 1;
    static constexpr int SNOW_MEDIUM = 2;
    static constexpr int SNOW_FULL_BALL = 3;

    struct Projectile {
        float x;
        float y;
        float vx;
        bool active;
    };

    struct Enemy {
        float x;
        float y;
        float vx;
        int snow_stage;       // 0: Normal, 1: Slowed, 2: Frozen, 3: Full Giant Snowball
        bool is_rolling;      // Rolling across platforms like a bowling ball
        float roll_vx;
        float melt_timer;     // Thawing timer if left untouched
        bool active;
    };

    struct Potion {
        float x;
        float y;
        int type;             // 0: Red (Speed), 1: Blue (Power), 2: Yellow (Range)
        bool active;
    };

    Game067SnowBros();
    ~Game067SnowBros() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "Snow Bros. (1990)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    int GetLives() const { return lives_; }
    float GetPlayerX() const { return px_; }
    float GetPlayerY() const { return py_; }
    int GetEnemiesDefeated() const { return enemies_defeated_; }
    bool HasSpeedPotion() const { return has_speed_potion_; }
    bool HasPowerPotion() const { return has_power_potion_; }

    void ThrowSnow();
    void Jump();

private:
    void InitStage();
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateProjectiles(float dt);
    void UpdateEnemies(float dt);
    void CheckCollisions();

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;
    int lives_;

    // Player snowman state
    float px_;
    float py_;
    float pvy_;
    bool on_ground_;
    int facing_;
    float shoot_cooldown_;

    bool has_speed_potion_;
    bool has_power_potion_;
    bool has_range_potion_;

    int enemies_defeated_;

    Projectile shots_[MAX_SHOTS];
    Enemy enemies_[MAX_ENEMIES];
    Potion potions_[MAX_POTIONS];
};

} // namespace arcade
