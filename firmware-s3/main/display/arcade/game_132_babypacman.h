#pragma once

#include <cstdint>
#include "esp_timer.h"

namespace arcade {

// Game #132: 幼年吃豆人弹珠台 (Baby Pac-Man 1982 / Bally Midway)
// 街机历史上绝无仅有的视频迷宫与实体弹珠台混合机台鼻祖：
// 无大力丸无助吃豆迷宫、底部通道穿梭降落弹珠台、击打挡板与目标槽解锁大力丸、返航吞噬幽灵。

class Game132BabyPacman {
public:
    static constexpr uint8_t GAME_ID = 132;
    static constexpr const char* NAME = "幼年吃豆人弹珠台";
    static constexpr const char* ENGLISH_NAME = "Baby Pac-Man";
    static constexpr uint16_t RELEASE_YEAR = 1982;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t MODE_MAZE = 0;
    static constexpr uint8_t MODE_PINBALL = 1;

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_DEATH = 1;
    static constexpr uint8_t STATE_MAZE_CLEAR = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int NUM_GHOSTS = 3;
    static constexpr int NUM_TARGETS = 3;

    struct Ghost {
        float x;
        float y;
        int dir_x;
        int dir_y;
        bool frightened;
        bool alive;
    };

    struct PinballBall {
        float x;
        float y;
        float vx;
        float vy;
        bool in_play;
    };

    Game132BabyPacman();
    ~Game132BabyPacman() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetMode() const { return mode_; }
    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetEnergizersEarned() const { return energizers_earned_; }
    int GetRemainingDots() const { return remaining_dots_; }

private:
    void InitMaze();
    void StartPinball();
    void ReturnToMaze();
    void UpdateMaze(float dt, uint16_t buttons);
    void UpdatePinball(float dt, uint16_t buttons);
    void CheckMazeCollisions();

    uint8_t mode_; // 0: Maze, 1: Pinball
    uint8_t state_;
    float state_timer_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t level_;

    // Maze state
    float px_;
    float py_;
    int p_dir_x_;
    int p_dir_y_;
    int next_dir_x_;
    int next_dir_y_;
    bool dots_[16][16];
    bool energizer_active_[2]; // Unlocked top-left and top-right power pellets
    int remaining_dots_;
    float frightened_timer_;

    // Ghosts
    Ghost ghosts_[NUM_GHOSTS];

    // Pinball table state
    PinballBall ball_;
    bool pinball_targets_[NUM_TARGETS]; // Hit targets to unlock energizers
    uint8_t energizers_earned_;
    float left_flipper_angle_;
    float right_flipper_angle_;
};

} // namespace arcade
