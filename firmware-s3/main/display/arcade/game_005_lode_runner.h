// game_005_lode_runner.h —— 目标 #005 挖洞夺金 (Lode Runner)
// 机制: 平台攀梯 + 左右掘砖坑诱捕守卫 + 砖块定时再生 + 夺金开启逃生梯
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

struct LodeGold {
    int x;
    int y;
    bool collected;
};

struct LodeHole {
    int x;
    int y;
    float timer;
    bool active;
};

struct LodeGuard {
    int x;
    int y;
    int spawn_x;
    int spawn_y;
    float move_timer;
    float trap_timer;
    bool trapped;
    bool active;
};

class Game005LodeRunner : public Cartridge {
public:
    Game005LodeRunner();
    ~Game005LodeRunner() override = default;

    uint8_t GetId() const override { return 5; }
    const char* GetName() const override { return "挖洞夺金"; }
    const char* GetEnglishName() const override { return "Lode Runner"; }
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
    void LoadLevel(int level_idx);
    void RespawnActors();
    void AddScore(uint32_t pts);
    bool CanWalk(int x, int y) const;
    bool CanFall(int x, int y) const;
    bool TryDigAt(int hx, int hy);
    void DigSide(int preferred_dx);
    void UpdateHoles(float dt);
    void UpdateGuards(float dt);

    static const int kNumLevels = 2;
    static const int kMaxGold = 3;
    static const int kMaxHoles = 6;
    static const int kMaxGuards = 2;

    CartridgeState state_;
    int level_idx_;
    uint8_t lives_;
    int player_x_;
    int player_y_;
    int player_dir_;
    float move_cooldown_;
    float fall_timer_;
    bool escape_revealed_;
    int escape_x_;
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
    float anim_timer_;
    uint8_t grid_[16][16];
    LodeGold golds_[kMaxGold];
    LodeHole holes_[kMaxHoles];
    LodeGuard guards_[kMaxGuards];
};

} // namespace arcade
