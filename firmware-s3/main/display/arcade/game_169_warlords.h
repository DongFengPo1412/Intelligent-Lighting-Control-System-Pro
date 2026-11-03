#pragma once

#include <cstdint>

namespace arcade {

// Game #169: 军阀混战 (Warlords - 1980 / Atari & Carla Meninsky)
// 街机历史上四方角斗混战与弑君破壁开山丰碑：
// 四隅城堡要塞守卫君主、弧形滑轨盾牌回旋拦截、
// 盾牌吸附蓄力投掷烈焰火球、逐层剥蚀城防石砖、暗算斩首敌方军阀夺取霸权。

class Game169Warlords {
public:
    static constexpr uint8_t GAME_ID = 169;
    static constexpr const char* NAME = "军阀混战";
    static constexpr const char* ENGLISH_NAME = "Warlords";
    static constexpr uint16_t RELEASE_YEAR = 1980;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_ROUND_CLEAR = 1;
    static constexpr uint8_t STATE_PLAYER_ELIMINATED = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int NUM_WARLORDS = 4;
    static constexpr int MAX_BRICKS_PER_CASTLE = 6;

    struct Warlord {
        int8_t id;
        float king_x;
        float king_y;
        float shield_t;
        bool alive;
    };

    struct Brick {
        int8_t x;
        int8_t y;
        bool active;
    };

    Game169Warlords();
    ~Game169Warlords() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetRound() const { return round_; }
    bool IsPlayerAlive() const { return warlords_[0].alive; }
    uint8_t GetAliveCpus() const;

private:
    uint8_t state_;
    uint32_t score_;
    uint8_t round_;
    float state_timer_;

    Warlord warlords_[NUM_WARLORDS];
    Brick bricks_[NUM_WARLORDS][MAX_BRICKS_PER_CASTLE];

    float ball_x_;
    float ball_y_;
    float ball_vx_;
    float ball_vy_;
    float ball_speed_;
    int8_t ball_caught_by_;
    float ball_catch_timer_;

    void InitRound();
    void GetShieldCoord(int wid, float t, float& out_x, float& out_y) const;
};

} // namespace arcade
