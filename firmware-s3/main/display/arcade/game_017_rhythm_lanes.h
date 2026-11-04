// game_017_rhythm_lanes.h —— 目标 #017 四轨节奏 (Rhythm Lanes)
// 机制: 统一节拍时钟驱动四轨彩色音符下落 + y=13..14 判定线精准打击 (Perfect/Good/Combo)
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

struct RhythmNote {
    uint8_t lane;
    float y;
    bool active;
};

class Game017RhythmLanes : public Cartridge {
public:
    Game017RhythmLanes();
    ~Game017RhythmLanes() override = default;

    uint8_t GetId() const override { return 17; }
    const char* GetName() const override { return "四轨节奏"; }
    const char* GetEnglishName() const override { return "Rhythm Lanes"; }
    uint16_t GetReleaseYear() const override { return 2014; }
    ControlType GetControlType() const override { return CTRL_MULTI_TRACK; }

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
    void SpawnBeatNote();
    void HandleLanePress(uint8_t lane);
    bool AnyActiveNotes() const;

    static const int kMaxNotes = 10;
    static const int kTotalBeats = 64;
    static const int kMaxMisses = 5;

    CartridgeState state_;
    RhythmNote notes_[kMaxNotes];
    float beat_timer_;
    int beats_spawned_;
    int notes_cleared_;
    int combo_;
    int misses_;
    uint8_t last_lane_;
    float lane_flash_[4];
    uint8_t lane_grade_[4]; // 0=none, 1=good, 2=perfect
    float miss_flash_timer_;

    uint32_t score_;
    uint32_t high_score_;
    uint32_t rng_seed_;
    float state_timer_;
    float anim_timer_;
};

} // namespace arcade
