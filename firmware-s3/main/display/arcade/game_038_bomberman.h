// game_038_bomberman.h —— 目标 #038 炸弹人 (Bomberman 1983)
// 机制: 定时炸弹放置 + 十字烈焰冲击波 + 软砖碎裂与自身回避 + 巡逻怪爆破消灭
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

enum BomberTileType {
    TILE_EMPTY = 0,
    TILE_HARD_WALL = 1,
    TILE_SOFT_BRICK = 2,
    TILE_EXIT = 3
};

struct BomberBomb {
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

class Game038Bomberman : public Cartridge {
public:
    Game038Bomberman();
    ~Game038Bomberman() override = default;

    uint8_t GetId() const override { return 38; }
    const char* GetName() const override { return "炸弹人"; }
    const char* GetEnglishName() const override { return "Bomberman 1983"; }
    uint16_t GetReleaseYear() const override { return 1983; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    void Init() override;
    void Reset() override;
    void Start() override;
    void Pause() override;
    void Resume() override;
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
    float anim_timer_;

    uint8_t map_[16][16];

    BomberBomb bomb_;

    static const int kMaxFlames = 9;
    FlamePixel flames_[kMaxFlames];
    int flame_count_;

    static const int kNumEnemies = 3;
    BomberEnemy enemies_[kNumEnemies];
    int remaining_enemies_;
};

} // namespace arcade
