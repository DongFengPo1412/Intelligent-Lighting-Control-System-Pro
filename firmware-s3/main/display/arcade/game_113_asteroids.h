#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game113Asteroids : public Cartridge {
public:
    Game113Asteroids();
    ~Game113Asteroids() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 113; }
    std::string GetName() const override { return "Asteroids (1979)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_PLAYING = 0,
        STATE_PLAYER_EXPLODING = 1,
        STATE_WAVE_CLEAR = 2,
        STATE_GAME_OVER = 3
    };

    struct Asteroid {
        float x{0.0f};
        float y{0.0f};
        float vx{0.0f};
        float vy{0.0f};
        int tier{0}; // 3 = Large, 2 = Medium, 1 = Small
        bool active{false};
    };

    struct Bullet {
        float x{0.0f};
        float y{0.0f};
        float vx{0.0f};
        float vy{0.0f};
        float life{0.0f};
        bool active{false};
    };

    struct Saucer {
        float x{0.0f};
        float y{0.0f};
        float vx{0.0f};
        bool active{false};
        float shoot_timer{0.0f};
    };

    static constexpr int MAX_ASTEROIDS = 16;
    static constexpr int MAX_BULLETS = 4;

    GameState GetState() const { return state_; }
    int GetScore() const { return score_; }
    int GetLives() const { return lives_; }
    int GetWave() const { return wave_; }
    float GetPlayerX() const { return px_; }
    float GetPlayerY() const { return py_; }
    float GetAngle() const { return angle_; }
    float GetVelocityX() const { return vx_; }
    float GetVelocityY() const { return vy_; }

    const Asteroid& GetAsteroid(int i) const { return asteroids_[i]; }
    const Saucer& GetSaucer() const { return saucer_; }

    void HyperspaceJump();

private:
    GameState state_{STATE_PLAYING};
    float state_timer_{0.0f};
    int score_{0};
    int lives_{3};
    int wave_{1};

    // Vector Ship
    float px_{8.0f};
    float py_{8.0f};
    float vx_{0.0f};
    float vy_{0.0f};
    float angle_{-1.57079f}; // Facing UP initially (-PI/2)
    bool thrusting_{false};

    Asteroid asteroids_[MAX_ASTEROIDS];
    Bullet bullets_[MAX_BULLETS];
    Saucer saucer_;
    float saucer_spawn_timer_{10.0f};

    void InitWave();
    void FireBullet();
    void SpawnAsteroid(float x, float y, float vx, float vy, int tier);
    void SplitAsteroid(int idx);
    void UpdateShip(float dt, uint32_t buttons);
    void UpdateAsteroids(float dt);
    void UpdateBullets(float dt);
    void UpdateSaucer(float dt);
    void CheckCollisions();
    void CheckWaveClear();
};

} // namespace arcade