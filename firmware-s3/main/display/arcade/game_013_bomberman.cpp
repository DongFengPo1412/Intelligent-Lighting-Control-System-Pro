// game_013_bomberman.cpp —— 像素炸弹人 1983 核心实现
#include "game_013_bomberman.h"
#include <string.h>
#include <math.h>
#include <stdlib.h>

namespace arcade {

Game013Bomberman::Game013Bomberman()
    : state_(STATE_TITLE),
      player_x_(1.0f),
      player_y_(1.0f),
      lives_(3),
      score_(0),
      high_score_(0),
      state_timer_(0.0f),
      flame_range_(2),
      num_flames_(0),
      remaining_enemies_(kNumEnemies) {
    bomb_.active = false;
}

void Game013Bomberman::ResetPlayer() {
    player_x_ = 1.0f;
    player_y_ = 1.0f;
    bomb_.active = false;
    num_flames_ = 0;
}

void Game013Bomberman::Init() {
    Reset();
}

void Game013Bomberman::Reset() {
    state_ = STATE_PLAYING;
    score_ = 0;
    lives_ = 3;
    state_timer_ = 0.0f;
    flame_range_ = 2;
    num_flames_ = 0;
    remaining_enemies_ = kNumEnemies;

    // 1. 初始化地图网格
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (x == 0 || x == 15 || y == 0 || y == 15) {
                map_[y][x] = TILE_HARD_WALL;
            } else if (x % 2 == 0 && y % 2 == 0) {
                map_[y][x] = TILE_HARD_WALL; // 经典支柱
            } else {
                // 玩家出生点净空
                if ((x <= 2 && y <= 2)) {
                    map_[y][x] = TILE_EMPTY;
                } else if ((x == 13 && y == 1) || (x == 1 && y == 13)) {
                    map_[y][x] = TILE_EMPTY; // 敌怪出生点净空
                } else {
                    // 放置可炸毁软砖 (~45% 概率)
                    map_[y][x] = ((x * 7 + y * 13) % 10 < 5) ? TILE_SOFT_BRICK : TILE_EMPTY;
                }
            }
        }
    }

    // 2. 初始化巡逻敌怪
    enemies_[0].alive = true;
    enemies_[0].x = 13.0f; enemies_[0].y = 1.0f;
    enemies_[0].dir_x = -1; enemies_[0].dir_y = 0;
    enemies_[0].speed = 2.4f;

    enemies_[1].alive = true;
    enemies_[1].x = 1.0f; enemies_[1].y = 13.0f;
    enemies_[1].dir_x = 0; enemies_[1].dir_y = -1;
    enemies_[1].speed = 2.2f;

    ResetPlayer();
}

bool Game013Bomberman::IsWalkable(int gx, int gy, bool allow_bomb) const {
    if (gx < 0 || gx >= 16 || gy < 0 || gy >= 16) return false;
    if (map_[gy][gx] == TILE_HARD_WALL || map_[gy][gx] == TILE_SOFT_BRICK) return false;
    if (!allow_bomb && bomb_.active && bomb_.gx == gx && bomb_.gy == gy) return false;
    return true;
}

void Game013Bomberman::ExplodeBomb() {
    bomb_.active = false;
    num_flames_ = 0;

    auto add_flame = [this](int fx, int fy) {
        if (num_flames_ < kMaxFlames) {
            flames_[num_flames_].x = fx;
            flames_[num_flames_].y = fy;
            flames_[num_flames_].timer = 0.45f;
            num_flames_++;
        }
    };

    int cx = bomb_.gx;
    int cy = bomb_.gy;
    add_flame(cx, cy);

    // 四向十字爆破
    const int dxs[4] = {0, 0, -1, 1};
    const int dys[4] = {-1, 1, 0, 0};

    for (int i = 0; i < 4; ++i) {
        for (int step = 1; step <= bomb_.range; ++step) {
            int tx = cx + dxs[i] * step;
            int ty = cy + dys[i] * step;

            if (tx < 0 || tx >= 16 || ty < 0 || ty >= 16) break;
            if (map_[ty][tx] == TILE_HARD_WALL) break; // 硬墙阻隔

            if (map_[ty][tx] == TILE_SOFT_BRICK) {
                // 炸碎软砖
                map_[ty][tx] = TILE_EMPTY;
                add_flame(tx, ty);
                score_ += 20;
                if (score_ > high_score_) high_score_ = score_;
                break; // 烈焰被软砖吸收停滞
            }

            // 空地继续穿透
            add_flame(tx, ty);
        }
    }

    // 伤害判定
    for (int f = 0; f < num_flames_; ++f) {
        int fx = flames_[f].x;
        int fy = flames_[f].y;

        // 烈焰伤及玩家
        int px = (int)roundf(player_x_);
        int py = (int)roundf(player_y_);
        if (px == fx && py == fy) {
            if (lives_ > 0) lives_--;
            if (lives_ == 0) {
                state_ = STATE_GAMEOVER;
                state_timer_ = 0.0f;
                return;
            } else {
                ResetPlayer();
                return;
            }
        }

        // 烈焰消灭敌怪
        for (int e = 0; e < kNumEnemies; ++e) {
            if (enemies_[e].alive) {
                int ex = (int)roundf(enemies_[e].x);
                int ey = (int)roundf(enemies_[e].y);
                if (ex == fx && ey == fy) {
                    enemies_[e].alive = false;
                    remaining_enemies_--;
                    score_ += 100;
                    if (score_ > high_score_) high_score_ = score_;

                    if (remaining_enemies_ <= 0) {
                        state_ = STATE_VICTORY;
                        state_timer_ = 0.0f;
                        return;
                    }
                }
            }
        }
    }
}

void Game013Bomberman::MoveEnemy(BomberEnemy& e, float dt) {
    if (!e.alive) return;

    int cur_gx = (int)roundf(e.x);
    int cur_gy = (int)roundf(e.y);
    float dist = fabsf(e.x - (float)cur_gx) + fabsf(e.y - (float)cur_gy);

    if (dist < 0.12f) {
        e.x = (float)cur_gx;
        e.y = (float)cur_gy;

        // 尝试维持当前方向，遇墙拐弯
        int next_gx = cur_gx + e.dir_x;
        int next_gy = cur_gy + e.dir_y;

        if (!IsWalkable(next_gx, next_gy, false)) {
            // 随机寻找可用方向
            const int dxs[4] = {0, 0, -1, 1};
            const int dys[4] = {-1, 1, 0, 0};
            int valid_dirs[4];
            int valid_cnt = 0;
            for (int i = 0; i < 4; ++i) {
                if (IsWalkable(cur_gx + dxs[i], cur_gy + dys[i], false)) {
                    valid_dirs[valid_cnt++] = i;
                }
            }
            if (valid_cnt > 0) {
                int pick = valid_dirs[rand() % valid_cnt];
                e.dir_x = dxs[pick];
                e.dir_y = dys[pick];
            } else {
                e.dir_x = -e.dir_x;
                e.dir_y = -e.dir_y;
            }
        }
    }

    e.x += e.dir_x * e.speed * dt;
    e.y += e.dir_y * e.speed * dt;
}

void Game013Bomberman::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt > 0.05f) dt = 0.05f;
    state_timer_ += dt;

    if (state_ == STATE_TITLE) {
        if (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP | KEY_DOWN)) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        if (state_timer_ > 0.5f && (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP | KEY_DOWN))) {
            Reset();
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

        // 1. 玩家移动
        const float player_speed = 4.2f;
        float move_x = 0.0f, move_y = 0.0f;
        if (keys_down & KEY_UP) move_y = -player_speed * dt;
        else if (keys_down & KEY_DOWN) move_y = player_speed * dt;
        else if (keys_down & KEY_LEFT) move_x = -player_speed * dt;
        else if (keys_down & KEY_RIGHT) move_x = player_speed * dt;

        if (move_x != 0.0f || move_y != 0.0f) {
            float new_x = player_x_ + move_x;
            float new_y = player_y_ + move_y;

            bool can_move = true;
            const float r = 0.35f;
            const float offsets[4][2] = {{-r, -r}, {r, -r}, {-r, r}, {r, r}};
            bool on_own_bomb = bomb_.active && ((int)roundf(player_x_) == bomb_.gx) && ((int)roundf(player_y_) == bomb_.gy);

            for (int i = 0; i < 4; ++i) {
                int cx = (int)roundf(new_x + offsets[i][0]);
                int cy = (int)roundf(new_y + offsets[i][1]);
                if (!IsWalkable(cx, cy, on_own_bomb)) {
                    can_move = false;
                    break;
                }
            }
            if (can_move) {
                player_x_ = new_x;
                player_y_ = new_y;
            }
        }

        // 2. 放置炸弹
        if ((keys_pressed & (KEY_A | KEY_B)) && !bomb_.active) {
            int bx = (int)roundf(player_x_);
            int by = (int)roundf(player_y_);
            bomb_.active = true;
            bomb_.gx = bx;
            bomb_.gy = by;
            bomb_.timer = 2.0f;
            bomb_.range = flame_range_;
        }

        // 3. 炸弹倒计时
        if (bomb_.active) {
            bomb_.timer -= dt;
            if (bomb_.timer <= 0.0f) {
                ExplodeBomb();
            }
        }

        // 4. 烈焰残留消退
        for (int f = 0; f < num_flames_; ++f) {
            flames_[f].timer -= dt;
        }
        // 清除过期火焰
        int write_idx = 0;
        for (int f = 0; f < num_flames_; ++f) {
            if (flames_[f].timer > 0.0f) {
                flames_[write_idx++] = flames_[f];
            }
        }
        num_flames_ = write_idx;

        // 5. 敌怪移动与玩家碰撞
        for (int e = 0; e < kNumEnemies; ++e) {
            if (enemies_[e].alive) {
                MoveEnemy(enemies_[e], dt);

                // 触碰玩家致死
                if (fabsf(player_x_ - enemies_[e].x) < 0.75f && fabsf(player_y_ - enemies_[e].y) < 0.75f) {
                    if (lives_ > 0) lives_--;
                    if (lives_ == 0) {
                        state_ = STATE_GAMEOVER;
                        state_timer_ = 0.0f;
                        return;
                    } else {
                        ResetPlayer();
                        return;
                    }
                }
            }
        }
    }
}

void Game013Bomberman::Render(uint8_t* fb_rgb24) {
    memset(fb_rgb24, 0, 16 * 16 * 3);

    // 1. 绘制地面与墙壁
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            if (map_[y][x] == TILE_HARD_WALL) {
                // 不可破坏硬柱: 青灰深色
                fb_rgb24[idx + 0] = 52;  fb_rgb24[idx + 1] = 73;  fb_rgb24[idx + 2] = 94;
            } else if (map_[y][x] == TILE_SOFT_BRICK) {
                // 可炸软砖: 红褐砖块
                fb_rgb24[idx + 0] = 211; fb_rgb24[idx + 1] = 84;  fb_rgb24[idx + 2] = 0;
            } else {
                // 走廊草坪底色: 暗草绿
                fb_rgb24[idx + 0] = 20;  fb_rgb24[idx + 1] = 90;  fb_rgb24[idx + 2] = 50;
            }
        }
    }

    // 2. 绘制炸弹 (黑色带红闪光灯)
    if (bomb_.active) {
        int idx = (bomb_.gy * 16 + bomb_.gx) * 3;
        bool tick = ((int)(bomb_.timer * 8.0f) % 2 == 0);
        fb_rgb24[idx + 0] = tick ? 231 : 20;
        fb_rgb24[idx + 1] = tick ? 76  : 20;
        fb_rgb24[idx + 2] = tick ? 60  : 20;
    }

    // 3. 绘制爆破十字烈焰 (明亮橙黄火光)
    for (int f = 0; f < num_flames_; ++f) {
        int idx = (flames_[f].y * 16 + flames_[f].x) * 3;
        fb_rgb24[idx + 0] = 255; fb_rgb24[idx + 1] = 200; fb_rgb24[idx + 2] = 0;
    }

    // 4. 绘制敌怪 (粉红气球怪)
    for (int e = 0; e < kNumEnemies; ++e) {
        if (enemies_[e].alive) {
            int ex = (int)roundf(enemies_[e].x);
            int ey = (int)roundf(enemies_[e].y);
            if (ex >= 0 && ex < 16 && ey >= 0 && ey < 16) {
                int idx = (ey * 16 + ex) * 3;
                fb_rgb24[idx + 0] = 255; fb_rgb24[idx + 1] = 105; fb_rgb24[idx + 2] = 180;
            }
        }
    }

    // 5. 绘制炸弹人 (纯白身体 + 蓝面罩)
    int px = (int)roundf(player_x_);
    int py = (int)roundf(player_y_);
    if (px >= 0 && px < 16 && py >= 0 && py < 16) {
        int idx = (py * 16 + px) * 3;
        fb_rgb24[idx + 0] = 255;
        fb_rgb24[idx + 1] = 255;
        fb_rgb24[idx + 2] = 255;
    }

    // 6. 顶部生命显示 (y=0 红色点阵)
    for (int i = 0; i < lives_; ++i) {
        int idx = (0 * 16 + (i * 2 + 1)) * 3;
        fb_rgb24[idx + 0] = 231; fb_rgb24[idx + 1] = 76; fb_rgb24[idx + 2] = 60;
    }

    // 7. 特效渲染
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

CartridgeStatus Game013Bomberman::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.lives = lives_;
    st.state = (uint8_t)state_;
    st.progress = (remaining_enemies_ == 0) ? 100 : (uint8_t)(((kNumEnemies - remaining_enemies_) * 100) / kNumEnemies);
    return st;
}

} // namespace arcade
