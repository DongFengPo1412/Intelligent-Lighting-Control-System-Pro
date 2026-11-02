#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game086KiKiKaiKai : public Cartridge {
public:
    Game086KiKiKaiKai();
    ~Game086KiKiKaiKai() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 86; }
    std::string GetName() const override { return "KiKi KaiKai (1986)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_PLAYING = 0,
        STATE_STAGE_CLEAR = 1,
        STATE_HERO_DEAD = 2
    };

    enum EnemyType {
        EN_BAKE_NEKO = 0, // Quick cat spirit
        EN_KASA_OBAKE = 1, // Bouncing umbrella ghost
        EN_TENGU = 2       // Flying projectile shooter
    };

    struct Enemy {
        float x{0.0f};
        float y{0.0f};
        float vx{0.0f};
        float vy{0.0f};
        EnemyType type{EN_BAKE_NEKO};
        int hp{1};
        bool active{false};
        float shoot_timer{0.0f};
    };

    struct Projectile {
        float x{0.0f};
        float y{0.0f};
        float vx{0.0f};
        float vy{0.0f};
        bool is_talisman{true}; // true = Sayo's Ofuda, false = Enemy Fireball
        bool active{false};
    };

    GameState GetState() const { return state_; }
    int GetScore() const { return score_; }
    int GetLives() const { return lives_; }
    float GetPlayerX() const { return px_; }
    float GetPlayerY() const { return py_; }
    bool IsSwingingGohei() const { return gohei_timer_ > 0.0f; }

private:
    void ResetStage();
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateEnemies(float dt);
    void UpdateProjectiles(float dt);
    void FireTalisman();
    void SwingGohei();
    void CheckCollisions();

    GameState state_{STATE_PLAYING};
    float state_timer_{0.0f};
    int score_{0};
    int high_score_{24000};
    int lives_{3};
    int yokai_defeated_{0};

    // Shrine Maiden Sayo-chan
    float px_{7.5f};
    float py_{12.0f};
    int facing_x_{0};
    int facing_y_{-1}; // default facing north
    float gohei_timer_{0.0f}; // Gohei wand swing duration
    bool empowered_talisman_{false};

    static constexpr int MAX_ENEMIES = 4;
    Enemy enemies_[MAX_ENEMIES];

    static constexpr int MAX_PROJECTILES = 8;
    Projectile projs_[MAX_PROJECTILES];

    float spawn_timer_{0.0f};
    float scroll_offset_{0.0f};
};

} // namespace arcade
