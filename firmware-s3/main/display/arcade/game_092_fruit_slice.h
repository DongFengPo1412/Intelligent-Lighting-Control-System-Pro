// game_092_fruit_slice.h —— 目标 #092 水果忍者 (Fruit Ninja)
// 机制: 抛物线上抛多彩水果与脉冲炸弹 + 十字键刀光游标与10像素直线斩击 + 多果连斩暴击
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

struct FruitItem {
    bool active;
    bool is_bomb;
    uint8_t kind;
    float x;
    float y;
    float vx;
    float vy;
};

struct JuiceDrop {
    bool active;
    float x;
    float y;
    float vx;
    float vy;
    float life;
    uint8_t r;
    uint8_t g;
    uint8_t b;
};

class Game092FruitSlice : public Cartridge {
public:
    Game092FruitSlice();
    ~Game092FruitSlice() override = default;

    uint8_t GetId() const override { return 92; }
    const char* GetName() const override { return "水果忍者"; }
    const char* GetEnglishName() const override { return "Fruit Ninja"; }
    uint16_t GetReleaseYear() const override { return 2010; }
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
    void SetupMatch();
    void SpawnWave();
    void SpawnJuice(float cx, float cy, uint8_t kind, bool explosion);
    void PerformSlash(uint16_t keys_down, uint16_t keys_pressed);

    CartridgeState state_;
    uint32_t score_;
    uint32_t high_score_;
    uint8_t lives_;
    uint16_t fruits_sliced_;
    uint32_t rng_seed_;
    float state_timer_;
    float anim_timer_;
    float spawn_timer_;
    float blade_x_;
    float blade_y_;
    float slash_timer_;
    float slash_x0_;
    float slash_y0_;
    float slash_x1_;
    float slash_y1_;
    uint8_t last_combo_;
    bool exploded_;

    static const int kMaxItems = 8;
    FruitItem items_[kMaxItems];

    static const int kMaxDrops = 24;
    JuiceDrop drops_[kMaxDrops];
};

} // namespace arcade
