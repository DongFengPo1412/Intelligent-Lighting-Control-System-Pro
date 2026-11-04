// game_062_reversi.h —— 目标 #062 黑白棋 (Reversi, 1980)
// 机制: 8x8 八向夹吃翻转棋盘 + 合法落点微光提示 + 无子自动让手 + 角位权重启发式 AI
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

class Game062Reversi : public arcade::Cartridge {
public:
    Game062Reversi();
    ~Game062Reversi() override = default;

    uint8_t GetId() const override { return 62; }
    const char* GetName() const override { return "黑白棋"; }
    const char* GetEnglishName() const override { return "Reversi"; }
    uint16_t GetReleaseYear() const override { return 1980; }
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
    static const int kBoardSize = 8;
    static const uint8_t kEmpty = 0;
    static const uint8_t kPlayer = 1;
    static const uint8_t kAi = 2;

    void InitBoard();
    void UpdateDiscCounts();
    void AddScore(uint32_t pts);
    int CountFlipsDir(int x, int y, uint8_t side, int dx, int dy) const;
    int TotalFlips(int x, int y, uint8_t side) const;
    bool IsValidMove(int x, int y, uint8_t side) const;
    bool HasValidMove(uint8_t side) const;
    int PlaceDisc(int x, int y, uint8_t side);
    void MakeAiMove();
    void ResolveNextTurn(uint8_t preferred_next);
    void FinishGame();

    CartridgeState state_;
    uint8_t board_[kBoardSize][kBoardSize];
    int cursor_x_;
    int cursor_y_;
    bool player_turn_;
    float ai_timer_;
    int player_count_;
    int ai_count_;
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
    float anim_timer_;
};

} // namespace arcade
