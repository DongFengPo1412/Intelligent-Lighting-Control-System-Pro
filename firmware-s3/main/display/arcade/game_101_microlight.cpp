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

namespace {

inline uint64_t MicroHashStep(uint64_t h, int64_t val) {
    uint64_t z = static_cast<uint64_t>(val) + 0x9E3779B97F4A7C15ULL;
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    h ^= z ^ (z >> 31);
    return h * 0x00E7037ED1A0B428ULL;
}

inline double MicroRnd(int64_t a, int64_t b, int64_t c) {
    uint64_t h = 0xA0761D6478BD642FULL;
    h = MicroHashStep(h, a);
    h = MicroHashStep(h, b);
    h = MicroHashStep(h, c);
    return static_cast<double>(h >> 11) / static_cast<double>(1ULL << 53);
}

inline double SmoothStep(double t) {
    return t * t * (3.0 - 2.0 * t);
}

inline double ValueNoise(double x, double y, int64_t seed) {
    int64_t xi = static_cast<int64_t>(std::floor(x));
    int64_t yi = static_cast<int64_t>(std::floor(y));
    double a = SmoothStep(x - static_cast<double>(xi));
    double b = SmoothStep(y - static_cast<double>(yi));
    double t00 = MicroRnd(xi, yi, seed);
    double t10 = MicroRnd(xi + 1, yi, seed);
    double t01 = MicroRnd(xi, yi + 1, seed);
    double t11 = MicroRnd(xi + 1, yi + 1, seed);
    return (t00 * (1.0 - a) + t10 * a) * (1.0 - b) + (t01 * (1.0 - a) + t11 * a) * b;
}

struct TileMeta {
    bool solid;
    uint8_t hardness;
    uint8_t light;
    uint8_t r, g, b;
    int8_t drop1;
    uint8_t drop1_qty;
    int8_t drop2;
    uint8_t drop2_qty;
};

constexpr int8_t R_NONE = -1;
const TileMeta kTiles[TILE_COUNT] = {
    /* AIR        */ {false, 0,   0,   0,   0,   0, R_NONE, 0, R_NONE, 0},
    /* GRASS      */ {true,  2,   0,  65, 153,  72, Game101MicroLight::RES_DIRT, 1, R_NONE, 0},
    /* DIRT       */ {true,  2,   0, 116,  79,  49, Game101MicroLight::RES_DIRT, 1, R_NONE, 0},
    /* STONE      */ {true,  3,   0,  93,  98, 112, Game101MicroLight::RES_STONE, 1, R_NONE, 0},
    /* WOOD       */ {true,  2,   0, 143,  91,  47, Game101MicroLight::RES_WOOD, 2, R_NONE, 0},
    /* LEAF       */ {false, 1,   0,  42, 130,  54, Game101MicroLight::RES_FIBER, 1, R_NONE, 0},
    /* SAND       */ {true,  1,   0, 225, 184,  94, Game101MicroLight::RES_SAND, 1, R_NONE, 0},
    /* SNOW       */ {true,  1,   0, 209, 238, 245, Game101MicroLight::RES_SNOW, 1, R_NONE, 0},
    /* ICE        */ {true,  2,   0, 105, 199, 229, Game101MicroLight::RES_ICE, 1, R_NONE, 0},
    /* WATER      */ {false, 0,   0,  35, 112, 211, R_NONE, 0, R_NONE, 0},
    /* MUD        */ {true,  2,   0,  83, 103,  61, Game101MicroLight::RES_DIRT, 1, R_NONE, 0},
    /* BASALT     */ {true,  4,   0,  83,  69,  82, Game101MicroLight::RES_STONE, 1, R_NONE, 0},
    /* LAVA       */ {false, 0,   4, 249,  88,  25, R_NONE, 0, R_NONE, 0},
    /* CACTUS     */ {true,  2,   0,  53, 141,  83, Game101MicroLight::RES_WOOD, 1, Game101MicroLight::RES_FIBER, 1},
    /* COPPER     */ {true,  3,   0, 203, 113,  55, Game101MicroLight::RES_ORE, 1, R_NONE, 0},
    /* CRYSTAL    */ {true,  4,   2, 169,  88, 240, Game101MicroLight::RES_CRYSTAL, 1, R_NONE, 0},
    /* COAL       */ {true,  3,   0,  55,  64,  79, Game101MicroLight::RES_COAL, 1, R_NONE, 0},
    /* FLOWER     */ {false, 1,   0, 237, 129, 167, Game101MicroLight::RES_FIBER, 1, R_NONE, 0},
    /* TORCH      */ {false, 1,   4, 255, 191,  83, Game101MicroLight::RES_WOOD, 1, R_NONE, 0},
    /* WOOD_WALL  */ {true,  2,   0, 159, 110,  63, Game101MicroLight::RES_WOOD, 1, R_NONE, 0},
    /* STONE_WALL */ {true,  3,   0, 149, 159, 168, Game101MicroLight::RES_STONE, 1, R_NONE, 0},
    /* BRIDGE     */ {true,  2,   0, 175, 127,  72, Game101MicroLight::RES_WOOD, 1, R_NONE, 0},
    /* LADDER     */ {false, 2,   0, 230, 165,  75, Game101MicroLight::RES_WOOD, 1, R_NONE, 0},
    /* PLATFORM   */ {true,  2,   0, 168, 118,  67, Game101MicroLight::RES_WOOD, 1, R_NONE, 0},
    /* CAMPFIRE   */ {false, 1,   5, 255, 126,  48, Game101MicroLight::RES_WOOD, 1, R_NONE, 0},
    /* BEACON     */ {true,  4,   8,  91, 240, 249, Game101MicroLight::RES_CRYSTAL, 1, R_NONE, 0},
    /* CHEST      */ {true,  2,   1, 249, 198,  53, R_NONE, 0, R_NONE, 0},
    /* RUIN       */ {true,  3,   0, 115, 122, 157, Game101MicroLight::RES_STONE, 1, R_NONE, 0},
    /* MUSHROOM   */ {false, 1,   1, 218, 102, 194, Game101MicroLight::RES_BERRY, 1, R_NONE, 0},
    /* BEDROCK    */ {true,  255, 0,  43,  48,  67, R_NONE, 0, R_NONE, 0},
};

} // namespace

int Game101MicroLight::FloorDiv(int a, int b) {
    int q = a / b;
    int r = a % b;
    if (r != 0 && ((r < 0) != (b < 0))) {
        --q;
    }
    return q;
}

int Game101MicroLight::FloorMod(int a, int b) {
    int r = a % b;
    if (r < 0) {
        r += b;
    }
    return r;
}

uint8_t Game101MicroLight::GetBiome(int world_x) const {
    return static_cast<uint8_t>(FloorMod(FloorDiv(world_x, kBiomeWidth), 7));
}

int Game101MicroLight::GetSurfaceAt(int world_x) const {
    if (world_x >= -4 && world_x <= 4) {
        return 11; // Safe spawn platform
    }
    uint8_t biome = GetBiome(world_x);
    static const int kLevels[7] = {11, 10, 13, 11, 9, 12, 9};
    double level = static_cast<double>(kLevels[biome]);
    double slope = (ValueNoise(static_cast<double>(world_x) / 27.0, 0.0, int64_t(world_seed_) + 10) - 0.5) * 3.0;
    double detail = (ValueNoise(static_cast<double>(world_x) / 8.0, 0.0, int64_t(world_seed_) + 11) - 0.5) * 1.8;
    if (biome == 3) {
        detail += (ValueNoise(static_cast<double>(world_x) / 14.0, 1.0, int64_t(world_seed_) + 13) - 0.5) * 2.5;
    } else if (biome == 6) {
        detail += (ValueNoise(static_cast<double>(world_x) / 11.0, 1.0, int64_t(world_seed_) + 17) - 0.5) * 3.0;
    }
    int pos_in_biome = FloorMod(world_x, kBiomeWidth);
    if (pos_in_biome < 6) {
        uint8_t prev_b = GetBiome(world_x - 8);
        double a = SmoothStep(static_cast<double>(pos_in_biome) / 6.0);
        level = static_cast<double>(kLevels[prev_b]) * (1.0 - a) + level * a;
    } else if (pos_in_biome > kBiomeWidth - 6) {
        uint8_t next_b = GetBiome(world_x + 8);
        double a = SmoothStep(static_cast<double>(pos_in_biome - (kBiomeWidth - 6)) / 6.0);
        level = level * (1.0 - a) + static_cast<double>(kLevels[next_b]) * a;
    }
    int surf = static_cast<int>(std::llround(level + slope + detail));
    return std::max(7, std::min(15, surf));
}

uint8_t Game101MicroLight::GetRawTile(int world_x, int world_y) const {
    if (world_y >= 26) {
        return TILE_BEDROCK;
    }
    int surface = GetSurfaceAt(world_x);
    uint8_t biome = GetBiome(world_x);
    int64_t s = static_cast<int64_t>(world_seed_);

    if (world_y < surface) {
        if (biome == 2 && world_y >= 11) {
            return TILE_WATER;
        }
        if (biome == 5 && world_y >= 11 && FloorMod(FloorDiv(world_x, 5), 3) != 0) {
            return TILE_WATER;
        }
        if (biome == 6 && world_y >= 11 && MicroRnd(FloorDiv(world_x, 4), s, 451) < 0.22) {
            return TILE_LAVA;
        }
        if (world_x >= -4 && world_x <= 4) {
            if (world_y == surface - 1) {
                if (world_x == 2) return TILE_WOOD;
                if (world_x == 3) return TILE_COPPER;
                if (world_x == -2) return TILE_FLOWER;
            }
            return TILE_AIR;
        }
        if (world_y == surface - 1 && MicroRnd(world_x, s, 901) < 0.02 && std::abs(world_x) > 10) {
            return TILE_CHEST;
        }
        if (biome == 3 && (world_y == surface - 1 || world_y == surface - 2)) {
            if (MicroRnd(world_x, s, 222) < 0.08) {
                return TILE_CACTUS;
            }
        }
        if (biome == 0 || biome == 1 || biome == 5) {
            double tree_chance = (biome == 1) ? 0.22 : (biome == 5 ? 0.10 : 0.08);
            bool has_tree = (MicroRnd(world_x, s, 123) < tree_chance) &&
                            (MicroRnd(world_x - 1, s, 123) >= tree_chance) &&
                            (std::abs(world_x) > 4);
            if (has_tree && (world_y == surface - 1 || world_y == surface - 2)) {
                return TILE_WOOD;
            }
            for (int dx = -1; dx <= 1; ++dx) {
                int bx = world_x + dx;
                bool b_tree = (MicroRnd(bx, s, 123) < tree_chance) &&
                              (MicroRnd(bx - 1, s, 123) >= tree_chance) &&
                              (std::abs(bx) > 4);
                if (b_tree) {
                    int top = GetSurfaceAt(bx) - 3;
                    if (world_y == top || (dx == 0 && world_y == top - 1)) {
                        return TILE_LEAF;
                    }
                }
            }
        }
        if (world_y == surface - 1 && MicroRnd(world_x, s, 314) < 0.14) {
            if (biome == 5) return TILE_MUSHROOM;
            if (biome == 0 || biome == 1) return TILE_FLOWER;
        }
        return TILE_AIR;
    }

    if (world_y == surface) {
        switch (biome) {
            case 0: return TILE_GRASS;
            case 1: return TILE_GRASS;
            case 2: return TILE_SAND;
            case 3: return TILE_SAND;
            case 4: return TILE_SNOW;
            case 5: return TILE_MUD;
            case 6: return TILE_BASALT;
            default: return TILE_GRASS;
        }
    }

    int depth = world_y - surface;
    if (depth <= 2) {
        if (biome == 2 || biome == 3) return TILE_SAND;
        if (biome == 4) return TILE_ICE;
        if (biome == 6) return TILE_BASALT;
        return TILE_DIRT;
    }

    double cave = ValueNoise(world_x / 9.0, world_y / 7.0, s + 52) * 0.67 +
                  ValueNoise(world_x / 3.0, world_y / 4.0, s + 53) * 0.33;
    if (cave > 0.66) {
        return TILE_AIR;
    }
    double ore = ValueNoise(world_x / 3.7, world_y / 3.5, s + 38);
    if (depth >= 5 && ore > 0.77) return TILE_CRYSTAL;
    if (ore > 0.66) return TILE_COPPER;
    if (ore < 0.24) return TILE_COAL;
    return (biome == 6 || world_y > 20) ? TILE_BASALT : TILE_STONE;
}

uint8_t Game101MicroLight::GetTile(int world_x, int world_y) const {
    for (int i = 0; i < kMaxEdits; ++i) {
        if (edits_[i].valid && edits_[i].x == world_x && edits_[i].y == world_y) {
            return edits_[i].tile;
        }
    }
    return GetRawTile(world_x, world_y);
}

bool Game101MicroLight::PutTile(int world_x, int world_y, uint8_t tile) {
    if (tile >= TILE_COUNT) return false;
    ++edit_clock_;
    int free_idx = -1;
    int oldest_idx = 0;
    uint32_t oldest_stamp = 0xFFFFFFFFu;
    for (int i = 0; i < kMaxEdits; ++i) {
        if (edits_[i].valid && edits_[i].x == world_x && edits_[i].y == world_y) {
            edits_[i].tile = tile;
            edits_[i].stamp = edit_clock_;
            return true;
        }
        if (!edits_[i].valid && free_idx < 0) {
            free_idx = i;
        }
        if (edits_[i].valid && edits_[i].stamp < oldest_stamp) {
            oldest_stamp = edits_[i].stamp;
            oldest_idx = i;
        }
    }
    int slot = (free_idx >= 0) ? free_idx : oldest_idx;
    edits_[slot].x = static_cast<int32_t>(world_x);
    edits_[slot].y = static_cast<int16_t>(world_y);
    edits_[slot].tile = tile;
    edits_[slot].valid = true;
    edits_[slot].stamp = edit_clock_;
    return true;
}

bool Game101MicroLight::IsSolidTile(int world_x, int world_y) const {
    uint8_t tid = GetTile(world_x, world_y);
    return tid < TILE_COUNT && kTiles[tid].solid;
}

int Game101MicroLight::GetEditCount() const {
    int c = 0;
    for (int i = 0; i < kMaxEdits; ++i) {
        if (edits_[i].valid) ++c;
    }
    return c;
}

int Game101MicroLight::GetEnemyCount() const {
    int c = 0;
    for (int i = 0; i < kMaxEnemies; ++i) {
        if (enemies_[i].active) ++c;
    }
    return c;
}

int Game101MicroLight::VisitedBiomeCount() const {
    int count = 0;
    for (int b = 0; b < 7; ++b) {
        if (biomes_visited_ & (1 << b)) ++count;
    }
    return count;
}

bool Game101MicroLight::Collides(float x, float y) const {
    if (y < -40.0f) return true;
    int x0 = static_cast<int>(std::floor(x + 1e-4f));
    int x1 = static_cast<int>(std::floor(x + 1.0f - 1e-4f));
    int y0 = static_cast<int>(std::floor(y + 1e-4f));
    int y1 = static_cast<int>(std::floor(y + 2.0f - 1e-4f));
    for (int tx = x0; tx <= x1; ++tx) {
        for (int ty = y0; ty <= y1; ++ty) {
            if (IsSolidTile(tx, ty)) return true;
        }
    }
    return false;
}

bool Game101MicroLight::MoveAxis(float delta, bool horizontal) {
    if (delta == 0.0f) return false;
    float tx = horizontal ? (px_ + delta) : px_;
    float ty = horizontal ? py_ : (py_ + delta);
    if (!Collides(tx, ty)) {
        if (horizontal) px_ = tx;
        else py_ = ty;
        return false;
    }
    float lo = 0.0f, hi = 1.0f;
    for (int iter = 0; iter < 12; ++iter) {
        float mid = (lo + hi) * 0.5f;
        float nx = horizontal ? (px_ + delta * mid) : px_;
        float ny = horizontal ? py_ : (py_ + delta * mid);
        if (Collides(nx, ny)) hi = mid;
        else lo = mid;
    }
    if (horizontal) {
        px_ += delta * lo;
        vx_ = 0.0f;
    } else {
        py_ += delta * lo;
        vy_ = 0.0f;
    }
    return true;
}

uint8_t Game101MicroLight::InFluid() const {
    int xs[2] = {static_cast<int>(std::floor(px_ + 0.1f)), static_cast<int>(std::floor(px_ + 0.9f))};
    int ys[2] = {static_cast<int>(std::floor(py_ + 0.5f)), static_cast<int>(std::floor(py_ + 1.5f))};
    for (int tx : xs) {
        for (int ty : ys) {
            uint8_t tid = GetTile(tx, ty);
            if (tid == TILE_WATER || tid == TILE_LAVA) return tid;
        }
    }
    return TILE_AIR;
}

bool Game101MicroLight::TouchingCactus() const {
    int xs[2] = {static_cast<int>(std::floor(px_ - 0.1f)), static_cast<int>(std::floor(px_ + 1.1f))};
    int ys[2] = {static_cast<int>(std::floor(py_ + 0.2f)), static_cast<int>(std::floor(py_ + 1.8f))};
    for (int tx : xs) {
        for (int ty : ys) {
            if (GetTile(tx, ty) == TILE_CACTUS) return true;
        }
    }
    return false;
}

void Game101MicroLight::ApplyDamage(int amt) {
    if (hurt_cd_ > 0.0f || state_ != STATE_PLAYING) return;
    hp_ = std::max(0, hp_ - amt);
    hurt_cd_ = 1.0f;
    hit_flash_ = 0.3f;
    SoundEvent(Sound::Collision);
}

void Game101MicroLight::GetTarget(int& out_x, int& out_y) const {
    int px_i = static_cast<int>(std::floor(px_ + 0.5f));
    int py_i = static_cast<int>(std::floor(py_ + 0.45f));
    if (aim_dx_ != 0) {
        out_x = px_i + aim_dx_;
        out_y = py_i + 1;
    } else if (aim_dy_ < 0) {
        out_x = px_i;
        out_y = py_i - 1;
    } else {
        out_x = px_i;
        out_y = py_i + 2;
    }
}

bool Game101MicroLight::IsNight() const {
    float phase = std::fmod(day_clock_, 180.0f) / 180.0f;
    return phase > 0.60f || phase < 0.09f;
}

float Game101MicroLight::AmbientLight() const {
    float phase = std::fmod(day_clock_, 180.0f) / 180.0f;
    float v = (0.58f - std::abs(phase - 0.45f)) * 3.1f;
    return std::max(0.15f, std::min(1.0f, v));
}

bool Game101MicroLight::CanAffordSlot(uint8_t slot) const {
    switch (slot) {
        case BUILD_TORCH:      return inv_[RES_WOOD] >= 1 && inv_[RES_FIBER] >= 1;
        case BUILD_WOOD_WALL:  return inv_[RES_WOOD] >= 2;
        case BUILD_STONE_WALL: return inv_[RES_STONE] >= 2;
        case BUILD_BRIDGE:     return inv_[RES_WOOD] >= 2;
        case BUILD_CAMPFIRE:   return inv_[RES_WOOD] >= 2 && inv_[RES_COAL] >= 1;
        case BUILD_BEACON:     return inv_[RES_ORE] >= 2 && inv_[RES_CRYSTAL] >= 2;
        default:               return false;
    }
}

void Game101MicroLight::PaySlot(uint8_t slot) {
    switch (slot) {
        case BUILD_TORCH:      inv_[RES_WOOD] -= 1; inv_[RES_FIBER] -= 1; break;
        case BUILD_WOOD_WALL:  inv_[RES_WOOD] -= 2; break;
        case BUILD_STONE_WALL: inv_[RES_STONE] -= 2; break;
        case BUILD_BRIDGE:     inv_[RES_WOOD] -= 2; break;
        case BUILD_CAMPFIRE:   inv_[RES_WOOD] -= 2; inv_[RES_COAL] -= 1; break;
        case BUILD_BEACON:     inv_[RES_ORE] -= 2; inv_[RES_CRYSTAL] -= 2; break;
        default: break;
    }
}

uint8_t Game101MicroLight::SlotToTile(uint8_t slot) const {
    switch (slot) {
        case BUILD_TORCH:      return TILE_TORCH;
        case BUILD_WOOD_WALL:  return TILE_WOOD_WALL;
        case BUILD_STONE_WALL: return TILE_STONE_WALL;
        case BUILD_BRIDGE:     return TILE_BRIDGE;
        case BUILD_CAMPFIRE:   return TILE_CAMPFIRE;
        case BUILD_BEACON:     return TILE_BEACON;
        default:               return TILE_TORCH;
    }
}

bool Game101MicroLight::MineTarget() {
    if (mine_cd_ > 0.0f) return false;
    mine_cd_ = 0.12f;
    int tx = 0, ty = 0;
    GetTarget(tx, ty);
    uint8_t tid = GetTile(tx, ty);
    if (tid == TILE_AIR || tid == TILE_WATER || tid == TILE_LAVA || tid == TILE_BEDROCK) {
        return false;
    }
    if (tid == TILE_CHEST) {
        PutTile(tx, ty, TILE_AIR);
        inv_[RES_RELIC] += 1;
        inv_[RES_ORE] += 2;
        inv_[RES_CRYSTAL] += 1;
        inv_[RES_BERRY] += 2;
        Award(80);
        SoundEvent(Sound::Score);
        return true;
    }
    if (tx != mine_tx_ || ty != mine_ty_ || tid != mine_tid_) {
        mine_tx_ = tx;
        mine_ty_ = ty;
        mine_tid_ = tid;
        mine_hits_ = 0;
    }
    mine_hits_ += 1 + static_cast<int>(pick_tier_);
    if (mine_hits_ < kTiles[tid].hardness) {
        SoundEvent(Sound::Action);
        return false;
    }
    const TileMeta& meta = kTiles[tid];
    if (meta.drop1 != R_NONE) inv_[meta.drop1] += meta.drop1_qty;
    if (meta.drop2 != R_NONE) inv_[meta.drop2] += meta.drop2_qty;
    PutTile(tx, ty, TILE_AIR);
    mine_tid_ = TILE_AIR;
    mine_hits_ = 0;
    Award(15u * meta.hardness);
    SoundEvent(Sound::Action);
    return true;
}

bool Game101MicroLight::BuildAtTarget() {
    if (build_cd_ > 0.0f) return false;
    build_cd_ = 0.15f;
    int tx = 0, ty = 0;
    GetTarget(tx, ty);
    uint8_t existing = GetTile(tx, ty);

    uint8_t slot = build_index_;
    if (existing == TILE_WATER) {
        slot = BUILD_BRIDGE;
    }
    uint8_t place_tid = SlotToTile(slot);
    if (!CanAffordSlot(slot)) {
        return false;
    }
    if (slot == BUILD_BRIDGE) {
        if (existing != TILE_WATER && existing != TILE_AIR) return false;
    } else if (existing != TILE_AIR) {
        return false;
    }
    // Never place a solid block intersecting the player's 1x2 body
    if (kTiles[place_tid].solid &&
        px_ < float(tx + 1) && (px_ + 1.0f) > float(tx) &&
        py_ < float(ty + 1) && (py_ + 2.0f) > float(ty)) {
        return false;
    }
    bool has_support = IsSolidTile(tx, ty + 1) || IsSolidTile(tx - 1, ty) ||
                       IsSolidTile(tx + 1, ty) || GetTile(tx, ty + 1) == TILE_WATER;
    if (!has_support) {
        return false;
    }
    PaySlot(slot);
    PutTile(tx, ty, place_tid);
    if (place_tid == TILE_BEACON) {
        beacons_placed_++;
    }
    Award(30);
    SoundEvent(Sound::Score);
    return true;
}

bool Game101MicroLight::AttackTarget() {
    if (attack_cd_ > 0.0f) return false;
    int tx = 0, ty = 0;
    GetTarget(tx, ty);
    for (int i = 0; i < kMaxEnemies; ++i) {
        Enemy& e = enemies_[i];
        if (!e.active) continue;
        bool near_target = std::abs(e.x - float(tx)) <= 1.65f && std::abs(e.y - float(ty)) <= 1.85f;
        bool near_player = std::abs(e.x - px_) <= 1.55f && std::abs(e.y - (py_ + 1.0f)) <= 1.55f;
        if (near_target || near_player) {
            attack_cd_ = 0.25f;
            attack_fx_ = 0.16f;
            e.hp -= static_cast<int8_t>(1 + sword_tier_);
            // Knockback away from player
            e.x += (e.x >= px_) ? 1.2f : -1.2f;
            if (e.hp <= 0) {
                e.active = false;
                inv_[RES_FIBER] += 1;
                if ((B3Random(prng_) & 3u) == 0u) inv_[RES_ORE] += 1;
                Award(40);
            } else {
                Award(15);
            }
            SoundEvent(Sound::Hit);
            return true;
        }
    }
    return false;
}

bool Game101MicroLight::SpawnEnemyAt(float x, float y, uint8_t kind, int hp) {
    for (int i = 0; i < kMaxEnemies; ++i) {
        if (!enemies_[i].active) {
            enemies_[i].active = true;
            enemies_[i].x = x;
            enemies_[i].y = y;
            enemies_[i].kind = kind;
            enemies_[i].hp = static_cast<int8_t>(hp);
            enemies_[i].attack_timer = 0.3f;
            return true;
        }
    }
    return false;
}

void Game101MicroLight::SpawnAmbientEnemy() {
    if (GetEnemyCount() >= kMaxEnemies) return;
    int px_i = static_cast<int>(std::floor(px_));
    bool underground = py_ > static_cast<float>(GetSurfaceAt(px_i) + 2);
    if (!underground && !IsNight()) return;
    int side = (B3Random(prng_) & 1u) ? 1 : -1;
    int dist = 8 + static_cast<int>(B3Random(prng_) % 4u);
    int sx = px_i + side * dist;
    if (underground) {
        int sy = static_cast<int>(std::floor(py_)) + static_cast<int>((B3Random(prng_) % 5u)) - 2;
        if (!IsSolidTile(sx, sy)) {
            SpawnEnemyAt(float(sx), float(sy), ENEMY_WISP, 2);
        }
    } else {
        int surf = GetSurfaceAt(sx);
        int sy = surf - 1;
        if (!IsSolidTile(sx, sy)) {
            uint8_t biome = GetBiome(sx);
            uint8_t kind = (biome == 3) ? ENEMY_SCORPION : (biome == 4 ? ENEMY_ICEBUG : (biome == 5 ? ENEMY_WISP : ENEMY_SLIME));
            int ehp = (kind == ENEMY_SCORPION) ? 3 : 2;
            SpawnEnemyAt(float(sx), float(sy), kind, ehp);
        }
    }
}

void Game101MicroLight::UpdateEnemies(float dt) {
    for (int i = 0; i < kMaxEnemies; ++i) {
        Enemy& e = enemies_[i];
        if (!e.active) continue;
        if (std::abs(e.x - px_) > 18.0f) {
            e.active = false;
            continue;
        }
        e.attack_timer = std::max(0.0f, e.attack_timer - dt);
        float dir = (px_ > e.x) ? 1.0f : -1.0f;
        float speed = (e.kind == ENEMY_SLIME) ? 1.0f : 1.45f;
        e.x += dir * speed * dt;
        if (e.kind == ENEMY_WISP) {
            float dy = std::max(-1.0f, std::min(1.0f, (py_ + 1.0f) - e.y));
            e.y += dy * dt * 0.65f;
        } else {
            int sx = static_cast<int>(std::floor(e.x));
            e.y = static_cast<float>(GetSurfaceAt(sx) - 1);
        }
        if (std::abs(e.x - px_) < 1.05f && std::abs(e.y - (py_ + 1.0f)) < 1.3f && e.attack_timer <= 0.0f) {
            ApplyDamage(1);
            e.attack_timer = 1.4f;
        }
    }
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
    world_seed_ = seed ? seed : 9527u;
    prng_ = world_seed_;

    for (int i = 0; i < kMaxEdits; ++i) edits_[i] = TileEdit{};
    for (int i = 0; i < kMaxEnemies; ++i) enemies_[i] = Enemy{};
    for (int r = 0; r < RES_COUNT; ++r) inv_[r] = 0;
    inv_[RES_WOOD] = 5;
    inv_[RES_STONE] = 3;
    inv_[RES_FIBER] = 3;
    inv_[RES_BERRY] = 3;

    px_ = 0.0f;
    py_ = static_cast<float>(GetSurfaceAt(0) - 2);
    vx_ = 0.0f;
    vy_ = 0.0f;
    grounded_ = true;
    coyote_ = 0.12f;
    jump_buffer_ = 0.0f;
    hp_ = 5;
    max_hp_ = 5;
    facing_ = 1;
    aim_dx_ = 1;
    aim_dy_ = 0;
    pick_tier_ = 1;
    sword_tier_ = 0;
    build_index_ = BUILD_TORCH;
    biomes_visited_ = static_cast<uint8_t>(1u << GetBiome(0));
    beacons_placed_ = 0;
    day_clock_ = 32.0f;
    hurt_cd_ = 0.0f;
    hit_flash_ = 0.0f;
    mine_cd_ = 0.0f;
    build_cd_ = 0.0f;
    attack_cd_ = 0.0f;
    attack_fx_ = 0.0f;
    spawn_timer_ = 4.0f;
    mine_tid_ = TILE_AIR;
    mine_hits_ = 0;
    edit_clock_ = 0;
}

void Game101MicroLight::Tick(float dt, uint16_t down, uint16_t pressed) {
    day_clock_ = std::fmod(day_clock_ + dt, 180.0f);
    hurt_cd_ = std::max(0.0f, hurt_cd_ - dt);
    hit_flash_ = std::max(0.0f, hit_flash_ - dt);
    mine_cd_ = std::max(0.0f, mine_cd_ - dt);
    build_cd_ = std::max(0.0f, build_cd_ - dt);
    attack_cd_ = std::max(0.0f, attack_cd_ - dt);
    attack_fx_ = std::max(0.0f, attack_fx_ - dt);
    jump_buffer_ = std::max(0.0f, jump_buffer_ - dt);

    if (grounded_) coyote_ = 0.12f;
    else coyote_ = std::max(0.0f, coyote_ - dt);

    uint8_t fluid = InFluid();
    int move_dir = (((down | pressed) & KEY_RIGHT) ? 1 : 0) - (((down | pressed) & KEY_LEFT) ? 1 : 0);
    if (move_dir != 0) {
        facing_ = move_dir;
    }

    // Distinct aim direction without moving horizontally when holding UP or DOWN
    if ((down & KEY_UP) || ((pressed & KEY_UP) && !grounded_)) {
        aim_dx_ = 0;
        aim_dy_ = -1;
    } else if (down & KEY_DOWN) {
        aim_dx_ = 0;
        aim_dy_ = 1;
    } else {
        aim_dx_ = facing_;
        aim_dy_ = 0;
    }

    float max_speed = (fluid == TILE_WATER) ? 3.25f : 5.3f;
    int px_foot = static_cast<int>(std::floor(px_ + 0.5f));
    int py_foot = static_cast<int>(std::floor(py_ + 2.05f));
    bool on_ice = grounded_ && GetTile(px_foot, py_foot) == TILE_ICE;
    if (move_dir != 0) {
        vx_ = static_cast<float>(move_dir) * max_speed;
    } else if (on_ice) {
        vx_ *= std::max(0.0f, 1.0f - 2.5f * dt); // Ice inertia glide
    } else {
        vx_ = 0.0f;
    }
    MoveAxis(vx_ * dt, true);

    // Jump exclusively on KEY_UP (never overloaded with KEY_A mining!)
    if (pressed & KEY_UP) {
        jump_buffer_ = 0.15f;
    }
    if (jump_buffer_ > 0.0f && (grounded_ || coyote_ > 0.0f) && fluid != TILE_WATER) {
        vy_ = -10.1f;
        jump_buffer_ = 0.0f;
        coyote_ = 0.0f;
        grounded_ = false;
        SoundEvent(Sound::Jump);
    } else if (fluid == TILE_WATER && ((down & KEY_UP) || (pressed & KEY_UP))) {
        vy_ = std::min(vy_, -3.4f);
    }

    if (fluid == TILE_WATER) {
        vy_ = std::min(3.2f, vy_ + 6.5f * dt);
        if (down & KEY_DOWN) vy_ = 3.3f;
    } else {
        vy_ = std::min(12.0f, vy_ + 21.0f * dt);
    }

    bool hit_y = MoveAxis(vy_ * dt, false);
    grounded_ = (hit_y && vy_ == 0.0f && Collides(px_, py_ + 0.04f)) ||
                (Collides(px_, py_ + 0.04f) && vy_ >= 0.0f);
    if (grounded_) {
        vy_ = std::max(0.0f, vy_);
    }

    // Environmental hazards: Lava burn & Desert Cactus prick
    if (fluid == TILE_LAVA || TouchingCactus()) {
        ApplyDamage(1);
    }
    if (py_ > 60.0f) {
        hp_ = 0;
    }

    // Action A: Directional Mine / Open Chest (pure action, zero jump conflict)
    if (pressed & KEY_A) {
        MineTarget();
    }

    // Action B: Attack nearby enemy OR Build structure (consumes inventory & places block)
    if (pressed & KEY_B) {
        if (!AttackTarget()) {
            BuildAtTarget();
        }
    }

    // Auto-ration berry healing when damaged and holding DOWN+A/B or picking mushroom
    if (hp_ > 0 && hp_ < max_hp_ && inv_[RES_BERRY] >= 2 && (down & KEY_DOWN) && (pressed & KEY_A)) {
        inv_[RES_BERRY] -= 2;
        hp_ = std::min(max_hp_, hp_ + 1);
        SoundEvent(Sound::Score);
    }

    // Ambient enemy lifecycle & combat
    spawn_timer_ -= dt;
    if (spawn_timer_ <= 0.0f) {
        spawn_timer_ = IsNight() ? 4.5f : 9.5f;
        SpawnAmbientEnemy();
    }
    UpdateEnemies(dt);

    // Biome exploration tracker
    uint8_t cur_biome = GetBiome(static_cast<int>(std::floor(px_)));
    if (!(biomes_visited_ & (1u << cur_biome))) {
        biomes_visited_ |= static_cast<uint8_t>(1u << cur_biome);
        Award(100);
        SoundEvent(Sound::Score);
    }

    // Victory / Loss rules (proper bitmask popcount check, never raw bitmask >= 4!)
    if (biomes_visited_ == 0x7F || beacons_placed_ >= 1) {
        Award(500);
        Finish(true);
    } else if (hp_ <= 0) {
        Finish(false);
    } else if (elapsed_ > (difficulty_ == 0 ? 180.0 : difficulty_ == 1 ? 120.0 : 90.0)) {
        Finish(VisitedBiomeCount() >= 4);
    }
}

int Game101MicroLight::Progress() const {
    return VisitedBiomeCount() * 100 / 7;
}

void Game101MicroLight::Draw(uint8_t* fb) {
    float phase = std::fmod(day_clock_, 180.0f) / 180.0f;
    float ambient = AmbientLight();

    int cam_x = static_cast<int>(std::llround(px_)) - 7;
    int cam_y = static_cast<int>(std::llround(py_)) - 7;

    // Gather light sources inside or near viewport
    struct LightSrc { float x, y, rad; };
    LightSrc lights[20];
    int nlights = 0;
    lights[nlights++] = {px_ + 0.5f, py_ + 1.0f, 3.1f};
    for (int sy = 0; sy < 16 && nlights < 20; ++sy) {
        for (int sx = 0; sx < 16 && nlights < 20; ++sx) {
            uint8_t tid = GetTile(cam_x + sx, cam_y + sy);
            if (tid < TILE_COUNT && kTiles[tid].light > 0) {
                lights[nlights++] = {float(cam_x + sx) + 0.5f, float(cam_y + sy) + 0.5f, float(kTiles[tid].light)};
            }
        }
    }

    for (int sy = 0; sy < 16; ++sy) {
        int wy = cam_y + sy;
        for (int sx = 0; sx < 16; ++sx) {
            int wx = cam_x + sx;
            uint8_t biome = GetBiome(wx);
            int surf = GetSurfaceAt(wx);
            uint8_t tid = GetTile(wx, wy);

            if (tid == TILE_AIR) {
                if (wy < surf) {
                    static const uint8_t kDaySky[7][3] = {
                        {70, 167, 235}, {50, 132, 204}, {64, 168, 235},
                        {118, 179, 223}, {112, 182, 211}, {55, 133, 139}, {138, 97, 112}
                    };
                    float sr = 12.0f * (1.0f - ambient) + float(kDaySky[biome][0]) * ambient;
                    float sg = 20.0f * (1.0f - ambient) + float(kDaySky[biome][1]) * ambient;
                    float sb = 42.0f * (1.0f - ambient) + float(kDaySky[biome][2]) * ambient;
                    if (phase > 0.48f && phase < 0.66f) {
                        float dusk = 0.34f * std::max(0.0f, 1.0f - std::abs(phase - 0.58f) / 0.11f);
                        sr = sr * (1.0f - dusk) + 200.0f * dusk;
                        sg = sg * (1.0f - dusk) + 108.0f * dusk;
                        sb = sb * (1.0f - dusk) + 65.0f * dusk;
                    }
                    if (ambient < 0.52f && MicroRnd(wx, wy, int64_t(world_seed_) + 109) > 0.976) {
                        sr = 167; sg = 198; sb = 230;
                    }
                    Px(fb, sx, sy, int(sr), int(sg), int(sb));
                } else {
                    Px(fb, sx, sy, 12, 14, 27);
                }
            } else {
                const TileMeta& tm = kTiles[tid];
                float illum = (wy <= surf + 1) ? std::max(0.14f, ambient) : 0.18f;
                for (int li = 0; li < nlights; ++li) {
                    float dist = std::hypot(float(wx) + 0.5f - lights[li].x, float(wy) + 0.5f - lights[li].y);
                    float falloff = 0.22f + 0.85f * std::max(0.0f, 1.0f - dist / lights[li].rad);
                    illum = std::max(illum, falloff);
                }
                illum = std::min(1.12f, illum);
                Px(fb, sx, sy,
                   std::min(255, int(tm.r * illum)),
                   std::min(255, int(tm.g * illum)),
                   std::min(255, int(tm.b * illum)));
            }
        }
    }

    // 1-pixel enemies
    static const uint8_t kEnemyRgb[4][3] = {
        {220, 64, 83}, {238, 120, 42}, {115, 218, 253}, {186, 97, 246}
    };
    for (int i = 0; i < kMaxEnemies; ++i) {
        if (!enemies_[i].active) continue;
        int ex = static_cast<int>(std::llround(enemies_[i].x)) - cam_x;
        int ey = static_cast<int>(std::llround(enemies_[i].y)) - cam_y;
        uint8_t ek = enemies_[i].kind % 4;
        Px(fb, ex, ey, kEnemyRgb[ek][0], kEnemyRgb[ek][1], kEnemyRgb[ek][2]);
    }

    // Aim cursor / Attack flash
    int tx = 0, ty = 0;
    GetTarget(tx, ty);
    int ax = tx - cam_x, ay = ty - cam_y;
    if (attack_fx_ > 0.0f) {
        Px(fb, ax, ay, 255, 239, 142);
    } else if (static_cast<int>(day_clock_ * 3.0f) % 2 == 0) {
        Px(fb, ax, ay, 91, 240, 249);
    }

    // Strictly 2-pixel Player (Yellow Head + Cyan Body)
    int pl_sx = static_cast<int>(std::llround(px_)) - cam_x;
    int pl_sy = static_cast<int>(std::llround(py_)) - cam_y;
    if (hurt_cd_ > 0.0f && (static_cast<int>(hurt_cd_ * 10.0f) % 2 == 1)) {
        Px(fb, pl_sx, pl_sy, 255, 255, 255);
        Px(fb, pl_sx, pl_sy + 1, 255, 255, 255);
    } else {
        Px(fb, pl_sx, pl_sy, 255, 222, 96);     // Yellow Head
        Px(fb, pl_sx, pl_sy + 1, 94, 215, 245); // Cyan Body
    }

    // Top-Right Health Bar
    int cap_hp = std::min(7, max_hp_);
    for (int h = 0; h < cap_hp; ++h) {
        int hx = 16 - cap_hp + h;
        if (h < hp_) Px(fb, hx, 0, 251, 42, 70);
        else Px(fb, hx, 0, 69, 24, 43);
    }
}

} // namespace arcade
