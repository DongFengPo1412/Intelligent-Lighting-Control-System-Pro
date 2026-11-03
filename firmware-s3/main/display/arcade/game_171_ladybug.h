#pragma once

#include <cstdint>

namespace arcade {

// Game #171: 瓢虫大冒险 (Lady Bug - 1981 / Universal)
// 街机历史上第一款90度旋转门拓扑改变与骷髅毒药诱敌神作：
// 穿梭迷宫推动十字旋转门改变通道结构封闭追击敌虫、
// 诱使掠食天牛触碰骷髅毒药自爆消亡、拾取红心翻倍倍率并全域采蜜清盘。

class Game171LadyBug {
public:
    static constexpr uint8_t GAME_ID = 171;
    static constexpr const char* NAME = "瓢虫大冒险";
    static constexpr const char* ENGLISH_NAME = "Lady Bug";
    static constexpr uint16_t RELEASE_YEAR = 1981;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_LADYBUG_DIED = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int NUM_TURNSTILES = 6;
    static constexpr int NUM_BEETLES = 2;

    struct Turnstile {
        int8_t x;
        int8_t y;
        uint8_t ori; // 0: 'H', 1: 'V'
    };

    struct Beetle {
        int8_t id;
        float x;
        float y;
        float speed;
        bool alive;
    };

    Game171LadyBug();
    ~Game171LadyBug() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetStage() const { return stage_; }
    uint8_t GetMultiplier() const { return multiplier_; }
    uint16_t GetDotsLeft() const { return dots_left_; }

private:
    uint8_t state_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t stage_;
    uint8_t multiplier_;
    float state_timer_;

    float px_;
    float py_;
    float speed_;

    uint8_t dots_mask_[32]; // 256 bits for dots
    uint16_t dots_left_;

    Turnstile turnstiles_[NUM_TURNSTILES];
    Beetle beetles_[NUM_BEETLES];

    void InitStage();
    bool IsDot(int x, int y) const;
    void RemoveDot(int x, int y);
    bool IsSkull(int x, int y) const;
    bool IsHeart(int x, int y) const;
    bool IsTurnstile(int x, int y) const;
};

} // namespace arcade
