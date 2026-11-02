#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game100TimePilot : public Cartridge {
public:
    Game100TimePilot();
    ~Game100TimePilot() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 100; }
    std::string GetName() const override { return "Time Pilot (1982)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_DOGFIGHT = 0,
        STATE_TIME_WARP = 1,
        STATE_PLAYER_SHOT_DOWN = 2,
        STATE_GAME_OVER = 3
    };

    struct Bullet {
        float x{0.0f};
        float y{0.0f};
        float vx{0.0f};
        float vy{0.0f};
        float life{0.0f};
        bool is_enemy{false};
        bool active{false};
    };

    struct EnemyFighter {
        float x{0.0f};
        float y{0.0f};
        float vx{0.0f};
        float vy{0.0f};
        int hp{1};
        bool is_boss{false};
        float fire_timer{0.0f};
        bool active{false};
    };

    struct Parachutist {
        float x{0.0f};
        float y{0.0f};
        float vy{0.8f};
        bool active{false};
    };

    struct Cloud {
        float x{0.0f};
        float y{0.0f};
        float speed{1.0f};
    };

    static constexpr int MAX_PLAYER_BULLETS = 4;
    static constexpr int MAX_ENEMY_BULLETS = 4;
    static constexpr int MAX_ENEMIES = 4;
    static constexpr int MAX_PARACHUTES = 2;
    static constexpr int MAX_CLOUDS = 4;

    GameState GetState() const { return state_; }
    int GetScore() const { return score_; }
    int GetLives() const { return lives_; }
    int GetEra() const { return era_; }
    int GetSquadronDefeated() const { return squadron_defeated_; }
    float GetPlayerAngle() const { return player_angle_; }
    bool IsBossActive() const { return boss_active_; }

    const EnemyFighter& GetEnemy(int i) const { return enemies_[i]; }
    const Parachutist& GetParachute(int i) const { return parachutes_[i]; }

private:
    GameState state_{STATE_DOGFIGHT};
    float state_timer_{0.0f};
    int score_{0};
    int lives_{3};
    int era_{0}; // 0: 1910, 1: 1940, 2: 1970, 3: 2001, 4: UFO
    int squadron_defeated_{0};
    bool boss_active_{false};

    // Centered ship orientation
    float player_angle_{ -1.5707963f }; // Upwards (-PI/2)
    float speed_{ 4.5f };
    float fire_cooldown_{0.0f};

    EnemyFighter enemies_[MAX_ENEMIES + 1]; // +1 for Boss
    Bullet player_bullets_[MAX_PLAYER_BULLETS];
    Bullet enemy_bullets_[MAX_ENEMY_BULLETS];
    Parachutist parachutes_[MAX_PARACHUTES];
    Cloud clouds_[MAX_CLOUDS];

    void ResetEra();
    void SpawnBoss();
    void SpawnParachute(float x, float y);
    void UpdateFlight(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateEnemies(float dt, float scroll_x, float scroll_y);
    void UpdateBullets(float dt, float scroll_x, float scroll_y);
    void UpdateParachutes(float dt, float scroll_x, float scroll_y);
    void UpdateClouds(float dt, float scroll_x, float scroll_y);
    void CheckCollisions();
};

} // namespace arcade
