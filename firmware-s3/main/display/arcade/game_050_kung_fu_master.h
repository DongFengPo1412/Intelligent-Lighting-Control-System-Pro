#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game050KungFuMaster : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_PLAYING = 1;
    static constexpr uint8_t STATE_DEAD = 2;
    static constexpr uint8_t STATE_VICTORY = 3;

    static constexpr int MAX_ENEMIES = 4;
    static constexpr int MAX_DAGGERS = 2;

    enum EnemyType {
        TYPE_GRIPPER = 0,
        TYPE_KNIFE_THROWER = 1,
        TYPE_BOSS_STAFF = 2
    };

    struct Enemy {
        float x;
        EnemyType type;
        float vx;
        int health;
        bool active;
        bool is_gripping;   // Clamped onto player
        float attack_timer;
    };

    struct Dagger {
        float x;
        float y;
        float vx;
        bool active;
    };

    Game050KungFuMaster();
    ~Game050KungFuMaster() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "Kung-Fu Master (1984)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    int GetHealth() const { return player_health_; }
    int GetGripperCount() const { return num_gripping_; }
    int GetAttackStance() const { return attack_stance_; }

    float GetPlayerX() const { return player_x_; }
    void SetPlayerPos(float x) { player_x_ = x; }

    void ExecutePunch();
    void ExecuteKick();
    void ShakeOffGrippers();

private:
    void InitFloor();
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateEnemies(float dt);
    void UpdateDaggers(float dt);
    void CheckHitboxes();

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;
    int player_health_;
    int enemies_defeated_;
    int total_stage_enemies_;

    float player_x_;
    int player_facing_;     // +1 (right) or -1 (left)
    bool is_crouching_;
    bool is_jumping_;
    float jump_y_offset_;
    float jump_vy_;

    int attack_stance_;     // 0: Idle, 1: High Punch, 2: Mid Kick, 3: Low Sweep, 4: Jump Kick
    float attack_timer_;
    float attack_duration_;

    int num_gripping_;      // Number of thugs currently clinging to player
    int wiggle_counter_;    // Counter for shaking free

    Enemy enemies_[MAX_ENEMIES];
    Dagger daggers_[MAX_DAGGERS];
};

} // namespace arcade
