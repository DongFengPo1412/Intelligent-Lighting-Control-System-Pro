// game_055_mirror_laser.cpp —— 目标 #055 镜面激光 (Mirror Laser) 核心实现
#include "game_055_mirror_laser.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>

namespace arcade {

namespace {

static inline void SetPx(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

} // namespace

Game055MirrorLaser::Game055MirrorLaser()
    : state_(STATE_TITLE),
      stage_(0),
      lives_(3),
      cursor_x_(3),
      cursor_y_(3),
      emit_x_(0),
      emit_y_(1),
      emit_dx_(1),
      emit_dy_(0),
      total_crystals_(0),
      lit_crystals_(0),
      receiver_hit_(false),
      receiver_powered_(false),
      bomb_hit_(false),
      charge_timer_(0.0f),
      bomb_timer_(0.0f),
      score_(0),
      high_score_(0),
      state_timer_(0.0f),
      anim_timer_(0.0f),
      beam_len_(0) {
    memset(grid_, 0, sizeof(grid_));
    memset(rotatable_, 0, sizeof(rotatable_));
    memset(crystal_lit_, 0, sizeof(crystal_lit_));
    memset(beam_path_, 0, sizeof(beam_path_));
    LoadStage(0);
}

void Game055MirrorLaser::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

void Game055MirrorLaser::LoadStage(int stage_idx) {
    firing_=false;
    if (stage_idx < 0 || stage_idx >= kNumStages) stage_idx = 0;
    stage_ = stage_idx;
    memset(grid_, LASER_EMPTY, sizeof(grid_));
    memset(rotatable_, 0, sizeof(rotatable_));

    auto put_mirror = [&](int x, int y, uint8_t init_type, bool can_rot) {
        grid_[y][x] = init_type;
        rotatable_[y][x] = can_rot;
    };

    if (stage_ == 0) {
        // Stage 0: 双镜折弯过水晶，避开右侧炸弹
        // 解法: 翻转 (5,1)->'\' 与 (5,5)->'/'
        emit_x_ = 0; emit_y_ = 1; emit_dx_ = 1; emit_dy_ = 0;
        grid_[1][0] = LASER_EMITTER;
        put_mirror(5, 1, LASER_MIRROR_SLASH, true);     // 翻转后 '\'
        grid_[3][5] = LASER_CRYSTAL;
        put_mirror(5, 5, LASER_MIRROR_BACKSLASH, true); // 翻转后 '/'
        grid_[5][1] = LASER_RECEIVER;
        grid_[5][6] = LASER_BOMB;
        grid_[3][2] = LASER_WALL;
        cursor_x_ = 5; cursor_y_ = 1;
    } else if (stage_ == 1) {
        // Stage 1: 三镜双水晶绕墙折返
        // 解法: (0,4)->'\', (4,4)->'/', (4,1)->'/'
        emit_x_ = 0; emit_y_ = 0; emit_dx_ = 0; emit_dy_ = 1;
        grid_[0][0] = LASER_EMITTER;
        grid_[2][0] = LASER_CRYSTAL;
        put_mirror(0, 4, LASER_MIRROR_SLASH, true);     // 翻转后 '\'
        grid_[2][3] = LASER_WALL;
        put_mirror(4, 4, LASER_MIRROR_BACKSLASH, true); // 翻转后 '/'
        grid_[2][4] = LASER_CRYSTAL;
        put_mirror(4, 1, LASER_MIRROR_BACKSLASH, true); // 翻转后 '/'
        grid_[1][6] = LASER_RECEIVER;
        grid_[6][4] = LASER_BOMB;
        cursor_x_ = 0; cursor_y_ = 4;
    } else if (stage_ == 2) {
        // Stage 2: 四镜环形聚焦
        // 解法: (1,0)->'/', (1,6)->'\', (5,6)->'/', (5,2)->'\'
        emit_x_ = 6; emit_y_ = 0; emit_dx_ = -1; emit_dy_ = 0;
        grid_[0][6] = LASER_EMITTER;
        put_mirror(1, 0, LASER_MIRROR_BACKSLASH, true); // -> '/'
        grid_[3][1] = LASER_CRYSTAL;
        put_mirror(1, 6, LASER_MIRROR_SLASH, true);     // -> '\'
        put_mirror(5, 6, LASER_MIRROR_BACKSLASH, true); // -> '/'
        grid_[4][5] = LASER_CRYSTAL;
        put_mirror(5, 2, LASER_MIRROR_SLASH, true);     // -> '\'
        grid_[2][3] = LASER_RECEIVER;
        grid_[4][3] = LASER_WALL;
        grid_[2][6] = LASER_BOMB;
        cursor_x_ = 1; cursor_y_ = 0;
    } else {
        // Stage 3: 五镜三水晶之字谐振终章
        // 解法: (0,1)->'/', (3,1)->'\', (3,5)->'\', (6,5)->'/', (6,0)->'\'
        emit_x_ = 0; emit_y_ = 6; emit_dx_ = 0; emit_dy_ = -1;
        grid_[6][0] = LASER_EMITTER;
        grid_[4][0] = LASER_CRYSTAL;
        put_mirror(0, 1, LASER_MIRROR_BACKSLASH, true); // -> '/'
        put_mirror(3, 1, LASER_MIRROR_SLASH, true);     // -> '\'
        grid_[3][3] = LASER_CRYSTAL;
        put_mirror(3, 5, LASER_MIRROR_SLASH, true);     // -> '\'
        put_mirror(6, 5, LASER_MIRROR_BACKSLASH, true); // -> '/'
        grid_[3][6] = LASER_CRYSTAL;
        put_mirror(6, 0, LASER_MIRROR_SLASH, true);     // -> '\'
        grid_[0][2] = LASER_RECEIVER;
        grid_[5][1] = LASER_BOMB;
        cursor_x_ = 0; cursor_y_ = 1;
    }

    total_crystals_ = 0;
    for (int y = 0; y < kGridSize; ++y) {
        for (int x = 0; x < kGridSize; ++x) {
            if (grid_[y][x] == LASER_CRYSTAL) total_crystals_++;
        }
    }

    charge_timer_ = 0.0f;
    bomb_timer_ = 0.0f;
    TraceBeam();
}

void Game055MirrorLaser::TraceBeam() {
    memset(crystal_lit_, 0, sizeof(crystal_lit_));
    beam_len_ = 0;
    lit_crystals_ = 0;
    receiver_hit_ = false;
    bomb_hit_ = false;

    int cx = emit_x_;
    int cy = emit_y_;
    int dx = emit_dx_;
    int dy = emit_dy_;

    for (int step = 0; step < kMaxBeamSteps; ++step) {
        cx += dx;
        cy += dy;
        if (cx < 0 || cx >= kGridSize || cy < 0 || cy >= kGridSize) {
            break;
        }
        beam_path_[beam_len_++] = {cx, cy};

        uint8_t cell = grid_[cy][cx];
        if (cell == LASER_EMPTY) {
            continue;
        } else if (cell == LASER_CRYSTAL) {
            if (!crystal_lit_[cy][cx]) {
                crystal_lit_[cy][cx] = true;
                lit_crystals_++;
            }
            continue;
        } else if (cell == LASER_MIRROR_SLASH) {
            int ndx = -dy;
            int ndy = -dx;
            dx = ndx;
            dy = ndy;
        } else if (cell == LASER_MIRROR_BACKSLASH) {
            int ndx = dy;
            int ndy = dx;
            dx = ndx;
            dy = ndy;
        } else if (cell == LASER_RECEIVER) {
            receiver_hit_ = true;
            break;
        } else if (cell == LASER_BOMB) {
            bomb_hit_ = true;
            break;
        } else {
            // WALL or EMITTER
            break;
        }
    }

    receiver_powered_ = receiver_hit_ && (lit_crystals_ == total_crystals_);
}

void Game055MirrorLaser::Init() {
    Reset();
}

void Game055MirrorLaser::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    state_ = STATE_TITLE;
    lives_ = 3;
    score_ = 0;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    LoadStage(0);
}

void Game055MirrorLaser::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        state_ = STATE_PLAYING;
        lives_ = 3;
        score_ = 0;
        state_timer_ = 0.0f;
        anim_timer_ = 0.0f;
        LoadStage(0);
    }
}

void Game055MirrorLaser::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game055MirrorLaser::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

void Game055MirrorLaser::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
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

        if (keys_pressed & KEY_SELECT) {
            LoadStage(stage_);
            return;
        }

        if(keys_pressed&KEY_B){firing_=!firing_;charge_timer_=bomb_timer_=0;SoundEvent(Sound::Shot);}

        if (keys_pressed & KEY_LEFT) {
            if (cursor_x_ > 0) cursor_x_--;
        } else if (keys_pressed & KEY_RIGHT) {
            if (cursor_x_ < kGridSize - 1) cursor_x_++;
        } else if (keys_pressed & KEY_UP) {
            if (cursor_y_ > 0) cursor_y_--;
        } else if (keys_pressed & KEY_DOWN) {
            if (cursor_y_ < kGridSize - 1) cursor_y_++;
        }

        if (keys_pressed & KEY_A) {
            if (rotatable_[cursor_y_][cursor_x_]) {
                firing_=false; // Safe editing; only explicit fire can consume a life.
                SoundEvent(Sound::Action,cursor_y_*7+cursor_x_);
                if (grid_[cursor_y_][cursor_x_] == LASER_MIRROR_SLASH) {
                    grid_[cursor_y_][cursor_x_] = LASER_MIRROR_BACKSLASH;
                } else if (grid_[cursor_y_][cursor_x_] == LASER_MIRROR_BACKSLASH) {
                    grid_[cursor_y_][cursor_x_] = LASER_MIRROR_SLASH;
                }
                charge_timer_ = 0.0f;
                bomb_timer_ = 0.0f;
                TraceBeam();
            }
        }

        if (firing_ && bomb_hit_) {
            bomb_timer_ += dt;
            if (bomb_timer_ >= 0.45f) {
                if (lives_ > 1) {
                    lives_--;
                    LoadStage(stage_);
                } else {
                    lives_ = 0;
                    state_ = STATE_GAMEOVER;
                    state_timer_ = 0.0f;
                }
                return;
            }
        } else {
            bomb_timer_ = 0.0f;
        }

        if (firing_ && receiver_powered_) {
            charge_timer_ += dt;
            if (charge_timer_ >= 0.40f) {
                AddScore(200u);
                if (stage_ + 1 < kNumStages) {
                    LoadStage(stage_ + 1);
                } else {
                    state_ = STATE_VICTORY;
                    state_timer_ = 0.0f;
                }
            }
        } else {
            charge_timer_ = 0.0f;
        }
    }
}

void Game055MirrorLaser::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    // 外框与 7x7 光学网格底色 (x=1..14, y=1..14)
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (x >= 1 && x <= 14 && y >= 1 && y <= 14) {
                int gx = (x - 1) / 2;
                int gy = (y - 1) / 2;
                uint8_t v = ((gx + gy) & 1) ? 20 : 14;
                SetPx(fb_rgb24, x, y, v, v + 3, v + 10);
            } else {
                SetPx(fb_rgb24, x, y, 30, 36, 48);
            }
        }
    }

    // 顶部生命与关卡指示 (y=0)
    for (int i = 0; i < (int)lives_; ++i) {
        SetPx(fb_rgb24, 1 + i * 2, 0, 245, 70, 80);
    }
    for (int s = 0; s < kNumStages; ++s) {
        int px = 9 + s * 2;
        if (s < stage_) SetPx(fb_rgb24, px, 0, 46, 220, 100);
        else if (s == stage_) SetPx(fb_rgb24, px, 0, 255, 215, 35);
    }

    // 先绘制激光束轨迹 (鲜亮洋红/电红激光)
    for (int i = 0; i < beam_len_; ++i) {
        int px = 1 + beam_path_[i].x * 2;
        int py = 1 + beam_path_[i].y * 2;
        uint8_t lr = receiver_powered_ ? 80 : 255;
        uint8_t lg = receiver_powered_ ? 255 : 45;
        uint8_t lb = receiver_powered_ ? 140 : 120;
        for (int dy = 0; dy < 2; ++dy) {
            for (int dx = 0; dx < 2; ++dx) {
                SetPx(fb_rgb24, px + dx, py + dy, lr, lg, lb);
            }
        }
    }

    // 绘制光学元件 (覆盖在光束之上，清晰呈现 '/' 与 '\' 对角线像素!)
    for (int gy = 0; gy < kGridSize; ++gy) {
        for (int gx = 0; gx < kGridSize; ++gx) {
            int px = 1 + gx * 2;
            int py = 1 + gy * 2;
            uint8_t cell = grid_[gy][gx];

            if (cell == LASER_WALL) {
                for (int dy = 0; dy < 2; ++dy) {
                    for (int dx = 0; dx < 2; ++dx) {
                        SetPx(fb_rgb24, px + dx, py + dy, 95, 108, 126);
                    }
                }
            } else if (cell == LASER_EMITTER) {
                for (int dy = 0; dy < 2; ++dy) {
                    for (int dx = 0; dx < 2; ++dx) {
                        SetPx(fb_rgb24, px + dx, py + dy, 255, 95, 30);
                    }
                }
            } else if (cell == LASER_MIRROR_SLASH) {
                // '/' 对角像素: 左下 (px, py+1) 与 右上 (px+1, py)
                SetPx(fb_rgb24, px, py + 1, 140, 235, 255);
                SetPx(fb_rgb24, px + 1, py, 210, 250, 255);
            } else if (cell == LASER_MIRROR_BACKSLASH) {
                // '\' 对角像素: 左上 (px, py) 与 右下 (px+1, py+1)
                SetPx(fb_rgb24, px, py, 210, 250, 255);
                SetPx(fb_rgb24, px + 1, py + 1, 140, 235, 255);
            } else if (cell == LASER_CRYSTAL) {
                bool lit = crystal_lit_[gy][gx];
                uint8_t cr = lit ? 80 : 25;
                uint8_t cg = lit ? 255 : 135;
                uint8_t cb = lit ? 235 : 175;
                SetPx(fb_rgb24, px, py, cr, cg, cb);
                SetPx(fb_rgb24, px + 1, py + 1, cr, cg, cb);
            } else if (cell == LASER_RECEIVER) {
                uint8_t rr = receiver_powered_ ? 50 : 235;
                uint8_t rg = receiver_powered_ ? 245 : 185;
                uint8_t rb = receiver_powered_ ? 95 : 25;
                for (int dy = 0; dy < 2; ++dy) {
                    for (int dx = 0; dx < 2; ++dx) {
                        SetPx(fb_rgb24, px + dx, py + dy, rr, rg, rb);
                    }
                }
            } else if (cell == LASER_BOMB) {
                uint8_t br = bomb_hit_ ? 255 : 175;
                uint8_t bg = bomb_hit_ ? 120 : 25;
                uint8_t bb = 25;
                SetPx(fb_rgb24, px, py, br, bg, bb);
                SetPx(fb_rgb24, px + 1, py, 90, 20, 20);
                SetPx(fb_rgb24, px, py + 1, 90, 20, 20);
                SetPx(fb_rgb24, px + 1, py + 1, br, bg, bb);
            }
        }
    }

    // 光标闪烁
    if (state_ == STATE_PLAYING || state_ == STATE_TITLE) {
        if (((int)(anim_timer_ * 6.0f) % 2) == 0) {
            int cx = 1 + cursor_x_ * 2;
            int cy = 1 + cursor_y_ * 2;
            SetPx(fb_rgb24, cx, cy, 255, 255, 120);
        }
    }

    SetPx(fb_rgb24,15,0,firing_?255:30,firing_?70:210,firing_?20:240);
    if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPx(fb_rgb24, 6, y, 250, 250, 250);
            SetPx(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game055MirrorLaser::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = lives_;
    st.state = (uint8_t)state_;
    int prog = stage_ * 25 + (receiver_powered_ ? 20 : 0);
    if (state_ == STATE_VICTORY) prog = 100;
    st.progress = (uint8_t)(prog > 100 ? 100 : prog);
    return st;
}

static_assert(sizeof(Game055MirrorLaser) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
