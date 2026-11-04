// game_040_mirror_maze.cpp —— 目标 #040 镜像双人迷宫 (Mirror Twins) 核心实现
#include "game_040_mirror_maze.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>
#include <math.h>

namespace arcade {

static const char kMirrorLevels[4][16][17] = {
    // Level 0: 入门水平卡位对齐
    {
        "################",
        "################",
        "#......##......#",
        "#....G.##..H...#",
        "#......##......#",
        "#......##......#",
        "#.X....##....X.#",
        "#......##......#",
        "#......##.#....#",
        "#......##......#",
        "#X.....##.....X#",
        "#......##......#",
        "#......##......#",
        "#.A....##....B.#",
        "#......##......#",
        "################",
    },
    // Level 1: 纵横双向卡位错相
    {
        "################",
        "################",
        "#......##......#",
        "#.G....##......#",
        "#......##...H..#",
        "#......##......#",
        "#X.....##.....X#",
        "#......##......#",
        "#......##..#...#",
        "#......##....#.#",
        "#......##......#",
        "#.....X##X.....#",
        "#......##......#",
        "#.A....##....B.#",
        "#......##......#",
        "################",
    },
    // Level 2: 底部阻挡与中段错位
    {
        "################",
        "################",
        "#......##......#",
        "#......##.H....#",
        "#.G....##......#",
        "#......##......#",
        "#.....X##...X..#",
        "#......##......#",
        "#..#...##..#...#",
        "#....X.##....X.#",
        "#......##......#",
        "#......##......#",
        "#......##......#",
        "#....A.##.B#...#",
        "#......##......#",
        "################",
    },
    // Level 3: 终章双生迷阵
    {
        "################",
        "################",
        "#A.....##..#..B#",
        "#......##......#",
        "#......##......#",
        "#.X....##.X....#",
        "#......##......#",
        "#......##....#.#",
        "#......##......#",
        "#......##......#",
        "#..X...##.....X#",
        "#......##......#",
        "#......##...H..#",
        "#.X..G.##.....X#",
        "#......##......#",
        "################",
    },
};

static inline void SetPx(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

Game040MirrorMaze::Game040MirrorMaze()
    : state_(STATE_TITLE),
      level_(0),
      ax_(2),
      ay_(13),
      bx_(13),
      by_(13),
      goal_ax_(5),
      goal_ay_(3),
      goal_bx_(11),
      goal_by_(3),
      moves_(0),
      lives_(1),
      score_(0),
      high_score_(0),
      state_timer_(0.0f),
      anim_timer_(0.0f) {
    memset(map_, 0, sizeof(map_));
    LoadLevel(0);
}

void Game040MirrorMaze::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

void Game040MirrorMaze::LoadLevel(int lvl) {
    if (lvl < 0) lvl = 0;
    if (lvl >= kTotalLevels) lvl = kTotalLevels - 1;
    level_ = lvl;
    moves_ = 0;

    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            char ch = kMirrorLevels[lvl][y][x];
            if (ch == '#') {
                map_[y][x] = 1;
            } else if (ch == 'X') {
                map_[y][x] = 2;
            } else if (ch == 'G') {
                map_[y][x] = 3;
                goal_ax_ = x;
                goal_ay_ = y;
            } else if (ch == 'H') {
                map_[y][x] = 4;
                goal_bx_ = x;
                goal_by_ = y;
            } else if (ch == 'A') {
                map_[y][x] = 0;
                ax_ = x;
                ay_ = y;
            } else if (ch == 'B') {
                map_[y][x] = 0;
                bx_ = x;
                by_ = y;
            } else {
                map_[y][x] = 0;
            }
        }
    }
}

void Game040MirrorMaze::Init() {
    Reset();
}

void Game040MirrorMaze::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    state_ = STATE_TITLE;
    score_ = 0;
    lives_ = 1;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    LoadLevel(0);
}

void Game040MirrorMaze::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        score_ = 0;
        lives_ = 1;
        state_timer_ = 0.0f;
        anim_timer_ = 0.0f;
        LoadLevel(0);
        state_ = STATE_PLAYING;
    }
}

void Game040MirrorMaze::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game040MirrorMaze::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

void Game040MirrorMaze::StepMove(int dx, int dy) {
    int nax = ax_ + dx;
    int nay = ay_ + dy;
    int nbx = bx_ - dx;
    int nby = by_ + dy;

    if (nax >= 0 && nax < 16 && nay >= 0 && nay < 16 && map_[nay][nax] != 1) {
        ax_ = nax;
        ay_ = nay;
    }
    if (nbx >= 0 && nbx < 16 && nby >= 0 && nby < 16 && map_[nby][nbx] != 1) {
        bx_ = nbx;
        by_ = nby;
    }

    moves_++;

    if (map_[ay_][ax_] == 2 || map_[by_][bx_] == 2) {
        lives_ = 0;
        state_ = STATE_GAMEOVER;
        state_timer_ = 0.0f;
        if (score_ > high_score_) {
            high_score_ = score_;
            ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
        }
        return;
    }

    if (ax_ == goal_ax_ && ay_ == goal_ay_ && bx_ == goal_bx_ && by_ == goal_by_) {
        int bonus = (30 - moves_) * 2;
        if (bonus < 0) bonus = 0;
        AddScore((uint32_t)(150 + bonus));
        if (level_ + 1 >= kTotalLevels) {
            state_ = STATE_VICTORY;
            state_timer_ = 0.0f;
        } else {
            LoadLevel(level_ + 1);
        }
    }
}

void Game040MirrorMaze::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    (void)keys_down;
    if (dt > 0.05f) dt = 0.05f;
    state_timer_ += dt;
    anim_timer_ += dt;

    if (state_ == STATE_TITLE) {
        if (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT)) {
            Start();
        }
        return;
    }

    if (state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        if (state_timer_ > 0.5f && (keys_pressed & (KEY_START | KEY_A | KEY_B))) {
            Start();
        }
        return;
    }

    if (state_ == STATE_PAUSED) {
        if (keys_pressed & KEY_START) {
            state_ = STATE_PLAYING;
        }
        return;
    }

    if (state_ == STATE_PLAYING) {
        if (keys_pressed & KEY_START) {
            state_ = STATE_PAUSED;
            return;
        }

        if (keys_pressed & KEY_LEFT) {
            StepMove(-1, 0);
        } else if (keys_pressed & KEY_RIGHT) {
            StepMove(1, 0);
        } else if (keys_pressed & KEY_UP) {
            StepMove(0, -1);
        } else if (keys_pressed & KEY_DOWN) {
            StepMove(0, 1);
        }
    }
}

void Game040MirrorMaze::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    float pulse = 0.5f + 0.5f * sinf(anim_timer_ * 6.0f);

    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            uint8_t cell = map_[y][x];
            if (y == 0) {
                SetPx(fb_rgb24, x, y, 16, 18, 28);
            } else if (cell == 1) {
                if (x == 7 || x == 8) {
                    SetPx(fb_rgb24, x, y, 75, 55, 140);
                } else {
                    SetPx(fb_rgb24, x, y, 42, 58, 86);
                }
            } else if (cell == 2) {
                uint8_t r = (uint8_t)(185 + pulse * 65.0f);
                SetPx(fb_rgb24, x, y, r, 28, 32);
            } else if (cell == 3 || cell == 4) {
                uint8_t g = (uint8_t)(165 + pulse * 80.0f);
                uint8_t b = (uint8_t)(90 + pulse * 50.0f);
                SetPx(fb_rgb24, x, y, 35, g, b);
            } else {
                SetPx(fb_rgb24, x, y, 12, 16, 26);
            }
        }
    }

    // Top HUD: level progress dots (x = 1..4) & life indicator (x = 14)
    for (int i = 0; i < kTotalLevels; ++i) {
        if (i < level_) {
            SetPx(fb_rgb24, 1 + i, 0, 50, 230, 120);
        } else if (i == level_) {
            SetPx(fb_rgb24, 1 + i, 0, 255, 215, 40);
        } else {
            SetPx(fb_rgb24, 1 + i, 0, 45, 50, 68);
        }
    }
    if (lives_ > 0) {
        SetPx(fb_rgb24, 14, 0, 245, 65, 95);
    }

    // Draw Twin A (Cyan) & Twin B (Magenta)
    bool a_on_goal = (ax_ == goal_ax_ && ay_ == goal_ay_);
    bool b_on_goal = (bx_ == goal_bx_ && by_ == goal_by_);

    if (a_on_goal) {
        SetPx(fb_rgb24, ax_, ay_, 220, 255, 255);
    } else {
        SetPx(fb_rgb24, ax_, ay_, 0, 235, 255);
    }

    if (b_on_goal) {
        SetPx(fb_rgb24, bx_, by_, 255, 230, 255);
    } else {
        SetPx(fb_rgb24, bx_, by_, 255, 75, 215);
    }

    if (state_ == STATE_GAMEOVER) {
        for (int x = 0; x < 16; ++x) {
            SetPx(fb_rgb24, x, 0, 235, 50, 50);
        }
    } else if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPx(fb_rgb24, 6, y, 250, 250, 250);
            SetPx(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game040MirrorMaze::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = lives_;
    st.state = (uint8_t)state_;
    st.progress = (uint8_t)((state_ == STATE_VICTORY) ? 100 : (level_ * 25));
    return st;
}

static_assert(sizeof(Game040MirrorMaze) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
