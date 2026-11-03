#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game118YieArKungFu : public Cartridge {
public:
    Game118YieArKungFu();
    ~Game118YieArKungFu() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 118; }
    std::string GetName() const override { return "Yie Ar Kung-Fu (1985)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_FIGHTING = 0,
        STATE_KO_VICTORY = 1,
        STATE_PLAYER_DEFEATED = 2,
        STATE_GAME_OVER = 3
    };

    enum AttackStance {
        STANCE_IDLE = 0,
        STANCE_MID_PUNCH = 1,
        STANCE_MID_KICK = 2,
        STANCE_HIGH_JUMP_KICK = 3,
        STANCE_LOW_SWEEP = 4
    };

    struct Projectile {
        float x{0.0f};
        float y{0.0f};
        float vx{0.0f};
        bool active{false};
    };

    struct Fighter {
        float x{4.0f};
        float y{13.0f};
        float vy{0.0f};
        int hp{100};
        int facing{1}; // 1 = Right, -1 = Left
        AttackStance stance{STANCE_IDLE};
        float stance_timer{0.0f};
        float hurt_timer{0.0f};
    };

    static constexpr int MAX_PROJECTILES = 2;

    GameState GetState() const { return state_; }
    int GetScore() const { return score_; }
    int GetLives() const { return lives_; }
    int GetRound() const { return round_; }
    const Fighter& GetPlayer() const { return player_; }
    const Fighter& GetOpponent() const { return opponent_; }
    const Projectile& GetProjectile(int i) const { return projectiles_[i]; }

    void ExecutePlayerAttack(AttackStance stance);

private:
    GameState state_{STATE_FIGHTING};
    float state_timer_{0.0f};
    int score_{0};
    int lives_{3};
    int round_{1};

    Fighter player_;
    Fighter opponent_;
    Projectile projectiles_[MAX_PROJECTILES];
    float ai_action_timer_{0.0f};

    void InitMatch();
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateOpponentAI(float dt);
    void UpdateProjectiles(float dt);
    void CheckStrikesAndParries();
};

} // namespace arcade