#pragma once

#include <cstdint>

namespace arcade {

// Game #178: 弹珠回旋环 (Puzz Loop - 1998 / Mitchell Corporation)
// 螺旋轨道滚珠链向心推进、中心旋转炮台定向弹射填缝、
// 三色消灭与磁吸回拉级联连锁。

class Game178PuzzLoop {
public:
    static constexpr uint8_t GAME_ID = 178;
    static constexpr const char* NAME = "弹珠回旋环";
    static constexpr const char* ENGLISH_NAME = "Puzz Loop";
    static constexpr uint16_t RELEASE_YEAR = 1998;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_DRAIN_LOST = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr uint8_t COLOR_RED = 1;
    static constexpr uint8_t COLOR_GREEN = 2;
    static constexpr uint8_t COLOR_BLUE = 3;
    static constexpr uint8_t COLOR_YELLOW = 4;

    static constexpr int TRACK_STEPS = 46;
    static constexpr int MAX_TRAIN = 32;

    struct Waypoint {
        float x;
        float y;
    };

    struct Bullet {
        bool active;
        float x;
        float y;
        float vx;
        float vy;
        uint8_t color;
    };

    Game178PuzzLoop();
    ~Game178PuzzLoop() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetStage() const { return stage_; }

    float GetAimAngle() const { return aim_angle_; }
    uint8_t GetCurColor() const { return cur_color_; }
    uint8_t GetNextColor() const { return next_color_; }
    uint8_t GetTrainLength() const { return train_len_; }

private:
    uint8_t state_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t stage_;
    float state_timer_;

    float aim_angle_;
    uint8_t cur_color_;
    uint8_t next_color_;

    Bullet bullet_;
    Waypoint track_[TRACK_STEPS];

    uint8_t train_[MAX_TRAIN];
    uint8_t train_len_;
    float train_progress_;
    float train_speed_;

    void InitStage();
    void GenerateTrack();
    void CheckMatch3(int idx);
};

} // namespace arcade

