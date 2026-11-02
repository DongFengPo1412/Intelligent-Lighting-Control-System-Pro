#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game110DevilWorld : public Cartridge {
public:
    Game110DevilWorld();
    ~Game110DevilWorld() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 110; }
    std::string GetName() const override { return "Devil World (1984)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_NAVIGATING = 0,
        STATE_CRUSHED = 1,
        STATE_ROUND_CLEAR = 2,
        STATE_GAME_OVER = 3
    };

    struct Monster {
        float x{0.0f};
        float y{0.0f};
        float vx{2.0f};
        float vy{0.0f};
        bool is_fried_egg{false};
        float egg_timer{0.0f};
        bool active{false};
    };

    static constexpr int MAZE_WIDTH = 16;
    static constexpr int MAZE_HEIGHT = 16;
    static constexpr int MAX_MONSTERS = 2;

    GameState GetState() const { return state_; }
    int GetScore() const { return score_; }
    int GetLives() const { return lives_; }
    int GetRound() const { return round_; }
    float GetPlayerX() const { return px_; }
    float GetPlayerY() const { return py_; }
    bool HasCross() const { return has_cross_; }
    int GetDevilPointDir() const { return devil_point_dir_; } // 0=None, 1=Left, 2=Right, 3=Up, 4=Down
    int GetPearlsRemaining() const { return pearls_remaining_; }

    const Monster& GetMonster(int i) const { return monsters_[i]; }

    void SetDevilDirection(int dir);

private:
    GameState state_{STATE_NAVIGATING};
    float state_timer_{0.0f};
    int score_{0};
    int lives_{3};
    int round_{1};
    int pearls_remaining_{0};

    // Tamagon Dragon
    float px_{8.0f};
    float py_{8.0f};
    int facing_x_{1};
    int facing_y_{0};
    bool has_cross_{false};
    float fire_breath_timer_{0.0f};

    // The Devil at top (x=7..8, y=0..1)
    int devil_point_dir_{0}; // 1=Left, 2=Right, 3=Up, 4=Down
    float devil_timer_{2.5f};
    float maze_shift_x_{0.0f};
    float maze_shift_y_{0.0f};

    // Holy Cross position
    float cross_x_{8.0f};
    float cross_y_{12.0f};
    bool cross_spawned_{true};

    // Maze grid: 0=open, 1=wall, 2=pearl dot
    uint8_t maze_[MAZE_HEIGHT][MAZE_WIDTH];

    Monster monsters_[MAX_MONSTERS];

    void InitMaze();
    void UpdateDevil(float dt);
    void UpdateTamagon(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateMonsters(float dt);
    void CheckCollisions();
    void CheckWallCrush();
};

} // namespace arcade
