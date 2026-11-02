// game_021_dig_dug.cpp —— 掘地打气人 1982 核心实现
#include "game_021_dig_dug.h"
#include <string.h>
#include <stdlib.h>
#include <math.h>

namespace arcade {

static const int DX[4] = {0, 1, 0, -1}; // UP, RIGHT, DOWN, LEFT
static const int DY[4] = {-1, 0, 1, 0};

Game021DigDug::Game021DigDug()
    : state_(STATE_TITLE),
      player_x_(7),
      player_y_(7),
      player_dir_(1),
      player_lives_(3),
      move_timer_(0.0f),
      score_(0),
      high_score_(0),
      state_timer_(0.0f) {
    harpoon_.active = false;
}

void Game021DigDug::InitLevel() {
    // 1. 初始化地表与泥土网格
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (y == 0) {
                grid_[y][x] = TILE_EMPTY; // 地表蓝天
            } else {
                grid_[y][x] = TILE_DIRT;  // 地下泥土
            }
        }
    }

    // 2. 玩家初始出生竖井与小室
    player_x_ = 7;
    player_y_ = 7;
    player_dir_ = 1;
    move_timer_ = 0.0f;
    for (int y = 5; y <= 7; ++y) {
        grid_[y][7] = TILE_EMPTY;
    }
    grid_[7][6] = TILE_EMPTY;
    grid_[7][8] = TILE_EMPTY;

    // 3. 怪物洞窟挖掘与初始化
    // 怪物 0: 红色波卡 (左上小室)
    for (int x = 2; x <= 4; ++x) grid_[3][x] = TILE_EMPTY;
    enemies_[0].active = true;
    enemies_[0].type = ENEMY_POOKA;
    enemies_[0].x = 3.0f;
    enemies_[0].y = 3.0f;
    enemies_[0].dir = 1;
    enemies_[0].inflate_stage = 0;
    enemies_[0].inflate_timer = 0.0f;
    enemies_[0].move_timer = 0.0f;
    enemies_[0].is_ghost = false;
    enemies_[0].firing = false;
    enemies_[0].fire_timer = 0.0f;

    // 怪物 1: 喷火飞加 (右下小室)
    for (int x = 11; x <= 13; ++x) grid_[11][x] = TILE_EMPTY;
    enemies_[1].active = true;
    enemies_[1].type = ENEMY_FYGAR;
    enemies_[1].x = 12.0f;
    enemies_[1].y = 11.0f;
    enemies_[1].dir = 3;
    enemies_[1].inflate_stage = 0;
    enemies_[1].inflate_timer = 0.0f;
    enemies_[1].move_timer = 0.0f;
    enemies_[1].is_ghost = false;
    enemies_[1].firing = false;
    enemies_[1].fire_timer = 0.0f;

    // 怪物 2: 红色波卡 (左下小室)
    for (int x = 3; x <= 5; ++x) grid_[12][x] = TILE_EMPTY;
    enemies_[2].active = true;
    enemies_[2].type = ENEMY_POOKA;
    enemies_[2].x = 4.0f;
    enemies_[2].y = 12.0f;
    enemies_[2].dir = 1;
    enemies_[2].inflate_stage = 0;
    enemies_[2].inflate_timer = 0.0f;
    enemies_[2].move_timer = 0.0f;
    enemies_[2].is_ghost = false;
    enemies_[2].firing = false;
    enemies_[2].fire_timer = 0.0f;

    // 怪物 3: 喷火飞加 (右上小室)
    for (int x = 10; x <= 12; ++x) grid_[4][x] = TILE_EMPTY;
    enemies_[3].active = true;
    enemies_[3].type = ENEMY_FYGAR;
    enemies_[3].x = 11.0f;
    enemies_[3].y = 4.0f;
    enemies_[3].dir = 3;
    enemies_[3].inflate_stage = 0;
    enemies_[3].inflate_timer = 0.0f;
    enemies_[3].move_timer = 0.0f;
    enemies_[3].is_ghost = false;
    enemies_[3].firing = false;
    enemies_[3].fire_timer = 0.0f;

    // 4. 布置两颗摇摇欲坠的巨石
    rocks_[0].active = true;
    rocks_[0].x = 4;
    rocks_[0].y = 2;
    rocks_[0].falling = false;
    rocks_[0].shake_timer = 0.0f;
    grid_[2][4] = TILE_ROCK;

    rocks_[1].active = true;
    rocks_[1].x = 12;
    rocks_[1].y = 8;
    rocks_[1].falling = false;
    rocks_[1].shake_timer = 0.0f;
    grid_[8][12] = TILE_ROCK;

    harpoon_.active = false;
}

void Game021DigDug::Init() {
    Reset();
}

void Game021DigDug::Reset() {
    state_ = STATE_PLAYING;
    score_ = 0;
    player_lives_ = 3;
    state_timer_ = 0.0f;
    InitLevel();
}

void Game021DigDug::PumpTarget() {
    if (!harpoon_.active) {
        // 尝试向前发射鱼叉气管 (最多检测 2 格)
        int hx = player_x_;
        int hy = player_y_;
        for (int step = 1; step <= 2; ++step) {
            hx += DX[player_dir_];
            hy += DY[player_dir_];
            if (hx < 0 || hx >= 16 || hy < 0 || hy >= 16) break;

            // 撞击泥土则停住 (只能在已挖掘隧道中穿过)
            if (grid_[hy][hx] == TILE_DIRT || grid_[hy][hx] == TILE_ROCK) break;

            // 检测是否刺中怪物
            for (int i = 0; i < MAX_ENEMIES; ++i) {
                if (enemies_[i].active) {
                    int ex = (int)roundf(enemies_[i].x);
                    int ey = (int)roundf(enemies_[i].y);
                    if (ex == hx && ey == hy) {
                        harpoon_.active = true;
                        harpoon_.origin_x = player_x_;
                        harpoon_.origin_y = player_y_;
                        harpoon_.dir = player_dir_;
                        harpoon_.target_enemy_idx = i;
                        harpoon_.timer = 0.8f;
                        enemies_[i].inflate_stage = 1;
                        enemies_[i].inflate_timer = 0.9f;
                        return;
                    }
                }
            }
        }
    } else {
        // 已经锁定目标，连续打气
        int tidx = harpoon_.target_enemy_idx;
        if (tidx >= 0 && tidx < MAX_ENEMIES && enemies_[tidx].active) {
            enemies_[tidx].inflate_stage++;
            enemies_[tidx].inflate_timer = 0.9f;
            harpoon_.timer = 0.8f;

            if (enemies_[tidx].inflate_stage >= 3) {
                // 膨胀引爆！
                enemies_[tidx].active = false;
                harpoon_.active = false;
                score_ += 200;
                if (score_ > high_score_) high_score_ = score_;
            }
        } else {
            harpoon_.active = false;
        }
    }
}

void Game021DigDug::UpdateRocks(float dt) {
    for (int i = 0; i < MAX_ROCKS; ++i) {
        if (!rocks_[i].active) continue;

        int rx = rocks_[i].x;
        int ry = rocks_[i].y;

        if (!rocks_[i].falling) {
            // 检测下方是否有空洞诱发下坠
            if (ry < 15 && grid_[ry + 1][rx] == TILE_EMPTY) {
                rocks_[i].shake_timer += dt;
                if (rocks_[i].shake_timer >= 0.7f) {
                    rocks_[i].falling = true;
                    grid_[ry][rx] = TILE_EMPTY; // 巨石脱离原位
                }
            } else {
                rocks_[i].shake_timer = 0.0f;
            }
        } else {
            // 巨石重力下坠
            rocks_[i].shake_timer += dt;
            if (rocks_[i].shake_timer >= 0.12f) {
                rocks_[i].shake_timer = 0.0f;
                int next_y = ry + 1;

                if (next_y < 16 && grid_[next_y][rx] != TILE_DIRT && grid_[next_y][rx] != TILE_ROCK) {
                    grid_[ry][rx] = TILE_EMPTY;
                    rocks_[i].y = next_y;
                    grid_[next_y][rx] = TILE_ROCK;

                    // 碾压判定: 砸死怪物
                    for (int e = 0; e < MAX_ENEMIES; ++e) {
                        if (enemies_[e].active) {
                            int ex = (int)roundf(enemies_[e].x);
                            int ey = (int)roundf(enemies_[e].y);
                            if (ex == rx && ey == next_y) {
                                enemies_[e].active = false;
                                score_ += 500;
                                if (score_ > high_score_) high_score_ = score_;
                            }
                        }
                    }

                    // 碾压判定: 砸死玩家
                    if (player_x_ == rx && player_y_ == next_y) {
                        player_lives_--;
                        if (player_lives_ <= 0) {
                            state_ = STATE_GAMEOVER;
                            state_timer_ = 0.0f;
                            return;
                        } else {
                            player_x_ = 7;
                            player_y_ = 7;
                        }
                    }
                } else {
                    // 触底或撞击泥土破碎
                    rocks_[i].active = false;
                }
            }
        }
    }
}

void Game021DigDug::UpdateEnemies(float dt) {
    bool any_alive = false;

    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;
        any_alive = true;

        // 1. 膨胀状态管理 (若未打气则漏气缩小)
        if (enemies_[i].inflate_stage > 0) {
            enemies_[i].inflate_timer -= dt;
            if (enemies_[i].inflate_timer <= 0.0f) {
                enemies_[i].inflate_stage--;
                enemies_[i].inflate_timer = 0.6f;
                if (enemies_[i].inflate_stage == 0 && harpoon_.active && harpoon_.target_enemy_idx == i) {
                    harpoon_.active = false;
                }
            }
            continue; // 膨胀中的怪物定身无法移动或攻击
        }

        // 2. 飞加喷火逻辑
        if (enemies_[i].type == ENEMY_FYGAR) {
            enemies_[i].fire_timer += dt;
            if (!enemies_[i].firing && enemies_[i].fire_timer > 3.5f) {
                // 预警喷火
                enemies_[i].firing = true;
                enemies_[i].fire_timer = 0.0f;
            } else if (enemies_[i].firing) {
                if (enemies_[i].fire_timer > 1.2f) {
                    enemies_[i].firing = false;
                    enemies_[i].fire_timer = 0.0f;
                } else {
                    // 火焰向前喷射 2 格伤害判定
                    int fx = (int)roundf(enemies_[i].x);
                    int fy = (int)roundf(enemies_[i].y);
                    int fdir = enemies_[i].dir;
                    for (int step = 1; step <= 2; ++step) {
                        fx += DX[fdir];
                        fy += DY[fdir];
                        if (fx < 0 || fx >= 16 || fy < 0 || fy >= 16) break;
                        if (grid_[fy][fx] == TILE_DIRT) break; // 泥土阻挡火焰

                        if (player_x_ == fx && player_y_ == fy) {
                            player_lives_--;
                            if (player_lives_ <= 0) {
                                state_ = STATE_GAMEOVER;
                                state_timer_ = 0.0f;
                                return;
                            } else {
                                player_x_ = 7;
                                player_y_ = 7;
                            }
                        }
                    }
                }
            }
        }

        // 3. 移动巡逻与追踪
        enemies_[i].move_timer += dt;
        if (enemies_[i].move_timer >= 0.28f) {
            enemies_[i].move_timer = 0.0f;
            int ex = (int)roundf(enemies_[i].x);
            int ey = (int)roundf(enemies_[i].y);

            // 优先沿已挖掘的隧道走
            int next_x = ex + DX[enemies_[i].dir];
            int next_y = ey + DY[enemies_[i].dir];

            bool can_walk = (next_x >= 0 && next_x < 16 && next_y >= 0 && next_y < 16 &&
                             grid_[next_y][next_x] == TILE_EMPTY);

            if (!can_walk) {
                // 随机寻找可用通道
                int new_dir = rand() % 4;
                for (int t = 0; t < 4; ++t) {
                    int d = (new_dir + t) % 4;
                    int nx = ex + DX[d];
                    int ny = ey + DY[d];
                    if (nx >= 0 && nx < 16 && ny >= 0 && ny < 16 && grid_[ny][nx] == TILE_EMPTY) {
                        enemies_[i].dir = d;
                        next_x = nx;
                        next_y = ny;
                        can_walk = true;
                        break;
                    }
                }
            }

            if (can_walk) {
                enemies_[i].x = (float)next_x;
                enemies_[i].y = (float)next_y;
            }

            // 接触玩家致命碰撞
            if ((int)roundf(enemies_[i].x) == player_x_ && (int)roundf(enemies_[i].y) == player_y_) {
                player_lives_--;
                if (player_lives_ <= 0) {
                    state_ = STATE_GAMEOVER;
                    state_timer_ = 0.0f;
                    return;
                } else {
                    player_x_ = 7;
                    player_y_ = 7;
                }
            }
        }
    }

    // 全灭通关判定
    if (!any_alive) {
        state_ = STATE_VICTORY;
        state_timer_ = 0.0f;
    }
}

void Game021DigDug::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
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

        // 1. 鱼叉生命期衰减
        if (harpoon_.active) {
            harpoon_.timer -= dt;
            if (harpoon_.timer <= 0.0f) {
                harpoon_.active = false;
            }
        }

        // 2. 按键 A 发射气管或打气充能
        if (keys_pressed & KEY_A) {
            PumpTarget();
        }

        // 3. 玩家移动与挖掘
        move_timer_ += dt;
        if (move_timer_ >= 0.16f) {
            int target_dir = -1;
            if (keys_down & KEY_UP) target_dir = 0;
            else if (keys_down & KEY_RIGHT) target_dir = 1;
            else if (keys_down & KEY_DOWN) target_dir = 2;
            else if (keys_down & KEY_LEFT) target_dir = 3;

            if (target_dir != -1) {
                move_timer_ = 0.0f;
                player_dir_ = target_dir;
                int nx = player_x_ + DX[target_dir];
                int ny = player_y_ + DY[target_dir];

                if (nx >= 0 && nx < 16 && ny >= 0 && ny < 16) {
                    // 不能直接穿透巨石
                    if (grid_[ny][nx] != TILE_ROCK) {
                        player_x_ = nx;
                        player_y_ = ny;

                        // 掘开泥土开辟新隧道
                        if (grid_[ny][nx] == TILE_DIRT) {
                            grid_[ny][nx] = TILE_EMPTY;
                            score_ += 10;
                            if (score_ > high_score_) high_score_ = score_;
                        }
                    }
                }
            }
        }

        // 4. 更新巨石与怪物
        UpdateRocks(dt);
        UpdateEnemies(dt);
    }
}

void Game021DigDug::Render(uint8_t* fb_rgb24) {
    memset(fb_rgb24, 0, 16 * 16 * 3);

    // 1. 绘制网格背景
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            if (grid_[y][x] == TILE_EMPTY) {
                if (y == 0) {
                    fb_rgb24[idx + 0] = 52;  fb_rgb24[idx + 1] = 152; fb_rgb24[idx + 2] = 219; // 蓝天
                } else {
                    fb_rgb24[idx + 0] = 18;  fb_rgb24[idx + 1] = 18;  fb_rgb24[idx + 2] = 22;  // 隧道深黑
                }
            } else if (grid_[y][x] == TILE_DIRT) {
                // 地层深度渐变色
                if (y <= 4) {
                    fb_rgb24[idx + 0] = 160; fb_rgb24[idx + 1] = 90;  fb_rgb24[idx + 2] = 40;  // 浅红褐
                } else if (y <= 9) {
                    fb_rgb24[idx + 0] = 130; fb_rgb24[idx + 1] = 70;  fb_rgb24[idx + 2] = 25;  // 赭石褐
                } else {
                    fb_rgb24[idx + 0] = 95;  fb_rgb24[idx + 1] = 48;  fb_rgb24[idx + 2] = 18;  // 深岩褐
                }
            } else if (grid_[y][x] == TILE_ROCK) {
                fb_rgb24[idx + 0] = 149; fb_rgb24[idx + 1] = 165; fb_rgb24[idx + 2] = 166; // 巨石岩灰
            }
        }
    }

    // 2. 绘制怪物
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;
        int ex = (int)roundf(enemies_[i].x);
        int ey = (int)roundf(enemies_[i].y);
        if (ex < 0 || ex >= 16 || ey < 0 || ey >= 16) continue;

        int idx = (ey * 16 + ex) * 3;
        if (enemies_[i].inflate_stage > 0) {
            // 膨胀阶段亮黄白色闪烁
            fb_rgb24[idx + 0] = 255;
            fb_rgb24[idx + 1] = (enemies_[i].inflate_stage == 1) ? 220 : 100;
            fb_rgb24[idx + 2] = (enemies_[i].inflate_stage == 1) ? 50 : 200;
        } else if (enemies_[i].type == ENEMY_POOKA) {
            fb_rgb24[idx + 0] = 231; fb_rgb24[idx + 1] = 76;  fb_rgb24[idx + 2] = 60;  // 猩红波卡
        } else {
            fb_rgb24[idx + 0] = 46;  fb_rgb24[idx + 1] = 204; fb_rgb24[idx + 2] = 113; // 翠绿飞加
        }

        // 喷火火焰
        if (enemies_[i].type == ENEMY_FYGAR && enemies_[i].firing) {
            int fx = ex;
            int fy = ey;
            for (int step = 1; step <= 2; ++step) {
                fx += DX[enemies_[i].dir];
                fy += DY[enemies_[i].dir];
                if (fx >= 0 && fx < 16 && fy >= 0 && fy < 16 && grid_[fy][fx] == TILE_EMPTY) {
                    int fidx = (fy * 16 + fx) * 3;
                    fb_rgb24[fidx + 0] = 243; fb_rgb24[fidx + 1] = 156; fb_rgb24[fidx + 2] = 18; // 炽热橙火
                }
            }
        }
    }

    // 3. 绘制鱼叉气管连线
    if (harpoon_.active) {
        int hx = player_x_ + DX[player_dir_];
        int hy = player_y_ + DY[player_dir_];
        if (hx >= 0 && hx < 16 && hy >= 0 && hy < 16) {
            int idx = (hy * 16 + hx) * 3;
            fb_rgb24[idx + 0] = 255; fb_rgb24[idx + 1] = 255; fb_rgb24[idx + 2] = 255; // 纯白充气软管
        }
    }

    // 4. 绘制掘地打气人 (纯白与亮蓝交织 [255, 255, 255])
    if (player_lives_ > 0) {
        int idx = (player_y_ * 16 + player_x_) * 3;
        fb_rgb24[idx + 0] = 255; fb_rgb24[idx + 1] = 255; fb_rgb24[idx + 2] = 255;
    }

    // 5. 顶部 HUD: 剩余生命 (蓝天右侧显示白点)
    for (int i = 0; i < player_lives_; ++i) {
        int idx = (0 * 16 + (15 - i)) * 3;
        fb_rgb24[idx + 0] = 255; fb_rgb24[idx + 1] = 255; fb_rgb24[idx + 2] = 255;
    }

    // 6. 胜利与失败特效
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

CartridgeStatus Game021DigDug::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.lives = player_lives_;
    st.state = (uint8_t)state_;

    int alive = 0;
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (enemies_[i].active) alive++;
    }
    st.progress = (uint8_t)(((MAX_ENEMIES - alive) * 100) / MAX_ENEMIES);
    return st;
}

} // namespace arcade
