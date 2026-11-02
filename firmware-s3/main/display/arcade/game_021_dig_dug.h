// game_021_dig_dug.h —— 掘地打气人 1982 (Dig Dug 1982)
// 编号: #021 | 机制: 地底自由隧道挖掘 + 鱼叉充气引爆 + 巨石塌陷碾压 + 喷火伏击
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

enum DigTile : uint8_t {
    TILE_EMPTY = 0,
    TILE_DIRT = 1,
    TILE_ROCK = 2,
};

enum EnemyType : uint8_t {
    ENEMY_POOKA = 0, // 红色波卡 (可幽灵穿墙)
    ENEMY_FYGAR = 1, // 绿色飞加 (喷吐烈焰)
};

struct DigEnemy {
    bool active;
    EnemyType type;
    float x;
    float y;
    int dir;          // 0:UP, 1:RIGHT, 2:DOWN, 3:LEFT
    int inflate_stage; // 0=正常, 1=膨胀1级, 2=膨胀2级, 3=引爆破裂
    float inflate_timer;
    float move_timer;
    bool is_ghost;
    float fire_timer; // Fygar 喷火预警与持续时间
    bool firing;
};

struct DigRock {
    bool active;
    int x;
    int y;
    bool falling;
    float shake_timer;
};

struct Harpoon {
    bool active;
    int origin_x;
    int origin_y;
    int dir;
    int target_enemy_idx; // -1 表示未命中
    float timer;
};

class Game021DigDug : public Cartridge {
public:
    Game021DigDug();
    ~Game021DigDug() override = default;

    uint8_t GetId() const override { return 21; }
    const char* GetName() const override { return "掘地打气人"; }
    const char* GetEnglishName() const override { return "Dig Dug 1982"; }
    uint16_t GetReleaseYear() const override { return 1982; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    void Init() override;
    void Reset() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

private:
    void InitLevel();
    void PumpTarget();
    void UpdateRocks(float dt);
    void UpdateEnemies(float dt);

    CartridgeState state_;
    uint8_t grid_[16][16]; // TILE_EMPTY, TILE_DIRT, TILE_ROCK

    int player_x_;
    int player_y_;
    int player_dir_; // 0:UP, 1:RIGHT, 2:DOWN, 3:LEFT
    int player_lives_;
    float move_timer_;

    Harpoon harpoon_;
    static constexpr int MAX_ENEMIES = 4;
    DigEnemy enemies_[MAX_ENEMIES];

    static constexpr int MAX_ROCKS = 2;
    DigRock rocks_[MAX_ROCKS];

    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
};

} // namespace arcade
