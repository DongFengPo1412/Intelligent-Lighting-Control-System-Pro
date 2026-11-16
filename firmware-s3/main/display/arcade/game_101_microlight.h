// game_101_microlight.h —— #101 微光纪元 (MicroLight)
// 原作与原型设计: 队友 / 《微光纪元：横版世界》 16x16 WS2812 模拟
// 移植与统一街机大厅整合: 未来道具研究所 · PixelArcade Core
#pragma once
#include "arcade_b3_helpers.h"
#include <cstdint>

namespace arcade {

enum MicroTile : uint8_t {
    TILE_AIR = 0,
    TILE_GRASS = 1,
    TILE_DIRT = 2,
    TILE_STONE = 3,
    TILE_WOOD = 4,
    TILE_LEAF = 5,
    TILE_SAND = 6,
    TILE_SNOW = 7,
    TILE_ICE = 8,
    TILE_WATER = 9,
    TILE_MUD = 10,
    TILE_BASALT = 11,
    TILE_LAVA = 12,
    TILE_CACTUS = 13,
    TILE_COPPER = 14,
    TILE_CRYSTAL = 15,
    TILE_COAL = 16,
    TILE_FLOWER = 17,
    TILE_TORCH = 18,
    TILE_WOOD_WALL = 19,
    TILE_STONE_WALL = 20,
    TILE_BRIDGE = 21,
    TILE_LADDER = 22,
    TILE_PLATFORM = 23,
    TILE_CAMPFIRE = 24,
    TILE_BEACON = 25,
    TILE_CHEST = 26,
    TILE_RUIN = 27,
    TILE_MUSHROOM = 28,
    TILE_BEDROCK = 29,
    TILE_COUNT = 30
};

class Game101MicroLight : public BatchCartridge {
public:
    static constexpr int kMaxEdits = 256;
    static constexpr int kMaxEnemies = 4;
    static constexpr int kBiomeWidth = 40;

    enum ResourceKind : uint8_t {
        RES_WOOD = 0,
        RES_STONE = 1,
        RES_DIRT = 2,
        RES_SAND = 3,
        RES_SNOW = 4,
        RES_ICE = 5,
        RES_ORE = 6,
        RES_COAL = 7,
        RES_CRYSTAL = 8,
        RES_FIBER = 9,
        RES_BERRY = 10,
        RES_RELIC = 11,
        RES_COUNT = 12
    };

    enum BuildSlot : uint8_t {
        BUILD_TORCH = 0,
        BUILD_WOOD_WALL = 1,
        BUILD_STONE_WALL = 2,
        BUILD_BRIDGE = 3,
        BUILD_CAMPFIRE = 4,
        BUILD_BEACON = 5,
        BUILD_SLOT_COUNT = 6
    };

    enum EnemyKind : uint8_t {
        ENEMY_SLIME = 0,
        ENEMY_SCORPION = 1,
        ENEMY_ICEBUG = 2,
        ENEMY_WISP = 3
    };

    struct TileEdit {
        int32_t x = 0;
        int16_t y = 0;
        uint8_t tile = TILE_AIR;
        bool valid = false;
        uint32_t stamp = 0;
    };

    struct Enemy {
        float x = 0.0f;
        float y = 0.0f;
        uint8_t kind = ENEMY_SLIME;
        int8_t hp = 2;
        float attack_timer = 0.0f;
        bool active = false;
    };

    uint8_t GetId() const override { return 101; }
    const char* GetName() const override { return "微光纪元"; }
    const char* GetEnglishName() const override { return "MicroLight"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    CartridgeStatus GetStatus() const override {
        CartridgeStatus s = BatchCartridge::GetStatus();
        s.lives = static_cast<uint8_t>(std::max(0, hp_));
        return s;
    }

    void SetReplaySeed(uint32_t seed) {
        replay_seed_ = seed;
        replay_seeded_ = true;
    }
    void UseRandomSeeds() { replay_seeded_ = false; }

    // Deterministic world/state queries & test helpers (also bound on RAM)
    static int FloorDiv(int a, int b);
    static int FloorMod(int a, int b);
    uint8_t GetBiome(int world_x) const;
    int GetSurfaceAt(int world_x) const;
    uint8_t GetTile(int world_x, int world_y) const;
    bool PutTile(int world_x, int world_y, uint8_t tile);
    bool IsSolidTile(int world_x, int world_y) const;
    int VisitedBiomeCount() const;

    void GetTarget(int& out_x, int& out_y) const;
    float GetPlayerX() const { return px_; }
    float GetPlayerY() const { return py_; }
    bool IsGrounded() const { return grounded_; }
    int GetHp() const { return hp_; }
    int GetMaxHp() const { return max_hp_; }
    uint8_t GetVisitedBiomesMask() const { return biomes_visited_; }
    int GetResource(ResourceKind r) const { return (r < RES_COUNT) ? inv_[r] : 0; }
    void SetResource(ResourceKind r, int v) { if (r < RES_COUNT) inv_[r] = std::max(0, v); }
    int GetEditCount() const;
    int GetEnemyCount() const;
    uint8_t GetBuildIndex() const { return build_index_; }
    void SelectBuildSlot(uint8_t idx) { build_index_ = idx % BUILD_SLOT_COUNT; }
    void SetDayClock(float clk) { day_clock_ = clk; }
    bool SpawnEnemyAt(float x, float y, uint8_t kind, int hp);
    bool MineTarget();
    bool BuildAtTarget();
    bool AttackTarget();

private:
    bool replay_seeded_ = false;
    uint32_t replay_seed_ = 0, last_seed_ = 0;
    uint32_t world_seed_ = 9527;
    uint32_t prng_ = 9527;

    // 玩家物理与状态 (1x2 AABB: [px_, px_+1) x [py_, py_+2))
    float px_ = 0.0f;
    float py_ = 9.0f;
    float vx_ = 0.0f;
    float vy_ = 0.0f;
    bool grounded_ = false;
    float coyote_ = 0.0f;
    float jump_buffer_ = 0.0f;
    int hp_ = 5;
    int max_hp_ = 5;
    int facing_ = 1;
    int aim_dx_ = 1;
    int aim_dy_ = 0;
    int inv_[RES_COUNT]{};
    uint8_t pick_tier_ = 1;
    uint8_t sword_tier_ = 0;
    uint8_t build_index_ = BUILD_TORCH;
    uint8_t biomes_visited_ = 0;
    int beacons_placed_ = 0;
    float day_clock_ = 32.0f;
    float hurt_cd_ = 0.0f;
    float hit_flash_ = 0.0f;
    float mine_cd_ = 0.0f;
    float build_cd_ = 0.0f;
    float attack_cd_ = 0.0f;
    float attack_fx_ = 0.0f;
    float spawn_timer_ = 4.0f;
    int mine_tx_ = 0, mine_ty_ = 0;
    uint8_t mine_tid_ = TILE_AIR;
    int mine_hits_ = 0;
    uint32_t edit_clock_ = 0;

    TileEdit edits_[kMaxEdits]{};
    Enemy enemies_[kMaxEnemies]{};

    void Setup() override;
    void Tick(float dt, uint16_t down, uint16_t pressed) override;
    void Draw(uint8_t* fb) override;
    int Progress() const override;

    uint8_t GetRawTile(int world_x, int world_y) const;
    bool Collides(float x, float y) const;
    bool MoveAxis(float delta, bool horizontal);
    uint8_t InFluid() const;
    bool TouchingCactus() const;
    void ApplyDamage(int amt);
    bool IsNight() const;
    float AmbientLight() const;
    bool CanAffordSlot(uint8_t slot) const;
    void PaySlot(uint8_t slot);
    uint8_t SlotToTile(uint8_t slot) const;
    void SpawnAmbientEnemy();
    void UpdateEnemies(float dt);
};

} // namespace arcade
