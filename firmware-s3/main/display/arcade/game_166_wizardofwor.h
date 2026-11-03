#pragma once

#include <cstdint>

namespace arcade {

// Game #166: 沃之巫师 (Wizard of Wor - 1980 / Bally Midway & Dave Nutting)
// 街机历史上第一款语音合成地牢迷宫双人射击与雷达搜敌神作：
// 隐形恶魔（加沃、索沃）地牢潜行、底部雷达扫描仪定位坐标、
// 左右双向穿梭虫洞门瞬移逃生、消灭杂兵迎战瞬移闪电大巫师。

class Game166WizardOfWor {
public:
    static constexpr uint8_t GAME_ID = 166;
    static constexpr const char* NAME = "沃之巫师";
    static constexpr const char* ENGLISH_NAME = "Wizard of Wor";
    static constexpr uint16_t RELEASE_YEAR = 1980;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_DUNGEON_CLEAR = 1;
    static constexpr uint8_t STATE_WORRIOR_DIED = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int NUM_MONSTERS = 3;
    static constexpr int MAX_BULLETS = 2;

    struct Monster {
        int8_t id;
        uint8_t type; // 0: burwor, 1: garwor, 2: thorwor
        float x;
        float y;
        float vx;
        float vy;
        bool is_cloaked;
        bool alive;
    };

    struct Bullet {
        float x;
        float y;
        float vx;
        float vy;
        float life;
        bool active;
    };

    Game166WizardOfWor();
    ~Game166WizardOfWor() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetDungeon() const { return dungeon_; }
    bool IsWizardActive() const { return wizard_active_; }
    bool IsWizardAlive() const { return wizard_alive_; }

private:
    uint8_t state_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t dungeon_;
    float state_timer_;

    float px_;
    float py_;
    float facing_dx_;
    float facing_dy_;
    float speed_;
    float fire_cooldown_;

    Monster monsters_[NUM_MONSTERS];
    Bullet bullets_[MAX_BULLETS];

    bool wizard_active_;
    bool wizard_alive_;
    float wizard_x_;
    float wizard_y_;
    float wizard_teleport_timer_;
    uint8_t wizard_teleport_count_;

    void InitDungeon();
    void FireBeam();
    void SpawnWizard();
    bool IsWall(float x, float y) const;
    bool IsLineOfSight(float x, float y) const;
};

} // namespace arcade
