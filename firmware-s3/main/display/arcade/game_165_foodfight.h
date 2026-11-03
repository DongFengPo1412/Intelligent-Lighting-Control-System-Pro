#pragma once

#include <cstdint>

namespace arcade {

// Game #165: 食物大战 (Food Fight - 1983 / Atari & General Computer Corporation)
// 街机历史上最著名恶搞食物大战与冰淇淋甜筒融化竞速名作：
// 操控查理·查克抢在甜筒融化前横穿厨房、抓取地面散落馅饼西红柿飞掷击晕追击大厨、
// 规避大厨抛投飞馅饼与致命下水井盖陷阱。

class Game165FoodFight {
public:
    static constexpr uint8_t GAME_ID = 165;
    static constexpr const char* NAME = "食物大战";
    static constexpr const char* ENGLISH_NAME = "Food Fight";
    static constexpr uint16_t RELEASE_YEAR = 1983;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_CHARLEY_SPLAT = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int NUM_FOOD_PILES = 4;
    static constexpr int NUM_CHEFS = 3;
    static constexpr int MAX_PROJECTILES = 6;

    struct FoodPile {
        float x;
        float y;
        uint8_t remaining;
    };

    struct Chef {
        int8_t id;
        float x;
        float y;
        float speed;
        float stunned_timer;
        float throw_timer;
    };

    struct Projectile {
        float x;
        float y;
        float vx;
        float vy;
        bool is_player;
        bool active;
    };

    Game165FoodFight();
    ~Game165FoodFight() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetLevel() const { return level_; }
    uint8_t GetFoodAmmo() const { return food_ammo_; }
    float GetMeltTimer() const { return melt_timer_; }

private:
    uint8_t state_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t level_;
    float state_timer_;

    float px_;
    float py_;
    float facing_dx_;
    float facing_dy_;
    float speed_;
    uint8_t food_ammo_;
    float fire_cooldown_;

    float cone_x_;
    float cone_y_;
    float melt_timer_;

    FoodPile food_piles_[NUM_FOOD_PILES];
    Chef chefs_[NUM_CHEFS];
    Projectile projectiles_[MAX_PROJECTILES];

    void InitLevel();
    void ThrowFood();
};

} // namespace arcade
