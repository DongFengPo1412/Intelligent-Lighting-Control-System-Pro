#pragma once

#include <cstdint>
#include "esp_timer.h"

namespace arcade {

// Game #139: 阿米达格网 (Amidar 1981 / Konami & Stern)
// 街机历史上最经典的阿弥陀签梯子画线与区域封合格网涂色益智游戏：
// 沿纵横交错格线巡回描边、闭合矩形四周边界涂实填色、
// 按键B起跳腾空规避追击巡逻怪、全图九宫格点亮清屏通关。

class Game139Amidar {
public:
    static constexpr uint8_t GAME_ID = 139;
    static constexpr const char* NAME = "阿米达格网";
    static constexpr const char* ENGLISH_NAME = "Amidar";
    static constexpr uint16_t RELEASE_YEAR = 1981;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_CAUGHT = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int NUM_ENEMIES = 3;

    struct Enemy {
        float x;
        float y;
        float dir_x;
        float dir_y;
        float speed;
    };

    Game139Amidar();
    ~Game139Amidar() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetLevel() const { return level_; }

private:
    void InitLevel();
    bool IsOnGrid(float x, float y);
    void CheckBoxes();

    uint8_t state_;
    float state_timer_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t level_;

    float px_;
    float py_;
    uint8_t jumps_left_;
    float jump_timer_;

    bool traced_[16][16];
    bool boxes_[3][3];
    Enemy enemies_[NUM_ENEMIES];
};

} // namespace arcade

