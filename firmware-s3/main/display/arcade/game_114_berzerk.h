#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game114Berzerk : public Cartridge {
public:
    Game114Berzerk();
    ~Game114Berzerk() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 114; }
    std::string GetName() const override { return "Berzerk (1980)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_EXPLORING = 0,
        STATE_PLAYER_DYING = 1,
        STATE_ROOM_TRANSITION = 2,
        STATE_GAME_OVER = 3
    };

    struct Robot {
        float x{0.0f};
        float y{0.0f};
        float shoot_timer{0.0f};
        bool active{false};
    };

    struct Laser {
        float x{0.0f};
        float y{0.0f};
        float vx{0.0f};
        float vy{0.0f};
        bool is_player{true};
        bool active{false};
    };

    struct EvilOtto {
        float x{0.0f};
        float y{0.0f};
        float bounce_timer{0.0f};
        bool active{false};
    };

    static constexpr int MAX_ROBOTS = 4;
    static constexpr int MAX_LASERS = 6;

    GameState GetState() const { return state_; }
    int GetScore() const { return score_; }
    int GetLives() const { return lives_; }
    int GetRoomsCleared() const { return rooms_cleared_; }
    float GetPlayerX() const { return px_; }
    float GetPlayerY() const { return py_; }
    int GetAimDirX() const { return aim_dx_; }
    int GetAimDirY() const { return aim_dy_; }

    const Robot& GetRobot(int i) const { return robots_[i]; }
    const EvilOtto& GetEvilOtto() const { return otto_; }

    void ForceSpawnOtto();

private:
    GameState state_{STATE_EXPLORING};
    float state_timer_{0.0f};
    int score_{0};
    int lives_{3};
    int rooms_cleared_{0};

    // Player Stickman
    float px_{8.0f};
    float py_{8.0f};
    int aim_dx_{1};
    int aim_dy_{0};

    // Electrified Maze Walls (16x16 grid: 1 = Electric Wall, 0 = Empty)
    uint8_t maze_[16][16];

    Robot robots_[MAX_ROBOTS];
    Laser lasers_[MAX_LASERS];
    EvilOtto otto_;
    float room_timer_{0.0f};

    void GenerateRoom();
    void FireLaser(float x, float y, float vx, float vy, bool is_player);
    void UpdatePlayer(float dt, uint32_t buttons);
    void UpdateRobots(float dt);
    void UpdateLasers(float dt);
    void UpdateEvilOtto(float dt);
    void CheckCollisions();
    bool IsWall(int x, int y) const;
};

} // namespace arcade