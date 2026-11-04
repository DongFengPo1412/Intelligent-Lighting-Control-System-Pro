// game_028_missile_command.h —— 目标 #028 导弹指挥官 (Missile Command, 1980)
// 机制: 底部4座城市保卫战 + 准星瞄准发射拦截弹 + 圆形冲击波AoE扩散/收缩摧毁来袭弹道导弹
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

struct EnemyBallistic028 {
    bool active;
    float start_x;
    float x;
    float y;
    float vx;
    float vy;
    float target_x;
};

struct CounterMissile028 {
    bool active;
    float x;
    float y;
    float vx;
    float vy;
    float target_x;
    float target_y;
};

struct ShockwaveBlast028 {
    bool active;
    bool expanding;
    float x;
    float y;
    float radius;
    float max_radius;
};

class Game028MissileCommand : public Cartridge {
public:
    static const int kNumCities = 4;

    Game028MissileCommand();
    ~Game028MissileCommand() override = default;

    uint8_t GetId() const override { return 28; }
    const char* GetName() const override { return "导弹指挥官"; }
    const char* GetEnglishName() const override { return "Missile Command"; }
    uint16_t GetReleaseYear() const override { return 1980; }
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
    static const int kMaxEnemyMissiles = 8;
    static const int kMaxCounterMissiles = 4;
    static const int kMaxBlasts = 6;

    uint32_t NextRand();
    void AddScore(uint32_t pts);
    void SetupNewGame(CartridgeState new_state);
    void InitWave();
    uint8_t CountCities() const;
    void SpawnEnemyMissile();
    bool FireCounterMissile();

    CartridgeState state_;
    uint32_t score_;
    uint32_t high_score_;
    uint8_t wave_;
    uint8_t ammo_;
    uint8_t spawn_remaining_;

    float cross_x_;
    float cross_y_;
    float fire_cooldown_;
    float spawn_timer_;

    bool city_alive_[kNumCities];
    EnemyBallistic028 enemies_[kMaxEnemyMissiles];
    CounterMissile028 counters_[kMaxCounterMissiles];
    ShockwaveBlast028 blasts_[kMaxBlasts];

    float state_timer_;
    float anim_timer_;
    uint32_t seed_;
};

} // namespace arcade
