// game_029_centipede.h —— 目标 #029 百足蜈蚣 (Centipede, 1980)
// 机制: 多节蜈蚣蜿蜒触壁/触菇下移折返 + 击中中间节变蘑菇并分裂为两条独立蜈蚣链
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

struct CentipedeSeg029 {
    bool active;
    bool is_head;
    int8_t ahead;   // 前方相邻节索引, -1 表示本节为独立链头
    int8_t x;
    int8_t y;
    int8_t dir_x;
    int8_t dir_y;
};

struct BugBolt029 {
    bool active;
    float x;
    float y;
};

class Game029Centipede : public Cartridge {
public:
    static const int kMaxSegments = 8;
    static const int kMaxBullets = 3;

    Game029Centipede();
    ~Game029Centipede() override = default;

    uint8_t GetId() const override { return 29; }
    const char* GetName() const override { return "百足蜈蚣"; }
    const char* GetEnglishName() const override { return "Centipede"; }
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
    uint32_t NextRand();
    void AddScore(uint32_t pts);
    void SetupNewGame(CartridgeState new_state);
    void InitMushrooms();
    void SpawnCentipedeWave();
    void StepCentipede();
    void HitSegment(int idx);
    void FireBolt();
    int CountActiveSegments() const;

    CartridgeState state_;
    uint32_t score_;
    uint32_t high_score_;
    uint8_t lives_;
    uint8_t wave_;

    float player_x_;
    float player_y_;
    float fire_cooldown_;
    float invuln_timer_;
    float step_timer_;
    float step_interval_;

    uint8_t mushrooms_[16][16]; // 0=空, 1..2=蘑菇生命值
    CentipedeSeg029 segments_[kMaxSegments];
    BugBolt029 bullets_[kMaxBullets];

    float state_timer_;
    float anim_timer_;
    uint32_t seed_;
};

} // namespace arcade
