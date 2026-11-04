// game_005_lode_runner.cpp —— 目标 #005 挖洞夺金 (Lode Runner) 核心实现
#include "game_005_lode_runner.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <math.h>
#include <string.h>

namespace arcade {

enum LodeTileType : uint8_t {
    LR_AIR    = 0,
    LR_BRICK  = 1,
    LR_SOLID  = 2,
    LR_LADDER = 3,
    LR_BAR    = 4,
    LR_HOLE   = 5,
};

static inline void SetPx005(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

Game005LodeRunner::Game005LodeRunner()
    : state_(STATE_TITLE),
      level_idx_(0),
      lives_(3),
      player_x_(6),
      player_y_(10),
      player_dir_(1),
      move_cooldown_(0.0f),
      fall_timer_(0.0f),
      escape_revealed_(false),
      escape_x_(2),
      score_(0),
      high_score_(0),
      state_timer_(0.0f),
      anim_timer_(0.0f),
      grid_{},
      golds_{},
      holes_{},
      guards_{} {
}

void Game005LodeRunner::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

void Game005LodeRunner::RespawnActors() {
    if (level_idx_ == 0) {
        player_x_ = 6;
        player_y_ = 10;
    } else {
        player_x_ = 6;
        player_y_ = 10;
    }
    player_dir_ = 1;
    move_cooldown_ = 0.0f;
    fall_timer_ = 0.0f;

    for (int i = 0; i < kMaxHoles; ++i) {
        if (holes_[i].active) {
            grid_[holes_[i].y][holes_[i].x] = LR_BRICK;
            holes_[i].active = false;
        }
    }

    for (int i = 0; i < kMaxGuards; ++i) {
        guards_[i].x = guards_[i].spawn_x;
        guards_[i].y = guards_[i].spawn_y;
        guards_[i].move_timer = 0.0f;
        guards_[i].trap_timer = 0.0f;
        guards_[i].trapped = false;
    }
}

void Game005LodeRunner::LoadLevel(int level_idx) {
    level_idx_ = level_idx;
    memset(grid_, LR_AIR, sizeof(grid_));
    for (int i = 0; i < kMaxHoles; ++i) holes_[i].active = false;
    escape_revealed_ = false;

    for (int x = 0; x < 16; ++x) {
        grid_[15][x] = LR_SOLID;
    }

    if (level_idx == 0) {
        for (int x = 0; x <= 12; ++x) grid_[11][x] = LR_BRICK;
        for (int x = 3; x <= 15; ++x) grid_[7][x] = LR_BRICK;
        for (int x = 0; x <= 11; ++x) grid_[3][x] = LR_BRICK;

        for (int y = 11; y <= 14; ++y) grid_[y][11] = LR_LADDER;
        for (int y = 7; y <= 10; ++y) grid_[y][4] = LR_LADDER;
        for (int y = 3; y <= 6; ++y) grid_[y][9] = LR_LADDER;

        for (int x = 10; x <= 13; ++x) grid_[5][x] = LR_BAR;

        golds_[0] = {2, 10, false};
        golds_[1] = {14, 6, false};
        golds_[2] = {5, 2, false};
        escape_x_ = 1;

        guards_[0] = {14, 14, 14, 14, 0.0f, 0.0f, false, true};
        guards_[1] = {13, 6, 13, 6, 0.0f, 0.0f, false, true};
    } else {
        for (int x = 2; x <= 15; ++x) grid_[11][x] = LR_BRICK;
        for (int x = 0; x <= 12; ++x) grid_[7][x] = LR_BRICK;
        for (int x = 3; x <= 15; ++x) grid_[3][x] = LR_BRICK;

        for (int y = 11; y <= 14; ++y) grid_[y][3] = LR_LADDER;
        for (int y = 7; y <= 10; ++y) grid_[y][11] = LR_LADDER;
        for (int y = 3; y <= 6; ++y) grid_[y][5] = LR_LADDER;

        for (int x = 1; x <= 4; ++x) grid_[5][x] = LR_BAR;

        golds_[0] = {13, 10, false};
        golds_[1] = {2, 6, false};
        golds_[2] = {12, 2, false};
        escape_x_ = 14;

        guards_[0] = {1, 14, 1, 14, 0.0f, 0.0f, false, true};
        guards_[1] = {2, 6, 2, 6, 0.0f, 0.0f, false, true};
    }

    RespawnActors();
}

void Game005LodeRunner::Init() {
    Reset();
}

void Game005LodeRunner::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    score_ = 0;
    lives_ = 3;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    LoadLevel(0);
    state_ = STATE_TITLE;
}

void Game005LodeRunner::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        score_ = 0;
        lives_ = 3;
        state_timer_ = 0.0f;
        anim_timer_ = 0.0f;
        LoadLevel(0);
        state_ = STATE_PLAYING;
    }
}

void Game005LodeRunner::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game005LodeRunner::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

bool Game005LodeRunner::CanWalk(int x, int y) const {
    if (x < 0 || x >= 16 || y < 0 || y >= 16) return false;
    uint8_t t = grid_[y][x];
    return (t == LR_AIR || t == LR_LADDER || t == LR_BAR || t == LR_HOLE);
}

bool Game005LodeRunner::CanFall(int x, int y) const {
    if (y >= 14) return false;
    uint8_t cur = grid_[y][x];
    if (cur == LR_LADDER || cur == LR_BAR) return false;

    uint8_t below = grid_[y + 1][x];
    if (below == LR_SOLID || below == LR_BRICK || below == LR_LADDER) return false;

    if (below == LR_AIR || below == LR_HOLE) {
        for (int i = 0; i < kMaxGuards; ++i) {
            if (guards_[i].active && guards_[i].trapped &&
                guards_[i].x == x && guards_[i].y == y + 1) {
                return false;
            }
        }
        return true;
    }
    return false;
}

bool Game005LodeRunner::TryDigAt(int hx, int hy) {
    if (hx < 0 || hx >= 16 || hy < 1 || hy >= 16) return false;
    if (grid_[hy][hx] != LR_BRICK) return false;
    uint8_t above = grid_[hy - 1][hx];
    if (above != LR_AIR && above != LR_BAR) return false;

    for (int i = 0; i < kMaxHoles; ++i) {
        if (!holes_[i].active) {
            holes_[i].active = true;
            holes_[i].x = hx;
            holes_[i].y = hy;
            holes_[i].timer = 4.0f;
            grid_[hy][hx] = LR_HOLE;
            AddScore(10);
            return true;
        }
    }
    return false;
}

void Game005LodeRunner::DigSide(int preferred_dx) {
    int hy = player_y_ + 1;
    if (TryDigAt(player_x_ + preferred_dx, hy)) {
        return;
    }
    if (preferred_dx == -1 && player_dir_ != -1) {
        TryDigAt(player_x_ + player_dir_, hy);
    }
}

void Game005LodeRunner::UpdateHoles(float dt) {
    for (int i = 0; i < kMaxHoles; ++i) {
        if (!holes_[i].active) continue;
        holes_[i].timer -= dt;
        if (holes_[i].timer <= 0.0f) {
            int hx = holes_[i].x;
            int hy = holes_[i].y;
            holes_[i].active = false;
            grid_[hy][hx] = LR_BRICK;

            for (int g = 0; g < kMaxGuards; ++g) {
                if (guards_[g].active && guards_[g].x == hx && guards_[g].y == hy) {
                    guards_[g].trapped = false;
                    guards_[g].trap_timer = 0.0f;
                    guards_[g].x = 7;
                    guards_[g].y = 1;
                    AddScore(100);
                }
            }
            if (player_x_ == hx && player_y_ == hy) {
                if (lives_ > 1) {
                    lives_--;
                    RespawnActors();
                    return;
                } else {
                    lives_ = 0;
                    state_ = STATE_GAMEOVER;
                    state_timer_ = 0.0f;
                    return;
                }
            }
        }
    }
}

void Game005LodeRunner::UpdateGuards(float dt) {
    for (int i = 0; i < kMaxGuards; ++i) {
        if (!guards_[i].active) continue;

        int gx = guards_[i].x;
        int gy = guards_[i].y;

        if (guards_[i].trapped) {
            guards_[i].trap_timer -= dt;
            if (guards_[i].trap_timer <= 0.0f) {
                guards_[i].trapped = false;
                if (gy > 0 && CanWalk(gx, gy - 1)) {
                    guards_[i].y = gy - 1;
                }
            }
            continue;
        }

        if (grid_[gy][gx] == LR_HOLE) {
            guards_[i].trapped = true;
            guards_[i].trap_timer = 3.2f;
            AddScore(50);
            continue;
        }

        if (CanFall(gx, gy)) {
            guards_[i].move_timer += dt;
            if (guards_[i].move_timer >= 0.12f) {
                guards_[i].move_timer = 0.0f;
                guards_[i].y += 1;
                if (grid_[guards_[i].y][guards_[i].x] == LR_HOLE) {
                    guards_[i].trapped = true;
                    guards_[i].trap_timer = 3.2f;
                    AddScore(50);
                }
            }
            continue;
        }

        guards_[i].move_timer += dt;
        if (guards_[i].move_timer >= 0.28f) {
            guards_[i].move_timer = 0.0f;

            int dx = 0;
            int dy = 0;
            if (gy < player_y_ && (grid_[gy][gx] == LR_LADDER || (gy + 1 < 16 && grid_[gy + 1][gx] == LR_LADDER) || grid_[gy][gx] == LR_BAR)) {
                dy = 1;
            } else if (gy > player_y_ && grid_[gy][gx] == LR_LADDER) {
                dy = -1;
            } else if (gx < player_x_) {
                dx = 1;
            } else if (gx > player_x_) {
                dx = -1;
            }

            if (dy != 0 && CanWalk(gx, gy + dy)) {
                guards_[i].y = gy + dy;
            } else if (dx != 0 && CanWalk(gx + dx, gy)) {
                guards_[i].x = gx + dx;
            }
        }

        if (!guards_[i].trapped && guards_[i].x == player_x_ && guards_[i].y == player_y_) {
            if (lives_ > 1) {
                lives_--;
                RespawnActors();
                return;
            } else {
                lives_ = 0;
                state_ = STATE_GAMEOVER;
                state_timer_ = 0.0f;
                return;
            }
        }
    }
}

void Game005LodeRunner::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt > 0.05f) dt = 0.05f;
    state_timer_ += dt;
    anim_timer_ += dt;

    if (state_ == STATE_TITLE) {
        if (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP | KEY_DOWN)) {
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

        if (move_cooldown_ > 0.0f) {
            move_cooldown_ -= dt;
            if (move_cooldown_ < 0.0f) move_cooldown_ = 0.0f;
        }

        // KEY_A digs brick down-left (with facing fallback), KEY_B digs brick down-right
        if (keys_pressed & KEY_A) DigSide(-1);
        if (keys_pressed & KEY_B) DigSide(1);

        if (CanFall(player_x_, player_y_)) {
            fall_timer_ += dt;
            if (fall_timer_ >= 0.09f) {
                fall_timer_ = 0.0f;
                player_y_ += 1;
            }
        } else {
            fall_timer_ = 0.0f;
            uint16_t dir_press = keys_pressed & (KEY_LEFT | KEY_RIGHT | KEY_UP | KEY_DOWN);
            if (dir_press != 0 || move_cooldown_ <= 0.0f) {
                int dx = 0;
                int dy = 0;
                uint16_t src = (dir_press != 0) ? dir_press : keys_down;
                if (src & KEY_UP) dy = -1;
                else if (src & KEY_DOWN) dy = 1;
                else if (src & KEY_LEFT) dx = -1;
                else if (src & KEY_RIGHT) dx = 1;

                if (dx != 0 || dy != 0) {
                    if (dy < 0) {
                        if (grid_[player_y_][player_x_] == LR_LADDER && CanWalk(player_x_, player_y_ - 1)) {
                            player_y_ -= 1;
                            move_cooldown_ = 0.13f;
                        }
                    } else if (dy > 0) {
                        bool can_descend = (grid_[player_y_][player_x_] == LR_LADDER) ||
                                           (grid_[player_y_][player_x_] == LR_BAR) ||
                                           (player_y_ + 1 < 16 && grid_[player_y_ + 1][player_x_] == LR_LADDER);
                        if (can_descend && CanWalk(player_x_, player_y_ + 1)) {
                            player_y_ += 1;
                            move_cooldown_ = 0.13f;
                        }
                    } else if (dx != 0) {
                        player_dir_ = (dx > 0) ? 1 : -1;
                        if (CanWalk(player_x_ + dx, player_y_)) {
                            player_x_ += dx;
                            move_cooldown_ = 0.13f;
                        }
                    }
                }
            }
        }

        // Gold collection
        bool all_gold = true;
        for (int i = 0; i < kMaxGold; ++i) {
            if (!golds_[i].collected) {
                if (player_x_ == golds_[i].x && player_y_ == golds_[i].y) {
                    golds_[i].collected = true;
                    AddScore(100);
                } else {
                    all_gold = false;
                }
            }
        }

        if (all_gold && !escape_revealed_) {
            escape_revealed_ = true;
            for (int y = 0; y <= 3; ++y) {
                grid_[y][escape_x_] = LR_LADDER;
            }
            AddScore(150);
        }

        // Escape at top of screen
        if (escape_revealed_ && player_x_ == escape_x_ && player_y_ == 0) {
            AddScore(200);
            if (level_idx_ + 1 < kNumLevels) {
                LoadLevel(level_idx_ + 1);
            } else {
                AddScore(300);
                state_ = STATE_VICTORY;
                state_timer_ = 0.0f;
            }
            return;
        }

        UpdateHoles(dt);
        if (state_ != STATE_PLAYING) return;
        UpdateGuards(dt);
    }
}

void Game005LodeRunner::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    memset(fb_rgb24, 0, 16 * 16 * 3);

    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            uint8_t t = grid_[y][x];
            if (t == LR_BRICK) {
                SetPx005(fb_rgb24, x, y, 185, 78, 38);
            } else if (t == LR_SOLID) {
                SetPx005(fb_rgb24, x, y, 110, 125, 135);
            } else if (t == LR_LADDER) {
                SetPx005(fb_rgb24, x, y, 52, 160, 225);
            } else if (t == LR_BAR) {
                SetPx005(fb_rgb24, x, y, 200, 190, 90);
            } else if (t == LR_HOLE) {
                SetPx005(fb_rgb24, x, y, 28, 16, 12);
            } else {
                SetPx005(fb_rgb24, x, y, 8, 10, 18);
            }
        }
    }

    for (int i = 0; i < kMaxGold; ++i) {
        if (!golds_[i].collected) {
            SetPx005(fb_rgb24, golds_[i].x, golds_[i].y, 255, 215, 0);
        }
    }

    for (int i = 0; i < kMaxGuards; ++i) {
        if (!guards_[i].active) continue;
        if (guards_[i].trapped) {
            SetPx005(fb_rgb24, guards_[i].x, guards_[i].y, 180, 50, 160);
        } else {
            SetPx005(fb_rgb24, guards_[i].x, guards_[i].y, 235, 65, 55);
        }
    }

    if (lives_ > 0) {
        SetPx005(fb_rgb24, player_x_, player_y_, 255, 255, 255);
    }

    for (int i = 0; i < (int)lives_ && i < 3; ++i) {
        SetPx005(fb_rgb24, 15 - i, 0, 46, 230, 120);
    }

    if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPx005(fb_rgb24, 6, y, 250, 250, 250);
            SetPx005(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game005LodeRunner::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = lives_;
    st.state = (uint8_t)state_;
    if (state_ == STATE_VICTORY) {
        st.progress = 100;
    } else {
        int gathered = 0;
        for (int i = 0; i < kMaxGold; ++i) {
            if (golds_[i].collected) gathered++;
        }
        st.progress = (uint8_t)(((level_idx_ * kMaxGold + gathered) * 100) / (kNumLevels * kMaxGold));
    }
    return st;
}

static_assert(sizeof(Game005LodeRunner) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
