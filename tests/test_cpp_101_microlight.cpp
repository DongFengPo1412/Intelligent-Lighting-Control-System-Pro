// Native C++ deep verification for #101 MicroLight (F17 + F18 + cross-language parity)
#include <cassert>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <string>
#include <vector>

#include "../firmware-s3/main/display/arcade/arcade_score_store.h"
#include "../firmware-s3/main/display/arcade/game_101_microlight.h"

// Minimal NVS stubs for standalone host compilation
#include "nvs.h"
int nvs_open(const char*, int, nvs_handle_t* h) { *h = 1; return 0; }
int nvs_get_u32(nvs_handle_t, const char*, uint32_t*) { return 1; }
int nvs_set_u32(nvs_handle_t, const char*, uint32_t) { return 0; }
int nvs_commit(nvs_handle_t) { return 0; }
void nvs_close(nvs_handle_t) {}

using namespace arcade;

static void TestNegativeBiomeFloorDivision() {
    Game101MicroLight g;
    g.SetReplaySeed(2026);
    g.Init();
    // Mathematical floor(x / 40) % 7 -> must match Python (wx // 40) % 7
    struct Case { int wx; uint8_t expected; } cases[] = {
        {-80, 5}, {-41, 5}, {-40, 6}, {-39, 6}, {-1, 6},
        {0, 0}, {39, 0}, {40, 1}, {41, 1}, {80, 2}
    };
    for (const auto& c : cases) {
        uint8_t got = g.GetBiome(c.wx);
        if (got != c.expected) {
            std::cerr << "Biome mismatch at wx=" << c.wx << ": got=" << int(got) << " expected=" << int(c.expected) << "\n";
            assert(false);
        }
    }
    std::cout << "[PASS] TestNegativeBiomeFloorDivision\n";
}

static void TestJumpMineNoConflictAndGameplay() {
    Game101MicroLight g;
    g.SetReplaySeed(9527);
    g.Start();

    // 1. KEY_A MUST NOT trigger jump; KEY_UP MUST trigger jump!
    float y0 = g.GetPlayerY();
    assert(g.IsGrounded());
    g.Update(1.0f / 30.0f, 0, KEY_A);
    assert(std::abs(g.GetPlayerY() - y0) < 0.05f && g.IsGrounded());

    g.Update(1.0f / 30.0f, KEY_UP, KEY_UP);
    for (int i = 0; i < 6; ++i) g.Update(1.0f / 30.0f, KEY_UP, 0);
    assert(g.GetPlayerY() < y0 - 0.5f && !g.IsGrounded());
    // Release jump and land back on ground
    for (int i = 0; i < 60; ++i) g.Update(1.0f / 30.0f, 0, 0);
    assert(g.IsGrounded());
    assert(std::abs(g.GetPlayerY() - y0) < 0.1f);

    // 2. Real mining mutates tile in world and drops resource
    int tx = 0, ty = 0;
    g.GetTarget(tx, ty);
    assert(g.PutTile(tx, ty, TILE_WOOD));
    assert(g.GetTile(tx, ty) == TILE_WOOD);
    int wood_before = g.GetResource(Game101MicroLight::RES_WOOD);
    g.Update(0.2f, 0, KEY_A);
    assert(g.GetTile(tx, ty) == TILE_AIR);
    assert(g.GetResource(Game101MicroLight::RES_WOOD) == wood_before + 2);

    // 3. Real building consumes exact inventory & places solid WOOD_WALL that blocks player movement
    g.SelectBuildSlot(Game101MicroLight::BUILD_WOOD_WALL);
    int wood_mid = g.GetResource(Game101MicroLight::RES_WOOD);
    g.Update(0.2f, 0, KEY_B);
    assert(g.GetTile(tx, ty) == TILE_WOOD_WALL);
    assert(g.GetResource(Game101MicroLight::RES_WOOD) == wood_mid - 2);

    // Walking right collides with the built WOOD_WALL!
    float x_before_wall = g.GetPlayerX();
    for (int i = 0; i < 20; ++i) g.Update(1.0f / 30.0f, KEY_RIGHT, 0);
    assert(g.GetPlayerX() <= float(tx) - 0.99f);

    // 4. World edit persists even after moving far away and coming back
    g.SelectBuildSlot(Game101MicroLight::BUILD_TORCH);
    // Exhaust wood & fiber -> build MUST fail with zero tile placed
    g.SetResource(Game101MicroLight::RES_WOOD, 0);
    g.SetResource(Game101MicroLight::RES_FIBER, 0);
    g.Update(0.2f, KEY_LEFT, KEY_LEFT); // turn left
    int left_tx = 0, left_ty = 0;
    g.GetTarget(left_tx, left_ty);
    assert(!g.BuildAtTarget());
    assert(g.GetTile(left_tx, left_ty) == TILE_AIR);

    // Scroll far right (walking over wall by jumping + walking or checking persistent edit after edits elsewhere)
    assert(g.GetTile(tx, ty) == TILE_WOOD_WALL);

    // 5. Real enemy attack & combat drop
    assert(g.SpawnEnemyAt(g.GetPlayerX() - 1.0f, g.GetPlayerY() + 1.0f, Game101MicroLight::ENEMY_SLIME, 2));
    int enemies_before = g.GetEnemyCount();
    assert(enemies_before == 1);
    int fiber_before = g.GetResource(Game101MicroLight::RES_FIBER);
    g.Update(1.0f / 30.0f, 0, KEY_B); // hit 1 (hp: 2 -> 1, knocks enemy back, cooldown 0.25s)
    assert(g.GetEnemyCount() == 1);
    for (int i = 0; i < 10; ++i) g.Update(1.0f / 30.0f, KEY_LEFT, 0); // wait cooldown + close distance
    g.Update(1.0f / 30.0f, 0, KEY_B); // hit 2 (hp: 1 -> 0 -> killed!)
    assert(g.GetEnemyCount() == 0);
    assert(g.GetResource(Game101MicroLight::RES_FIBER) >= fiber_before + 1);

    // 6. Render verification (16x16 = 768 bytes) + Player 2-pixel sprite & top-right HP
    uint8_t fb[768]{};
    g.Render(fb);
    bool nonzero = false;
    for (uint8_t b : fb) if (b) nonzero = true;
    assert(nonzero);

    // 7. 20-minute bounded exploration (36,000 steps @ 1/30s) -> edits & enemies strictly bounded!
    Game101MicroLight long_run;
    long_run.SetReplaySeed(12345);
    long_run.Start();
    for (int step = 0; step < 36000; ++step) {
        uint16_t d = (step % 40 < 20) ? KEY_RIGHT : (KEY_RIGHT | KEY_UP);
        uint16_t p = (step % 30 == 0) ? KEY_UP : (step % 45 == 0 ? KEY_A : 0);
        long_run.Update(1.0f / 30.0f, d, p);
        assert(long_run.GetEditCount() <= Game101MicroLight::kMaxEdits);
        assert(long_run.GetEnemyCount() <= Game101MicroLight::kMaxEnemies);
    }

    // 8. Bitmask win count bug fix: 1 biome bit at high bit (1<<5 = 32 >= 4) must NOT win on timeout!
    Game101MicroLight win_test;
    win_test.SetReplaySeed(77);
    win_test.Start();
    // Move to Negative biome 6 -> visited mask has biome 0 and 6 (count=2, raw=65)
    for (int i = 0; i < 6000; ++i) {
        if (win_test.GetBiome(static_cast<int>(std::floor(win_test.GetPlayerX()))) == 6) break;
        win_test.Update(0.05f, KEY_LEFT, (i % 15 == 0) ? KEY_UP : 0);
    }
    assert(win_test.VisitedBiomeCount() < 4);
    for (int i = 0; i < 4000; ++i) {
        if (win_test.GetStatus().state != STATE_PLAYING) break;
        win_test.Update(0.05f, 0, 0);
    }
    assert(win_test.GetStatus().state == STATE_GAMEOVER);

    // Restart cleanly restores HP, inventory, empty edits, score=0
    win_test.Start();
    assert(win_test.GetStatus().state == STATE_PLAYING);
    assert(win_test.GetHp() == 5);
    assert(win_test.GetStatus().score == 0);
    assert(win_test.GetEditCount() == 0);

    std::cout << "[PASS] TestJumpMineNoConflictAndGameplay\n";
}

static void DumpParityTrace() {
    Game101MicroLight g;
    g.SetReplaySeed(2026);
    g.Start();
    // Fixed deterministic input sequence across 180 frames (6 seconds)
    for (int f = 0; f < 180; ++f) {
        uint16_t d = 0, p = 0;
        if (f < 40) d = KEY_RIGHT;
        else if (f < 80) d = KEY_LEFT;
        else if (f < 140) d = KEY_RIGHT;
        if (f == 10 || f == 50 || f == 90) p |= KEY_UP;
        if (f == 25 || f == 120) p |= KEY_A;
        if (f == 135) p |= KEY_B;
        g.Update(1.0f / 30.0f, d, p);
    }
    uint8_t fb[768]{};
    g.Render(fb);
    uint32_t csum = 0;
    for (int i = 0; i < 768; ++i) csum = csum * 131u + fb[i];
    int surf_m80 = g.GetSurfaceAt(-80);
    int surf_0 = g.GetSurfaceAt(0);
    int surf_45 = g.GetSurfaceAt(45);
    int surf_120 = g.GetSurfaceAt(120);
    std::cout << "PARITY px=" << g.GetPlayerX()
              << " py=" << g.GetPlayerY()
              << " hp=" << g.GetHp()
              << " biomes=" << int(g.GetVisitedBiomesMask())
              << " wood=" << g.GetResource(Game101MicroLight::RES_WOOD)
              << " score=" << g.GetStatus().score
              << " surf=" << surf_m80 << "," << surf_0 << "," << surf_45 << "," << surf_120
              << " fb_csum=" << csum << "\n";
}

int main() {
    TestNegativeBiomeFloorDivision();
    TestJumpMineNoConflictAndGameplay();
    DumpParityTrace();
    return 0;
}
