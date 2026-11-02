#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game061BattleCity : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_PLAYING = 1;
    static constexpr uint8_t STATE_DEAD = 2;
    static constexpr uint8_t STATE_VICTORY = 3;

    static constexpr uint8_t TILE_EMPTY = 0;
    static constexpr uint8_t TILE_BRICK = 1;
    static constexpr uint8_t TILE_STEEL = 2;
    static constexpr uint8_t TILE_WATER = 3;
    static constexpr uint8_t TILE_FOREST = 4;
    static constexpr uint8_t TILE_EAGLE = 5;
    static constexpr uint8_t TILE_EAGLE_DEAD = 6;

    static constexpr int MAX_SHELLS = 6;
    static constexpr int MAX_ENEMIES = 3;

    struct Shell {
        float x;
        float y;
        float vx;
        float vy;
        bool is_player;
        bool active;
    };

    struct EnemyTank {
        float x;
        float y;
        int dir;        // 0: Up, 1: Right, 2: Down, 3: Left
        int health;
        int type;       // 0: Basic, 1: Fast, 2: Heavy Armor
        bool active;
        float shoot_cooldown;
        float move_timer;
    };

    Game061BattleCity();
    ~Game061BattleCity() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "Battle City (1980)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    int GetLives() const { return lives_; }
    bool IsEagleAlive() const { return eagle_alive_; }
    int GetEnemiesRemaining() const { return total_enemies_spawn_ - enemies_defeated_; }
    int GetTankTier() const { return tank_tier_; }
    float GetPlayerX() const { return player_x_; }
    float GetPlayerY() const { return player_y_; }

    void ShootShell();
    void TriggerShovelReinforce();
    void DestroyEagle();

private:
    void InitMap();
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateEnemies(float dt);
    void UpdateShells(float dt);
    void CheckCollisions();
    bool CanMoveTo(float x, float y) const;

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;
    int lives_;

    uint8_t map_[16][16];

    float player_x_;
    float player_y_;
    int player_dir_;
    int tank_tier_;
    float shoot_cooldown_;

    bool eagle_alive_;
    float shovel_timer_;

    int enemies_defeated_;
    int total_enemies_spawn_;
    float enemy_spawn_timer_;

    Shell shells_[MAX_SHELLS];
    EnemyTank enemies_[MAX_ENEMIES];
};

} // namespace arcade
