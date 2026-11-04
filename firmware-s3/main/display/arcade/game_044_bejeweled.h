// game_044_bejeweled.h —— 目标 #044 宝石迷阵 (Bejeweled)
// 机制: 6x6 宝石邻接交换 + 非三连自动回退 + 重力补位瀑布连锁与闪电计时
#pragma once

#include "arcade_cartridge.h"
#include <stdint.h>

namespace arcade {

class Game044Bejeweled : public Cartridge {
public:
    static const int kSize = 6;
    static const uint32_t kTargetScore = 500;

    Game044Bejeweled();
    ~Game044Bejeweled() override = default;

    uint8_t GetId() const override { return 44; }
    const char* GetName() const override { return "宝石迷阵"; }
    const char* GetEnglishName() const override { return "Bejeweled"; }
    uint16_t GetReleaseYear() const override { return 2001; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    void Init() override;
    void Reset() override;
    void Start() override;
    void Pause() override;
    void Resume() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

    bool TrySwap(int x1, int y1, int x2, int y2);
    bool HasValidMove();

private:
    uint32_t NextRand();
    uint8_t RandomGem();
    void GeneratePlayableBoard();
    int FindMatches(bool mark[kSize][kSize]) const;
    void ApplyGravityAndRefill();
    void AddScore(uint32_t pts);

    CartridgeState state_;
    uint8_t board_[kSize][kSize]; // 1..5 jewel colors
    int cx_;
    int cy_;
    int sel_x_;
    int sel_y_;
    int last_chain_;
    uint32_t seed_;
    uint32_t score_;
    uint32_t high_score_;
    float time_left_;
    float invalid_flash_;
    float state_timer_;
    float anim_timer_;
};

} // namespace arcade
