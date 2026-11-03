#pragma once

#include <cstdint>

namespace arcade {

// Game #149: 逆转大蜜蜂 (Gaplus 1984 / Namco)
// 街机历史上首款玩家逆转反捕敌机编队充当僚机护航的太空射击传奇：
// 玩家战机拥有纵深区域全向机动、按键B反向投射牵引光束抓捕俘获敌机收编为僚机、
// 按键A统领全队进行超宽多联装扇形齐射、僚机充当防空装甲护盾阻挡致命弹幕。

class Game149Gaplus {
public:
    static constexpr uint8_t GAME_ID = 149;
    static constexpr const char* NAME = "逆转大蜜蜂";
    static constexpr const char* ENGLISH_NAME = "Gaplus";
    static constexpr uint16_t RELEASE_YEAR = 1984;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_PLAYER_HIT = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int MAX_ENEMIES = 8;
    static constexpr int MAX_LASERS = 10;
    static constexpr int MAX_ENEMY_BULLETS = 6;
    static constexpr int MAX_ESCORTS = 4;

    struct Enemy {
        float base_x;
        float base_y;
        float x;
        float y;
        uint8_t state; // 0: formation, 1: diving, 2: captured_suck
        float vx;
        float vy;
        float dive_t;
        bool alive;
    };

    struct Projectile {
        float x;
        float y;
        float vy;
        bool active;
    };

    Game149Gaplus();
    ~Game149Gaplus() = default;

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

    bool beam_active_;
    float beam_energy_;
    uint8_t escorts_count_;

    Enemy enemies_[MAX_ENEMIES];
    Projectile lasers_[MAX_LASERS];
    Projectile enemy_bullets_[MAX_ENEMY_BULLETS];
    float fleet_sway_;
};

} // namespace arcade
