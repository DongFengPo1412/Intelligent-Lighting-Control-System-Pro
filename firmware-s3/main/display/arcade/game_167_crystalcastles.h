#pragma once

#include <cstdint>

namespace arcade {

// Game #167: 水晶城堡 (Crystal Castles - 1983 / Atari & Franz Lanzinger)
// 街机历史上第一款2.5D等轴伪3D阶梯城堡冒险平台动作开山名作：
// 操控宾利熊攀爬多层立体城堡梯台拾取水晶宝石、飞跃跳跃踩踏碾碎食晶毛虫、
// 拾取魔法蜂蜜罐狂暴无敌放逐狂暴女巫伯希尔达、穿梭拱门暗道跨层瞬移。

class Game167CrystalCastles {
public:
    static constexpr uint8_t GAME_ID = 167;
    static constexpr const char* NAME = "水晶城堡";
    static constexpr const char* ENGLISH_NAME = "Crystal Castles";
    static constexpr uint16_t RELEASE_YEAR = 1983;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_BENTLEY_DIED = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int NUM_GEMS = 12;

    struct Gem {
        float x;
        float y;
        bool collected;
    };

    struct Creature {
        float x;
        float y;
        float vx;
        bool alive;
    };

    Game167CrystalCastles();
    ~Game167CrystalCastles() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetCastle() const { return castle_; }
    uint8_t GetGemsLeft() const;
    bool IsInvulnerable() const { return invulnerable_timer_ > 0.0f; }

private:
    uint8_t state_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t castle_;
    float state_timer_;

    float px_;
    float py_;
    float vx_;
    float vy_;
    float speed_;
    bool is_jumping_;
    float invulnerable_timer_;

    Gem gems_[NUM_GEMS];
    float honey_pot_x_;
    float honey_pot_y_;
    bool honey_pot_active_;

    Creature gem_eater_;
    Creature witch_;

    void InitCastle();
    bool IsPlatform(int x, int y) const;
    bool IsStairs(int x, int y) const;
};

} // namespace arcade
