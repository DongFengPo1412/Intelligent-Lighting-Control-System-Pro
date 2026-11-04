// game_042_puyo_puyo.h —— 目标 #042 彩球连锁 (Puyo Puyo)
// 机制: 6x12 井道双联彩球下落旋转 + 悬空半截重力分离 + 4连通洪泛消除与阶梯连锁反应
#pragma once

#include "arcade_cartridge.h"
#include <stdint.h>

namespace arcade {

class Game042PuyoPuyo : public Cartridge {
public:
    static const int kCols = 6;
    static const int kRows = 12;

    Game042PuyoPuyo();
    ~Game042PuyoPuyo() override = default;

    uint8_t GetId() const override { return 42; }
    const char* GetName() const override { return "彩球连锁"; }
    const char* GetEnglishName() const override { return "Puyo Puyo"; }
    uint16_t GetReleaseYear() const override { return 1991; }
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
    uint8_t RandomColor();
    void GetSubOffset(int rot, int& ox, int& oy) const;
    bool IsCellFree(int c, int r) const;
    bool CanPlacePair(int c, int r, int rot) const;
    void SpawnPair();
    void RotatePair();
    void LockAndResolve();
    bool ApplyGravity();
    int PopConnectedGroups();
    void AddScore(uint32_t pts);

    CartridgeState state_;
    uint8_t grid_[kRows][kCols]; // 0: empty, 1..4: Red, Green, Blue, Yellow
    int cur_col_;
    int cur_row_;
    int cur_rot_; // 0: up, 1: right, 2: down, 3: left
    uint8_t main_color_;
    uint8_t sub_color_;
    uint8_t next_main_;
    uint8_t next_sub_;
    int last_chain_;
    int max_chain_;
    uint32_t seed_;
    uint32_t score_;
    uint32_t high_score_;
    float drop_timer_;
    float drop_interval_;
    float chain_flash_timer_;
    float state_timer_;
    float anim_timer_;
};

} // namespace arcade
