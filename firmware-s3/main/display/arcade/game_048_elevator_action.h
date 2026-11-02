#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game048ElevatorAction : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_PLAYING = 1;
    static constexpr uint8_t STATE_DEAD = 2;
    static constexpr uint8_t STATE_VICTORY = 3;

    static constexpr int NUM_FLOORS = 4;
    static constexpr int MAX_BULLETS = 4;
    static constexpr int MAX_ENEMIES = 3;
    static constexpr int NUM_RED_DOORS = 2;

    struct Bullet {
        float x;
        float y;
        float vx;
        bool is_player;
        bool active;
    };

    struct EnemySpy {
        float x;
        int floor;
        float vx;
        bool active;
        float shoot_timer;
    };

    struct RedDoor {
        int floor;
        int col;
        bool collected;
    };

    struct OverheadLight {
        int floor;
        int col;
        bool active;
    };

    Game048ElevatorAction();
    ~Game048ElevatorAction() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "Elevator Action (1983)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    int GetLives() const { return lives_; }
    int GetDocumentsRemaining() const;

    float GetPlayerX() const { return player_x_; }
    float GetPlayerY() const { return player_y_; }
    float GetElevatorY() const { return elevator_y_; }
    bool IsInElevator() const { return in_elevator_; }

    void SetPlayerPos(float x, float y) { player_x_ = x; player_y_ = y; }
    void FirePistol(bool is_player, float x, float y, float dir);

private:
    void InitBuilding();
    void UpdateElevator(float dt, uint32_t buttons);
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateEnemies(float dt);
    void UpdateBullets(float dt);
    void CheckCollisions();

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;
    int lives_;
    int docs_collected_;

    float player_x_;
    float player_y_;
    float player_vx_;
    int player_facing_;     // +1 or -1
    bool is_crouching_;
    bool in_elevator_;

    float elevator_y_;      // Shaft Y (3.0 to 15.0)
    float elevator_vy_;
    float blackout_timer_;

    Bullet bullets_[MAX_BULLETS];
    EnemySpy enemies_[MAX_ENEMIES];
    RedDoor red_doors_[NUM_RED_DOORS];
    OverheadLight lights_[NUM_FLOORS];
};

} // namespace arcade
