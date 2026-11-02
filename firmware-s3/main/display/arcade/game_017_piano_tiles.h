// game_017_piano_tiles.h —— 别踩白块儿 2014 (Piano Tiles 2014)
// 编号: #017 | 机制: 四轨乐符离散下落 + 底线节拍判定打击 + 踩白即死 + 漏击判负
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

struct PianoNote {
    bool active;
    uint8_t track; // 0, 1, 2, 3
    float y;       // 顶部 Y (-4 ~ 18)
    float height;  // 3 像素高
    bool hit;      // 是否已被成功击碎
};

class Game017PianoTiles : public Cartridge {
public:
    Game017PianoTiles();
    ~Game017PianoTiles() override = default;

    uint8_t GetId() const override { return 17; }
    const char* GetName() const override { return "别踩白块儿"; }
    const char* GetEnglishName() const override { return "Piano Tiles 2014"; }
    uint16_t GetReleaseYear() const override { return 2014; }
    ControlType GetControlType() const override { return CTRL_MULTI_TRACK; }

    void Init() override;
    void Reset() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

private:
    void SpawnNextNote();
    void HandleTrackHit(uint8_t track);

    CartridgeState state_;
    static const int kMaxNotes = 6;
    PianoNote notes_[kMaxNotes];

    float fall_speed_;       // 当前音符下沉速度 (10.0 ~ 22.0 px/s)
    uint32_t combo_;
    uint32_t total_hits_;
    static const uint32_t kTargetHits = 40; // 40连击通关乐章
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
    float spawn_timer_;
    float hit_flash_timer_[4]; // 4轨击中闪光特效
};

} // namespace arcade
