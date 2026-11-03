#pragma once

#include <cstdint>

namespace arcade {

// Game #162: 翻滚战机1942 (1942 - 1984 / Capcom & Yoshiki Okamoto)
// 街机历史上二战太平洋空战与纵向卷轴射击奠基丰碑：
// 驾驶P-38闪电战机空中翻滚大回旋无敌避弹、吃取POW合体双联僚机三路齐射、
// 迎战零式战机红色编队与决战亚达克超级重型轰炸机。

class Game162Roll1942 {
public:
    static constexpr uint8_t GAME_ID = 162;
    static constexpr const char* NAME = "翻滚战机1942";
    static constexpr const char* ENGLISH_NAME = "1942";
    static constexpr uint16_t RELEASE_YEAR = 1984;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_PLAYER_EXPLODING = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int MAX_PLAYER_BULLETS = 6;
    static constexpr int MAX_ENEMY_BULLETS = 4;
    static constexpr int MAX_ENEMIES = 6;
    static constexpr int MAX_POW = 2;

    struct Bullet {
        float x;
        float y;
        float vy;
        bool active;
    };

    struct Enemy {
        int8_t id;
        float x;
        float y;
        float vx;
        float vy;
        int8_t hp;
        bool is_red;
        bool is_boss;
        bool active;
    };

    struct PowItem {
        float x;
        float y;
        float vy;
        bool active;
    };

    Game162Roll1942();
    ~Game162Roll1942() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetStage() const { return stage_; }
    uint8_t GetLoopsLeft() const { return loops_left_; }
    bool IsLooping() const { return is_looping_; }
    bool HasWingmen() const { return has_wingmen_; }

private:
    uint8_t state_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t stage_;
    float state_timer_;

    float px_;
    float py_;
    float speed_;
    uint8_t loops_left_;
    bool is_looping_;
    float loop_timer_;
    bool has_wingmen_;
    float fire_cooldown_;

    Bullet player_bullets_[MAX_PLAYER_BULLETS];
    Bullet enemy_bullets_[MAX_ENEMY_BULLETS];
    Enemy enemies_[MAX_ENEMIES];
    PowItem pow_items_[MAX_POW];

    float enemy_spawn_timer_;
    uint8_t red_squadron_count_;
    uint8_t red_squadron_killed_;
    bool boss_active_;

    void RespawnPlayer();
    void TriggerLoop();
    void FireCannons();
    void SpawnRedFormation();
    void SpawnBoss();
};

} // namespace arcade
