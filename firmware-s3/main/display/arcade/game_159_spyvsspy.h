#pragma once

#include <cstdint>

namespace arcade {

// Game #159: 间谍大战 (Spy vs Spy 1984 / First Star & Sega Arcade)
// 街机与家用机历史上最负盛名的双雄谍战与机关陷阱暗算开山名作：
// 穿梭使馆多房间搜寻文件柜与壁画保密箱、集齐护照美钞钥匙机密文件与公文包、
// 在家具暗藏炸药弹簧陷阱阴击宿敌黑间谍、突破封锁赶赴机场大门登机撤离。

class Game159SpyVsSpy {
public:
    static constexpr uint8_t GAME_ID = 159;
    static constexpr const char* NAME = "间谍大战";
    static constexpr const char* ENGLISH_NAME = "Spy vs Spy";
    static constexpr uint16_t RELEASE_YEAR = 1984;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_SPY_BLOWN_UP = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int MAX_FURNITURE_PER_ROOM = 4;

    struct Furniture {
        float x;
        float y;
        uint8_t item_type; // 0: none, 1: briefcase, 2: plans, 3: passport, 4: money, 5: key
        bool has_bomb;
        bool searched;
    };

    Game159SpyVsSpy();
    ~Game159SpyVsSpy() = default;

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

    int8_t rx_;
    int8_t ry_;
    float px_;
    float py_;
    float facing_x_;
    float facing_y_;

    bool has_briefcase_;
    uint8_t items_mask_; // bits 0: plans, 1: passport, 2: money, 3: key

    Furniture furniture_[2][2][MAX_FURNITURE_PER_ROOM];
    int num_furniture_[2][2];

    int8_t rival_rx_;
    int8_t rival_ry_;
    float rival_x_;
    float rival_y_;
    bool rival_alive_;
    float rival_respawn_timer_;
};

} // namespace arcade

