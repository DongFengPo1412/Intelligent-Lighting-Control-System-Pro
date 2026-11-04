// game_063_gomoku.h —— 目标 #063 五子棋 (Gomoku, 1985)
// 机制: 15x15 交叉点木纹棋盘 + 四轴五连珠判定 + 活四/冲四/活三攻防评估 AI
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

class Game063Gomoku : public arcade::Cartridge {
public:
    Game063Gomoku();
    ~Game063Gomoku() override = default;

    uint8_t GetId() const override { return 63; }
    const char* GetName() const override { return "五子棋"; }
    const char* GetEnglishName() const override { return "Gomoku"; }
    uint16_t GetReleaseYear() const override { return 1985; }
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
    static const int kGridSize = 15;
    static const uint8_t kEmpty = 0;
    static const uint8_t kPlayer = 1;
    static const uint8_t kAi = 2;

    void InitBoard();
    void AddScore(uint32_t pts);
    bool CheckWinAt(int x, int y, uint8_t side) const;
    int EvaluatePointForSide(int x, int y, uint8_t side) const;
    void MakeAiMove();

    CartridgeState state_;
    uint8_t board_[kGridSize][kGridSize];
    int cursor_x_;
    int cursor_y_;
    int last_x_;
    int last_y_;
    int moves_count_;
    bool player_turn_;
    float ai_timer_;
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
    float anim_timer_;
};

} // namespace arcade
