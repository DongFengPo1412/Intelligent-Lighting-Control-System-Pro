#pragma once

#include <cstdint>

namespace arcade {

// Game #154: 魔法泡泡破裂者 (Pang / Buster Bros 1989 / Mitchell & Capcom)
// 街机历史上最受欢迎的铁锚射天与抛物线巨球二分分裂射击经典：
// 地面左右敏捷穿梭、按键A垂直发射上升铁锚抓钩搭接天花板形成刺绳切线、
// 触碰巨型弹跳球引发级联两极分裂、在微型弹球密集轰炸中缝隙求生全歼清屏。

class Game154Pang {
public:
    static constexpr uint8_t GAME_ID = 154;
    static constexpr const char* NAME = "魔法泡泡破裂者";
    static constexpr const char* ENGLISH_NAME = "Pang";
    static constexpr uint16_t RELEASE_YEAR = 1989;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_PLAYER_HIT = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr float FLOOR_Y = 13.5f;
    static constexpr float CEILING_Y = 1.0f;
    static constexpr int MAX_BALLS = 16;

    struct Ball {
        float x;
        float y;
        float vx;
        float vy;
        uint8_t size; // 3: huge, 2: medium, 1: small
        bool active;
    };

    Game154Pang();
    ~Game154Pang() = default;

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
    void LoseLife();

    uint8_t state_;
    float state_timer_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t level_;

    float px_;
    float py_;
    int8_t facing_;

    bool harpoon_active_;
    float harpoon_x_;
    float harpoon_tip_y_;
    bool harpoon_anchored_;
    float harpoon_anchor_timer_;

    Ball balls_[MAX_BALLS];
};

} // namespace arcade

