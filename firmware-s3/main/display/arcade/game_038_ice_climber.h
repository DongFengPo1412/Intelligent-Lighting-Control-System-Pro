#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game038IceClimber : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_PLAYING = 1;
    static constexpr uint8_t STATE_DEAD = 2;
    static constexpr uint8_t STATE_VICTORY = 3;

    static constexpr int NUM_FLOORS = 4;
    static constexpr int MAX_ENEMIES = 2;

    struct Topi {
        float x;
        int floor_y;
        float vx;
        bool active;
    };

    struct Condor {
        float x;
        float y;
        float vx;
        bool active;
    };

    Game038IceClimber();
    ~Game038IceClimber() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "Ice Climber (1985)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    int GetLives() const { return lives_; }
    int GetCurrentFloor() const;

    float GetPlayerX() const { return player_x_; }
    float GetPlayerY() const { return player_y_; }
    bool IsGrounded() const { return is_grounded_; }

    void SetPlayerPos(float x, float y) { player_x_ = x; player_y_ = y; }
    void BreakIceAt(int x, int y);
    bool IsIceBlock(int x, int y) const;

private:
    void InitMountain();
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateTopis(float dt);
    void UpdateCondor(float dt);
    void CheckCollisions();

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;
    int lives_;

    float player_x_;
    float player_y_;
    float player_vx_;
    float player_vy_;
    bool is_grounded_;
    float hammer_timer_;

    Condor condor_;
    Topi topis_[MAX_ENEMIES];

    uint8_t ice_grid_[16][16]; // 0: Empty, 1: Solid base, 2: Breakable Ice Block
};

} // namespace arcade
