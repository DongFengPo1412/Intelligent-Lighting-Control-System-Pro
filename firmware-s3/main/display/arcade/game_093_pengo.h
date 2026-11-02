#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game093Pengo : public Cartridge {
public:
    Game093Pengo();
    ~Game093Pengo() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 93; }
    std::string GetName() const override { return "Pengo (1982)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_PLAYING = 0,
        STATE_PENGO_HIT = 1,
        STATE_ROUND_CLEAR = 2,
        STATE_GAME_OVER = 3
    };

    enum BlockType : uint8_t {
        BLOCK_EMPTY = 0,
        BLOCK_ICE = 1,
        BLOCK_DIAMOND = 2,
        BLOCK_WALL = 3
    };

    struct SnoBee {
        int x{0};
        int y{0};
        float move_timer{0.0f};
        float stun_timer{0.0f};
        bool active{false};
        float respawn_timer{0.0f};
    };

    struct SlidingBlock {
        float x{0.0f};
        float y{0.0f};
        float vx{0.0f};
        float vy{0.0f};
        bool is_diamond{false};
        bool active{false};
    };

    static constexpr int GRID_SIZE = 16;
    static constexpr int MAX_SNOBEES = 3;

    GameState GetState() const { return state_; }
    int GetScore() const { return score_; }
    int GetLives() const { return lives_; }
    int GetPlayerX() const { return px_; }
    int GetPlayerY() const { return py_; }
    int GetFacingX() const { return facing_x_; }
    int GetFacingY() const { return facing_y_; }
    bool IsSlidingActive() const { return sliding_block_.active; }
    int GetSnoBeesCrushed() const { return snobees_crushed_; }
    BlockType GetCell(int x, int y) const {
        if (x >= 0 && x < GRID_SIZE && y >= 0 && y < GRID_SIZE) return grid_[y][x];
        return BLOCK_WALL;
    }

    const SnoBee& GetSnoBee(int i) const { return snobees_[i]; }

private:
    void ResetMaze(bool hard_reset);
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateSlidingBlock(float dt);
    void UpdateSnoBees(float dt);
    void CheckDiamondAlignment();

    GameState state_{STATE_PLAYING};
    float state_timer_{0.0f};
    int score_{0};
    int lives_{3};
    int round_{1};
    int snobees_crushed_{0};

    // Penguin Hero (Pengo)
    int px_{7};
    int py_{12};
    int facing_x_{0};
    int facing_y_{-1};
    float move_cooldown_{0.0f};

    // Maze grid
    BlockType grid_[GRID_SIZE][GRID_SIZE];

    SlidingBlock sliding_block_;
    SnoBee snobees_[MAX_SNOBEES];
};

} // namespace arcade
