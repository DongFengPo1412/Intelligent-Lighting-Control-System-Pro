// game_009_space_invaders.h —— 太空侵略者 1978 (Space Invaders 1978)
// 编号: #009 | 机制: 外星阵列编队平移下压 + 阵亡提速 + 掩体阻挡损毁 + 垂直防空阻击
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

struct Alien {
    bool alive;
    uint8_t r, g, b;
    uint16_t score_val;
};

struct BunkerPixel {
    uint8_t hp; // 0=损坏, 1=受损, 2=完好
};

struct Bullet {
    bool active;
    float x;
    float y;
    float vy; // 玩家子弹向上负值，敌机炸弹向下正值
};

class Game009SpaceInvaders : public Cartridge {
public:
    Game009SpaceInvaders();
    ~Game009SpaceInvaders() override = default;

    uint8_t GetId() const override { return 9; }
    const char* GetName() const override { return "太空侵略者"; }
    const char* GetEnglishName() const override { return "Space Invaders 1978"; }
    uint16_t GetReleaseYear() const override { return 1978; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    void Init() override;
    void Reset() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

private:
    void ResetFleet();
    void FirePlayerBullet();
    void SpawnAlienBomb();

    CartridgeState state_;
    float player_x_;        // 玩家中心 X (1.0 ~ 14.0)
    uint8_t lives_;         // 玩家生命 (初始 3)
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;

    // 侵略者阵列: 3 排 4 列
    static const int kFleetRows = 3;
    static const int kFleetCols = 4;
    Alien fleet_[kFleetRows][kFleetCols];
    int fleet_x_;           // 舰队左上角网格 X (0 ~ 9)
    int fleet_y_;           // 舰队左上角网格 Y (1 ~ 11)
    int fleet_dir_;         // +1 向右, -1 向左
    float march_timer_;
    float march_interval_;  // 移动间隔 (初始 0.6s，随存活数减少至 0.12s)
    int remaining_aliens_;

    // 玩家子弹 (单发)
    Bullet player_bullet_;

    // 敌机炸弹 (最多 2 枚同屏)
    static const int kMaxAlienBombs = 2;
    Bullet alien_bombs_[kMaxAlienBombs];
    float bomb_drop_timer_;

    // 掩体 (3座，每座2x2像素，位于 y=11..12)
    static const int kNumBunkers = 3;
    BunkerPixel bunkers_[kNumBunkers][2][2]; // [掩体号][行][列]
};

} // namespace arcade
