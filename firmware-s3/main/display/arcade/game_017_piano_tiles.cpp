// game_017_piano_tiles.cpp —— 别踩白块儿 2014 核心实现
#include "game_017_piano_tiles.h"
#include <string.h>
#include <stdlib.h>

namespace arcade {

Game017PianoTiles::Game017PianoTiles()
    : state_(STATE_TITLE),
      fall_speed_(10.0f),
      combo_(0),
      total_hits_(0),
      score_(0),
      high_score_(0),
      state_timer_(0.0f),
      spawn_timer_(0.0f) {
    for (int i = 0; i < kMaxNotes; ++i) notes_[i].active = false;
    for (int t = 0; t < 4; ++t) hit_flash_timer_[t] = 0.0f;
}

void Game017PianoTiles::SpawnNextNote() {
    int slot = -1;
    for (int i = 0; i < kMaxNotes; ++i) {
        if (!notes_[i].active) {
            slot = i;
            break;
        }
    }
    if (slot == -1) return;

    notes_[slot].active = true;
    notes_[slot].track = rand() % 4;
    notes_[slot].y = -3.5f;
    notes_[slot].height = 3.0f;
    notes_[slot].hit = false;
}

void Game017PianoTiles::Init() {
    Reset();
}

void Game017PianoTiles::Reset() {
    state_ = STATE_PLAYING;
    score_ = 0;
    combo_ = 0;
    total_hits_ = 0;
    fall_speed_ = 10.0f;
    state_timer_ = 0.0f;
    spawn_timer_ = 0.0f;

    for (int i = 0; i < kMaxNotes; ++i) notes_[i].active = false;
    for (int t = 0; t < 4; ++t) hit_flash_timer_[t] = 0.0f;

    // 初始刷出第一颗音符
    SpawnNextNote();
}

void Game017PianoTiles::HandleTrackHit(uint8_t track) {
    // 寻找该轨道上最靠近底部的未命中音符
    int candidate_idx = -1;
    float lowest_y = -999.0f;

    for (int i = 0; i < kMaxNotes; ++i) {
        if (notes_[i].active && !notes_[i].hit && notes_[i].track == track) {
            if (notes_[i].y > lowest_y) {
                lowest_y = notes_[i].y;
                candidate_idx = i;
            }
        }
    }

    if (candidate_idx != -1) {
        PianoNote& note = notes_[candidate_idx];
        // 判定区间: 底线位于 y=12..14，音符范围在 10.0 ~ 15.5 之间视为精准命中
        if ((note.y + note.height) >= 10.5f && note.y <= 15.5f) {
            note.hit = true;
            note.active = false; // 击碎
            combo_++;
            total_hits_++;
            hit_flash_timer_[track] = 0.2f;

            uint32_t pts = 25 * combo_;
            score_ += pts;
            if (score_ > high_score_) high_score_ = score_;

            // 提速
            if (fall_speed_ < 24.0f) {
                fall_speed_ += 0.35f;
            }

            // 通关判定
            if (total_hits_ >= kTargetHits) {
                state_ = STATE_VICTORY;
                state_timer_ = 0.0f;
            }
            return;
        }
    }

    // 若无匹配音符或过早按键：踩到白块，立即猝死！
    state_ = STATE_GAMEOVER;
    state_timer_ = 0.0f;
}

void Game017PianoTiles::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
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

        // 闪光计时消退
        for (int t = 0; t < 4; ++t) {
            if (hit_flash_timer_[t] > 0.0f) {
                hit_flash_timer_[t] -= dt;
            }
        }

        // 玩家按键判定 (Track 0..3 映射: LEFT, DOWN, UP, RIGHT)
        if (keys_pressed & KEY_LEFT) {
            HandleTrackHit(0);
            if (state_ != STATE_PLAYING) return;
        }
        if (keys_pressed & KEY_DOWN) {
            HandleTrackHit(1);
            if (state_ != STATE_PLAYING) return;
        }
        if (keys_pressed & KEY_UP) {
            HandleTrackHit(2);
            if (state_ != STATE_PLAYING) return;
        }
        if (keys_pressed & KEY_RIGHT) {
            HandleTrackHit(3);
            if (state_ != STATE_PLAYING) return;
        }

        // 音符下沉与漏击检测
        for (int i = 0; i < kMaxNotes; ++i) {
            if (notes_[i].active && !notes_[i].hit) {
                notes_[i].y += fall_speed_ * dt;

                // 漏击跌出底线 (Miss) -> 猝死判定
                if (notes_[i].y > 15.2f) {
                    state_ = STATE_GAMEOVER;
                    state_timer_ = 0.0f;
                    return;
                }
            }
        }

        // 生成新音符节奏周期
        spawn_timer_ += dt;
        float spawn_interval = 4.8f / fall_speed_;
        if (spawn_timer_ >= spawn_interval) {
            spawn_timer_ = 0.0f;
            SpawnNextNote();
        }
    }
}

void Game017PianoTiles::Render(uint8_t* fb_rgb24) {
    // 1. 底色: 白色琴键底色 (复古暖白 [240, 243, 244]) 与细分割线
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            if (x == 3 || x == 7 || x == 11) {
                // 轨道微弱分割灰线
                fb_rgb24[idx + 0] = 189; fb_rgb24[idx + 1] = 195; fb_rgb24[idx + 2] = 199;
            } else {
                // 白键背景
                fb_rgb24[idx + 0] = 236; fb_rgb24[idx + 1] = 240; fb_rgb24[idx + 2] = 241;
            }
        }
    }

    // 2. 绘制下沉黑色钢琴块 (曜石深蓝 [0, 120, 255])
    for (int i = 0; i < kMaxNotes; ++i) {
        if (notes_[i].active && !notes_[i].hit) {
            int track_x = notes_[i].track * 4;
            int y_start = (int)notes_[i].y;
            int y_end = (int)(notes_[i].y + notes_[i].height);

            for (int y = y_start; y < y_end; ++y) {
                if (y >= 0 && y < 16) {
                    for (int dx = 0; dx < 3; ++dx) {
                        int x = track_x + dx;
                        if (x < 16) {
                            int idx = (y * 16 + x) * 3;
                            fb_rgb24[idx + 0] = 24;  fb_rgb24[idx + 1] = 44;  fb_rgb24[idx + 2] = 97; // 墨色深蓝
                        }
                    }
                }
            }
        }
    }

    // 3. 绘制底线黄金判定线 (y=13)
    for (int x = 0; x < 16; ++x) {
        int idx = (13 * 16 + x) * 3;
        fb_rgb24[idx + 0] = 241; fb_rgb24[idx + 1] = 196; fb_rgb24[idx + 2] = 15;
    }

    // 4. 绘制打击闪光特效
    for (int t = 0; t < 4; ++t) {
        if (hit_flash_timer_[t] > 0.0f) {
            int tx = t * 4;
            for (int y = 12; y <= 14; ++y) {
                for (int dx = 0; dx < 3; ++dx) {
                    int x = tx + dx;
                    int idx = (y * 16 + x) * 3;
                    fb_rgb24[idx + 0] = 46; fb_rgb24[idx + 1] = 204; fb_rgb24[idx + 2] = 113; // 翠绿高光
                }
            }
        }
    }

    // 5. 特效渲染
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

CartridgeStatus Game017PianoTiles::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.lives = (state_ == STATE_GAMEOVER) ? 0 : 1;
    st.state = (uint8_t)state_;
    st.progress = (uint8_t)((total_hits_ * 100) / kTargetHits);
    return st;
}

} // namespace arcade
