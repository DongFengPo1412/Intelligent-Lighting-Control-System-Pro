#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game116LunarLander : public Cartridge {
public:
    Game116LunarLander();
    ~Game116LunarLander() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 116; }
    std::string GetName() const override { return "Lunar Lander (1979)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_FLYING = 0,
        STATE_TOUCHDOWN_SAFE = 1,
        STATE_CRASHED = 2,
        STATE_GAME_OVER = 3
    };

    struct LandingPad {
        int x_start{0};
        int x_end{0};
        int y{0};
        int multiplier{1};
    };

    static constexpr int NUM_PADS = 3;
    static constexpr float SAFE_MAX_VY = 1.25f;
    static constexpr float SAFE_MAX_VX = 0.85f;

    GameState GetState() const { return state_; }
    int GetScore() const { return score_; }
    int GetLives() const { return lives_; }
    float GetFuel() const { return fuel_; }
    float GetLanderX() const { return px_; }
    float GetLanderY() const { return py_; }
    float GetVelocityX() const { return vx_; }
    float GetVelocityY() const { return vy_; }
    bool IsThrusting() const { return thrusting_; }

    const LandingPad& GetPad(int i) const { return pads_[i]; }

    void SetPositionAndVelocity(float x, float y, float vx, float vy);

private:
    GameState state_{STATE_FLYING};
    float state_timer_{0.0f};
    int score_{0};
    int lives_{3};
    float fuel_{400.0f}; // Limited fuel units

    // Lunar Lander Physics
    float px_{8.0f};
    float py_{2.0f};
    float vx_{0.0f};
    float vy_{0.0f};
    bool thrusting_{false};

    // Terrain profile: terrain_y_[x] is the surface height at column x (0..15)
    uint8_t terrain_y_[16];
    LandingPad pads_[NUM_PADS];

    void InitSite();
    void BuildTerrain();
    void UpdatePhysics(float dt, uint32_t buttons);
    void CheckTouchdown();
};

} // namespace arcade