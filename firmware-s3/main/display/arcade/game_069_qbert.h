#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game069Qbert : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_PLAYING = 1;
    static constexpr uint8_t STATE_DEAD = 2;
    static constexpr uint8_t STATE_VICTORY = 3;

    // Pyramid size: Row 0 has 1 cube, Row 1 has 2, ... Row 4 has 5 cubes (Total 15 cubes)
    static constexpr int NUM_ROWS = 5;
    static constexpr int TOTAL_CUBES = 15; // 1 + 2 + 3 + 4 + 5 = 15

    static constexpr int MAX_BALLS = 2;

    struct Ball {
        int row;
        int col;
        float jump_timer;
        bool is_green;      // Green freezes time, Red is lethal
        bool active;
    };

    struct Coily {
        int row;
        int col;
        bool is_hatched;    // Starts as purple egg, hatches at bottom row into snake
        float jump_timer;
        bool active;
    };

    Game069Qbert();
    ~Game069Qbert() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "Q*bert (1982)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    int GetLives() const { return lives_; }
    int GetPlayerRow() const { return player_row_; }
    int GetPlayerCol() const { return player_col_; }
    int GetCubesFlipped() const { return cubes_flipped_; }
    bool IsDiscLeftAvailable() const { return disc_left_active_; }
    bool IsDiscRightAvailable() const { return disc_right_active_; }
    bool IsFreezeActive() const { return freeze_timer_ > 0.0f; }

    void Jump(int drow, int dcol);

private:
    void InitStage();
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateEnemies(float dt);
    void CheckCollisions();
    int GetCubeIndex(int r, int c) const;

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;
    int lives_;

    // Q*bert position
    int player_row_;
    int player_col_;
    float jump_anim_timer_;
    float jump_offset_x_;
    float jump_offset_y_;

    // Pyramid cubes flipped states (false: starting blue, true: flipped yellow)
    bool cube_flipped_[TOTAL_CUBES];
    int cubes_flipped_;

    // Escape discs
    bool disc_left_active_;
    bool disc_right_active_;

    // Coily the snake & falling balls
    Coily coily_;
    Ball balls_[MAX_BALLS];
    float freeze_timer_;
    float enemy_spawn_timer_;
};

} // namespace arcade
