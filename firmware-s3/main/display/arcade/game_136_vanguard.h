#pragma once

#include <cstdint>
#include "esp_timer.h"

namespace arcade {

// Game #136: 宇宙巡航拦截者 (Vanguard 1981 / TOSE & SNK)
// 街机历史上第一部具备变向隧道卷轴、能量荚舱无敌冲撞与贡德巨眼BOSS的里程碑射击游戏：
// 山洞隧道变轨飞行、燃油能量条持续衰减补给、拾取能量荚舱启动彩虹无敌冲撞摧毁一切、
// 按键A前向主激光炮、按键B反向拦截炮、突破旋转护盾轰击贡德核心。

class Game136Vanguard {
public:
    static constexpr uint8_t GAME_ID = 136;
    static constexpr const char* NAME = "宇宙巡航拦截者";
    static constexpr const char* ENGLISH_NAME = "Vanguard";
    static constexpr uint16_t RELEASE_YEAR = 1981;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_SHIP_CRASH = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr uint8_t ZONE_MOUNTAIN = 0;
    static constexpr uint8_t ZONE_STRIPE = 1;
    static constexpr uint8_t ZONE_GOND = 2;

    static constexpr int MAX_BULLETS = 3;
    static constexpr int NUM_ENEMIES = 3;

    struct Bullet {
        float x;
        float y;
        float vx;
        float vy;
        bool active;
    };

    struct Enemy {
        float x;
        float y;
        float vx;
        float vy;
        bool alive;
    };

    struct EnergyPod {
        float x;
        float y;
        bool collected;
    };

    Game136Vanguard();
    ~Game136Vanguard() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint8_t GetZone() const { return zone_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetLevel() const { return level_; }
    float GetFuel() const { return fuel_; }

private:
    void InitLevel();
    void InitZoneMountain();
    void InitZoneStripe();
    void InitZoneGond();
    void CrashShip();

    uint8_t state_;
    float state_timer_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t level_;
    float fuel_;

    uint8_t zone_;
    float px_;
    float py_;
    float heading_x_;
    float heading_y_;
    float invulnerable_timer_;

    float top_walls_[16];
    float bot_walls_[16];

    Bullet bullets_[MAX_BULLETS];
    Enemy enemies_[NUM_ENEMIES];
    EnergyPod energy_pod_;
    bool has_energy_pod_;

    int8_t gond_hp_;
    float gond_shield_angle_;
};

} // namespace arcade

