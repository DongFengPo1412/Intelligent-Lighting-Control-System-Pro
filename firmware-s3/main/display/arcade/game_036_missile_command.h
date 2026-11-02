#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game036MissileCommand : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_PLAYING = 1;
    static constexpr uint8_t STATE_WAVE_CLEAR = 2;
    static constexpr uint8_t STATE_GAMEOVER = 3;

    static constexpr int MAX_ENEMY_MISSILES = 8;
    static constexpr int MAX_INTERCEPTORS = 4;
    static constexpr int MAX_EXPLOSIONS = 6;
    static constexpr int NUM_CITIES = 6;

    struct EnemyMissile {
        float x;
        float y;
        float target_x;
        float target_y;
        float vx;
        float vy;
        bool active;
    };

    struct Interceptor {
        float x;
        float y;
        float target_x;
        float target_y;
        float vx;
        float vy;
        bool active;
    };

    struct Explosion {
        float x;
        float y;
        float radius;
        float max_radius;
        float timer;
        bool active;
    };

    Game036MissileCommand();
    ~Game036MissileCommand() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "Missile Command (1980)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    int GetWave() const { return wave_; }
    int GetAmmo() const { return ammo_; }
    int GetSurvivingCities() const;

    float GetCrosshairX() const { return crosshair_x_; }
    float GetCrosshairY() const { return crosshair_y_; }

    void SetCrosshair(float x, float y) { crosshair_x_ = x; crosshair_y_ = y; }
    void SetAmmo(int a) { ammo_ = a; }
    bool FireInterceptor();

private:
    void InitWave();
    void SpawnEnemyMissile();
    void UpdateEnemyMissiles(float dt);
    void UpdateInterceptors(float dt);
    void UpdateExplosions(float dt);
    void CheckCollisions();
    void CheckWaveEnd();

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;
    int wave_;
    int ammo_;
    int enemy_spawn_remaining_;
    float spawn_timer_;

    float crosshair_x_;
    float crosshair_y_;

    bool cities_alive_[NUM_CITIES];
    EnemyMissile enemy_missiles_[MAX_ENEMY_MISSILES];
    Interceptor interceptors_[MAX_INTERCEPTORS];
    Explosion explosions_[MAX_EXPLOSIONS];
};

} // namespace arcade
