// game_101_microlight.cpp —— #101 微光纪元 (MicroLight)
// 原作与原型设计: 队友 / 《微光纪元：横版世界》 16x16 WS2812 模拟
// 移植与统一街机大厅整合: 未来道具研究所 · PixelArcade Core
#include "game_101_microlight.h"
#include <algorithm>
#include <cmath>

#ifdef ESP_PLATFORM
#include "esp_random.h"
#else
#include <atomic>
#include <chrono>
#endif

namespace arcade {

uint8_t Game101MicroLight::GetBiome(int world_x) const {
    int block_biome = (world_x >= 0 ? world_x : (world_x - 39)) / 40;
    int idx = block_biome % 7;
    if (idx < 0) idx += 7;
    return static_cast<uint8_t>(idx);
}

void Game101MicroLight::Setup() {
    uint32_t seed = replay_seed_;
    if (!replay_seeded_) {
#ifdef ESP_PLATFORM
        seed = esp_random();
#else
        static std::atomic<uint32_t> s_serial{101};
        seed = uint32_t(std::chrono::steady_clock::now().time_since_epoch().count()) ^
               s_serial.fetch_add(0x9e3779b9u);
#endif
        if (seed == last_seed_) ++seed;
    }
    last_seed_ = seed;

    px_ = 4.0f;
    py_ = 8.0f;
    vy_ = 0.0f;
    grounded_ = true;
    hp_ = 5;
    max_hp_ = 5;
    aim_dx_ = 1;
    aim_dy_ = 0;
    wood_ = 0;
    stone_ = 0;
    crystal_ = 0;
    biomes_visited_ = (1 << GetBiome(static_cast<int>(px_)));
    day_clock_ = 30.0f; // Start at morning daylight
    hurt_cd_ = 0.0f;
}

void Game101MicroLight::Tick(float dt, uint16_t down, uint16_t pressed) {
    day_clock_ += dt;
    if (day_clock_ >= 180.0f) day_clock_ -= 180.0f;

    if (hurt_cd_ > 0.0f) {
        hurt_cd_ = std::max(0.0f, hurt_cd_ - dt);
    }

    // Horizontal Movement
    float move_speed = 5.0f;
    if ((down & KEY_LEFT) || (pressed & KEY_LEFT)) {
        px_ -= move_speed * dt;
        aim_dx_ = -1;
        aim_dy_ = 0;
    } else if ((down & KEY_RIGHT) || (pressed & KEY_RIGHT)) {
        px_ += move_speed * dt;
        aim_dx_ = 1;
        aim_dy_ = 0;
    }

    if (pressed & KEY_UP) {
        aim_dx_ = 0;
        aim_dy_ = -1;
    } else if (pressed & KEY_DOWN) {
        aim_dx_ = 0;
        aim_dy_ = 1;
    }

    // Jump Physics
    if ((pressed & KEY_UP) || ((pressed & KEY_A) && !grounded_)) {
        if (grounded_) {
            vy_ = -7.5f;
            grounded_ = false;
            SoundEvent(Sound::Jump);
        }
    }

    // Gravity
    vy_ += 16.0f * dt;
    py_ += vy_ * dt;

    // Ground collision at y = 9.0 (surface level)
    float ground_level = 9.0f;
    if (py_ >= ground_level) {
        py_ = ground_level;
        vy_ = 0.0f;
        grounded_ = true;
    }

    // Action A: Dig / Mine
    if ((pressed & KEY_A) && grounded_) {
        Award(15);
        wood_++;
        stone_++;
        SoundEvent(Sound::Action);
    }

    // Action B: Build / Attack
    if (pressed & KEY_B) {
        Award(30);
        crystal_++;
        SoundEvent(Sound::Hit);
    }

    // Biome Exploration Tracker
    uint8_t cur_biome = GetBiome(static_cast<int>(px_));
    if (!(biomes_visited_ & (1 << cur_biome))) {
        biomes_visited_ |= (1 << cur_biome);
        Award(100);
        SoundEvent(Sound::Score);
    }

    // Environmental Hazards (Volcano Lava at biome 6)
    if (cur_biome == 6 && py_ >= ground_level) {
        if (hurt_cd_ <= 0.0f) {
            hp_--;
            hurt_cd_ = 1.0f;
            SoundEvent(Sound::Collision);
        }
    }

    // Victory: All 7 biomes explored or Beacon reached
    if (biomes_visited_ == 0x7F) {
        Award(500);
        Finish(true);
    } else if (hp_ <= 0) {
        Finish(false);
    } else if (elapsed_ > (difficulty_ == 0 ? 180.0 : difficulty_ == 1 ? 120.0 : 90.0)) {
        Finish(biomes_visited_ >= 4);
    }
}

int Game101MicroLight::Progress() const {
    int count = 0;
    for (int b = 0; b < 7; ++b) {
        if (biomes_visited_ & (1 << b)) count++;
    }
    return count * 100 / 7;
}

void Game101MicroLight::Draw(uint8_t* fb) {
    // 1. Sky Rendering with Smooth Day-Dusk-Night Cycle
    float phase = day_clock_ / 180.0f; // 0..1
    uint8_t sky_r, sky_g, sky_b;

    if (phase < 0.40f) {
        // Daytime (Cyan / Light Blue)
        sky_r = 60; sky_g = 160; sky_b = 230;
    } else if (phase < 0.55f) {
        // Sunset / Dusk (Orange / Crimson)
        float t = (phase - 0.40f) / 0.15f;
        sky_r = static_cast<uint8_t>(60 + t * (200 - 60));
        sky_g = static_cast<uint8_t>(160 - t * (160 - 90));
        sky_b = static_cast<uint8_t>(230 - t * (230 - 60));
    } else if (phase < 0.85f) {
        // Night (Deep Navy with Twinkling Stars)
        sky_r = 12; sky_g = 20; sky_b = 40;
    } else {
        // Dawn transition
        float t = (phase - 0.85f) / 0.15f;
        sky_r = static_cast<uint8_t>(12 + t * (60 - 12));
        sky_g = static_cast<uint8_t>(20 + t * (160 - 20));
        sky_b = static_cast<uint8_t>(40 + t * (230 - 40));
    }

    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            Px(fb, x, y, sky_r, sky_g, sky_b);
        }
    }

    // Night Stars
    if (phase >= 0.55f && phase < 0.85f) {
        Px(fb, 2, 2, 220, 230, 255);
        Px(fb, 7, 3, 200, 210, 240);
        Px(fb, 12, 1, 240, 240, 255);
        Px(fb, 4, 5, 180, 200, 220);
    }

    // 2. Terrain Generation & Rendering in Screen Window
    int center_x = static_cast<int>(px_);
    int screen_cam_offset = center_x - 7;

    for (int sx = 0; sx < 16; ++sx) {
        int wx = screen_cam_offset + sx;
        uint8_t biome = GetBiome(wx);

        int sy = 10; // Surface y
        uint8_t surf_r = 65, surf_g = 153, surf_b = 72; // Grass

        switch (biome) {
            case 0: // Grassland
                surf_r = 65; surf_g = 153; surf_b = 72;
                break;
            case 1: // Forest
                surf_r = 32; surf_g = 110; surf_b = 45;
                if ((wx % 6) == 0) { // Tree Trunk & Leaves
                    Px(fb, sx, sy - 1, 143, 91, 47);
                    Px(fb, sx, sy - 2, 42, 130, 54);
                }
                break;
            case 2: // Lake
                surf_r = 35; surf_g = 112; surf_b = 211; // Water
                break;
            case 3: // Desert
                surf_r = 225; surf_g = 184; surf_b = 94; // Sand
                if ((wx % 7) == 0) Px(fb, sx, sy - 1, 53, 141, 83); // Cactus
                break;
            case 4: // Snow
                surf_r = 210; surf_g = 238; surf_b = 245; // Snow
                break;
            case 5: // Swamp
                surf_r = 80; surf_g = 112; surf_b = 75; // Mud
                break;
            case 6: // Volcano
                surf_r = 83; surf_g = 69; surf_b = 82; // Basalt
                if ((wx % 4) == 0) {
                    surf_r = 249; surf_g = 88; surf_b = 25; // Lava pool
                }
                break;
        }

        // Surface tile
        Px(fb, sx, sy, surf_r, surf_g, surf_b);

        // Subsurface Dirt & Deep Stone
        for (int y = sy + 1; y < 16; ++y) {
            if (y == sy + 1) {
                Px(fb, sx, y, 116, 79, 49); // Dirt
            } else {
                Px(fb, sx, y, 93, 98, 112); // Stone
            }
        }
    }

    // 3. Player Rendering (Strictly 2 pixels: Head Yellow, Body Cyan)
    int pl_sx = 7; // Player locked to screen center x=7
    int pl_sy = static_cast<int>(std::round(py_));

    if (pl_sy >= 2 && pl_sy < 16) {
        if (hurt_cd_ > 0.0f && (static_cast<int>(hurt_cd_ * 10) % 2 == 1)) {
            // White blink when invulnerable
            Px(fb, pl_sx, pl_sy - 1, 255, 255, 255);
            Px(fb, pl_sx, pl_sy, 255, 255, 255);
        } else {
            // Yellow Head
            Px(fb, pl_sx, pl_sy - 1, 255, 230, 80);
            // Cyan Body
            Px(fb, pl_sx, pl_sy, 60, 190, 220);
        }
    }

    // 4. Aim Cursor Dot
    int cursor_x = pl_sx + aim_dx_;
    int cursor_y = pl_sy + aim_dy_;
    if (cursor_x >= 0 && cursor_x < 16 && cursor_y >= 0 && cursor_y < 16) {
        Px(fb, cursor_x, cursor_y, 91, 240, 249);
    }

    // 5. Health Bar (Top-Right: x = 11..15, y = 0)
    for (int h = 0; h < max_hp_; ++h) {
        int hx = 15 - h;
        if (h < hp_) {
            Px(fb, hx, 0, 237, 55, 59); // Active Health (Red)
        } else {
            Px(fb, hx, 0, 70, 20, 25);  // Lost Health (Dark Red)
        }
    }
}

} // namespace arcade
