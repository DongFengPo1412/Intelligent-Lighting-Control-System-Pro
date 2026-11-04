// game_076_mini_golf.h —— 目标 #076 迷你高尔夫 (Mini Golf, 1987)
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

enum GolfTile : uint8_t {
    GOLF_FAIRWAY = 0,
    GOLF_WALL = 1,
    GOLF_SAND = 2,
    GOLF_WATER = 3,
};

class Game076MiniGolf : public Cartridge {
public:
    Game076MiniGolf();
    ~Game076MiniGolf() override = default;

    uint8_t GetId() const override { return 76; }
    const char* GetName() const override { return "迷你高尔夫"; }
    const char* GetEnglishName() const override { return "Mini Golf"; }
    uint16_t GetReleaseYear() const override { return 1987; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    void Init() override;
    void Reset() override;
    void Start() override;
    void Pause() override;
    void Resume() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

private:
    static const int kTotalHoles = 4;
    static const int kMaxTotalStrokes = 18;

    void InitGameData();
    void LoadHole(int idx);
    void AddScore(uint32_t pts);
    bool IsWallAt(float px, float py) const;

    CartridgeState state_;
    uint8_t tiles_[16][16];
    int hole_index_;
    int hole_strokes_;
    int total_strokes_;
    float ball_x_;
    float ball_y_;
    float ball_vx_;
    float ball_vy_;
    float saved_x_;
    float saved_y_;
    float cup_x_;
    float cup_y_;
    bool ball_moving_;
    int aim_angle_;
    int power_level_;
    float splash_timer_;
    float sink_flash_timer_;
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
    float anim_timer_;
};

} // namespace arcade
