// game_026_space_invaders.h —— 目标 #026 太空侵略者 (Space Invaders 1978)
// 机制: 外星阵列编队平移下压 + 阵亡提速 + 掩体阻挡损毁 + 垂直防空阻击
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

struct SpaceAlien {
    bool alive;
    uint8_t r, g, b;
    uint16_t score_val;
};

struct BunkerPixel {
    uint8_t hp;
};

struct SpaceBullet {
    bool active;
    float x;
    float y;
    float vy;
};

class Game026SpaceInvaders : public Cartridge {
public:
    Game026SpaceInvaders();
    ~Game026SpaceInvaders() override = default;

    uint8_t GetId() const override { return 26; }
    const char* GetName() const override { return "太空侵略者"; }
    const char* GetEnglishName() const override { return "Space Invaders 1978"; }
    uint16_t GetReleaseYear() const override { return 1978; }
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
    void ResetFleet();
    void FirePlayerBullet();
    void SpawnAlienBomb();

    CartridgeState state_;
    float player_x_;
    uint8_t lives_;
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
    float anim_timer_;

    static const int kFleetRows = 3;
    static const int kFleetCols = 4;
    SpaceAlien fleet_[kFleetRows][kFleetCols];
    int fleet_x_;
    int fleet_y_;
    int fleet_dir_;
    float fleet_step_timer_;
    float fleet_step_interval_;
    int remaining_aliens_;
    bool fleet_anim_frame_;

    static const int kMaxBullets = 4;
    SpaceBullet bullets_[kMaxBullets];

    BunkerPixel bunkers_[3][3];
};

} // namespace arcade
