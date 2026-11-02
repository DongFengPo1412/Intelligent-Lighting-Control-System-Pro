// game_019_puzzle_bobble.cpp —— 像素泡泡龙 1994 核心实现
#include "game_019_puzzle_bobble.h"
#include <string.h>
#include <math.h>
#include <stdlib.h>

namespace arcade {

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

Game019PuzzleBobble::Game019PuzzleBobble()
    : state_(STATE_TITLE),
      angle_deg_(0.0f),
      current_color_(BUBBLE_RED),
      next_color_(BUBBLE_BLUE),
      shots_fired_(0),
      score_(0),
      high_score_(0),
      state_timer_(0.0f) {
    flying_.active = false;
}

int Game019PuzzleBobble::CountRemainingBubbles() const {
    int cnt = 0;
    for (int y = 0; y < 14; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (grid_[y][x] != BUBBLE_NONE) cnt++;
        }
    }
    return cnt;
}

void Game019PuzzleBobble::ResetLevel() {
    memset(grid_, BUBBLE_NONE, sizeof(grid_));

    // 初始化前 3 排泡泡 (Row 0..2)
    for (int y = 0; y < 3; ++y) {
        for (int x = 0; x < 16; ++x) {
            // 成簇分布同色泡泡
            uint8_t c = (uint8_t)(((x / 3) + y) % 4 + 1);
            grid_[y][x] = c;
        }
    }

    angle_deg_ = 0.0f;
    current_color_ = (rand() % 4) + 1;
    next_color_ = (rand() % 4) + 1;
    flying_.active = false;
    shots_fired_ = 0;
}

void Game019PuzzleBobble::Init() {
    Reset();
}

void Game019PuzzleBobble::Reset() {
    state_ = STATE_PLAYING;
    score_ = 0;
    state_timer_ = 0.0f;
    ResetLevel();
}

void Game019PuzzleBobble::FireBubble() {
    if (flying_.active) return;

    flying_.active = true;
    flying_.x = 7.5f;
    flying_.y = 14.0f;
    flying_.color = current_color_;

    // 角度转换为速度向量 (0°为垂直向上，即 -90° 极坐标)
    float rad = (angle_deg_ - 90.0f) * (float)M_PI / 180.0f;
    const float speed = 18.0f;
    flying_.vx = speed * cosf(rad);
    flying_.vy = speed * sinf(rad);

    current_color_ = next_color_;
    next_color_ = (rand() % 4) + 1;
    shots_fired_++;
}

void Game019PuzzleBobble::RemoveFloatingIslands() {
    // 标记所有与天花板 y=0 连通的存活泡泡
    bool connected[16][16];
    memset(connected, false, sizeof(connected));

    int queue_x[256], queue_y[256];
    int q_head = 0, q_tail = 0;

    // 将 Row 0 的所有非空泡泡入队作为根节点
    for (int x = 0; x < 16; ++x) {
        if (grid_[0][x] != BUBBLE_NONE) {
            connected[0][x] = true;
            queue_x[q_tail] = x;
            queue_y[q_tail] = 0;
            q_tail++;
        }
    }

    const int dxs[4] = {0, 0, -1, 1};
    const int dys[4] = {-1, 1, 0, 0};

    while (q_head < q_tail) {
        int cx = queue_x[q_head];
        int cy = queue_y[q_head];
        q_head++;

        for (int i = 0; i < 4; ++i) {
            int nx = cx + dxs[i];
            int ny = cy + dys[i];
            if (nx >= 0 && nx < 16 && ny >= 0 && ny < 14) {
                if (grid_[ny][nx] != BUBBLE_NONE && !connected[ny][nx]) {
                    connected[ny][nx] = true;
                    queue_x[q_tail] = nx;
                    queue_y[q_tail] = ny;
                    q_tail++;
                }
            }
        }
    }

    // 消除所有未与天花板连通的悬空孤岛泡泡
    int dropped_count = 0;
    for (int y = 0; y < 14; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (grid_[y][x] != BUBBLE_NONE && !connected[y][x]) {
                grid_[y][x] = BUBBLE_NONE;
                dropped_count++;
            }
        }
    }

    if (dropped_count > 0) {
        score_ += dropped_count * 50; // 悬空脱落高额暴击分
        if (score_ > high_score_) high_score_ = score_;
    }
}

void Game019PuzzleBobble::SnapAndResolve(float fx, float fy, uint8_t color) {
    flying_.active = false;
    int sx = (int)roundf(fx);
    int sy = (int)roundf(fy);

    if (sx < 0) sx = 0; if (sx > 15) sx = 15;
    if (sy < 0) sy = 0; if (sy > 13) sy = 13;

    // 如果目标已被占，在周围寻找最近的空位吸附
    if (grid_[sy][sx] != BUBBLE_NONE) {
        const int dxs[4] = {0, 0, -1, 1};
        const int dys[4] = {1, -1, 0, 0};
        bool found = false;
        for (int i = 0; i < 4; ++i) {
            int nx = sx + dxs[i];
            int ny = sy + dys[i];
            if (nx >= 0 && nx < 16 && ny >= 0 && ny < 14) {
                if (grid_[ny][nx] == BUBBLE_NONE) {
                    sx = nx;
                    sy = ny;
                    found = true;
                    break;
                }
            }
        }
        if (!found) {
            state_ = STATE_GAMEOVER;
            state_timer_ = 0.0f;
            return;
        }
    }

    grid_[sy][sx] = color;
    flying_.active = false;

    // 触底即亡判定 (y >= 13)
    if (sy >= 13) {
        state_ = STATE_GAMEOVER;
        state_timer_ = 0.0f;
        return;
    }

    // BFS 查找同色连通簇
    bool visited[16][16];
    memset(visited, false, sizeof(visited));
    int cluster_x[256], cluster_y[256];
    int cluster_size = 0;

    int q_x[256], q_y[256];
    int q_head = 0, q_tail = 0;

    visited[sy][sx] = true;
    q_x[q_tail] = sx;
    q_y[q_tail] = sy;
    q_tail++;

    const int dxs[4] = {0, 0, -1, 1};
    const int dys[4] = {-1, 1, 0, 0};

    while (q_head < q_tail) {
        int cx = q_x[q_head];
        int cy = q_y[q_head];
        q_head++;

        cluster_x[cluster_size] = cx;
        cluster_y[cluster_size] = cy;
        cluster_size++;

        for (int i = 0; i < 4; ++i) {
            int nx = cx + dxs[i];
            int ny = cy + dys[i];
            if (nx >= 0 && nx < 16 && ny >= 0 && ny < 14) {
                if (grid_[ny][nx] == color && !visited[ny][nx]) {
                    visited[ny][nx] = true;
                    q_x[q_tail] = nx;
                    q_y[q_tail] = ny;
                    q_tail++;
                }
            }
        }
    }

    // 若同色连通 >= 3，予以爆破消除！
    if (cluster_size >= 3) {
        for (int i = 0; i < cluster_size; ++i) {
            grid_[cluster_y[i]][cluster_x[i]] = BUBBLE_NONE;
        }
        score_ += cluster_size * 30;
        if (score_ > high_score_) high_score_ = score_;

        // 移除悬空孤岛
        RemoveFloatingIslands();
    }

    // 每 6 次发射天花板压迫下沉一行
    if (shots_fired_ > 0 && (shots_fired_ % 6 == 0)) {
        for (int y = 12; y >= 0; --y) {
            for (int x = 0; x < 16; ++x) {
                grid_[y + 1][x] = grid_[y][x];
            }
        }
        // 顶部新增随机一行
        for (int x = 0; x < 16; ++x) {
            grid_[0][x] = (rand() % 4) + 1;
        }
    }

    // 清屏通关判定
    if (CountRemainingBubbles() == 0) {
        state_ = STATE_VICTORY;
        state_timer_ = 0.0f;
    }
}

void Game019PuzzleBobble::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
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

        // 炮台角度旋转
        const float rot_speed = 65.0f;
        if (keys_down & KEY_LEFT) {
            angle_deg_ -= rot_speed * dt;
            if (angle_deg_ < -60.0f) angle_deg_ = -60.0f;
        } else if (keys_down & KEY_RIGHT) {
            angle_deg_ += rot_speed * dt;
            if (angle_deg_ > 60.0f) angle_deg_ = 60.0f;
        }

        // 发射按键 (A 键或 UP 键)
        if (keys_pressed & (KEY_A | KEY_B | KEY_UP)) {
            FireBubble();
        }

        // 飞行中泡泡物理与碰撞检测
        if (flying_.active) {
            flying_.x += flying_.vx * dt;
            flying_.y += flying_.vy * dt;

            // 侧壁弹性反弹
            if (flying_.x <= 0.0f) {
                flying_.x = 0.0f;
                flying_.vx = fabsf(flying_.vx);
            } else if (flying_.x >= 15.0f) {
                flying_.x = 15.0f;
                flying_.vx = -fabsf(flying_.vx);
            }

            // 撞顶吸附
            if (flying_.y <= 0.5f) {
                SnapAndResolve(flying_.x, 0.0f, flying_.color);
            } else {
                // 与现有泡泡吸附碰撞判定
                bool collided = false;
                for (int y = 0; y < 14 && !collided; ++y) {
                    for (int x = 0; x < 16; ++x) {
                        if (grid_[y][x] != BUBBLE_NONE) {
                            float dist_sq = (flying_.x - (float)x) * (flying_.x - (float)x) +
                                            (flying_.y - (float)y) * (flying_.y - (float)y);
                            if (dist_sq < 0.92f) { // 吸附半径
                                SnapAndResolve(flying_.x, flying_.y, flying_.color);
                                collided = true;
                                break;
                            }
                        }
                    }
                }
            }
        }
    }
}

static void GetBubbleRGB(uint8_t color, uint8_t& r, uint8_t& g, uint8_t& b) {
    switch (color) {
        case BUBBLE_RED:    r = 231; g = 76;  b = 60;  break;
        case BUBBLE_BLUE:   r = 52;  g = 152; b = 219; break;
        case BUBBLE_GREEN:  r = 46;  g = 204; b = 113; break;
        case BUBBLE_YELLOW: r = 241; g = 196; b = 15;  break;
        default:            r = 0;   g = 0;   b = 0;   break;
    }
}

void Game019PuzzleBobble::Render(uint8_t* fb_rgb24) {
    memset(fb_rgb24, 0, 16 * 16 * 3);

    // 1. 绘制网格上悬挂的泡泡
    for (int y = 0; y < 14; ++y) {
        for (int x = 0; x < 16; ++x) {
            uint8_t c = grid_[y][x];
            if (c != BUBBLE_NONE) {
                int idx = (y * 16 + x) * 3;
                GetBubbleRGB(c, fb_rgb24[idx + 0], fb_rgb24[idx + 1], fb_rgb24[idx + 2]);
            }
        }
    }

    // 2. 绘制飞行中泡泡
    if (flying_.active) {
        int fx = (int)roundf(flying_.x);
        int fy = (int)roundf(flying_.y);
        if (fx >= 0 && fx < 16 && fy >= 0 && fy < 16) {
            int idx = (fy * 16 + fx) * 3;
            GetBubbleRGB(flying_.color, fb_rgb24[idx + 0], fb_rgb24[idx + 1], fb_rgb24[idx + 2]);
        }
    }

    // 3. 绘制警戒底线 (y=13 暗红虚线)
    for (int x = 0; x < 16; x += 2) {
        int idx = (13 * 16 + x) * 3;
        fb_rgb24[idx + 0] = 192; fb_rgb24[idx + 1] = 57; fb_rgb24[idx + 2] = 43;
    }

    // 4. 绘制底部发射炮台 (y=15, 居中底座)
    int idx_cur = (15 * 16 + 7) * 3;
    int idx_cur2 = (15 * 16 + 8) * 3;
    GetBubbleRGB(current_color_, fb_rgb24[idx_cur + 0], fb_rgb24[idx_cur + 1], fb_rgb24[idx_cur + 2]);
    GetBubbleRGB(current_color_, fb_rgb24[idx_cur2 + 0], fb_rgb24[idx_cur2 + 1], fb_rgb24[idx_cur2 + 2]);

    // 5. 绘制瞄准指针 (从 7.5, 14 延伸 2 像素)
    float rad = (angle_deg_ - 90.0f) * (float)M_PI / 180.0f;
    int aim_x = (int)roundf(7.5f + 2.0f * cosf(rad));
    int aim_y = (int)roundf(14.0f + 2.0f * sinf(rad));
    if (aim_x >= 0 && aim_x < 16 && aim_y >= 0 && aim_y < 16) {
        int idx = (aim_y * 16 + aim_x) * 3;
        fb_rgb24[idx + 0] = 255; fb_rgb24[idx + 1] = 255; fb_rgb24[idx + 2] = 255; // 纯白指针
    }

    // 6. 特效渲染
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

CartridgeStatus Game019PuzzleBobble::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.lives = (state_ == STATE_GAMEOVER) ? 0 : 1;
    st.state = (uint8_t)state_;
    int remaining = CountRemainingBubbles();
    st.progress = (remaining == 0) ? 100 : (uint8_t)fmaxf(0, 100 - remaining);
    return st;
}

} // namespace arcade
