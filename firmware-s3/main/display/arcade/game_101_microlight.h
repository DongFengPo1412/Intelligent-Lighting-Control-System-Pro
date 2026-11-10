// game_101_microlight.h —— #101 微光纪元 (MicroLight)
// 原作与原型设计: 队友 / 《微光纪元：横版世界》 16x16 WS2812 模拟
// 移植与统一街机大厅整合: 未来道具研究所 · PixelArcade Core
#pragma once
#include "arcade_b3_helpers.h"

namespace arcade {

class Game101MicroLight : public BatchCartridge {
public:
    uint8_t GetId() const override { return 101; }
    const char* GetName() const override { return "微光纪元"; }
    const char* GetEnglishName() const override { return "MicroLight"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    void SetReplaySeed(uint32_t seed) {
        replay_seed_ = seed;
        replay_seeded_ = true;
    }
    void UseRandomSeeds() { replay_seeded_ = false; }

private:
    bool replay_seeded_ = false;
    uint32_t replay_seed_ = 0, last_seed_ = 0;

    // 玩家物理与状态
    float px_ = 0.0f;       // 世界 X 坐标
    float py_ = 6.0f;       // 世界 Y 坐标
    float vy_ = 0.0f;       // 垂直速度 (重力跳跃)
    bool grounded_ = false;
    int hp_ = 5;            // 当前生命值 (默认5格)
    int max_hp_ = 5;
    int aim_dx_ = 1;        // 瞄准方向
    int aim_dy_ = 0;
    int wood_ = 0;          // 采集木材
    int stone_ = 0;         // 采集石块
    int crystal_ = 0;       // 采集星晶
    uint8_t biomes_visited_ = 0; // 7个生态访问记录 (bit 0..6)
    float day_clock_ = 0.0f;// 昼夜时钟 (0..180s)
    float hurt_cd_ = 0.0f;  // 受伤硬直与无敌时间

    // 16x16 局部可视窗口地形
    uint8_t terrain_[16][16]{};

    void Setup() override;
    void Tick(float dt, uint16_t down, uint16_t pressed) override;
    void Draw(uint8_t* fb) override;
    int Progress() const override;

    uint8_t GetBiome(int world_x) const;
    void GenerateTerrainWindow(int center_x);
};

} // namespace arcade
