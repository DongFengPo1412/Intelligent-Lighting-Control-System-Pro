#pragma once

#include <cstdint>

namespace arcade {

// Game #152: 救难小鸟 (Flicky 1984 / Sega)
// 街机历史上首款雏鸟长龙护航救援与杂物投掷动作经典：
// 蓝鸟弗利基扑翼穿梭多层悬空跳台寻回走失雏鸟组建跟随长队、
// 投掷电话茶杯击退巡逻恶猫、护送全员归巢大门结算递增巨额连携得分。

class Game152Flicky {
public:
    static constexpr uint8_t GAME_ID = 152;
    static constexpr const char* NAME = "救难小鸟";
    static constexpr const char* ENGLISH_NAME = "Flicky";
    static constexpr uint16_t RELEASE_YEAR = 1984;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_FLICKY_DOWN = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int NUM_CHICKS = 6;
    static constexpr int NUM_CATS = 2;
    static constexpr int MAX_ITEMS = 2;
    static constexpr int TRAIL_HISTORY_LEN = 64;

    struct Chick {
        float x;
        float y;
        uint8_t state; // 0: idle, 1: following, 2: rescued
        int8_t order;
    };

    struct Cat {
        float x;
        float y;
        float vx;
        bool alive;
    };

    struct Item {
        float x;
        float y;
        float vx;
        bool active;
    };

    Game152Flicky();
    ~Game152Flicky() = default;

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
    float GetPlatformY(float x, float y) const;

    uint8_t state_;
    float state_timer_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t level_;

    float px_;
    float py_;
    float pvx_;
    float pvy_;
    int8_t facing_;
    bool is_grounded_;

    uint8_t rescued_count_;

    Chick chicks_[NUM_CHICKS];
    Cat cats_[NUM_CATS];
    Item throwables_[MAX_ITEMS];
    Item flying_items_[MAX_ITEMS];

    float trail_x_[TRAIL_HISTORY_LEN];
    float trail_y_[TRAIL_HISTORY_LEN];
    int trail_head_;
    int trail_count_;
};

} // namespace arcade
