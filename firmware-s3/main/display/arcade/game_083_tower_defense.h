// game_083_tower_defense.h —— 目标 #083 路径塔防 (Path Tower Defense)
// 机制: S形蜿蜒道路 + 三系防御塔建造/升级(激光/冰霜减速/火炮溅射) + 四波敌军攻防
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

struct TDTower {
    bool active;
    int x;
    int y;
    uint8_t type;   // 0=Laser Cyan, 1=Frost Blue, 2=Cannon Orange
    uint8_t level;  // 1..3
    float cooldown;
    float beam_timer;
    float target_x;
    float target_y;
};

struct TDEnemy {
    bool alive;
    float x;
    float y;
    int wp_idx;
    float hp;
    float max_hp;
    float speed;
    float slow_timer;
    uint8_t reward;
    bool is_boss;
};

class Game083TowerDefense : public arcade::Cartridge {
public:
    Game083TowerDefense();
    ~Game083TowerDefense() override = default;

    uint8_t GetId() const override { return 83; }
    const char* GetName() const override { return "路径塔防"; }
    const char* GetEnglishName() const override { return "Path Tower Defense"; }
    uint16_t GetReleaseYear() const override { return 2007; }
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
    void SetupMatch(CartridgeState new_state);
    void StartWave(uint8_t w);
    void SpawnEnemy();
    void HandleBuildOrUpgrade();
    void AddScore(uint32_t pts);
    bool IsRoad(int x, int y) const;
    int FindTowerAt(int x, int y) const;

    static const int kMaxTowers = 16;
    static const int kMaxEnemies = 10;

    CartridgeState state_;
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
    float anim_timer_;
    int gold_;
    uint8_t base_hp_;
    uint8_t wave_;
    uint8_t spawned_in_wave_;
    uint8_t total_in_wave_;
    float spawn_timer_;
    float wave_delay_;
    int cursor_x_;
    int cursor_y_;
    uint8_t selected_tower_type_;
    float move_cooldown_;
    int num_towers_;
    TDTower towers_[kMaxTowers];
    TDEnemy enemies_[kMaxEnemies];
};

} // namespace arcade
