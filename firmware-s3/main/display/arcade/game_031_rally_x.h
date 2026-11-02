#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game031RallyX : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_PLAYING = 1;
    static constexpr uint8_t STATE_DEAD = 2;
    static constexpr uint8_t STATE_VICTORY = 3;

    static constexpr int MAX_FLAGS = 8;
    static constexpr int MAX_ENEMIES = 3;
    static constexpr int MAX_SMOKES = 6;

    struct Flag {
        int x;
        int y;
        bool collected;
        bool is_special; // 特殊旗帜双倍得分
    };

    struct Enemy {
        float x;
        float y;
        int dir; // 0: Up, 1: Right, 2: Down, 3: Left
        float stun_timer;
        bool active;
    };

    struct Smoke {
        int x;
        int y;
        float timer;
        bool active;
    };

    Game031RallyX();
    ~Game031RallyX() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "Rally-X (1980)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    int GetLives() const { return lives_; }
    float GetFuel() const { return fuel_; }
    int GetFlagsRemaining() const;

    float GetPlayerX() const { return player_x_; }
    float GetPlayerY() const { return player_y_; }

    void SetPlayerPos(float x, float y) { player_x_ = x; player_y_ = y; }
    void SetFuel(float f) { fuel_ = f; }
    void SetState(uint8_t s) { state_ = s; }

    bool DeploySmoke();

private:
    void InitMaze();
    void ResetCars();
    bool IsWallOrRock(int x, int y) const;
    void UpdatePlayer(float dt, uint32_t buttons);
    void UpdateEnemies(float dt);
    void UpdateSmokes(float dt);
    void CheckCollisions();

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;
    int lives_;
    float fuel_; // 0.0f ~ 100.0f

    float player_x_;
    float player_y_;
    int player_dir_;
    int next_dir_;
    float smoke_cooldown_;

    uint8_t maze_[16][16];

    Flag flags_[MAX_FLAGS];
    Enemy enemies_[MAX_ENEMIES];
    Smoke smokes_[MAX_SMOKES];
};

} // namespace arcade
