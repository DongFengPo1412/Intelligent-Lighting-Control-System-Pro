// game_029_slither_arena.cpp —— 像素贪吃蛇大作战 2016 核心实现
#include "game_029_slither_arena.h"
#include <string.h>
#include <stdlib.h>
#include <math.h>

namespace arcade {

static const int8_t DX[4] = {0, 1, 0, -1}; // UP, RIGHT, DOWN, LEFT
static const int8_t DY[4] = {-1, 0, 1, 0};

Game029SlitherArena::Game029SlitherArena()
    : state_(STATE_TITLE),
      player_len_(5),
      player_dir_(1),
      player_timer_(0.0f),
      player_boosting_(false),
      player_boost_cost_timer_(0.0f),
      lives_(3),
      ai_len_(5),
      ai_dir_(3),
      ai_timer_(0.0f),
      ai_alive_(true),
      ai_respawn_timer_(0.0f),
      kill_count_(0),
      score_(0),
      high_score_(0),
      state_timer_(0.0f) {
}

void Game029SlitherArena::SpawnRandomOrb() {
    for (int i = 0; i < MAX_ORBS; ++i) {
        if (!orbs_[i].active) {
            orbs_[i].active = true;
            orbs_[i].x = (int8_t)(1 + (rand() % 14));
            orbs_[i].y = (int8_t)(1 + (rand() % 14));
            orbs_[i].value = 1;
            break;
        }
    }
}

void Game029SlitherArena::DissolveSnake(bool is_player) {
    if (is_player) {
        for (int i = 0; i < player_len_; ++i) {
            for (int o = 0; o < MAX_ORBS; ++o) {
                if (!orbs_[o].active) {
                    orbs_[o].active = true;
                    orbs_[o].x = player_body_[i].x;
                    orbs_[o].y = player_body_[i].y;
                    orbs_[o].value = 2;
                    break;
                }
            }
        }
    } else {
        for (int i = 0; i < ai_len_; ++i) {
            for (int o = 0; o < MAX_ORBS; ++o) {
                if (!orbs_[o].active) {
                    orbs_[o].active = true;
                    orbs_[o].x = ai_body_[i].x;
                    orbs_[o].y = ai_body_[i].y;
                    orbs_[o].value = 2;
                    break;
                }
            }
        }
    }
}

void Game029SlitherArena::RespawnEnemyAI() {
    ai_alive_ = true;
    ai_len_ = 5;
    ai_dir_ = 3; // 向左
    ai_timer_ = 0.0f;
    int8_t start_x = 13;
    int8_t start_y = (rand() % 2 == 0) ? 3 : 12;
    for (int i = 0; i < ai_len_; ++i) {
        ai_body_[i].x = start_x + (int8_t)i;
        ai_body_[i].y = start_y;
    }
}

void Game029SlitherArena::InitArena() {
    player_len_ = 5;
    player_dir_ = 1; // 向右
    player_timer_ = 0.0f;
    player_boosting_ = false;
    player_boost_cost_timer_ = 0.0f;

    for (int i = 0; i < player_len_; ++i) {
        player_body_[i].x = (int8_t)(6 - i);
        player_body_[i].y = 7;
    }

    RespawnEnemyAI();

    for (int i = 0; i < MAX_ORBS; ++i) {
        orbs_[i].active = false;
    }
    for (int i = 0; i < 6; ++i) {
        SpawnRandomOrb();
    }
}

void Game029SlitherArena::Init() {
    Reset();
}

void Game029SlitherArena::Reset() {
    state_ = STATE_PLAYING;
    score_ = 0;
    lives_ = 3;
    kill_count_ = 0;
    state_timer_ = 0.0f;
    InitArena();
}

void Game029SlitherArena::UpdatePlayer(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    // 1. 转向控制 (不可直接调头)
    if ((keys_pressed & KEY_UP) && player_dir_ != 2) player_dir_ = 0;
    else if ((keys_pressed & KEY_RIGHT) && player_dir_ != 3) player_dir_ = 1;
    else if ((keys_pressed & KEY_DOWN) && player_dir_ != 0) player_dir_ = 2;
    else if ((keys_pressed & KEY_LEFT) && player_dir_ != 1) player_dir_ = 3;

    // 2. 超速冲刺控制 (按住 A 键)
    player_boosting_ = (keys_down & KEY_A) && (player_len_ > 3);
    float step_interval = player_boosting_ ? 0.08f : 0.16f;

    // 冲刺消耗尾段并掉落光子
    if (player_boosting_) {
        player_boost_cost_timer_ += dt;
        if (player_boost_cost_timer_ >= 0.35f) {
            player_boost_cost_timer_ = 0.0f;
            if (player_len_ > 3) {
                // 在蛇尾处掉落光子
                for (int o = 0; o < MAX_ORBS; ++o) {
                    if (!orbs_[o].active) {
                        orbs_[o].active = true;
                        orbs_[o].x = player_body_[player_len_ - 1].x;
                        orbs_[o].y = player_body_[player_len_ - 1].y;
                        orbs_[o].value = 1;
                        break;
                    }
                }
                player_len_--;
            }
        }
    }

    // 3. 步进位移
    player_timer_ += dt;
    if (player_timer_ >= step_interval) {
        player_timer_ = 0.0f;

        int8_t next_hx = player_body_[0].x + DX[player_dir_];
        int8_t next_hy = player_body_[0].y + DY[player_dir_];

        // 撞击四周墙壁致死
        if (next_hx < 0 || next_hx >= 16 || next_hy < 0 || next_hy >= 16) {
            DissolveSnake(true);
            lives_--;
            if (lives_ <= 0) {
                state_ = STATE_GAMEOVER;
                state_timer_ = 0.0f;
                return;
            } else {
                InitArena();
                return;
            }
        }

        // 撞击自身躯体致死
        for (int i = 1; i < player_len_; ++i) {
            if (next_hx == player_body_[i].x && next_hy == player_body_[i].y) {
                DissolveSnake(true);
                lives_--;
                if (lives_ <= 0) {
                    state_ = STATE_GAMEOVER;
                    state_timer_ = 0.0f;
                    return;
                } else {
                    InitArena();
                    return;
                }
            }
        }

        // 吞食光子
        bool grow = false;
        for (int o = 0; o < MAX_ORBS; ++o) {
            if (orbs_[o].active && orbs_[o].x == next_hx && orbs_[o].y == next_hy) {
                orbs_[o].active = false;
                grow = true;
                score_ += (orbs_[o].value * 30);
                if (score_ > high_score_) high_score_ = score_;
                SpawnRandomOrb();
                break;
            }
        }

        // 移动蛇身
        if (grow && player_len_ < MAX_LEN) {
            player_len_++;
        }
        for (int i = player_len_ - 1; i > 0; --i) {
            player_body_[i] = player_body_[i - 1];
        }
        player_body_[0].x = next_hx;
        player_body_[0].y = next_hy;
    }
}

void Game029SlitherArena::UpdateEnemyAI(float dt) {
    if (!ai_alive_) {
        ai_respawn_timer_ += dt;
        if (ai_respawn_timer_ >= 2.0f) {
            ai_respawn_timer_ = 0.0f;
            RespawnEnemyAI();
        }
        return;
    }

    ai_timer_ += dt;
    if (ai_timer_ >= 0.18f) {
        ai_timer_ = 0.0f;

        int8_t hx = ai_body_[0].x;
        int8_t hy = ai_body_[0].y;

        // 简单追光子与避障 AI
        // 寻找最近的活跃光子
        int8_t target_x = player_body_[player_len_ - 1].x;
        int8_t target_y = player_body_[player_len_ - 1].y;
        float min_dist = 999.0f;
        for (int o = 0; o < MAX_ORBS; ++o) {
            if (orbs_[o].active) {
                float dist = fabsf((float)(orbs_[o].x - hx)) + fabsf((float)(orbs_[o].y - hy));
                if (dist < min_dist) {
                    min_dist = dist;
                    target_x = orbs_[o].x;
                    target_y = orbs_[o].y;
                }
            }
        }

        // 评估 4 个方向可用度 (避免撞墙和撞自身/玩家身体)
        int best_dir = -1;
        float best_eval = 999.0f;

        for (int d = 0; d < 4; ++d) {
            // 不能直接掉头
            if ((d + 2) % 4 == ai_dir_) continue;

            int8_t nx = hx + DX[d];
            int8_t ny = hy + DY[d];

            // 越界排除
            if (nx < 0 || nx >= 16 || ny < 0 || ny >= 16) continue;

            // 撞自身排除
            bool self_hit = false;
            for (int s = 1; s < ai_len_; ++s) {
                if (nx == ai_body_[s].x && ny == ai_body_[s].y) {
                    self_hit = true; break;
                }
            }
            if (self_hit) continue;

            // 撞玩家身躯排除 (避免去撞玩家身体送死)
            bool p_hit = false;
            for (int p = 0; p < player_len_; ++p) {
                if (nx == player_body_[p].x && ny == player_body_[p].y) {
                    p_hit = true; break;
                }
            }
            if (p_hit) continue;

            float dist_to_target = fabsf((float)(nx - target_x)) + fabsf((float)(ny - target_y));
            if (dist_to_target < best_eval) {
                best_eval = dist_to_target;
                best_dir = d;
            }
        }

        if (best_dir != -1) {
            ai_dir_ = best_dir;
        }

        int8_t next_hx = hx + DX[ai_dir_];
        int8_t next_hy = hy + DY[ai_dir_];

        // 撞墙或自身解体
        if (next_hx < 0 || next_hx >= 16 || next_hy < 0 || next_hy >= 16) {
            DissolveSnake(false);
            ai_alive_ = false;
            return;
        }

        bool grow = false;
        for (int o = 0; o < MAX_ORBS; ++o) {
            if (orbs_[o].active && orbs_[o].x == next_hx && orbs_[o].y == next_hy) {
                orbs_[o].active = false;
                grow = true;
                SpawnRandomOrb();
                break;
            }
        }

        if (grow && ai_len_ < MAX_LEN) {
            ai_len_++;
        }
        for (int i = ai_len_ - 1; i > 0; --i) {
            ai_body_[i] = ai_body_[i - 1];
        }
        ai_body_[0].x = next_hx;
        ai_body_[0].y = next_hy;
    }
}

void Game029SlitherArena::CheckInterSnakeCollisions() {
    if (!ai_alive_) return;

    int8_t phx = player_body_[0].x;
    int8_t phy = player_body_[0].y;
    int8_t ahx = ai_body_[0].x;
    int8_t ahy = ai_body_[0].y;

    // 1. 玩家蛇头撞到 AI 蛇身 (玩家暴毙)
    for (int i = 1; i < ai_len_; ++i) {
        if (phx == ai_body_[i].x && phy == ai_body_[i].y) {
            DissolveSnake(true);
            lives_--;
            if (lives_ <= 0) {
                state_ = STATE_GAMEOVER;
                state_timer_ = 0.0f;
                return;
            } else {
                InitArena();
                return;
            }
        }
    }

    // 2. AI 蛇头撞到玩家蛇身 (AI 暴毙解体，玩家获得击杀大分与光子！)
    for (int i = 1; i < player_len_; ++i) {
        if (ahx == player_body_[i].x && ahy == player_body_[i].y) {
            DissolveSnake(false);
            ai_alive_ = false;
            kill_count_++;
            score_ += 500;
            if (score_ > high_score_) high_score_ = score_;

            // 击杀 3 条竞争蛇达成霸主胜利！
            if (kill_count_ >= 3 || player_len_ >= 16) {
                state_ = STATE_VICTORY;
                state_timer_ = 0.0f;
                return;
            }
            return;
        }
    }

    // 3. 双方蛇头对撞
    if (phx == ahx && phy == ahy) {
        if (player_len_ > ai_len_) {
            DissolveSnake(false);
            ai_alive_ = false;
            kill_count_++;
            score_ += 500;
            if (score_ > high_score_) high_score_ = score_;
        } else {
            DissolveSnake(true);
            lives_--;
            if (lives_ <= 0) {
                state_ = STATE_GAMEOVER;
                state_timer_ = 0.0f;
                return;
            } else {
                InitArena();
                return;
            }
        }
    }
}

void Game029SlitherArena::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
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

        UpdatePlayer(dt, keys_down, keys_pressed);
        UpdateEnemyAI(dt);
        CheckInterSnakeCollisions();

        if (player_len_ >= 16 || kill_count_ >= 3) {
            state_ = STATE_VICTORY;
            state_timer_ = 0.0f;
            score_ += 1500;
            if (score_ > high_score_) high_score_ = score_;
        }
    }
}

void Game029SlitherArena::Render(uint8_t* fb_rgb24) {
    memset(fb_rgb24, 0, 16 * 16 * 3);

    // 1. 竞技场幽暗六角微光地板
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            if ((x + y) % 4 == 0) {
                fb_rgb24[idx + 0] = 15; fb_rgb24[idx + 1] = 20; fb_rgb24[idx + 2] = 28;
            }
        }
    }

    // 2. 绘制散落的能量光子 (多阶闪耀黄白 [255, 230, 100])
    for (int i = 0; i < MAX_ORBS; ++i) {
        if (!orbs_[i].active) continue;
        int idx = (orbs_[i].y * 16 + orbs_[i].x) * 3;
        if (orbs_[i].value == 2) {
            // 残骸大型光子 (亮金粉)
            fb_rgb24[idx + 0] = 255; fb_rgb24[idx + 1] = 180; fb_rgb24[idx + 2] = 50;
        } else {
            fb_rgb24[idx + 0] = 241; fb_rgb24[idx + 1] = 196; fb_rgb24[idx + 2] = 15;
        }
    }

    // 3. 绘制竞争 AI 蛇 (猩红杀意 [231, 76, 60], 蛇头橙红 [255, 120, 80])
    if (ai_alive_) {
        for (int i = ai_len_ - 1; i >= 0; --i) {
            int idx = (ai_body_[i].y * 16 + ai_body_[i].x) * 3;
            if (i == 0) {
                fb_rgb24[idx + 0] = 255; fb_rgb24[idx + 1] = 120; fb_rgb24[idx + 2] = 80;
            } else {
                fb_rgb24[idx + 0] = 231; fb_rgb24[idx + 1] = 76;  fb_rgb24[idx + 2] = 60;
            }
        }
    }

    // 4. 绘制玩家蛇 (青翠幽蓝 [46, 204, 113], 冲刺时亮紫光流, 蛇头白金 [0, 255, 255])
    if (lives_ > 0) {
        for (int i = player_len_ - 1; i >= 0; --i) {
            int idx = (player_body_[i].y * 16 + player_body_[i].x) * 3;
            if (i == 0) {
                fb_rgb24[idx + 0] = 0; fb_rgb24[idx + 1] = 255; fb_rgb24[idx + 2] = 255; // 青蓝蛇头
            } else if (player_boosting_) {
                fb_rgb24[idx + 0] = 155; fb_rgb24[idx + 1] = 89; fb_rgb24[idx + 2] = 182; // 冲刺紫光
            } else {
                fb_rgb24[idx + 0] = 46; fb_rgb24[idx + 1] = 204; fb_rgb24[idx + 2] = 113; // 翠绿身躯
            }
        }
    }

    // 5. 顶部 HUD: 生命指示 (青点) 与击杀数 (金点)
    for (int i = 0; i < lives_; ++i) {
        int idx = (0 * 16 + i) * 3;
        fb_rgb24[idx + 0] = 0; fb_rgb24[idx + 1] = 255; fb_rgb24[idx + 2] = 255;
    }
    for (int i = 0; i < kill_count_; ++i) {
        int idx = (0 * 16 + (15 - i)) * 3;
        fb_rgb24[idx + 0] = 241; fb_rgb24[idx + 1] = 196; fb_rgb24[idx + 2] = 15;
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

CartridgeStatus Game029SlitherArena::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.lives = lives_;
    st.state = (uint8_t)state_;
    // 进度基于长度成长 (5 到 16)
    int prog = ((player_len_ - 5) * 100) / 11;
    if (prog < 0) prog = 0;
    if (prog > 100) prog = 100;
    st.progress = (uint8_t)prog;
    return st;
}

} // namespace arcade
