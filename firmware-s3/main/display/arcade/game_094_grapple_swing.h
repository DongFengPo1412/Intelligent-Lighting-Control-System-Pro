// game_094_grapple_swing.h —— 目标 #094 钩爪摆荡 (Grapple Swing)
// 机制: 横向卷轴熔岩峡谷 + 天顶锚点钩爪锁定 + 真实圆弧单摆角动量摆荡与切向抛射
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

struct SwingAnchor {
    float x;
    float y;
    bool visited;
};

struct CanyonGem {
    float x;
    float y;
    bool collected;
};

struct CanyonLedge {
    float x1;
    float x2;
    float y;
};

class Game094GrappleSwing : public Cartridge {
public:
    Game094GrappleSwing();
    ~Game094GrappleSwing() override = default;

    uint8_t GetId() const override { return 94; }
    const char* GetName() const override { return "钩爪摆荡"; }
    const char* GetEnglishName() const override { return "Grapple Swing"; }
    uint16_t GetReleaseYear() const override { return 1983; }
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
    void AddScore(uint32_t pts);
    void SetupCourse();
    void RespawnPlayer();
    bool TryAttachAnchor(bool held);
    void DetachGrapple();
    void LoseLife();

    CartridgeState state_;
    uint32_t score_;
    uint32_t high_score_;
    uint8_t lives_;
    float px_;
    float py_;
    float vx_;
    float vy_;
    bool on_ground_;
    bool latched_;
    bool latched_by_hold_;
    int8_t latched_anchor_;
    float rope_len_;
    float theta_;
    float omega_;
    float grapple_buffer_;
    float checkpoint_x_;
    float checkpoint_y_;
    float state_timer_;
    float anim_timer_;

    static const int kNumAnchors = 8;
    SwingAnchor anchors_[kNumAnchors];

    static const int kNumGems = 7;
    CanyonGem gems_[kNumGems];

    static const int kNumLedges = 3;
    CanyonLedge ledges_[kNumLedges];
};

} // namespace arcade
