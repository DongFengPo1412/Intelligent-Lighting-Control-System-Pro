#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game105Arkanoid : public Cartridge {
public:
    Game105Arkanoid();
    ~Game105Arkanoid() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 105; }
    std::string GetName() const override { return "Arkanoid (1986)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_PLAYING = 0,
        STATE_BOSS_DOH = 1,
        STATE_BALL_LOST = 2,
        STATE_ROUND_CLEAR = 3,
        STATE_GAME_OVER = 4
    };

    enum CapsuleType {
        CAPSULE_NONE = 0,
        CAPSULE_LASER = 1,   // 'L': Red laser guns
        CAPSULE_ENLARGE = 2, // 'E': Blue wide paddle
        CAPSULE_CATCH = 3,   // 'C': Green magnetic catch
        CAPSULE_SLOW = 4,    // 'S': Orange slow ball
        CAPSULE_BREAK = 5    // 'B': Purple warp exit
    };

    struct Capsule {
        float x{0.0f};
        float y{0.0f};
        CapsuleType type{CAPSULE_NONE};
        bool active{false};
    };

    struct LaserBolt {
        float x{0.0f};
        float y{0.0f};
        bool active{false};
    };

    static constexpr int BRICK_ROWS = 5;
    static constexpr int BRICK_COLS = 7;
    static constexpr int MAX_CAPSULES = 2;
    static constexpr int MAX_LASERS = 4;

    GameState GetState() const { return state_; }
    int GetScore() const { return score_; }
    int GetLives() const { return lives_; }
    int GetRound() const { return round_; }
    float GetPaddleX() const { return paddle_x_; }
    int GetPaddleWidth() const { return paddle_width_; }
    CapsuleType GetActiveCapsule() const { return active_powerup_; }
    bool IsLaserEquipped() const { return active_powerup_ == CAPSULE_LASER; }
    bool IsBallCaught() const { return ball_caught_; }
    int GetDohHP() const { return doh_hp_; }

    const Capsule& GetCapsule(int i) const { return capsules_[i]; }

    void SetPowerup(CapsuleType type);
    void SpawnBossDoh();

private:
    GameState state_{STATE_PLAYING};
    float state_timer_{0.0f};
    int score_{0};
    int lives_{3};
    int round_{1};
    int bricks_remaining_{0};

    // Vaus Paddle
    float paddle_x_{6.5f};
    int paddle_width_{3};
    CapsuleType active_powerup_{CAPSULE_NONE};
    float laser_cooldown_{0.0f};

    // Energy Ball
    float ball_x_{8.0f};
    float ball_y_{13.0f};
    float ball_vx_{4.0f};
    float ball_vy_{-6.0f};
    bool ball_caught_{false};
    float ball_catch_offset_{0.0f};

    // Space Bricks: 0 = empty, 1..4 = colored bricks, 9 = silver (2 hits)
    uint8_t bricks_[BRICK_ROWS][BRICK_COLS];

    // Dimensional Boss Doh
    int doh_hp_{12};
    float doh_x_{6.0f};
    float doh_vx_{2.5f};

    Capsule capsules_[MAX_CAPSULES];
    LaserBolt lasers_[MAX_LASERS];

    void InitBricks();
    void ResetBall();
    void SpawnCapsule(float x, float y);
    void UpdatePaddle(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateBall(float dt);
    void UpdateCapsules(float dt);
    void UpdateLasers(float dt);
    void UpdateBossDoh(float dt);
    void CheckBallPaddleCollision();
    void CheckBallBrickCollision();
    void CheckLaserBrickCollision();
};

} // namespace arcade
