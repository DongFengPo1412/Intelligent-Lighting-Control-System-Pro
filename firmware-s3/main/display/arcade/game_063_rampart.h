#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game063Rampart : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_PLAYING = 1;
    static constexpr uint8_t STATE_DEAD = 2;
    static constexpr uint8_t STATE_VICTORY = 3;

    static constexpr uint8_t PHASE_BOMBARD = 0;
    static constexpr uint8_t PHASE_REBUILD = 1;

    static constexpr uint8_t CELL_OCEAN = 0;
    static constexpr uint8_t CELL_LAND = 1;
    static constexpr uint8_t CELL_CASTLE = 2;
    static constexpr uint8_t CELL_WALL = 3;
    static constexpr uint8_t CELL_CANNON = 4;

    static constexpr int MAX_SHIPS = 3;
    static constexpr int MAX_CANNONBALLS = 4;

    struct Ship {
        float x;
        float y;
        float vy;
        int health;
        bool active;
        float shoot_cooldown;
    };

    struct Cannonball {
        float x;
        float y;
        float target_x;
        float target_y;
        float t;            // 0.0 to 1.0 flight progress
        bool active;
    };

    Game063Rampart();
    ~Game063Rampart() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "Rampart (1990)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    uint8_t GetPhase() const { return phase_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    int GetRound() const { return round_; }
    float GetPhaseTimer() const { return phase_timer_; }
    int GetCursorX() const { return cursor_x_; }
    int GetCursorY() const { return cursor_y_; }
    bool IsCastleEnclosed() const { return castle_enclosed_; }
    int GetCannonsCount() const { return cannons_count_; }

    void FireCannonAtCursor();
    void PlaceWallAtCursor();
    void CheckEnclosure();

private:
    void InitRound();
    void UpdateBombard(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateRebuild(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateShips(float dt);
    void UpdateCannonballs(float dt);

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;

    uint8_t phase_;
    float phase_timer_;
    int round_;                 // 1 to 3 rounds
    int cursor_x_;
    int cursor_y_;

    uint8_t grid_[16][16];
    bool castle_enclosed_;
    int cannons_count_;
    int ships_destroyed_;

    Ship ships_[MAX_SHIPS];
    Cannonball cannonballs_[MAX_CANNONBALLS];
};

} // namespace arcade
