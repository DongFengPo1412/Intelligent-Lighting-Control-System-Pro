// game_088_atc_landing.h —— 目标 #088 机场降落引导 (Flight Control)
// 机制: 中央水平跑道(x=5..11, y=8)向东五边进近 + 多机航向引导 + 防相撞与燃油告警
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

enum AtcDir : uint8_t {
    ATC_DIR_RIGHT = 0, // EAST (+1, 0) - required final approach heading onto (5, 8)
    ATC_DIR_DOWN  = 1, // SOUTH (0, +1)
    ATC_DIR_LEFT  = 2, // WEST (-1, 0)
    ATC_DIR_UP    = 3, // NORTH (0, -1)
};

struct AtcPlane {
    bool active;
    float x;
    float y;
    uint8_t dir;
    float speed;
    float fuel;
    uint8_t color_id;
};

class Game088AtcLanding : public arcade::Cartridge {
public:
    Game088AtcLanding();
    ~Game088AtcLanding() override = default;

    uint8_t GetId() const override { return 88; }
    const char* GetName() const override { return "机场降落引导"; }
    const char* GetEnglishName() const override { return "Flight Control"; }
    uint16_t GetReleaseYear() const override { return 2009; }
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
    void SpawnPlane();
    void EnsureValidSelection();
    void SetSelectedHeading(uint8_t new_dir);
    void AddScore(uint32_t pts);

    static const int kMaxPlanes = 4;
    static const int kTargetLandings = 10;

    CartridgeState state_;
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
    float anim_timer_;
    int selected_plane_;
    uint8_t landed_count_;
    float spawn_timer_;
    float landing_flash_timer_;
    uint32_t rng_seed_;
    AtcPlane planes_[kMaxPlanes];
};

} // namespace arcade
