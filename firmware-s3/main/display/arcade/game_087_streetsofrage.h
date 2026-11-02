#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game087StreetsOfRage : public Cartridge {
public:
    Game087StreetsOfRage();
    ~Game087StreetsOfRage() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 87; }
    std::string GetName() const override { return "Streets of Rage (1991)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_STREET_BRAWL = 0,
        STATE_POLICE_BACKUP = 1, // Bazooka car animation
        STATE_STAGE_CLEAR = 2,
        STATE_HERO_DEAD = 3
    };

    enum AttackState {
        ATK_NONE = 0,
        ATK_PUNCH = 1,
        ATK_FLYING_KICK = 2,
        ATK_SUPLEX = 3
    };

    struct Thug {
        float x{14.0f};
        float y{10.0f};
        float vx{-2.2f};
        int hp{3};
        bool is_boss{false};
        bool active{false};
        float respawn_timer{0.0f};
    };

    GameState GetState() const { return state_; }
    int GetScore() const { return score_; }
    int GetHeroHp() const { return hero_hp_; }
    int GetLives() const { return lives_; }
    int GetBackupCalls() const { return backup_calls_; }
    float GetPlayerX() const { return px_; }
    float GetPlayerY() const { return py_; }
    AttackState GetAttackState() const { return atk_state_; }

private:
    void ResetStage();
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateThugs(float dt);
    void UpdatePoliceBackup(float dt);
    void CheckCombat();

    GameState state_{STATE_STREET_BRAWL};
    float state_timer_{0.0f};
    int score_{0};
    int high_score_{28000};
    int lives_{3};
    int hero_hp_{100};
    int backup_calls_{1}; // 1 police rocket call per stage
    int thugs_defeated_{0};

    // Hero Axel Stone
    float px_{3.5f};
    float py_{10.5f};
    int facing_{1};
    AttackState atk_state_{ATK_NONE};
    float atk_timer_{0.0f};

    static constexpr int MAX_THUGS = 3;
    Thug thugs_[MAX_THUGS];

    // Police backup animation
    float rocket_x_{0.0f};
    float rocket_y_{14.0f};
    float explosion_timer_{0.0f};
};

} // namespace arcade
