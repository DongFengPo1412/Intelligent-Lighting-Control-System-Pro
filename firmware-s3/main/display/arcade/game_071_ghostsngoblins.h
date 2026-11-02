#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game071GhostsNGoblins : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_PLAYING = 1;
    static constexpr uint8_t STATE_DEAD = 2;
    static constexpr uint8_t STATE_VICTORY = 3;

    // Armor stages
    static constexpr uint8_t ARMOR_STEEL = 0;
    static constexpr uint8_t ARMOR_BOXERS = 1;

    // Weapons
    static constexpr uint8_t WEAPON_LANCE = 0;  // Straight fast lance
    static constexpr uint8_t WEAPON_TORCH = 1;  // Lobbed fire flask with ground flame

    static constexpr int MAX_WEAPONS = 3;
    static constexpr int MAX_ENEMIES = 4;
    static constexpr int MAX_FLAMES = 2;

    struct Projectile {
        float x;
        float y;
        float vx;
        float vy;
        uint8_t type;
        bool active;
    };

    struct Flame {
        float x;
        float y;
        float duration;
        bool active;
    };

    struct Enemy {
        float x;
        float y;
        float vx;
        float vy;
        int type;       // 0: Ground Zombie, 1: Flying Red Arremer demon
        int health;
        bool active;
    };

    Game071GhostsNGoblins();
    ~Game071GhostsNGoblins() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "Ghosts 'n Goblins (1985)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    int GetLives() const { return lives_; }
    float GetPlayerX() const { return px_; }
    float GetPlayerY() const { return py_; }
    uint8_t GetArmorStage() const { return armor_stage_; }
    uint8_t GetCurrentWeapon() const { return weapon_type_; }
    int GetEnemiesDefeated() const { return enemies_defeated_; }

    void ThrowWeapon();
    void Jump();
    void SetArmorStage(uint8_t stage) { armor_stage_ = stage; }
    void SetWeapon(uint8_t weapon) { weapon_type_ = weapon; }

private:
    void InitStage();
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateWeapons(float dt);
    void UpdateEnemies(float dt);
    void CheckCollisions();

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;
    int lives_;

    // Arthur state
    float px_;
    float py_;
    float pvy_;
    bool on_ground_;
    bool is_ducking_;
    int facing_;
    uint8_t armor_stage_;
    uint8_t weapon_type_;
    float throw_cooldown_;

    int enemies_defeated_;
    bool armor_drop_active_;
    float armor_drop_x_;
    float armor_drop_y_;

    Projectile weapons_[MAX_WEAPONS];
    Flame flames_[MAX_FLAMES];
    Enemy enemies_[MAX_ENEMIES];
};

} // namespace arcade
