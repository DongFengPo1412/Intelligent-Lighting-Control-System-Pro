// game_027_magic_tower.h —— 经典魔塔 1996 (Magic Tower 1996)
// 编号: #027 | 机制: 零随机精密数值战斗 + 黄蓝钥匙门禁决策 + 攻防红蓝宝石强化 + 终极魔王讨伐
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

enum TowerTile : uint8_t {
    TOWER_FLOOR = 0,
    TOWER_WALL = 1,
    TOWER_DOOR_YELLOW = 2,
    TOWER_DOOR_BLUE = 3,
    TOWER_KEY_YELLOW = 4,
    TOWER_KEY_BLUE = 5,
    TOWER_GEM_RED = 6,        // +3 攻击力
    TOWER_GEM_BLUE = 7,       // +3 防御力
    TOWER_POTION_RED = 8,     // +200 生命
    TOWER_POTION_BLUE = 9,    // +500 生命
    TOWER_MONSTER_SLIME = 10,
    TOWER_MONSTER_SKELETON = 11,
    TOWER_MONSTER_MAGE = 12,
    TOWER_MONSTER_BOSS = 13,
    TOWER_STAIRS = 14,
};

struct MonsterStats {
    int hp;
    int atk;
    int def;
    int gold;
};

class Game027MagicTower : public Cartridge {
public:
    Game027MagicTower();
    ~Game027MagicTower() override = default;

    uint8_t GetId() const override { return 27; }
    const char* GetName() const override { return "经典魔塔"; }
    const char* GetEnglishName() const override { return "Magic Tower 1996"; }
    uint16_t GetReleaseYear() const override { return 1996; }
    ControlType GetControlType() const override { return CTRL_DPAD_4WAY; }

    void Init() override;
    void Reset() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

    MonsterStats GetMonsterStats(uint8_t tile_type) const;
    int CalculateDamage(uint8_t tile_type) const;

private:
    void InitLevel();
    bool Interact(int nx, int ny);

    CartridgeState state_;
    uint8_t grid_[16][16];

    int hero_x_;
    int hero_y_;
    int hero_hp_;
    int hero_atk_;
    int hero_def_;
    int yellow_keys_;
    int blue_keys_;

    float move_timer_;
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
};

} // namespace arcade
