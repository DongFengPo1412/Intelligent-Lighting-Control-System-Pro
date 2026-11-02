// game_028_danmaku.h —— 东方蜂群弹幕 1997 (Danmaku / Dodonpachi 1997)
// 编号: #028 | 机制: 极小1像素Hitbox判定点 + 几何旋转同心螺旋弹幕 + 擦弹(Graze)险中求分 + 保命全屏清弹
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

struct DanmakuBullet {
    bool active;
    float x;
    float y;
    float vx;
    float vy;
    bool is_player;
    bool grazed; // 是否已被擦过弹
};

struct DanmakuBoss {
    bool active;
    float x;
    float y;
    int hp;
    int max_hp;
    float pattern_timer;
    int pattern_phase; // 0: 螺旋弹, 1: 同心环散射, 2: 激光扫射
};

class Game028Danmaku : public Cartridge {
public:
    Game028Danmaku();
    ~Game028Danmaku() override = default;

    uint8_t GetId() const override { return 28; }
    const char* GetName() const override { return "蜂群极速弹幕"; }
    const char* GetEnglishName() const override { return "Danmaku 1997"; }
    uint16_t GetReleaseYear() const override { return 1997; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    void Init() override;
    void Reset() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

private:
    void InitBoss();
    void FirePlayerShot();
    void FireSpiralPattern(float angle_rad);
    void FireRingPattern(int count);
    void UseBomb();
    void UpdateBoss(float dt);
    void UpdateBullets(float dt);

    CartridgeState state_;

    float player_x_;
    float player_y_;
    int lives_;
    int bombs_;
    int graze_count_;
    float shoot_timer_;
    float bomb_flash_timer_;

    DanmakuBoss boss_;

    static constexpr int MAX_BULLETS = 32;
    DanmakuBullet bullets_[MAX_BULLETS];

    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
};

} // namespace arcade
