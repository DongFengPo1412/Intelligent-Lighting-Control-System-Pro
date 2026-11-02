// game_024_lode_runner.cpp —— 淘金者 1983 核心实现
#include "game_024_lode_runner.h"
#include <string.h>
#include <stdlib.h>
#include <math.h>

namespace arcade {

Game024LodeRunner::Game024LodeRunner()
    : state_(STATE_TITLE),
      player_x_(1.0f),
      player_y_(14.0f),
      player_dir_(1),
      lives_(3),
      move_timer_(0.0f),
      escape_ladder_revealed_(false),
      score_(0),
      high_score_(0),
      state_timer_(0.0f) {
}

void Game024LodeRunner::InitLevel() {
    // 1. 清空网格为空气
    memset(grid_, LODE_AIR, sizeof(grid_));

    // 2. 底层坚固基岩 (不可破坏)
    for (int x = 0; x < 16; ++x) grid_[15][x] = LODE_SOLID;

    // 3. 砖块平台 (可被激光枪挖坑)
    for (int x = 0; x <= 12; ++x) grid_[11][x] = LODE_BRICK;
    for (int x = 3; x <= 15; ++x) grid_[7][x] = LODE_BRICK;
    for (int x = 0; x <= 10; ++x) grid_[3][x] = LODE_BRICK;

    // 4. 爬梯
    for (int y = 11; y <= 14; ++y) grid_[y][11] = LODE_LADDER;
    for (int y = 7; y <= 11; ++y) grid_[y][4] = LODE_LADDER;
    for (int y = 3; y <= 7; ++y) grid_[y][9] = LODE_LADDER;

    // 5. 滑索/悬挂横杆
    for (int x = 10; x <= 13; ++x) grid_[5][x] = LODE_BAR;

    // 6. 金矿分布
    golds_[0].collected = false; golds_[0].x = 1;  golds_[0].y = 10;
    golds_[1].collected = false; golds_[1].x = 14; golds_[1].y = 6;
    golds_[2].collected = false; golds_[2].x = 5;  golds_[2].y = 2;

    // 7. 警卫与实体初始化
    player_x_ = 1.0f;
    player_y_ = 14.0f;
    player_dir_ = 1;
    move_timer_ = 0.0f;
    escape_ladder_revealed_ = false;

    for (int i = 0; i < MAX_HOLES; ++i) holes_[i].active = false;

    guards_[0].active = true;
    guards_[0].x = 12.0f;
    guards_[0].y = 10.0f;
    guards_[0].move_timer = 0.0f;
    guards_[0].trapped = false;
    guards_[0].trap_timer = 0.0f;

    guards_[1].active = true;
    guards_[1].x = 14.0f;
    guards_[1].y = 6.0f;
    guards_[1].move_timer = 0.0f;
    guards_[1].trapped = false;
    guards_[1].trap_timer = 0.0f;
}

void Game024LodeRunner::Init() {
    Reset();
}

void Game024LodeRunner::Reset() {
    state_ = STATE_PLAYING;
    score_ = 0;
    lives_ = 3;
    state_timer_ = 0.0f;
    InitLevel();
}

bool Game024LodeRunner::CanWalk(int x, int y) const {
    if (x < 0 || x >= 16 || y < 0 || y >= 16) return false;
    uint8_t t = grid_[y][x];
    return (t == LODE_AIR || t == LODE_LADDER || t == LODE_BAR || t == LODE_HOLE);
}

bool Game024LodeRunner::CanFall(int x, int y) const {
    if (y >= 14) return false; // 已到底层站稳
    uint8_t cur = grid_[y][x];
    if (cur == LODE_LADDER || cur == LODE_BAR) return false;

    uint8_t below = grid_[y + 1][x];
    // 下方是空洞或空气，且下方没有卡着警卫
    if (below == LODE_AIR || below == LODE_HOLE) {
        for (int i = 0; i < MAX_GUARDS; ++i) {
            if (guards_[i].active && guards_[i].trapped) {
                if ((int)roundf(guards_[i].x) == x && (int)roundf(guards_[i].y) == y + 1) {
                    return false; // 踏在被困警卫头上站稳
                }
            }
        }
        return true;
    }
    return false;
}

void Game024LodeRunner::DigHole(int dx) {
    int px = (int)roundf(player_x_);
    int py = (int)roundf(player_y_);
    int hx = px + dx;
    int hy = py + 1;

    if (hx < 0 || hx >= 16 || hy < 0 || hy >= 16) return;

    // 只有砖块才能被挖开成坑，且上方必须是空气以供通过
    if (grid_[hy][hx] == LODE_BRICK && grid_[py][hx] == LODE_AIR) {
        for (int i = 0; i < MAX_HOLES; ++i) {
            if (!holes_[i].active) {
                holes_[i].active = true;
                holes_[i].x = hx;
                holes_[i].y = hy;
                holes_[i].timer = 4.5f; // 4.5 秒后自动填平
                grid_[hy][hx] = LODE_HOLE;
                score_ += 20;
                if (score_ > high_score_) high_score_ = score_;
                break;
            }
        }
    }
}

void Game024LodeRunner::UpdateHoles(float dt) {
    for (int i = 0; i < MAX_HOLES; ++i) {
        if (!holes_[i].active) continue;

        holes_[i].timer -= dt;
        if (holes_[i].timer <= 0.0f) {
            holes_[i].active = false;
            int hx = holes_[i].x;
            int hy = holes_[i].y;
            grid_[hy][hx] = LODE_BRICK; // 砖块填平再生

            // 活埋检测：若警卫正在坑中，就地消灭！
            for (int g = 0; g < MAX_GUARDS; ++g) {
                if (guards_[g].active && guards_[g].trapped) {
                    if ((int)roundf(guards_[g].x) == hx && (int)roundf(guards_[g].y) == hy) {
                        guards_[g].trapped = false;
                        guards_[g].x = 7.0f; // 顶部重新空降
                        guards_[g].y = 1.0f;
                        score_ += 200;
                        if (score_ > high_score_) high_score_ = score_;
                    }
                }
            }
        }
    }
}

void Game024LodeRunner::UpdateGuards(float dt) {
    for (int i = 0; i < MAX_GUARDS; ++i) {
        if (!guards_[i].active) continue;

        int gx = (int)roundf(guards_[i].x);
        int gy = (int)roundf(guards_[i].y);

        // 1. 被坑陷害困住逻辑
        if (guards_[i].trapped) {
            guards_[i].trap_timer -= dt;
            if (guards_[i].trap_timer <= 0.0f) {
                // 挣扎爬出坑穴
                guards_[i].trapped = false;
                guards_[i].y = (float)(gy - 1);
            }
            continue; // 被困期间无法追踪
        }

        // 2. 坠入砖坑判定
        if (grid_[gy][gx] == LODE_HOLE) {
            guards_[i].trapped = true;
            guards_[i].trap_timer = 3.5f;
            score_ += 80;
            if (score_ > high_score_) high_score_ = score_;
            continue;
        }

        // 3. 重力下坠
        if (CanFall(gx, gy)) {
            guards_[i].move_timer += dt;
            if (guards_[i].move_timer >= 0.12f) {
                guards_[i].move_timer = 0.0f;
                guards_[i].y += 1.0f;
            }
            continue;
        }

        // 4. 寻路追踪玩家
        guards_[i].move_timer += dt;
        if (guards_[i].move_timer >= 0.26f) {
            guards_[i].move_timer = 0.0f;

            int target_dx = 0;
            int target_dy = 0;

            if (guards_[i].y < player_y_ && grid_[gy][gx] == LODE_LADDER) {
                target_dy = 1; // 爬下梯子
            } else if (guards_[i].y > player_y_ && (grid_[gy][gx] == LODE_LADDER || (gy > 0 && grid_[gy - 1][gx] == LODE_LADDER))) {
                target_dy = -1; // 爬上梯子
            } else if (guards_[i].x < player_x_) {
                target_dx = 1;
            } else if (guards_[i].x > player_x_) {
                target_dx = -1;
            }

            int nx = gx + target_dx;
            int ny = gy + target_dy;

            if (target_dy != 0 && CanWalk(gx, ny)) {
                guards_[i].y = (float)ny;
            } else if (target_dx != 0 && CanWalk(nx, gy)) {
                guards_[i].x = (float)nx;
            }
        }

        // 5. 抓捕玩家致命判定 (若警卫被困在坑中，玩家踏头不致死)
        if (!guards_[i].trapped) {
            if ((int)roundf(guards_[i].x) == (int)roundf(player_x_) &&
                (int)roundf(guards_[i].y) == (int)roundf(player_y_)) {
                lives_--;
                if (lives_ <= 0) {
                    state_ = STATE_GAMEOVER;
                    state_timer_ = 0.0f;
                    return;
                } else {
                    player_x_ = 1.0f;
                    player_y_ = 14.0f;
                    return;
                }
            }
        }
    }
}

void Game024LodeRunner::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt > 0.05f) dt = 0.05f;
    state_timer_ += dt;

    if (state_ == STATE_TITLE) {
        if (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT)) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        if (state_timer_ > 0.5f && (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT))) {
            Reset();
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

        // 1. 挖掘操作 (A 键向左下掘坑，B 键向右下掘坑)
        if (keys_pressed & KEY_A) DigHole(-1);
        if (keys_pressed & KEY_B) DigHole(1);

        // 2. 玩家移动逻辑
        int px = (int)roundf(player_x_);
        int py = (int)roundf(player_y_);

        // 重力下落检测
        if (CanFall(px, py)) {
            move_timer_ += dt;
            if (move_timer_ >= 0.10f) {
                move_timer_ = 0.0f;
                player_y_ += 1.0f;
            }
        } else {
            // 平地与攀爬
            move_timer_ += dt;
            if (move_timer_ >= 0.16f) {
                int dx = 0;
                int dy = 0;
                if (keys_down & KEY_UP) dy = -1;
                else if (keys_down & KEY_DOWN) dy = 1;
                else if (keys_down & KEY_LEFT) dx = -1;
                else if (keys_down & KEY_RIGHT) dx = 1;

                if (dx != 0 || dy != 0) {
                    move_timer_ = 0.0f;
                    int nx = px + dx;
                    int ny = py + dy;

                    if (dy != 0) {
                        // 爬梯检测
                        if (grid_[py][px] == LODE_LADDER || (dy < 0 && ny >= 0 && grid_[ny][px] == LODE_LADDER) ||
                            (escape_ladder_revealed_ && px == 2 && ny >= 0 && ny <= 3)) {
                            if (CanWalk(px, ny)) player_y_ = (float)ny;
                        }
                    } else if (dx != 0) {
                        player_dir_ = (dx > 0) ? 1 : -1;
                        if (CanWalk(nx, py)) player_x_ = (float)nx;
                    }
                }
            }
        }

        // 3. 金矿收集与逃生梯激活检测
        bool all_collected = true;
        for (int i = 0; i < TOTAL_GOLDS; ++i) {
            if (!golds_[i].collected) {
                if ((int)roundf(player_x_) == golds_[i].x && (int)roundf(player_y_) == golds_[i].y) {
                    golds_[i].collected = true;
                    score_ += 150;
                    if (score_ > high_score_) high_score_ = score_;
                } else {
                    all_collected = false;
                }
            }
        }

        if (all_collected && !escape_ladder_revealed_) {
            escape_ladder_revealed_ = true;
            for (int y = 0; y <= 3; ++y) grid_[y][2] = LODE_LADDER;
            score_ += 300;
            if (score_ > high_score_) high_score_ = score_;
        }

        // 4. 逃出顶部通关判定
        if (escape_ladder_revealed_ && (int)roundf(player_x_) == 2 && player_y_ <= 0.5f) {
            state_ = STATE_VICTORY;
            state_timer_ = 0.0f;
            score_ += 1000;
            if (score_ > high_score_) high_score_ = score_;
        }

        // 5. 更新砖坑与警卫
        UpdateHoles(dt);
        UpdateGuards(dt);
    }
}

void Game024LodeRunner::Render(uint8_t* fb_rgb24) {
    memset(fb_rgb24, 0, 16 * 16 * 3);

    // 1. 绘制网格地层
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            uint8_t t = grid_[y][x];
            if (t == LODE_BRICK) {
                fb_rgb24[idx + 0] = 180; fb_rgb24[idx + 1] = 80;  fb_rgb24[idx + 2] = 40;  // 红砖土褐
            } else if (t == LODE_SOLID) {
                fb_rgb24[idx + 0] = 127; fb_rgb24[idx + 1] = 140; fb_rgb24[idx + 2] = 141; // 不破基岩灰
            } else if (t == LODE_LADDER) {
                fb_rgb24[idx + 0] = 52;  fb_rgb24[idx + 1] = 152; fb_rgb24[idx + 2] = 219; // 冰蓝爬梯
            } else if (t == LODE_BAR) {
                fb_rgb24[idx + 0] = 241; fb_rgb24[idx + 1] = 196; fb_rgb24[idx + 2] = 15;  // 悬挂横杠金
            } else if (t == LODE_HOLE) {
                fb_rgb24[idx + 0] = 30;  fb_rgb24[idx + 1] = 20;  fb_rgb24[idx + 2] = 15;  // 陷阱深坑
            }
        }
    }

    // 2. 绘制金矿 (闪耀金币 [255, 215, 0])
    for (int i = 0; i < TOTAL_GOLDS; ++i) {
        if (!golds_[i].collected) {
            int idx = (golds_[i].y * 16 + golds_[i].x) * 3;
            fb_rgb24[idx + 0] = 255; fb_rgb24[idx + 1] = 215; fb_rgb24[idx + 2] = 0;
        }
    }

    // 3. 绘制警卫 (猩红敌影 [231, 76, 60])
    for (int i = 0; i < MAX_GUARDS; ++i) {
        if (!guards_[i].active) continue;
        int gx = (int)roundf(guards_[i].x);
        int gy = (int)roundf(guards_[i].y);
        if (gx >= 0 && gx < 16 && gy >= 0 && gy < 16) {
            int idx = (gy * 16 + gx) * 3;
            if (guards_[i].trapped) {
                fb_rgb24[idx + 0] = 192; fb_rgb24[idx + 1] = 57; fb_rgb24[idx + 2] = 43; // 挣扎深红
            } else {
                fb_rgb24[idx + 0] = 231; fb_rgb24[idx + 1] = 76; fb_rgb24[idx + 2] = 60;
            }
        }
    }

    // 4. 绘制淘金者 (纯白先驱 [255, 255, 255])
    if (lives_ > 0) {
        int px = (int)roundf(player_x_);
        int py = (int)roundf(player_y_);
        if (px >= 0 && px < 16 && py >= 0 && py < 16) {
            int idx = (py * 16 + px) * 3;
            fb_rgb24[idx + 0] = 255; fb_rgb24[idx + 1] = 255; fb_rgb24[idx + 2] = 255;
        }
    }

    // 5. 顶部生命显示
    for (int i = 0; i < lives_; ++i) {
        int idx = (0 * 16 + i) * 3;
        fb_rgb24[idx + 0] = 255; fb_rgb24[idx + 1] = 255; fb_rgb24[idx + 2] = 255;
    }

    // 6. 胜负特效
    if (state_ == STATE_VICTORY) {
        for (int x = 0; x < 16; ++x) {
            int idx = (15 * 16 + x) * 3;
            fb_rgb24[idx + 0] = 46; fb_rgb24[idx + 1] = 204; fb_rgb24[idx + 2] = 113;
        }
    } else if (state_ == STATE_GAMEOVER) {
        for (int x = 0; x < 16; ++x) {
            int idx = (15 * 16 + x) * 3;
            fb_rgb24[idx + 0] = 231; fb_rgb24[idx + 1] = 76; fb_rgb24[idx + 2] = 60;
        }
    }
}

CartridgeStatus Game024LodeRunner::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.lives = lives_;
    st.state = (uint8_t)state_;

    int gathered = 0;
    for (int i = 0; i < TOTAL_GOLDS; ++i) {
        if (golds_[i].collected) gathered++;
    }
    st.progress = (uint8_t)((gathered * 100) / TOTAL_GOLDS);
    return st;
}

} // namespace arcade
