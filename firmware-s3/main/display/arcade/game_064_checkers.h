// game_064_checkers.h —— 目标 #064 西洋跳棋 (Checkers, 1980)
// 机制: 8x8 棋盘斜向行棋 + 隔子连跳吃子 + 底线升王四向机动 + 战术启发式 AI
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

class Game064Checkers : public arcade::Cartridge {
public:
    Game064Checkers();
    ~Game064Checkers() override = default;

    uint8_t GetId() const override { return 64; }
    const char* GetName() const override { return "西洋跳棋"; }
    const char* GetEnglishName() const override { return "Checkers"; }
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
    static const uint8_t kPMan = 1;
    static const uint8_t kPKing = 2;
    static const uint8_t kAiMan = 3;
    static const uint8_t kAiKing = 4;

    void InitBoard();
    void AddScore(uint32_t pts);
    bool IsPlayerPiece(uint8_t p) const { return p == kPMan || p == kPKing; }
    bool IsAiPiece(uint8_t p) const { return p == kAiMan || p == kAiKing; }
    bool CanDirY(uint8_t p, int dy) const;
    bool IsValidMove(int sx, int sy, int tx, int ty, bool jump_only) const;
    bool HasMoveFrom(int sx, int sy, bool jump_only) const;
    bool SideHasAnyMove(bool for_player) const;
    int CountPieces(bool for_player) const;
    bool WouldBeCapturableAt(int tx, int ty, int from_x, int from_y) const;
    void EndPlayerTurn();
    void MakeAiTurn();

    CartridgeState state_;
    uint8_t board_[kBoardSize][kBoardSize];
    int cursor_x_;
    int cursor_y_;
    int selected_x_;
    int selected_y_;
    bool in_chain_jump_;
    bool player_turn_;
    float ai_timer_;
    int quiet_turns_;
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
    float anim_timer_;
};

} // namespace arcade
