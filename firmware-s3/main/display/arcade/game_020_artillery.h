// game_020_artillery.h —— 像素百战天虫 1980 (Artillery 1980)
// 编号: #020 | 机制: 仰角蓄力抛物线弹道 + 动态侧风抗风偏 + 可破坏弹坑地形 + 对阵炮战
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

struct ArtilleryShell {
    bool active;
    float x;
    float y;
    float vx;
    float vy;
    bool is_player; // true=玩家炮弹, false=AI炮弹
};

struct Tank {
    int x;
    int y;
    int hp;
    float angle_deg; // 仰角 10° ~ 80°
    float power;     // 蓄力 20% ~ 100%
};

class Game020Artillery : public Cartridge {
public:
    Game020Artillery();
    ~Game020Artillery() override = default;

    uint8_t GetId() const override { return 20; }
    const char* GetName() const override { return "像素百战天虫"; }
    const char* GetEnglishName() const override { return "Artillery 1980"; }
    uint16_t GetReleaseYear() const override { return 1980; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    void Init() override;
    void Reset() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

private:
    void GenerateTerrain();
    void FireShell(bool from_player);
    void Explode(float x, float y, bool from_player);
    void AIShoot();

    CartridgeState state_;
    uint8_t terrain_[16]; // 每个 X 坐标对应的地表高度 Y (0..15)

    Tank player_;
    Tank enemy_;
    ArtilleryShell shell_;

    float wind_;          // 当前侧风 (-2.5f ~ +2.5f)
    bool charging_power_; // 玩家当前是否正在按住 A 蓄力
    bool turn_player_;    // true: 玩家回合; false: AI回合
    float turn_timer_;

    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
};

} // namespace arcade
