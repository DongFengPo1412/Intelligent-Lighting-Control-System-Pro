// game_026_whack_a_mole.h —— 像素打地鼠 1976 (Whack-A-Mole 1976)
// 编号: #026 | 机制: 3x3 地洞多态探头 + 黄金地鼠与红刺炸弹鉴别 + 瞬时定点挥锤击打 + 倒计时反应力测试
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

enum MoleType : uint8_t {
    MOLE_NORMAL = 0, // 普通地鼠 (+100分)
    MOLE_GOLDEN = 1, // 黄金地鼠 (+300分)
    MOLE_BOMB = 2,   // 刺球炸弹 (扣减生命/扣分)
};

struct MoleHole {
    int cx; // 洞穴中心 X
    int cy; // 洞穴中心 Y
    bool popped;
    MoleType type;
    float pop_timer;
    bool whacked;
};

class Game026WhackAMole : public Cartridge {
public:
    Game026WhackAMole();
    ~Game026WhackAMole() override = default;

    uint8_t GetId() const override { return 26; }
    const char* GetName() const override { return "像素打地鼠"; }
    const char* GetEnglishName() const override { return "Whack-A-Mole 1976"; }
    uint16_t GetReleaseYear() const override { return 1976; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    void Init() override;
    void Reset() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

private:
    void InitHoles();
    void SpawnMole();
    void StrikeHammer();

    CartridgeState state_;

    int cursor_row_; // 0, 1, 2
    int cursor_col_; // 0, 1, 2
    float hammer_anim_timer_;
    int lives_;
    float time_remaining_; // 关卡倒计时 (45s)

    static constexpr int TOTAL_HOLES = 9;
    MoleHole holes_[TOTAL_HOLES];
    float spawn_cooldown_;

    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
};

} // namespace arcade
