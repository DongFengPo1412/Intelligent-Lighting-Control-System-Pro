#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>
#include <vector>

namespace arcade {

class Game079SubRoc3D : public Cartridge {
public:
    Game079SubRoc3D();
    ~Game079SubRoc3D() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 79; }
    std::string GetName() const override { return "SubRoc-3D (1982)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_PLAYING = 0,
        STATE_PLAYER_HIT = 1,
        STATE_GAME_OVER = 2,
        STATE_VICTORY = 3
    };

    enum TargetZone {
        ZONE_AIR = 0,     // Sky planes
        ZONE_SURFACE = 1, // Ships on horizon
        ZONE_DEPTH = 2    // Submarines & sea mines
    };

    struct Target {
        float x{0.0f};
        float y{0.0f};
        float z{10.0f}; // 10.0 (far away) to 1.0 (close threat)
        float vx{0.0f};
        float vy{0.0f};
        float vz{-1.5f}; // moves toward screen
        TargetZone zone{ZONE_SURFACE};
        bool active{false};
        int hp{1};
    };

    struct Projectile {
        float x{0.0f};
        float y{0.0f};
        float z{1.0f};  // 1.0 (fired from sub) to 10.0 (distant hit)
        float vz{12.0f};
        bool is_air_missile{false}; // true = air missile (B), false = torpedo (A)
        bool active{false};
    };

    GameState GetState() const { return state_; }
    int GetScore() const { return score_; }
    int GetLives() const { return lives_; }
    float GetCrosshairX() const { return cx_; }
    float GetCrosshairY() const { return cy_; }
    int GetActiveTargetsCount() const;

private:
    void SpawnTarget();
    void UpdateCrosshair(float dt, uint32_t buttons);
    void FireTorpedo();
    void FireAirMissile();
    void UpdateTargets(float dt);
    void UpdateProjectiles(float dt);
    void CheckHits();

    GameState state_{STATE_PLAYING};
    float state_timer_{0.0f};
    int score_{0};
    int high_score_{12000};
    int lives_{3};
    int targets_destroyed_{0};

    // Periscope crosshair coordinates
    float cx_{7.5f};
    float cy_{7.5f};

    static constexpr int MAX_TARGETS = 5;
    Target targets_[MAX_TARGETS];

    static constexpr int MAX_PROJECTILES = 4;
    Projectile projs_[MAX_PROJECTILES];

    float spawn_timer_{0.0f};
};

} // namespace arcade
