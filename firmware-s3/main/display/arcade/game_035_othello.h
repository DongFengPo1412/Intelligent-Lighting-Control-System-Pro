#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game035Othello : public Cartridge {
public:
    static constexpr uint8_t STATE_PLAYER_TURN = 0;
    static constexpr uint8_t STATE_AI_TURN = 1;
    static constexpr uint8_t STATE_GAMEOVER = 2;

    static constexpr int BOARD_SIZE = 8;

    enum Piece : uint8_t {
        PIECE_EMPTY = 0,
        PIECE_BLACK = 1, // 玩家
        PIECE_WHITE = 2, // AI
    };

    Game035Othello();
    ~Game035Othello() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "Othello (1980)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    int GetBlackCount() const { return black_count_; }
    int GetWhiteCount() const { return white_count_; }

    int GetCursorX() const { return cursor_x_; }
    int GetCursorY() const { return cursor_y_; }

    void SetCursor(int x, int y) { cursor_x_ = x; cursor_y_ = y; }
    bool IsValidMove(int x, int y, Piece color) const;
    bool PlaceMove(int x, int y, Piece color);
    bool HasAnyValidMove(Piece color) const;

private:
    void InitBoard();
    void UpdateCounts();
    int CountFlips(int x, int y, Piece color, int dx, int dy) const;
    void FlipDirection(int x, int y, Piece color, int dx, int dy);
    void MakeAIMove();

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;

    int cursor_x_;
    int cursor_y_;
    int black_count_;
    int white_count_;
    float ai_think_timer_;

    Piece board_[BOARD_SIZE][BOARD_SIZE];
};

} // namespace arcade
