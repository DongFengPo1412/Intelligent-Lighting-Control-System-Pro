// game_038_bomberman.cpp —— 目标 #038 炸弹人 核心实现
#include "game_038_bomberman.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>
#include <math.h>
#include <stdlib.h>

namespace arcade {

Game038Bomberman::Game038Bomberman()
    : state_(STATE_TITLE),
      player_x_(1.0f),
      player_y_(1.0f),
      lives_(3),
      score_(0),
      high_score_(0),
      state_timer_(0.0f),
      anim_timer_(0.0f),
      flame_count_(0),
      remaining_enemies_(kNumEnemies) {
    bomb_.active = false;
}

void Game038Bomberman::ResetPlayer() {
    player_x_ = 1.0f;
    player_y_ = 1.0f;
    bomb_.active = false;
    flame_count_ = 0;
}

void Game038Bomberman::Init() {
    Reset();
}

void Game038Bomberman::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    state_ = STATE_TITLE;
    score_ = 0;
    lives_ = 3;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    flame_count_ = 0;
    remaining_enemies_ = kNumEnemies;

    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (x == 0 || x == 15 || y == 0 || y == 15) {
                map_[y][x] = TILE_HARD_WALL;
            } else if (x % 2 == 0 && y % 2 == 0) {
                map_[y][x] = TILE_HARD_WALL;
            } else {
                if (x <= 2 && y <= 2) {
                    map_[y][x] = TILE_EMPTY;
                } else if ((x == 13 && y == 1) || (x == 1 && y == 13) || (x == 13 && y == 13)) {
                    map_[y][x] = TILE_EMPTY;
                } else {
                    map_[y][x] = ((x * 7 + y * 13) % 10 < 5) ? TILE_SOFT_BRICK : TILE_EMPTY;
                }
            }
        }
    }

    enemies_[0].alive = true;
    enemies_[0].x = 13.0f; enemies_[0].y = 1.0f;
    enemies_[0].dir_x = -1; enemies_[0].dir_y = 0;
    enemies_[0].speed = 2.4f;

    enemies_[1].alive = true;
    enemies_[1].x = 1.0f; enemies_[1].y = 13.0f;
    enemies_[1].dir_x = 0; enemies_[1].dir_y = -1;
    enemies_[1].speed = 2.2f;

    enemies_[2].alive = true;
    enemies_[2].x = 13.0f; enemies_[2].y = 13.0f;
    enemies_[2].dir_x = 0; enemies_[2].dir_y = -1;
    enemies_[2].speed = 2.0f;

    ResetPlayer();
}

void Game038Bomberman::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        state_ = STATE_PLAYING;
        score_ = 0;
        lives_ = 3;
        state_timer_ = 0.0f;
        anim_timer_ = 0.0f;
        flame_count_ = 0;
        remaining_enemies_ = kNumEnemies;

        for (int y = 0; y < 16; ++y) {
            for (int x = 0; x < 16; ++x) {
                if (x == 0 || x == 15 || y == 0 || y == 15) {
                    map_[y][x] = TILE_HARD_WALL;
                } else if (x % 2 == 0 && y % 2 == 0) {
                    map_[y][x] = TILE_HARD_WALL;
                } else {
                    if (x <= 2 && y <= 2) {
                        map_[y][x] = TILE_EMPTY;
                    } else if ((x == 13 && y == 1) || (x == 1 && y == 13) || (x == 13 && y == 13)) {
                        map_[y][x] = TILE_EMPTY;
                    } else {
                        map_[y][x] = ((x * 7 + y * 13) % 10 < 5) ? TILE_SOFT_BRICK : TILE_EMPTY;
                    }
                }
            }
        }

        enemies_[0].alive = true;
        enemies_[0].x = 13.0f; enemies_[0].y = 1.0f;
        enemies_[0].dir_x = -1; enemies_[0].dir_y = 0;
        enemies_[0].speed = 2.4f;

        enemies_[1].alive = true;
        enemies_[1].x = 1.0f; enemies_[1].y = 13.0f;
        enemies_[1].dir_x = 0; enemies_[1].dir_y = -1;
        enemies_[1].speed = 2.2f;

        enemies_[2].alive = true;
        enemies_[2].x = 13.0f; enemies_[2].y = 13.0f;
        enemies_[2].dir_x = 0; enemies_[2].dir_y = -1;
        enemies_[2].speed = 2.0f;

        ResetPlayer();
    }
}

void Game038Bomberman::Pause() {
    if (state_ == STATE_PLAYING) state_ = STATE_PAUSED;
}

void Game038Bomberman::Resume() {
    if (state_ == STATE_PAUSED) state_ = STATE_PLAYING;
}

bool Game038Bomberman::IsWalkable(int gx, int gy, bool allow_bomb) const {
    if (gx < 0 || gx >= 16 || gy < 0 || gy >= 16) return false;
    if (map_[gy][gx] == TILE_HARD_WALL || map_[gy][gx] == TILE_SOFT_BRICK) return false;
    if (!allow_bomb && bomb_.active && bomb_.gx == gx && bomb_.gy == gy) return false;
    return true;
}

void Game038Bomberman::ExplodeBomb() {
    bomb_.active = false;
    flame_count_ = 0;

    auto add_flame = [this](int fx, int fy) {
        if (flame_count_ < kMaxFlames) {
            flames_[flame_count_].x = fx;
            flames_[flame_count_].y = fy;
            flames_[flame_count_].timer = 0.45f;
            flame_count_++;
        }
    };

    int cx = bomb_.gx;
    int cy = bomb_.gy;
    add_flame(cx, cy);

    const int dxs[4] = {0, 0, -1, 1};
    const int dys[4] = {-1, 1, 0, 0};

    for (int i = 0; i < 4; ++i) {
        for (int step = 1; step <= bomb_.range; ++step) {
            int tx = cx + dxs[i] * step;
            int ty = cy + dys[i] * step;

            if (tx < 0 || tx >= 16 || ty < 0 || ty >= 16) break;
            if (map_[ty][tx] == TILE_HARD_WALL) break;

            if (map_[ty][tx] == TILE_SOFT_BRICK) {
                map_[ty][tx] = TILE_EMPTY;
                add_flame(tx, ty);
                score_ += 20;
                if (score_ > high_score_) {
                    high_score_ = score_;
                    ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
                }
                break;
            }

            add_flame(tx, ty);
        }
    }

    ApplyFlameDamage();
}

void Game038Bomberman::ApplyFlameDamage() {
    for (int f = 0; f < flame_count_; ++f) {
        int fx = flames_[f].x;
        int fy = flames_[f].y;

        for (int e = 0; e < kNumEnemies; ++e) {
            if (enemies_[e].alive) {
                if ((int)roundf(enemies_[e].x) == fx && (int)roundf(enemies_[e].y) == fy) {
                    enemies_[e].alive = false;
                    remaining_enemies_--;
                    score_ += 100;
                    if (score_ > high_score_) {
                        high_score_ = score_;
                        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
                    }
                    if (remaining_enemies_ <= 0) {
                        state_ = STATE_VICTORY;
                        state_timer_ = 0.0f;
                        return;
                    }
                }
            }
        }

        if ((int)roundf(player_x_) == fx && (int)roundf(player_y_) == fy) {
            if (lives_ > 1) {
                lives_--;
                ResetPlayer();  // 清空火焰并回到出生点, 本帧不再重复判定
            } else {
                lives_ = 0;
                state_ = STATE_GAMEOVER;
                state_timer_ = 0.0f;
                if (score_ > high_score_) {
                    high_score_ = score_;
                    ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
                }
            }
            return;
        }
    }
}

void Game038Bomberman::MoveEnemy(BomberEnemy& e, float dt) {
    float move_step = e.speed * dt;
    int cur_gx = (int)roundf(e.x);
    int cur_gy = (int)roundf(e.y);

    if (fabsf(e.x - (float)cur_gx) < move_step && fabsf(e.y - (float)cur_gy) < move_step) {
        e.x = (float)cur_gx;
        e.y = (float)cur_gy;

        int dirs[4][2] = {{1,0}, {-1,0}, {0,1}, {0,-1}};
        int valid_dirs[4][2];
        int count = 0;

        for (int i = 0; i < 4; ++i) {
            int ndx = dirs[i][0];
            int ndy = dirs[i][1];
            if (ndx == -e.dir_x && ndy == -e.dir_y) continue;
            if (IsWalkable(cur_gx + ndx, cur_gy + ndy, false)) {
                valid_dirs[count][0] = ndx;
                valid_dirs[count][1] = ndy;
                count++;
            }
        }

        if (count > 0) {
            int choice = rand() % count;
            e.dir_x = valid_dirs[choice][0];
            e.dir_y = valid_dirs[choice][1];
        } else {
            e.dir_x = -e.dir_x;
            e.dir_y = -e.dir_y;
        }
    }

    e.x += (float)e.dir_x * move_step;
    e.y += (float)e.dir_y * move_step;
}

void Game038Bomberman::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
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
        if (state_timer_ > 0.5f && (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT))) {
            Start();
        }
        return;
    }

    if (state_ == STATE_PAUSED) {
        if (keys_pressed & KEY_START) state_ = STATE_PLAYING;
        return;
    }

    if (state_ == STATE_PLAYING) {
        if (keys_pressed & KEY_START) {
            state_ = STATE_PAUSED;
            return;
        }

        const float p_speed = 3.6f;
        float move_step = p_speed * dt;

        int gx = (int)roundf(player_x_);
        int gy = (int)roundf(player_y_);

        if (keys_down & KEY_UP) {
            if (IsWalkable(gx, gy - 1, true) || player_y_ > (float)gy) player_y_ -= move_step;
        } else if (keys_down & KEY_DOWN) {
            if (IsWalkable(gx, gy + 1, true) || player_y_ < (float)gy) player_y_ += move_step;
        } else if (keys_down & KEY_LEFT) {
            if (IsWalkable(gx - 1, gy, true) || player_x_ > (float)gx) player_x_ -= move_step;
        } else if (keys_down & KEY_RIGHT) {
            if (IsWalkable(gx + 1, gy, true) || player_x_ < (float)gx) player_x_ += move_step;
        }

        if (player_x_ < 1.0f) player_x_ = 1.0f;
        if (player_x_ > 14.0f) player_x_ = 14.0f;
        if (player_y_ < 1.0f) player_y_ = 1.0f;
        if (player_y_ > 14.0f) player_y_ = 14.0f;

        if ((keys_pressed & (KEY_A | KEY_B)) && !bomb_.active) {
            bomb_.active = true;
            bomb_.gx = (int)roundf(player_x_);
            bomb_.gy = (int)roundf(player_y_);
            bomb_.timer = 2.4f;
            bomb_.range = 2;
        }

        if (bomb_.active) {
            bomb_.timer -= dt;
            if (bomb_.timer <= 0.0f) {
                ExplodeBomb();
            }
        }

        for (int i = 0; i < flame_count_; ++i) {
            flames_[i].timer -= dt;
        }
        int active_f = 0;
        for (int i = 0; i < flame_count_; ++i) {
            if (flames_[i].timer > 0.0f) {
                flames_[active_f++] = flames_[i];
            }
        }
        flame_count_ = active_f;
        if (flame_count_ > 0) {
            ApplyFlameDamage();
            if (state_ != STATE_PLAYING) return;
        }

        for (int i = 0; i < kNumEnemies; ++i) {
            if (enemies_[i].alive) {
                MoveEnemy(enemies_[i], dt);

                if (fabsf(enemies_[i].x - player_x_) < 0.7f && fabsf(enemies_[i].y - player_y_) < 0.7f) {
                    if (lives_ > 1) {
                        lives_--;
                        ResetPlayer();
                    } else {
                        lives_ = 0;
                        state_ = STATE_GAMEOVER;
                        state_timer_ = 0.0f;
                        if (score_ > high_score_) {
                            high_score_ = score_;
                            ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
                        }
                        return;
                    }
                }
            }
        }
    }
}

void Game038Bomberman::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    memset(fb_rgb24, 0, 16 * 16 * 3);

    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            if (map_[y][x] == TILE_HARD_WALL) {
                fb_rgb24[idx + 0] = 70; fb_rgb24[idx + 1] = 80; fb_rgb24[idx + 2] = 95;
            } else if (map_[y][x] == TILE_SOFT_BRICK) {
                fb_rgb24[idx + 0] = 180; fb_rgb24[idx + 1] = 100; fb_rgb24[idx + 2] = 50;
            } else {
                fb_rgb24[idx + 0] = 20; fb_rgb24[idx + 1] = 30; fb_rgb24[idx + 2] = 20;
            }
        }
    }

    if (bomb_.active) {
        int idx = (bomb_.gy * 16 + bomb_.gx) * 3;
        bool flash = ((int)(bomb_.timer * 6.0f) % 2) == 0;
        if (flash) {
            fb_rgb24[idx + 0] = 255; fb_rgb24[idx + 1] = 255; fb_rgb24[idx + 2] = 255;
        } else {
            fb_rgb24[idx + 0] = 231; fb_rgb24[idx + 1] = 76; fb_rgb24[idx + 2] = 60;
        }
    }

    for (int i = 0; i < flame_count_; ++i) {
        int fx = flames_[i].x;
        int fy = flames_[i].y;
        if (fx >= 0 && fx < 16 && fy >= 0 && fy < 16) {
            int idx = (fy * 16 + fx) * 3;
            fb_rgb24[idx + 0] = 255; fb_rgb24[idx + 1] = 140; fb_rgb24[idx + 2] = 0;
        }
    }

    for (int i = 0; i < kNumEnemies; ++i) {
        if (enemies_[i].alive) {
            int ex = (int)roundf(enemies_[i].x);
            int ey = (int)roundf(enemies_[i].y);
            if (ex >= 0 && ex < 16 && ey >= 0 && ey < 16) {
                int idx = (ey * 16 + ex) * 3;
                fb_rgb24[idx + 0] = 255; fb_rgb24[idx + 1] = 50; fb_rgb24[idx + 2] = 80;
            }
        }
    }

    int px = (int)roundf(player_x_);
    int py = (int)roundf(player_y_);
    if (px >= 0 && px < 16 && py >= 0 && py < 16) {
        int idx = (py * 16 + px) * 3;
        fb_rgb24[idx + 0] = 255; fb_rgb24[idx + 1] = 255; fb_rgb24[idx + 2] = 255;
    }

    for (int i = 0; i < lives_ && i < 3; ++i) {
        int idx = (0 * 16 + (i * 2 + 1)) * 3;
        fb_rgb24[idx + 0] = 255; fb_rgb24[idx + 1] = 255; fb_rgb24[idx + 2] = 255;
    }

    if (state_ == STATE_PAUSED) {
        for (int y = 6; y <= 9; ++y) {
            int idx1 = (y * 16 + 6) * 3;
            int idx2 = (y * 16 + 9) * 3;
            fb_rgb24[idx1 + 0] = fb_rgb24[idx1 + 1] = fb_rgb24[idx1 + 2] = 250;
            fb_rgb24[idx2 + 0] = fb_rgb24[idx2 + 1] = fb_rgb24[idx2 + 2] = 250;
        }
    }
}

CartridgeStatus Game038Bomberman::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = lives_;
    st.state = (uint8_t)state_;
    st.progress = (uint8_t)(((kNumEnemies - remaining_enemies_) * 100) / kNumEnemies);
    return st;
}

} // namespace arcade

