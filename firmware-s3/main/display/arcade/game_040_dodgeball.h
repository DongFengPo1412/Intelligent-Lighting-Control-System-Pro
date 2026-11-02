#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game040Dodgeball : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_PLAYING = 1;
    static constexpr uint8_t STATE_DEAD = 2;
    static constexpr uint8_t STATE_VICTORY = 3;

    struct PlayerChar {
        float x;
        float y;
        int hp;
        bool is_alive;
    };

    struct Ball {
        float x;
        float y;
        float vx;
        float vy;
        int state; // 0: Free on ground, 1: Held by Player, 2: Held by Enemy, 3: Thrown by Player, 4: Thrown by Enemy
        bool is_super;
    };

    Game040Dodgeball();
    ~Game040Dodgeball() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "Super Dodge Ball (1987)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    int GetPlayerHP() const { return player_.hp; }
    int GetEnemyHP() const { return enemy_.hp; }
    bool PlayerHasBall() const { return ball_.state == 1; }

    float GetPlayerX() const { return player_.x; }
    float GetPlayerY() const { return player_.y; }
    float GetBallX() const { return ball_.x; }
    float GetBallY() const { return ball_.y; }

    void SetPlayerPos(float x, float y) { player_.x = x; player_.y = y; }
    void ThrowBall(bool is_super);
    bool TryCatchBall();

private:
    void InitCourt();
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateAI(float dt);
    void UpdateBall(float dt);
    void CheckBallHits();

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;
    float charge_timer_; // 蓄力魔球计时
    float catch_window_timer_; // 接球瞬间判定

    PlayerChar player_;
    PlayerChar enemy_;
    Ball ball_;
};

} // namespace arcade
