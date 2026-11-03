#pragma once

#include <cstdint>

namespace arcade {

// Game #157: 酒吧侍应生 (Tapper / Root Beer Tapper 1983 / Bally Midway)
// 街机历史上最经典的吧台管理与滑杯斟酒接空杯名作：
// 上下穿梭四排平行吧台拉动酒阀滑行推酒款待蜂拥而至的酒客、
// 疾速反向接住酒客饮毕滑回的空酒杯防摔碎、拾取台面小费维持酒吧运转清场。

class Game157Tapper {
public:
    static constexpr uint8_t GAME_ID = 157;
    static constexpr const char* NAME = "酒吧侍应生";
    static constexpr const char* ENGLISH_NAME = "Tapper";
    static constexpr uint16_t RELEASE_YEAR = 1983;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_MUG_SHATTERED = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr float BAR_LEFT = 2.0f;
    static constexpr float BAR_RIGHT = 13.5f;
    static constexpr int NUM_BARS = 4;

    static constexpr int MAX_MUGS = 8;
    static constexpr int MAX_PATRONS = 8;
    static constexpr int MAX_TIPS = 4;

    struct Mug {
        uint8_t bar;
        float x;
        float vx;
        bool empty;
        bool active;
    };

    struct Patron {
        uint8_t bar;
        float x;
        float speed;
        bool drinking;
        bool active;
    };

    struct Tip {
        uint8_t bar;
        float x;
        bool active;
    };

    Game157Tapper();
    ~Game157Tapper() = default;

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

    uint8_t bar_idx_;
    float bx_;

    Mug mugs_[MAX_MUGS];
    Patron patrons_[MAX_PATRONS];
    Tip tips_[MAX_TIPS];

    uint8_t total_patrons_spawned_;
    uint8_t total_patrons_required_;
    float spawn_timer_;
};

} // namespace arcade

