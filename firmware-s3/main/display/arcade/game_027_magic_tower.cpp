// game_027_magic_tower.cpp —— 经典魔塔 1996 核心实现
#include "game_027_magic_tower.h"
#include <string.h>
#include <stdlib.h>
#include <math.h>

namespace arcade {

Game027MagicTower::Game027MagicTower()
    : state_(STATE_TITLE),
      hero_x_(1),
      hero_y_(14),
      hero_hp_(1000),
      hero_atk_(25),
      hero_def_(10),
      yellow_keys_(1),
      blue_keys_(0),
      move_timer_(0.0f),
      score_(0),
      high_score_(0),
      state_timer_(0.0f) {
}

MonsterStats Game027MagicTower::GetMonsterStats(uint8_t tile_type) const {
    MonsterStats s;
    if (tile_type == TOWER_MONSTER_SLIME) {
        s.hp = 50; s.atk = 20; s.def = 1; s.gold = 10;
    } else if (tile_type == TOWER_MONSTER_SKELETON) {
        s.hp = 110; s.atk = 35; s.def = 5; s.gold = 30;
    } else if (tile_type == TOWER_MONSTER_MAGE) {
        s.hp = 200; s.atk = 55; s.def = 10; s.gold = 60;
    } else if (tile_type == TOWER_MONSTER_BOSS) {
        s.hp = 500; s.atk = 80; s.def = 20; s.gold = 200;
    } else {
        s.hp = 0; s.atk = 0; s.def = 0; s.gold = 0;
    }
    return s;
}

int Game027MagicTower::CalculateDamage(uint8_t tile_type) const {
    MonsterStats m = GetMonsterStats(tile_type);
    if (hero_atk_ <= m.def) return -1; // 无法破防

    int hero_dmg = hero_atk_ - m.def;
    int enemy_dmg = (m.atk > hero_def_) ? (m.atk - hero_def_) : 0;
    int rounds = (m.hp + hero_dmg - 1) / hero_dmg;
    int total_dmg = (rounds - 1) * enemy_dmg;
    return total_dmg;
}

void Game027MagicTower::InitLevel() {
    // 1. 初始化空地面
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            grid_[y][x] = TOWER_FLOOR;
        }
    }

    // 2. 外围环形城墙
    for (int x = 0; x < 16; ++x) {
        grid_[0][x] = TOWER_WALL;
        grid_[15][x] = TOWER_WALL;
    }
    for (int y = 0; y < 16; ++y) {
        grid_[y][0] = TOWER_WALL;
        grid_[y][15] = TOWER_WALL;
    }

    // 3. 内部回廊墙壁隔断
    for (int x = 1; x <= 6; ++x) grid_[12][x] = TOWER_WALL;
    for (int y = 8; y <= 14; ++y) grid_[y][6] = TOWER_WALL;
    for (int x = 6; x <= 14; ++x) grid_[8][x] = TOWER_WALL;
    for (int y = 1; y <= 8; ++y) grid_[y][11] = TOWER_WALL;
    for (int x = 1; x <= 8; ++x) grid_[4][x] = TOWER_WALL;

    // 4. 门禁布置
    grid_[12][3] = TOWER_DOOR_YELLOW;
    grid_[8][8]  = TOWER_DOOR_YELLOW;
    grid_[4][4]  = TOWER_DOOR_YELLOW;
    grid_[4][11] = TOWER_DOOR_BLUE;

    // 5. 钥匙与宝石药水补给
    grid_[13][2] = TOWER_KEY_YELLOW;
    grid_[14][4] = TOWER_GEM_RED;       // +3 攻击
    grid_[13][5] = TOWER_POTION_RED;    // +200 HP

    grid_[10][2] = TOWER_KEY_YELLOW;
    grid_[9][3]  = TOWER_GEM_BLUE;      // +3 防御
    grid_[10][4] = TOWER_KEY_BLUE;

    grid_[6][2]  = TOWER_POTION_BLUE;   // +500 HP
    grid_[5][3]  = TOWER_GEM_RED;
    grid_[6][4]  = TOWER_GEM_BLUE;

    grid_[2][2]  = TOWER_GEM_RED;
    grid_[2][4]  = TOWER_GEM_BLUE;
    grid_[1][3]  = TOWER_POTION_BLUE;

    // 6. 怪物镇守
    grid_[12][4] = TOWER_MONSTER_SLIME;
    grid_[11][8] = TOWER_MONSTER_SLIME;
    grid_[8][9]  = TOWER_MONSTER_SKELETON;
    grid_[6][8]  = TOWER_MONSTER_SKELETON;
    grid_[4][9]  = TOWER_MONSTER_MAGE;
    grid_[2][8]  = TOWER_MONSTER_MAGE;
    grid_[2][12] = TOWER_MONSTER_BOSS;  // 魔王守在顶层密室

    // 7. 终极通关楼梯
    grid_[1][14] = TOWER_STAIRS;

    // 勇士初始属性
    hero_x_ = 1;
    hero_y_ = 14;
    hero_hp_ = 1000;
    hero_atk_ = 25;
    hero_def_ = 10;
    yellow_keys_ = 1;
    blue_keys_ = 0;
    move_timer_ = 0.0f;
}

void Game027MagicTower::Init() {
    Reset();
}

void Game027MagicTower::Reset() {
    state_ = STATE_PLAYING;
    score_ = 0;
    state_timer_ = 0.0f;
    InitLevel();
}

bool Game027MagicTower::Interact(int nx, int ny) {
    if (nx < 0 || nx >= 16 || ny < 0 || ny >= 16) return false;

    uint8_t tile = grid_[ny][nx];

    // 1. 空地面
    if (tile == TOWER_FLOOR) {
        hero_x_ = nx;
        hero_y_ = ny;
        return true;
    }

    // 2. 墙壁阻挡
    if (tile == TOWER_WALL) {
        return false;
    }

    // 3. 拾取钥匙与强化道具
    if (tile == TOWER_KEY_YELLOW) {
        yellow_keys_++;
        grid_[ny][nx] = TOWER_FLOOR;
        hero_x_ = nx; hero_y_ = ny;
        score_ += 10;
        return true;
    }
    if (tile == TOWER_KEY_BLUE) {
        blue_keys_++;
        grid_[ny][nx] = TOWER_FLOOR;
        hero_x_ = nx; hero_y_ = ny;
        score_ += 20;
        return true;
    }
    if (tile == TOWER_GEM_RED) {
        hero_atk_ += 3;
        grid_[ny][nx] = TOWER_FLOOR;
        hero_x_ = nx; hero_y_ = ny;
        score_ += 30;
        return true;
    }
    if (tile == TOWER_GEM_BLUE) {
        hero_def_ += 3;
        grid_[ny][nx] = TOWER_FLOOR;
        hero_x_ = nx; hero_y_ = ny;
        score_ += 30;
        return true;
    }
    if (tile == TOWER_POTION_RED) {
        hero_hp_ += 200;
        grid_[ny][nx] = TOWER_FLOOR;
        hero_x_ = nx; hero_y_ = ny;
        score_ += 15;
        return true;
    }
    if (tile == TOWER_POTION_BLUE) {
        hero_hp_ += 500;
        grid_[ny][nx] = TOWER_FLOOR;
        hero_x_ = nx; hero_y_ = ny;
        score_ += 40;
        return true;
    }

    // 4. 门禁开锁
    if (tile == TOWER_DOOR_YELLOW) {
        if (yellow_keys_ > 0) {
            yellow_keys_--;
            grid_[ny][nx] = TOWER_FLOOR;
            hero_x_ = nx; hero_y_ = ny;
            score_ += 20;
            return true;
        }
        return false;
    }
    if (tile == TOWER_DOOR_BLUE) {
        if (blue_keys_ > 0) {
            blue_keys_--;
            grid_[ny][nx] = TOWER_FLOOR;
            hero_x_ = nx; hero_y_ = ny;
            score_ += 50;
            return true;
        }
        return false;
    }

    // 5. 精密数值怪物决战
    if (tile >= TOWER_MONSTER_SLIME && tile <= TOWER_MONSTER_BOSS) {
        int dmg = CalculateDamage(tile);
        if (dmg == -1 || dmg >= hero_hp_) {
            // 打不过或者破不了防，坚决不进入战斗，保护玩家安全
            return false;
        }

        MonsterStats m = GetMonsterStats(tile);
        hero_hp_ -= dmg;
        score_ += m.gold;
        if (score_ > high_score_) high_score_ = score_;

        grid_[ny][nx] = TOWER_FLOOR;
        hero_x_ = nx;
        hero_y_ = ny;
        return true;
    }

    // 6. 登梯通关
    if (tile == TOWER_STAIRS) {
        hero_x_ = nx;
        hero_y_ = ny;
        state_ = STATE_VICTORY;
        state_timer_ = 0.0f;
        score_ += 1000;
        if (score_ > high_score_) high_score_ = score_;
        return true;
    }

    return false;
}

void Game027MagicTower::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
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

        // 玩家四向行走触碰互动
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
                Interact(hero_x_ + dx, hero_y_ + dy);
            }
        }
    }
}

void Game027MagicTower::Render(uint8_t* fb_rgb24) {
    memset(fb_rgb24, 0, 16 * 16 * 3);

    // 1. 渲染迷宫地块
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            uint8_t t = grid_[y][x];

            if (t == TOWER_FLOOR) {
                fb_rgb24[idx + 0] = 30;  fb_rgb24[idx + 1] = 30;  fb_rgb24[idx + 2] = 35;  // 灰石地面
            } else if (t == TOWER_WALL) {
                fb_rgb24[idx + 0] = 100; fb_rgb24[idx + 1] = 100; fb_rgb24[idx + 2] = 110; // 青砖城墙
            } else if (t == TOWER_DOOR_YELLOW) {
                fb_rgb24[idx + 0] = 241; fb_rgb24[idx + 1] = 196; fb_rgb24[idx + 2] = 15;  // 黄门
            } else if (t == TOWER_DOOR_BLUE) {
                fb_rgb24[idx + 0] = 41;  fb_rgb24[idx + 1] = 128; fb_rgb24[idx + 2] = 185; // 蓝门
            } else if (t == TOWER_KEY_YELLOW) {
                fb_rgb24[idx + 0] = 243; fb_rgb24[idx + 1] = 156; fb_rgb24[idx + 2] = 18;  // 黄钥匙
            } else if (t == TOWER_KEY_BLUE) {
                fb_rgb24[idx + 0] = 52;  fb_rgb24[idx + 1] = 152; fb_rgb24[idx + 2] = 219; // 蓝钥匙
            } else if (t == TOWER_GEM_RED) {
                fb_rgb24[idx + 0] = 231; fb_rgb24[idx + 1] = 76;  fb_rgb24[idx + 2] = 60;  // 红宝石
            } else if (t == TOWER_GEM_BLUE) {
                fb_rgb24[idx + 0] = 52;  fb_rgb24[idx + 1] = 152; fb_rgb24[idx + 2] = 219; // 蓝宝石
            } else if (t == TOWER_POTION_RED) {
                fb_rgb24[idx + 0] = 255; fb_rgb24[idx + 1] = 105; fb_rgb24[idx + 2] = 180; // 红血瓶
            } else if (t == TOWER_POTION_BLUE) {
                fb_rgb24[idx + 0] = 0;   fb_rgb24[idx + 1] = 255; fb_rgb24[idx + 2] = 255; // 蓝血瓶
            } else if (t == TOWER_MONSTER_SLIME) {
                fb_rgb24[idx + 0] = 46;  fb_rgb24[idx + 1] = 204; fb_rgb24[idx + 2] = 113; // 绿史莱姆
            } else if (t == TOWER_MONSTER_SKELETON) {
                fb_rgb24[idx + 0] = 189; fb_rgb24[idx + 1] = 195; fb_rgb24[idx + 2] = 199; // 白骷髅兵
            } else if (t == TOWER_MONSTER_MAGE) {
                fb_rgb24[idx + 0] = 155; fb_rgb24[idx + 1] = 89;  fb_rgb24[idx + 2] = 182; // 紫法师
            } else if (t == TOWER_MONSTER_BOSS) {
                fb_rgb24[idx + 0] = 255; fb_rgb24[idx + 1] = 0;   fb_rgb24[idx + 2] = 0;    // 猩红魔王
            } else if (t == TOWER_STAIRS) {
                fb_rgb24[idx + 0] = 255; fb_rgb24[idx + 1] = 255; fb_rgb24[idx + 2] = 255; // 纯白楼梯
            }
        }
    }

    // 2. 绘制勇士 (高贵金光 [255, 215, 0])
    int hero_idx = (hero_y_ * 16 + hero_x_) * 3;
    fb_rgb24[hero_idx + 0] = 255;
    fb_rgb24[hero_idx + 1] = 215;
    fb_rgb24[hero_idx + 2] = 0;

    // 3. 顶部 HUD: 生命指示 (根据生命多寡以绿/黄/红点表示)
    uint8_t hp_color_g = (hero_hp_ > 500) ? 200 : (hero_hp_ > 200) ? 150 : 50;
    fb_rgb24[0] = 231; fb_rgb24[1] = hp_color_g; fb_rgb24[2] = 60;

    // 4. 胜负特效
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

CartridgeStatus Game027MagicTower::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.lives = (hero_hp_ > 0) ? 1 : 0;
    st.state = (uint8_t)state_;
    // 进度基于击倒怪物情况 (Boss如果阵亡则达 100%)
    bool boss_alive = (grid_[2][12] == TOWER_MONSTER_BOSS);
    st.progress = boss_alive ? (uint8_t)((score_ * 100) / 1000) : 100;
    return st;
}

} // namespace arcade
