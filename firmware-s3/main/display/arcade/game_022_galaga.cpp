// game_022_galaga.cpp —— 星际双子战机 1981 核心实现
#include "game_022_galaga.h"
#include <string.h>
#include <math.h>
#include <stdlib.h>

namespace arcade {

Game022Galaga::Game022Galaga()
    : state_(STATE_TITLE),
      player_x_(7.0f),
      lives_(3),
      is_dual_(false),
      is_being_captured_(false),
      capture_timer_(0.0f),
      shoot_cooldown_(0.0f),
      beam_active_(false),
      beam_x_(0.0f),
      beam_y_(0.0f),
      beam_boss_idx_(-1),
      dive_cycle_timer_(0.0f),
      score_(0),
      high_score_(0),
      state_timer_(0.0f) {
}

void Game022Galaga::InitFormation() {
    int idx = 0;

    // 行 0: 2 只蜂后 Boss (y=2)
    for (int col = 0; col < 2; ++col) {
        aliens_[idx].active = true;
        aliens_[idx].type = ALIEN_BOSS;
        aliens_[idx].home_x = (col == 0) ? 5.0f : 10.0f;
        aliens_[idx].home_y = 2.0f;
        aliens_[idx].x = aliens_[idx].home_x;
        aliens_[idx].y = aliens_[idx].home_y;
        aliens_[idx].vx = 0.0f;
        aliens_[idx].vy = 0.0f;
        aliens_[idx].is_diving = false;
        aliens_[idx].dive_timer = 0.0f;
        aliens_[idx].has_captured_fighter = false;
        idx++;
    }

    // 行 1: 4 只红色蝴蝶 Goei (y=4)
    for (int col = 0; col < 4; ++col) {
        aliens_[idx].active = true;
        aliens_[idx].type = ALIEN_GOEI;
        aliens_[idx].home_x = 3.0f + col * 3.0f;
        aliens_[idx].home_y = 4.0f;
        aliens_[idx].x = aliens_[idx].home_x;
        aliens_[idx].y = aliens_[idx].home_y;
        aliens_[idx].vx = 0.0f;
        aliens_[idx].vy = 0.0f;
        aliens_[idx].is_diving = false;
        aliens_[idx].dive_timer = 0.0f;
        aliens_[idx].has_captured_fighter = false;
        idx++;
    }

    // 行 2: 4 只蓝色工蜂 Zako (y=6)
    for (int col = 0; col < 4; ++col) {
        aliens_[idx].active = true;
        aliens_[idx].type = ALIEN_ZAKO;
        aliens_[idx].home_x = 3.0f + col * 3.0f;
        aliens_[idx].home_y = 6.0f;
        aliens_[idx].x = aliens_[idx].home_x;
        aliens_[idx].y = aliens_[idx].home_y;
        aliens_[idx].vx = 0.0f;
        aliens_[idx].vy = 0.0f;
        aliens_[idx].is_diving = false;
        aliens_[idx].dive_timer = 0.0f;
        aliens_[idx].has_captured_fighter = false;
        idx++;
    }

    // 清空子弹池
    for (int i = 0; i < MAX_BULLETS; ++i) {
        bullets_[i].active = false;
    }

    player_x_ = 7.0f;
    is_dual_ = false;
    is_being_captured_ = false;
    capture_timer_ = 0.0f;
    shoot_cooldown_ = 0.0f;
    beam_active_ = false;
    beam_boss_idx_ = -1;
    dive_cycle_timer_ = 0.0f;
}

void Game022Galaga::Init() {
    Reset();
}

void Game022Galaga::Reset() {
    state_ = STATE_PLAYING;
    score_ = 0;
    lives_ = 3;
    state_timer_ = 0.0f;
    InitFormation();
}

void Game022Galaga::FirePlayerBullet() {
    if (shoot_cooldown_ > 0.0f) return;
    shoot_cooldown_ = 0.22f;

    if (!is_dual_) {
        // 单发主炮
        for (int i = 0; i < MAX_BULLETS; ++i) {
            if (!bullets_[i].active) {
                bullets_[i].active = true;
                bullets_[i].x = roundf(player_x_);
                bullets_[i].y = 13.0f;
                bullets_[i].vy = -14.0f;
                bullets_[i].is_player = true;
                break;
            }
        }
    } else {
        // 双联装平行齐射
        int placed = 0;
        for (int i = 0; i < MAX_BULLETS && placed < 2; ++i) {
            if (!bullets_[i].active) {
                bullets_[i].active = true;
                bullets_[i].x = (placed == 0) ? roundf(player_x_) : roundf(player_x_) + 1.0f;
                bullets_[i].y = 13.0f;
                bullets_[i].vy = -14.0f;
                bullets_[i].is_player = true;
                placed++;
            }
        }
    }
}

void Game022Galaga::TriggerTractorBeam(int boss_idx) {
    if (boss_idx < 0 || boss_idx >= MAX_ALIENS) return;
    beam_active_ = true;
    beam_boss_idx_ = boss_idx;
    beam_x_ = aliens_[boss_idx].x;
    beam_y_ = aliens_[boss_idx].y;
}

void Game022Galaga::UpdateAliens(float dt) {
    bool any_active = false;

    // 1. 整体编队微幅水平摆动
    float sway = sinf(state_timer_ * 2.5f) * 1.5f;

    for (int i = 0; i < MAX_ALIENS; ++i) {
        if (!aliens_[i].active) continue;
        any_active = true;

        if (!aliens_[i].is_diving) {
            aliens_[i].x = aliens_[i].home_x + sway;
            aliens_[i].y = aliens_[i].home_y;
        } else {
            // 俯冲状态追踪轨迹
            aliens_[i].dive_timer += dt;
            aliens_[i].y += aliens_[i].vy * dt;
            aliens_[i].x += aliens_[i].vx * dt;

            // 蜂后在半空中停留发射牵引光束
            if (aliens_[i].type == ALIEN_BOSS && !aliens_[i].has_captured_fighter && !is_dual_) {
                if (aliens_[i].y >= 7.0f && aliens_[i].y <= 7.5f && !beam_active_) {
                    TriggerTractorBeam(i);
                }
            }

            // 越过底部屏幕后重返顶部编队
            if (aliens_[i].y > 16.5f) {
                aliens_[i].y = -1.0f;
                aliens_[i].vy = 4.0f;
                aliens_[i].vx = (aliens_[i].home_x - aliens_[i].x) * 1.5f;
            }
            if (aliens_[i].y >= aliens_[i].home_y && aliens_[i].vy > 0.0f && aliens_[i].y < aliens_[i].home_y + 1.0f) {
                aliens_[i].is_diving = false;
                aliens_[i].x = aliens_[i].home_x;
                aliens_[i].y = aliens_[i].home_y;
                if (beam_active_ && beam_boss_idx_ == i) {
                    beam_active_ = false;
                    beam_boss_idx_ = -1;
                }
            }

            // 随机朝玩家投掷敌方炸弹
            if (rand() % 100 < 3) {
                for (int b = 0; b < MAX_BULLETS; ++b) {
                    if (!bullets_[b].active) {
                        bullets_[b].active = true;
                        bullets_[b].x = aliens_[i].x;
                        bullets_[b].y = aliens_[i].y + 0.5f;
                        bullets_[b].vy = 6.5f;
                        bullets_[b].is_player = false;
                        break;
                    }
                }
            }
        }
    }

    // 2. 俯冲调度器
    dive_cycle_timer_ += dt;
    if (dive_cycle_timer_ >= 3.0f) {
        dive_cycle_timer_ = 0.0f;
        // 随机挑选一只活着的敌机发起俯冲
        int pick = rand() % MAX_ALIENS;
        for (int t = 0; t < MAX_ALIENS; ++t) {
            int idx = (pick + t) % MAX_ALIENS;
            if (aliens_[idx].active && !aliens_[idx].is_diving) {
                aliens_[idx].is_diving = true;
                aliens_[idx].dive_timer = 0.0f;
                aliens_[idx].vy = 5.0f;
                aliens_[idx].vx = (player_x_ - aliens_[idx].x) * 0.4f;
                break;
            }
        }
    }

    // 3. 牵引光束吸取逻辑
    if (beam_active_ && beam_boss_idx_ >= 0) {
        int bi = beam_boss_idx_;
        if (!aliens_[bi].active) {
            beam_active_ = false;
            beam_boss_idx_ = -1;
        } else {
            // 光束在 y=8 ~ y=14 扇形张开 (宽度 1.5 ~ 3.5 格)
            float bx = aliens_[bi].x;
            float p_left = player_x_;
            float p_right = is_dual_ ? player_x_ + 1.0f : player_x_;

            // 如果玩家单机接触光束核心，则触发吸取
            if (!is_dual_ && !is_being_captured_ && fabsf(p_left - bx) <= 1.5f) {
                is_being_captured_ = true;
                capture_timer_ = 0.0f;
            }

            if (is_being_captured_) {
                capture_timer_ += dt;
                // 战机向 Boss 螺旋升天
                player_x_ += (bx - player_x_) * 5.0f * dt;
                if (capture_timer_ >= 1.2f) {
                    // 俘虏成功，扣除一条命
                    is_being_captured_ = false;
                    beam_active_ = false;
                    aliens_[bi].has_captured_fighter = true;
                    lives_--;
                    if (lives_ <= 0) {
                        state_ = STATE_GAMEOVER;
                        state_timer_ = 0.0f;
                        return;
                    } else {
                        player_x_ = 7.0f;
                    }
                }
            }
        }
    }

    // 通关判定
    if (!any_active) {
        state_ = STATE_VICTORY;
        state_timer_ = 0.0f;
    }
}

void Game022Galaga::UpdateBullets(float dt) {
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (!bullets_[i].active) continue;

        bullets_[i].y += bullets_[i].vy * dt;

        // 出界销毁
        if (bullets_[i].y < -0.5f || bullets_[i].y > 16.5f) {
            bullets_[i].active = false;
            continue;
        }

        // 玩家子弹打击敌机
        if (bullets_[i].is_player) {
            for (int a = 0; a < MAX_ALIENS; ++a) {
                if (!aliens_[a].active) continue;

                float dist = fabsf(bullets_[i].x - aliens_[a].x) + fabsf(bullets_[i].y - aliens_[a].y);
                if (dist <= 1.1f) {
                    bullets_[i].active = false;
                    aliens_[a].active = false;

                    // 得分计算
                    if (aliens_[a].type == ALIEN_BOSS) score_ += 200;
                    else if (aliens_[a].type == ALIEN_GOEI) score_ += 120;
                    else score_ += 80;

                    if (score_ > high_score_) high_score_ = score_;

                    // 若被击毁的蜂后携带有俘虏战机，则解救并合体双子战机！
                    if (aliens_[a].has_captured_fighter) {
                        aliens_[a].has_captured_fighter = false;
                        is_dual_ = true;
                        score_ += 500;
                        if (score_ > high_score_) high_score_ = score_;
                    }

                    if (beam_active_ && beam_boss_idx_ == a) {
                        beam_active_ = false;
                        beam_boss_idx_ = -1;
                    }
                    break;
                }
            }
        } else {
            // 敌方子弹击中玩家
            float p_left = player_x_ - 0.5f;
            float p_right = is_dual_ ? player_x_ + 1.5f : player_x_ + 0.5f;
            if (bullets_[i].y >= 13.5f && bullets_[i].y <= 15.0f &&
                bullets_[i].x >= p_left && bullets_[i].x <= p_right) {
                bullets_[i].active = false;

                if (is_dual_) {
                    // 双子战机受损降级为单机，保全一条性命
                    is_dual_ = false;
                } else {
                    lives_--;
                    if (lives_ <= 0) {
                        state_ = STATE_GAMEOVER;
                        state_timer_ = 0.0f;
                        return;
                    } else {
                        player_x_ = 7.0f;
                    }
                }
            }
        }
    }
}

void Game022Galaga::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt > 0.05f) dt = 0.05f;
    state_timer_ += dt;

    if (state_ == STATE_TITLE) {
        if (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP)) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        if (state_timer_ > 0.5f && (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP))) {
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

        if (shoot_cooldown_ > 0.0f) shoot_cooldown_ -= dt;

        // 1. 玩家水平位移控制 (被光束俘虏中不可操控)
        if (!is_being_captured_) {
            float speed = 8.5f;
            if (keys_down & KEY_LEFT) player_x_ -= speed * dt;
            if (keys_down & KEY_RIGHT) player_x_ += speed * dt;

            float max_x = is_dual_ ? 14.0f : 15.0f;
            if (player_x_ < 0.0f) player_x_ = 0.0f;
            if (player_x_ > max_x) player_x_ = max_x;

            if (keys_pressed & (KEY_A | KEY_B)) {
                FirePlayerBullet();
            }
        }

        // 2. 更新敌机编队与子弹
        UpdateAliens(dt);
        UpdateBullets(dt);
    }
}

void Game022Galaga::Render(uint8_t* fb_rgb24) {
    memset(fb_rgb24, 0, 16 * 16 * 3);

    // 1. 璀璨星空背景微光
    for (int i = 0; i < 6; ++i) {
        int sx = (i * 5 + (int)(state_timer_ * 4.0f)) % 16;
        int sy = (i * 3 + 2) % 16;
        int idx = (sy * 16 + sx) * 3;
        fb_rgb24[idx + 0] = 30; fb_rgb24[idx + 1] = 30; fb_rgb24[idx + 2] = 50;
    }

    // 2. 绘制牵引光束 (波纹幽蓝锥形投影)
    if (beam_active_ && beam_boss_idx_ >= 0) {
        int bx = (int)roundf(aliens_[beam_boss_idx_].x);
        for (int y = 8; y <= 14; ++y) {
            int width = (y - 7) / 2;
            for (int dx = -width; dx <= width; ++dx) {
                int px = bx + dx;
                if (px >= 0 && px < 16) {
                    int idx = (y * 16 + px) * 3;
                    fb_rgb24[idx + 0] = 41;  fb_rgb24[idx + 1] = 128; fb_rgb24[idx + 2] = 185;
                }
            }
        }
    }

    // 3. 绘制外星异形敌机
    for (int i = 0; i < MAX_ALIENS; ++i) {
        if (!aliens_[i].active) continue;

        int ax = (int)roundf(aliens_[i].x);
        int ay = (int)roundf(aliens_[i].y);
        if (ax < 0 || ax >= 16 || ay < 0 || ay >= 16) continue;

        int idx = (ay * 16 + ax) * 3;
        if (aliens_[i].type == ALIEN_BOSS) {
            fb_rgb24[idx + 0] = 46;  fb_rgb24[idx + 1] = 204; fb_rgb24[idx + 2] = 113; // 绿色蜂后
        } else if (aliens_[i].type == ALIEN_GOEI) {
            fb_rgb24[idx + 0] = 231; fb_rgb24[idx + 1] = 76;  fb_rgb24[idx + 2] = 60;  // 红色蝴蝶
        } else {
            fb_rgb24[idx + 0] = 52;  fb_rgb24[idx + 1] = 152; fb_rgb24[idx + 2] = 219; // 蓝色工蜂
        }

        // 若携带有俘虏战机，在其上方标记一颗蓝白微粒
        if (aliens_[i].has_captured_fighter && ay > 0) {
            int cidx = ((ay - 1) * 16 + ax) * 3;
            fb_rgb24[cidx + 0] = 255; fb_rgb24[cidx + 1] = 255; fb_rgb24[cidx + 2] = 100;
        }
    }

    // 4. 绘制子弹
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (!bullets_[i].active) continue;

        int bx = (int)roundf(bullets_[i].x);
        int by = (int)roundf(bullets_[i].y);
        if (bx >= 0 && bx < 16 && by >= 0 && by < 16) {
            int idx = (by * 16 + bx) * 3;
            if (bullets_[i].is_player) {
                fb_rgb24[idx + 0] = 255; fb_rgb24[idx + 1] = 255; fb_rgb24[idx + 2] = 255; // 银白光子炮
            } else {
                fb_rgb24[idx + 0] = 241; fb_rgb24[idx + 1] = 196; fb_rgb24[idx + 2] = 15;  // 橙黄等离子
            }
        }
    }

    // 5. 绘制玩家战机 (单机为纯白 [255, 255, 255]，双联机占两格)
    if (lives_ > 0) {
        int py = 14;
        int px1 = (int)roundf(player_x_);
        if (px1 >= 0 && px1 < 16) {
            int idx = (py * 16 + px1) * 3;
            fb_rgb24[idx + 0] = 255; fb_rgb24[idx + 1] = 255; fb_rgb24[idx + 2] = 255;
        }
        if (is_dual_) {
            int px2 = px1 + 1;
            if (px2 < 16) {
                int idx = (py * 16 + px2) * 3;
                fb_rgb24[idx + 0] = 0; fb_rgb24[idx + 1] = 255; fb_rgb24[idx + 2] = 255; // 僚机青蓝光辉
            }
        }
    }

    // 6. 顶部生命指示器
    for (int i = 0; i < lives_; ++i) {
        int idx = (0 * 16 + i) * 3;
        fb_rgb24[idx + 0] = 255; fb_rgb24[idx + 1] = 255; fb_rgb24[idx + 2] = 255;
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

CartridgeStatus Game022Galaga::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.lives = lives_;
    st.state = (uint8_t)state_;

    int alive = 0;
    for (int i = 0; i < MAX_ALIENS; ++i) {
        if (aliens_[i].active) alive++;
    }
    st.progress = (uint8_t)(((MAX_ALIENS - alive) * 100) / MAX_ALIENS);
    return st;
}

} // namespace arcade
