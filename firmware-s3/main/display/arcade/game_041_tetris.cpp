// game_041_tetris.cpp —— 俄罗斯方块 (Tetris)
#include "game_041_tetris.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>
#include <stdlib.h>

namespace arcade {

// 标准 7 种俄罗斯方块的 4 种旋转姿态定义 (7, 4, 4, 2)
static const int8_t kTetrisShapes[7][4][4][2] = {
    // 0: O 型 (方块)
    {{{0,0},{1,0},{0,1},{1,1}}, {{0,0},{1,0},{0,1},{1,1}}, {{0,0},{1,0},{0,1},{1,1}}, {{0,0},{1,0},{0,1},{1,1}}},
    // 1: I 型 (长条)
    {{{0,1},{1,1},{2,1},{3,1}}, {{2,0},{2,1},{2,2},{2,3}}, {{0,2},{1,2},{2,2},{3,2}}, {{1,0},{1,1},{1,2},{1,3}}},
    // 2: T 型
    {{{1,0},{0,1},{1,1},{2,1}}, {{1,0},{1,1},{2,1},{1,2}}, {{0,1},{1,1},{2,1},{1,2}}, {{1,0},{0,1},{1,1},{1,2}}},
    // 3: L 型
    {{{0,1},{1,1},{2,1},{2,0}}, {{1,0},{1,1},{1,2},{2,2}}, {{0,2},{0,1},{1,1},{2,1}}, {{0,0},{1,0},{1,1},{1,2}}},
    // 4: J 型
    {{{0,0},{0,1},{1,1},{2,1}}, {{1,2},{1,1},{1,0},{2,0}}, {{0,1},{1,1},{2,1},{2,2}}, {{0,2},{1,2},{1,1},{1,0}}},
    // 5: S 型
    {{{1,0},{2,0},{0,1},{1,1}}, {{1,0},{1,1},{2,1},{2,2}}, {{1,1},{2,1},{0,2},{1,2}}, {{0,0},{0,1},{1,1},{1,2}}},
    // 6: Z 型
    {{{0,0},{1,0},{1,1},{2,1}}, {{2,0},{2,1},{1,1},{1,2}}, {{0,1},{1,1},{1,2},{2,2}}, {{1,0},{1,1},{0,1},{0,2}}}
};

// 7 种方块的经典配色 (RGB)
static const uint8_t kPieceColors[7][3] = {
    {240, 220, 0},   // 0: O 黄色
    {0, 240, 240},   // 1: I 青色
    {170, 0, 240},   // 2: T 紫色
    {240, 140, 0},   // 3: L 橙色
    {0, 70, 240},    // 4: J 蓝色
    {0, 240, 0},     // 5: S 绿色
    {240, 0, 0}      // 6: Z 红色
};

Game041Tetris::Game041Tetris()
    : drop_timer_(0.0f),
      drop_interval_(0.60f),
      anim_timer_(0.0f),
      score_(0),
      high_score_(0),
      lines_cleared_(0),
      state_(STATE_TITLE)
{
}

void Game041Tetris::Init()
{
    Reset();
}

void Game041Tetris::Reset()
{
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    memset(field_, 0, sizeof(field_));
    score_ = 0;
    lines_cleared_ = 0;
    drop_interval_ = 0.60f;
    drop_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    state_ = STATE_TITLE; // 初始待命，通过 Start() 或按 A/START 激活
    SpawnPiece();
}

void Game041Tetris::Start()
{
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER) {
        Reset();
        state_ = STATE_PLAYING;
    } else if (state_ == STATE_PAUSED) {
        Resume();
    }
}

void Game041Tetris::Pause()
{
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game041Tetris::Resume()
{
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

bool Game041Tetris::CheckCollision(int type, int rot, int x, int y)
{
    for (int i = 0; i < 4; i++) {
        int px = x + kTetrisShapes[type][rot][i][0];
        int py = y + kTetrisShapes[type][rot][i][1];
        if (px < kBoardLeft || px > kBoardRight || py >= 16) {
            return true;
        }
        if (py >= 0 && field_[py][px] != 0) {
            return true;
        }
    }
    return false;
}

void Game041Tetris::SpawnPiece()
{
    piece_type_ = rand() % 7;
    piece_rot_ = 0;
    piece_x_ = kBoardLeft + 3;
    piece_y_ = 0;

    if (CheckCollision(piece_type_, piece_rot_, piece_x_, piece_y_)) {
        state_ = STATE_GAMEOVER;
        if (score_ > high_score_) { high_score_ = score_; ArcadeScoreStore::SaveHighScore(GetId(), high_score_); }
    }
}

void Game041Tetris::LockPiece()
{
    for (int i = 0; i < 4; i++) {
        int px = piece_x_ + kTetrisShapes[piece_type_][piece_rot_][i][0];
        int py = piece_y_ + kTetrisShapes[piece_type_][piece_rot_][i][1];
        if (py >= 0 && py < 16 && px >= 0 && px < 16) {
            field_[py][px] = (uint8_t)(piece_type_ + 1);
        }
    }
    ClearLines();
    SpawnPiece();
}

void Game041Tetris::ClearLines()
{
    int cleared = 0;
    for (int y = 15; y >= 0; y--) {
        bool full = true;
        for (int x = kBoardLeft; x <= kBoardRight; x++) {
            if (field_[y][x] == 0) {
                full = false;
                break;
            }
        }
        if (full) {
            cleared++;
            for (int ty = y; ty > 0; ty--) {
                for (int tx = kBoardLeft; tx <= kBoardRight; tx++) {
                    field_[ty][tx] = field_[ty - 1][tx];
                }
            }
            for (int tx = kBoardLeft; tx <= kBoardRight; tx++) {
                field_[0][tx] = 0;
            }
            y++; // 重新检查当前行
        }
    }

    if (cleared > 0) {
        lines_cleared_ += cleared;
        score_ += (cleared * cleared * 100);
        if (score_ > high_score_) high_score_ = score_;
        drop_interval_ = 0.60f - lines_cleared_ * 0.03f;
        if (drop_interval_ < 0.10f) drop_interval_ = 0.10f;
    }
}

void Game041Tetris::Update(float dt, uint16_t keys_down, uint16_t keys_pressed)
{
    anim_timer_ += dt;

    if (state_ == STATE_TITLE) {
        if (keys_pressed & (KEY_A | KEY_START)) {
            Start();
        }
        return;
    }

    if (state_ == STATE_GAMEOVER) {
        if (keys_pressed & (KEY_A | KEY_START)) {
            Start();
        }
        return;
    }

    if (keys_pressed & KEY_START) {
        if (state_ == STATE_PLAYING) {
            Pause();
        } else if (state_ == STATE_PAUSED) {
            Resume();
        }
        return;
    }

    if (state_ == STATE_PAUSED) return;

    // 左移 / 右移
    if ((keys_pressed & KEY_LEFT) && !CheckCollision(piece_type_, piece_rot_, piece_x_ - 1, piece_y_)) {
        piece_x_--;
    }
    if ((keys_pressed & KEY_RIGHT) && !CheckCollision(piece_type_, piece_rot_, piece_x_ + 1, piece_y_)) {
        piece_x_++;
    }

    // 旋转 (KEY_A 或 KEY_UP)
    if (keys_pressed & (KEY_A | KEY_UP)) {
        int next_rot = (piece_rot_ + 1) % 4;
        if (!CheckCollision(piece_type_, next_rot, piece_x_, piece_y_)) {
            piece_rot_ = next_rot;
        } else if (!CheckCollision(piece_type_, next_rot, piece_x_ - 1, piece_y_)) { // 踢墙
            piece_x_--;
            piece_rot_ = next_rot;
        } else if (!CheckCollision(piece_type_, next_rot, piece_x_ + 1, piece_y_)) {
            piece_x_++;
            piece_rot_ = next_rot;
        }
    }

    // 快速下落 (KEY_DOWN 或 KEY_B)
    float cur_interval = (keys_down & (KEY_DOWN | KEY_B)) ? 0.05f : drop_interval_;

    drop_timer_ += dt;
    if (drop_timer_ >= cur_interval) {
        drop_timer_ = 0.0f;
        if (!CheckCollision(piece_type_, piece_rot_, piece_x_, piece_y_ + 1)) {
            piece_y_++;
            if (keys_down & (KEY_DOWN | KEY_B)) score_ += 1;
        } else {
            LockPiece();
        }
    }
}

void Game041Tetris::Render(uint8_t* fb_rgb24)
{
    if (state_ == STATE_GAMEOVER) {
        ArcadeResultScreen::RenderResult(fb_rgb24, false, score_, high_score_, anim_timer_);
        return;
    }

    memset(fb_rgb24, 0, kFrameBufferSize);

    // 绘制左右边界线 (深灰冷色)
    for (int y = 0; y < 16; y++) {
        int idx_l = (y * 16 + (kBoardLeft - 1)) * 3;
        int idx_r = (y * 16 + (kBoardRight + 1)) * 3;
        fb_rgb24[idx_l + 0] = 40; fb_rgb24[idx_l + 1] = 40; fb_rgb24[idx_l + 2] = 50;
        fb_rgb24[idx_r + 0] = 40; fb_rgb24[idx_r + 1] = 40; fb_rgb24[idx_r + 2] = 50;
    }

    // 绘制已锁定的方块
    for (int y = 0; y < 16; y++) {
        for (int x = kBoardLeft; x <= kBoardRight; x++) {
            uint8_t color_idx = field_[y][x];
            if (color_idx > 0 && color_idx <= 7) {
                int idx = (y * 16 + x) * 3;
                fb_rgb24[idx + 0] = kPieceColors[color_idx - 1][0];
                fb_rgb24[idx + 1] = kPieceColors[color_idx - 1][1];
                fb_rgb24[idx + 2] = kPieceColors[color_idx - 1][2];
            }
        }
    }

    // 绘制当前下落方块
    for (int i = 0; i < 4; i++) {
        int px = piece_x_ + kTetrisShapes[piece_type_][piece_rot_][i][0];
        int py = piece_y_ + kTetrisShapes[piece_type_][piece_rot_][i][1];
        if (py >= 0 && py < 16 && px >= 0 && px < 16) {
            int idx = (py * 16 + px) * 3;
            fb_rgb24[idx + 0] = kPieceColors[piece_type_][0];
            fb_rgb24[idx + 1] = kPieceColors[piece_type_][1];
            fb_rgb24[idx + 2] = kPieceColors[piece_type_][2];
        }
    }
}

CartridgeStatus Game041Tetris::GetStatus() const
{
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = (state_ == STATE_GAMEOVER) ? 0 : 1;
    st.state = state_;
    st.progress = (lines_cleared_ * 10 > 100) ? 100 : (lines_cleared_ * 10);
    return st;
}

} // namespace arcade
