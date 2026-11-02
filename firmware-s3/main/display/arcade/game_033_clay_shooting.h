#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game033ClayShooting : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_LAUNCHING = 1;
    static constexpr uint8_t STATE_ROUND_CLEAR = 2;
    static constexpr uint8_t STATE_GAMEOVER = 3;

    static constexpr int MAX_CLAYS = 2;
    static constexpr int MAX_ROUNDS = 5;

    struct Clay {
        float x;
        float y;
        float vx;
        float vy;
        bool active;
        bool shattered;
        float shatter_timer;
    };

    Game033ClayShooting();
    ~Game033ClayShooting() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "Clay Shooting (1978)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    int GetCurrentRound() const { return current_round_; }
    int GetAmmo() const { return ammo_; }
    int GetClaysHit() const { return total_hits_; }

    float GetCrosshairX() const { return crosshair_x_; }
    float GetCrosshairY() const { return crosshair_y_; }

    void SetCrosshair(float x, float y) { crosshair_x_ = x; crosshair_y_ = y; }
    void SetAmmo(int a) { ammo_ = a; }
    void LaunchDoubleTrap();
    bool PullTrigger();

private:
    void LaunchRound();
    void UpdateClays(float dt);
    void CheckRoundProgression();

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;
    int current_round_;
    int total_hits_;
    int round_hits_;
    int ammo_;

    float crosshair_x_;
    float crosshair_y_;
    float muzzle_flash_;

    Clay clays_[MAX_CLAYS];
};

} // namespace arcade
