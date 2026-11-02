// game_013_bomberman.h —— 像素炸弹人 1983 (Bomberman 1983)
// 编号: #013 | 机制: 定时炸弹放置 + 十字烈焰冲击波 + 软砖碎裂与自身回避 + 巡逻怪爆破消灭
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

enum TileType {
    TILE_EMPTY = 0,
    TILE_HARD_WALL = 1,
    TILE_SOFT_BRICK = 2,
    TILE_EXIT = 3
};

struct Bomb {
    bool active;
    int gx;
    int gy;
    float timer;
    int range;
};

struct FlamePixel {
    int x;
    int y;
    float timer;
};

struct BomberEnemy {
    bool alive;
    float x;
    float y;
    int dir_x;
    int dir_y;
    float speed;
};

class Game013Bomberman : public Cartridge {
public:
    Game013Bomberman();
    ~Game013Bomberman() override = default;

    uint8_t GetId() const override { return 13; }
    const char* GetName() const override { return "像素炸弹人"; }
    const char* GetEnglishName() const override { return "Bomberman 1983"; }
    uint16_t GetReleaseYear() const override { return 1983; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    void Init() override;
    void Reset() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

private:
    void ResetPlayer();
    void ExplodeBomb();
    void MoveEnemy(BomberEnemy& e, float dt);
    bool IsWalkable(int gx, int gy, bool allow_bomb) const;

    CartridgeState state_;
    float player_x_;
    float player_y_;
    uint8_t lives_;
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;

    // 16x16 迷宫地图
    uint8_t map_[16][16];

    // 炸弹系统 (单发)
    Bomb bomb_;
    int flame_range_;

    // 爆炸烈焰残留 (最多 16 格，持续 0.4s)
    static const int kMaxFlames = 16;
    FlamePixel flames_[kMaxFlames];
    int num_flames_;

    // 巡逻敌怪 (2只)
    static const int kNumEnemies = 2;
    BomberEnemy enemies_[kNumEnemies];
    int remaining_enemies_;
};

} // namespace arcade
