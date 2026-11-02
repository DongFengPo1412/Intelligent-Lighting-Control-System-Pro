#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game092SengokuBlade : public Cartridge {
public:
    Game092SengokuBlade();
    ~Game092SengokuBlade() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 92; }
    std::string GetName() const override { return "Sengoku Blade (1996)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_AIR_BATTLE = 0,
        STATE_HERO_HIT = 1,
        STATE_STAGE_CLEAR = 2,
        STATE_GAME_OVER = 3
    };

    struct Bullet {
        float x{0.0f};
        float y{0.0f};
        float vx{0.0f};
        float vy{0.0f};
        bool is_charge_shot{false};
        bool active{false};
    };

    struct EnemyBullet {
        float x{0.0f};
        float y{0.0f};
        float vx{0.0f};
        float vy{0.0f};
        bool active{false};
    };

    struct KarakuriEnemy {
        float x{0.0f};
        float y{0.0f};
        float vy{1.2f};
        int hp{3};
        bool is_boss{false};
        float shoot_timer{1.2f};
        bool active{false};
        float respawn_timer{0.0f};
    };

    static constexpr int MAX_HERO_BULLETS = 6;
    static constexpr int MAX_ENEMY_BULLETS = 8;
    static constexpr int MAX_ENEMIES = 3;

    GameState GetState() const { return state_; }
    int GetScore() const { return score_; }
    int GetLives() const { return lives_; }
    int GetBombs() const { return bombs_; }
    float GetPlayerX() const { return px_; }
    float GetPlayerY() const { return py_; }
    float GetChargeTimer() const { return charge_timer_; }
    bool IsMeleeSlashing() const { return melee_timer_ > 0.0f; }
    bool IsBombActive() const { return bomb_timer_ > 0.0f; }
    int GetEnemiesDefeated() const { return enemies_defeated_; }

    const KarakuriEnemy& GetEnemy(int i) const { return enemies_[i]; }

private:
    void ResetBattle(bool hard_reset);
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateHeroProjectiles(float dt);
    void UpdateEnemies(float dt);
    void UpdateEnemyBullets(float dt);
    void CheckCombat();

    GameState state_{STATE_AIR_BATTLE};
    float state_timer_{0.0f};
    int score_{0};
    int lives_{3};
    int bombs_{2};
    int stage_{1};
    int enemies_defeated_{0};

    // Flying Miko Hero
    float px_{2.0f};
    float py_{8.0f};
    float charge_timer_{0.0f};
    bool is_charging_{false};
    float melee_timer_{0.0f};
    float bomb_timer_{0.0f};
    float fire_cooldown_{0.0f};

    // Scenery scroll
    float cloud_scroll_{0.0f};

    Bullet hero_bullets_[MAX_HERO_BULLETS];
    EnemyBullet enemy_bullets_[MAX_ENEMY_BULLETS];
    KarakuriEnemy enemies_[MAX_ENEMIES];
};

} // namespace arcade
