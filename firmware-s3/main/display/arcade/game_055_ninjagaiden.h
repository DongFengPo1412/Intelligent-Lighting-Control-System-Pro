#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game055NinjaGaiden : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_PLAYING = 1;
    static constexpr uint8_t STATE_DEAD = 2;
    static constexpr uint8_t STATE_VICTORY = 3;

    static constexpr uint8_t ACTION_IDLE = 0;
    static constexpr uint8_t ACTION_SLASH = 1;
    static constexpr uint8_t ACTION_WALL_JUMP = 2;
    static constexpr uint8_t ACTION_BAR_SWING = 3;

    static constexpr int MAX_ENEMIES = 4;

    struct Enemy {
        float x;
        float y;
        float vx;
        int health;
        bool active;
    };

    Game055NinjaGaiden();
    ~Game055NinjaGaiden() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "Ninja Gaiden (1988)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    int GetHealth() const { return player_health_; }
    int GetLives() const { return lives_; }
    uint8_t GetAction() const { return action_; }
    bool IsCarryingCrate() const { return is_carrying_crate_; }
    bool IsHangingBar() const { return is_hanging_bar_; }
    float GetPlayerX() const { return player_x_; }
    float GetPlayerY() const { return player_y_; }

    void SetPlayerPos(float x, float y) { player_x_ = x; player_y_ = y; }
    void TriggerBarGrab();
    void TriggerWallRebound();

private:
    void InitStage();
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateEnemies(float dt);
    void UpdateCrate(float dt);
    void CheckCollisions();

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;
    int lives_;
    int player_health_;
    int enemies_defeated_;
    int total_enemies_;

    // Player position & physics
    float player_x_;
    float player_y_;
    float player_vx_;
    float player_vy_;
    int player_facing_;     // +1 or -1
    uint8_t action_;
    float action_timer_;

    // Gymnastic Bar Swing & Wall rebound
    bool is_hanging_bar_;
    float swing_timer_;
    float swing_angle_;

    // Breakable street crate / booth
    float crate_x_;
    float crate_y_;
    float crate_vx_;
    bool is_carrying_crate_;
    bool crate_thrown_;
    bool crate_active_;

    Enemy enemies_[MAX_ENEMIES];
};

} // namespace arcade
