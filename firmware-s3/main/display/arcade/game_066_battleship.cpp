// game_066_battleship.cpp —— 目标 #066 海战棋 (Battleship) 核心实现
#include "game_066_battleship.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>

namespace arcade {

static const uint8_t kShipLengths[4] = {4, 3, 2, 2};

static const uint8_t kShotUntargeted = 0;
static const uint8_t kShotMiss = 1;
static const uint8_t kShotHit = 2;
static const uint8_t kShotSunk = 3;

static inline void SetPx066(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

Game066Battleship::Game066Battleship()
    : state_(STATE_TITLE),
      cursor_x_(3),
      cursor_y_(3),
      player_hits_(0),
      ai_hits_(0),
      ai_ships_sunk_(0),
      player_ships_sunk_(0),
      player_turn_(true),
      hold_peek_(false),
      peek_timer_(0.0f),
      sink_flash_timer_(0.0f),
      ai_timer_(0.0f),
      rng_seed_(0x66BA771Eu),
      match_count_(0),
      score_(0),
      high_score_(0),
      state_timer_(0.0f),
      anim_timer_(0.0f) {
    memset(player_grid_, 0, sizeof(player_grid_));
    memset(ai_grid_, 0, sizeof(ai_grid_));
    memset(player_shots_, 0, sizeof(player_shots_));
    memset(ai_shots_, 0, sizeof(ai_shots_));
    memset(player_ships_, 0, sizeof(player_ships_));
    memset(ai_ships_, 0, sizeof(ai_ships_));
}

uint32_t Game066Battleship::NextRand() {
    rng_seed_ = rng_seed_ * 1103515245u + 12345u;
    return (rng_seed_ >> 16) & 0x7FFF;
}

void Game066Battleship::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

bool Game066Battleship::CanPlaceShip(const uint8_t grid[kGridSize][kGridSize], int x, int y, int len, bool horiz) const {
    if (horiz) {
        if (x < 0 || x + len > kGridSize || y < 0 || y >= kGridSize) return false;
        for (int i = 0; i < len; ++i) {
            if (grid[y][x + i] != 0) return false;
        }
    } else {
        if (x < 0 || x >= kGridSize || y < 0 || y + len > kGridSize) return false;
        for (int i = 0; i < len; ++i) {
            if (grid[y + i][x] != 0) return false;
        }
    }
    return true;
}

void Game066Battleship::PlaceFleet(uint8_t grid[kGridSize][kGridSize], NavalShip ships[kNumShips]) {
    memset(grid, 0, kGridSize * kGridSize);
    for (int s = 0; s < kNumShips; ++s) {
        int len = kShipLengths[s];
        bool placed = false;
        for (int attempt = 0; attempt < 200; ++attempt) {
            bool horiz = (NextRand() & 1u) != 0;
            int x = (int)(NextRand() % kGridSize);
            int y = (int)(NextRand() % kGridSize);
            if (CanPlaceShip(grid, x, y, len, horiz)) {
                ships[s].x = (uint8_t)x;
                ships[s].y = (uint8_t)y;
                ships[s].len = (uint8_t)len;
                ships[s].horiz = horiz ? 1 : 0;
                ships[s].hits = 0;
                for (int i = 0; i < len; ++i) {
                    int cx = horiz ? (x + i) : x;
                    int cy = horiz ? y : (y + i);
                    grid[cy][cx] = (uint8_t)(s + 1);
                }
                placed = true;
                break;
            }
        }
        if (!placed) {
            for (int h = 0; h < 2 && !placed; ++h) {
                bool horiz = (h == 0);
                for (int y = 0; y < kGridSize && !placed; ++y) {
                    for (int x = 0; x < kGridSize && !placed; ++x) {
                        if (CanPlaceShip(grid, x, y, len, horiz)) {
                            ships[s].x = (uint8_t)x;
                            ships[s].y = (uint8_t)y;
                            ships[s].len = (uint8_t)len;
                            ships[s].horiz = horiz ? 1 : 0;
                            ships[s].hits = 0;
                            for (int i = 0; i < len; ++i) {
                                int cx = horiz ? (x + i) : x;
                                int cy = horiz ? y : (y + i);
                                grid[cy][cx] = (uint8_t)(s + 1);
                            }
                            placed = true;
                        }
                    }
                }
            }
        }
    }
}

void Game066Battleship::MarkShipSunk(uint8_t shots[kGridSize][kGridSize], const NavalShip& s) {
    for (int i = 0; i < s.len; ++i) {
        int cx = s.horiz ? (s.x + i) : s.x;
        int cy = s.horiz ? s.y : (s.y + i);
        if (cx >= 0 && cx < kGridSize && cy >= 0 && cy < kGridSize) {
            shots[cy][cx] = kShotSunk;
        }
    }
}

void Game066Battleship::InitMatch() {
    rng_seed_ = 0x66BA771Eu ^ (match_count_ * 0x9E3779B9u);
    memset(player_shots_, kShotUntargeted, sizeof(player_shots_));
    memset(ai_shots_, kShotUntargeted, sizeof(ai_shots_));
    PlaceFleet(player_grid_, player_ships_);
    PlaceFleet(ai_grid_, ai_ships_);
    cursor_x_ = 3;
    cursor_y_ = 3;
    player_hits_ = 0;
    ai_hits_ = 0;
    ai_ships_sunk_ = 0;
    player_ships_sunk_ = 0;
    player_turn_ = true;
    hold_peek_ = false;
    peek_timer_ = 0.0f;
    sink_flash_timer_ = 0.0f;
    ai_timer_ = 0.0f;
}

void Game066Battleship::Init() {
    Reset();
}

void Game066Battleship::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    state_ = STATE_TITLE;
    score_ = 0;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    match_count_ = 0;
    InitMatch();
}

void Game066Battleship::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        state_ = STATE_PLAYING;
        score_ = 0;
        state_timer_ = 0.0f;
        anim_timer_ = 0.0f;
        match_count_++;
        InitMatch();
    }
}

void Game066Battleship::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game066Battleship::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

void Game066Battleship::MakeAiShot() {
    static const int kOrtho[4][2] = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};
    uint8_t cand_x[64];
    uint8_t cand_y[64];
    int cand_n = 0;

    // 1. Aligned line extension on unsunk hits
    for (int y = 0; y < kGridSize; ++y) {
        for (int x = 0; x < kGridSize; ++x) {
            if (ai_shots_[y][x] != kShotHit) continue;
            if (x + 1 < kGridSize && ai_shots_[y][x + 1] == kShotHit) {
                if (x - 1 >= 0 && ai_shots_[y][x - 1] == kShotUntargeted) {
                    cand_x[cand_n] = (uint8_t)(x - 1);
                    cand_y[cand_n] = (uint8_t)y;
                    cand_n++;
                }
                if (x + 2 < kGridSize && ai_shots_[y][x + 2] == kShotUntargeted) {
                    cand_x[cand_n] = (uint8_t)(x + 2);
                    cand_y[cand_n] = (uint8_t)y;
                    cand_n++;
                }
            }
            if (y + 1 < kGridSize && ai_shots_[y + 1][x] == kShotHit) {
                if (y - 1 >= 0 && ai_shots_[y - 1][x] == kShotUntargeted) {
                    cand_x[cand_n] = (uint8_t)x;
                    cand_y[cand_n] = (uint8_t)(y - 1);
                    cand_n++;
                }
                if (y + 2 < kGridSize && ai_shots_[y + 2][x] == kShotUntargeted) {
                    cand_x[cand_n] = (uint8_t)x;
                    cand_y[cand_n] = (uint8_t)(y + 2);
                    cand_n++;
                }
            }
        }
    }

    // 2. Orthogonal neighbors of any unsunk hit
    if (cand_n == 0) {
        for (int y = 0; y < kGridSize; ++y) {
            for (int x = 0; x < kGridSize; ++x) {
                if (ai_shots_[y][x] != kShotHit) continue;
                for (int d = 0; d < 4; ++d) {
                    int nx = x + kOrtho[d][0];
                    int ny = y + kOrtho[d][1];
                    if (nx >= 0 && nx < kGridSize && ny >= 0 && ny < kGridSize &&
                        ai_shots_[ny][nx] == kShotUntargeted) {
                        cand_x[cand_n] = (uint8_t)nx;
                        cand_y[cand_n] = (uint8_t)ny;
                        cand_n++;
                    }
                }
            }
        }
    }

    // 3. Checkerboard hunt
    if (cand_n == 0) {
        for (int y = 0; y < kGridSize; ++y) {
            for (int x = 0; x < kGridSize; ++x) {
                if (((x + y) % 2 == 0) && ai_shots_[y][x] == kShotUntargeted) {
                    cand_x[cand_n] = (uint8_t)x;
                    cand_y[cand_n] = (uint8_t)y;
                    cand_n++;
                }
            }
        }
    }

    // 4. Remaining untargeted cells fallback
    if (cand_n == 0) {
        for (int y = 0; y < kGridSize; ++y) {
            for (int x = 0; x < kGridSize; ++x) {
                if (ai_shots_[y][x] == kShotUntargeted) {
                    cand_x[cand_n] = (uint8_t)x;
                    cand_y[cand_n] = (uint8_t)y;
                    cand_n++;
                }
            }
        }
    }

    if (cand_n > 0) {
        int pick = (int)(NextRand() % (uint32_t)cand_n);
        int tx = cand_x[pick];
        int ty = cand_y[pick];
        uint8_t cell = player_grid_[ty][tx];
        if (cell > 0) {
            int s_idx = cell - 1;
            ai_shots_[ty][tx] = kShotHit;
            player_ships_[s_idx].hits++;
            ai_hits_++;
            if (player_ships_[s_idx].hits >= player_ships_[s_idx].len) {
                MarkShipSunk(ai_shots_, player_ships_[s_idx]);
                player_ships_sunk_++;
            }
        } else {
            ai_shots_[ty][tx] = kShotMiss;
        }
    }

    if (ai_hits_ >= kTotalDeckCells) {
        state_ = STATE_GAMEOVER;
        state_timer_ = 0.0f;
        return;
    }
    player_turn_ = true;
}

void Game066Battleship::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt > 0.05f) dt = 0.05f;
    state_timer_ += dt;
    anim_timer_ += dt;
    if (sink_flash_timer_ > 0.0f) {
        sink_flash_timer_ -= dt;
        if (sink_flash_timer_ < 0.0f) sink_flash_timer_ = 0.0f;
    }
    if (peek_timer_ > 0.0f) {
        peek_timer_ -= dt;
        if (peek_timer_ < 0.0f) peek_timer_ = 0.0f;
    }

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

        hold_peek_ = ((keys_down & KEY_B) != 0);
        if (keys_pressed & KEY_B) {
            peek_timer_ = (peek_timer_ > 0.0f && !hold_peek_) ? 0.0f : 1.0f;
        }

        if (player_turn_) {
            if (keys_pressed & (KEY_LEFT | KEY_RIGHT | KEY_UP | KEY_DOWN | KEY_A)) {
                if (!hold_peek_) peek_timer_ = 0.0f;
            }

            if (keys_pressed & KEY_LEFT) {
                if (cursor_x_ > 0) cursor_x_--;
            } else if (keys_pressed & KEY_RIGHT) {
                if (cursor_x_ < kGridSize - 1) cursor_x_++;
            }
            if (keys_pressed & KEY_UP) {
                if (cursor_y_ > 0) cursor_y_--;
            } else if (keys_pressed & KEY_DOWN) {
                if (cursor_y_ < kGridSize - 1) cursor_y_++;
            }

            if ((keys_pressed & KEY_A) && !hold_peek_) {
                if (player_shots_[cursor_y_][cursor_x_] == kShotUntargeted) {
                    uint8_t cell = ai_grid_[cursor_y_][cursor_x_];
                    if (cell > 0) {
                        int s_idx = cell - 1;
                        player_shots_[cursor_y_][cursor_x_] = kShotHit;
                        ai_ships_[s_idx].hits++;
                        player_hits_++;
                        AddScore(50);

                        if (ai_ships_[s_idx].hits >= ai_ships_[s_idx].len) {
                            MarkShipSunk(player_shots_, ai_ships_[s_idx]);
                            ai_ships_sunk_++;
                            AddScore(100);
                            sink_flash_timer_ = 0.35f;
                        }

                        if (player_hits_ >= kTotalDeckCells) {
                            AddScore(300);
                            state_ = STATE_VICTORY;
                            state_timer_ = 0.0f;
                            return;
                        }
                        // Bonus shot granted on hit!
                    } else {
                        player_shots_[cursor_y_][cursor_x_] = kShotMiss;
                        player_turn_ = false;
                        ai_timer_ = 0.18f;
                    }
                }
            }
        } else {
            ai_timer_ -= dt;
            if (ai_timer_ <= 0.0f) {
                MakeAiShot();
            }
        }
    }
}

void Game066Battleship::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    bool show_own = (state_ == STATE_PLAYING) && (hold_peek_ || peek_timer_ > 0.0f);

    if (show_own) {
        for (int cy = 0; cy < kGridSize; ++cy) {
            for (int cx = 0; cx < kGridSize; ++cx) {
                int px = cx * 2;
                int py = cy * 2;
                bool even = ((cx + cy) % 2 == 0);
                uint8_t ship_id = player_grid_[cy][cx];
                uint8_t st = ai_shots_[cy][cx];

                uint8_t r = even ? 10 : 14;
                uint8_t g = even ? 36 : 44;
                uint8_t b = even ? 48 : 58;

                if (ship_id > 0) {
                    r = 75; g = 185; b = 210;
                }
                if (st == kShotMiss) {
                    r = 40; g = 95; b = 140;
                } else if (st == kShotHit || st == kShotSunk) {
                    r = 245; g = 50; b = 40;
                }

                SetPx066(fb_rgb24, px,     py,     r, g, b);
                SetPx066(fb_rgb24, px + 1, py,     r, g, b);
                SetPx066(fb_rgb24, px,     py + 1, r, g, b);
                SetPx066(fb_rgb24, px + 1, py + 1, r, g, b);
            }
        }
        for (int s = 0; s < kNumShips; ++s) {
            bool alive = (player_ships_[s].hits < player_ships_[s].len);
            SetPx066(fb_rgb24, s * 4, 0, alive ? 50 : 255, alive ? 245 : 40, alive ? 100 : 40);
        }
    } else {
        bool sink_flash = (sink_flash_timer_ > 0.0f) && (((int)(anim_timer_ * 16.0f)) % 2 == 0);
        for (int cy = 0; cy < kGridSize; ++cy) {
            for (int cx = 0; cx < kGridSize; ++cx) {
                int px = cx * 2;
                int py = cy * 2;
                bool even = ((cx + cy) % 2 == 0);
                uint8_t st = player_shots_[cy][cx];

                if (st == kShotUntargeted) {
                    uint8_t r = even ? 8 : 12;
                    uint8_t g = even ? 28 : 38;
                    uint8_t b = even ? 52 : 66;
                    SetPx066(fb_rgb24, px,     py,     r, g, b);
                    SetPx066(fb_rgb24, px + 1, py,     r, g, b);
                    SetPx066(fb_rgb24, px,     py + 1, r, g, b);
                    SetPx066(fb_rgb24, px + 1, py + 1, r, g, b);
                } else if (st == kShotMiss) {
                    SetPx066(fb_rgb24, px,     py,     70, 145, 205);
                    SetPx066(fb_rgb24, px + 1, py,     35,  95, 155);
                    SetPx066(fb_rgb24, px,     py + 1, 35,  95, 155);
                    SetPx066(fb_rgb24, px + 1, py + 1, 25,  75, 130);
                } else if (st == kShotHit) {
                    SetPx066(fb_rgb24, px,     py,     255, 205, 50);
                    SetPx066(fb_rgb24, px + 1, py,     255, 100, 20);
                    SetPx066(fb_rgb24, px,     py + 1, 255, 100, 20);
                    SetPx066(fb_rgb24, px + 1, py + 1, 220,  45, 15);
                } else {
                    uint8_t r = sink_flash ? 255 : 215;
                    uint8_t g = sink_flash ? 240 :  30;
                    uint8_t b = sink_flash ? 120 :  45;
                    SetPx066(fb_rgb24, px,     py,     r, g, b);
                    SetPx066(fb_rgb24, px + 1, py,     r, g, b);
                    SetPx066(fb_rgb24, px,     py + 1, r, g, b);
                    SetPx066(fb_rgb24, px + 1, py + 1, r, g, b);
                }
            }
        }

        if (state_ == STATE_PLAYING && player_turn_) {
            bool blink = (((int)(anim_timer_ * 6.0f)) % 2 == 0);
            if (blink) {
                int px = cursor_x_ * 2;
                int py = cursor_y_ * 2;
                SetPx066(fb_rgb24, px,     py,     100, 255, 120);
                SetPx066(fb_rgb24, px + 1, py + 1, 100, 255, 120);
            }
        }
    }

    if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPx066(fb_rgb24, 6, y, 250, 250, 250);
            SetPx066(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game066Battleship::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = (uint8_t)(kNumShips - player_ships_sunk_);
    st.state = (uint8_t)state_;
    st.progress = (uint8_t)((player_hits_ * 100) / kTotalDeckCells);
    return st;
}

static_assert(sizeof(Game066Battleship) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
