#pragma once

#include <cstdint>

namespace arcade {

// Game #168: 矿坑逃犯 (Bagman - 1982 / Valadon Automation & Stern)
// 街机历史上最具策略性盗宝运金与负重逃亡动作开山名作：
// 深入地下矿井背负沉重金袋减速运输、卸下重物攀爬梯子、
// 垂直丢金袋砸晕狱警、挥舞矿镐自卫防身、避让滚动机车将黄金归仓地表独轮车。

class Game168Bagman {
public:
    static constexpr uint8_t GAME_ID = 168;
    static constexpr const char* NAME = "矿坑逃犯";
    static constexpr const char* ENGLISH_NAME = "Bagman";
    static constexpr uint16_t RELEASE_YEAR = 1982;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_BAGMAN_CAUGHT = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int NUM_BAGS = 2;
    static constexpr int NUM_GUARDS = 2;

    struct GoldBag {
        float x;
        float y;
        bool delivered;
    };

    struct Guard {
        int8_t id;
        float x;
        float y;
        float vx;
        float stunned_timer;
    };

    Game168Bagman();
    ~Game168Bagman() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetMine() const { return mine_; }
    bool IsCarryingBag() const { return carrying_bag_idx_ != -1; }
    uint8_t GetBagsDelivered() const { return bags_delivered_; }

private:
    uint8_t state_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t mine_;
    float state_timer_;

    float px_;
    float py_;
    float speed_;
    int8_t carrying_bag_idx_;
    bool has_pickaxe_;
    float pickaxe_timer_;

    float wheelbarrow_x_;
    float wheelbarrow_y_;
    uint8_t bags_delivered_;

    GoldBag bags_[NUM_BAGS];
    Guard guards_[NUM_GUARDS];

    float cart_x_;
    float cart_vx_;

    float pickaxe_x_;
    float pickaxe_y_;
    bool pickaxe_active_;

    void InitMine();
    void GrabOrDropBag();
    bool IsPlatform(int x, int y) const;
    bool IsLadder(int x, int y) const;
};

} // namespace arcade

