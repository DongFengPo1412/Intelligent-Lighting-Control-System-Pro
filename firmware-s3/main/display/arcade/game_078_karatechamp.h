#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game078KarateChamp : public Cartridge {
public:
    Game078KarateChamp();
    ~Game078KarateChamp() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 78; }
    std::string GetName() const override { return "Karate Champ (1984)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_FIGHT = 0,
        STATE_POINT_SCORED = 1,
        STATE_ROUND_WIN = 2,
        STATE_BONUS_STAGE = 3,
        STATE_GAME_OVER = 4
    };

    enum AttackType {
        ATK_NONE = 0,
        ATK_HIGH_KICK = 1,   // High (2 pts / Ippon)
        ATK_MID_PUNCH = 2,   // Mid (1 pt / Waza-ari)
        ATK_LOW_SWEEP = 3,   // Low (2 pts / Ippon)
        ATK_BLOCK = 4        // Defensive stance
    };

    GameState GetState() const { return state_; }
    int GetPlayerPoints() const { return player_points_; }
    int GetCpuPoints() const { return cpu_points_; }
    int GetDanLevel() const { return dan_level_; }
    float GetPlayerX() const { return px_; }
    float GetCpuX() const { return cx_; }
    AttackType GetPlayerAttack() const { return p_attack_; }
    AttackType GetCpuAttack() const { return c_attack_; }

private:
    void ResetRound();
    void StartBonusStage();
    void UpdateFight(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateBonus(float dt, uint32_t buttons, uint32_t prev_buttons);
    void CheckHits();

    GameState state_{STATE_FIGHT};
    float state_timer_{0.0f};
    float round_timer_{30.0f};

    int player_points_{0}; // 2 points wins round
    int cpu_points_{0};
    int rounds_won_{0};
    int dan_level_{1}; // 1 = White Belt, 2 = Brown Belt, 3 = Black Belt 1-Dan, etc.
    int score_{0};

    // Player (White Gi)
    float px_{4.0f};
    AttackType p_attack_{ATK_NONE};
    float p_atk_timer_{0.0f};

    // CPU (Red Gi)
    float cx_{11.0f};
    AttackType c_attack_{ATK_NONE};
    float c_atk_timer_{0.0f};
    float c_ai_think_timer_{0.0f};

    // Point banner info
    std::string judge_call_;
    int last_scorer_{0}; // 1 = Player, 2 = CPU

    // Bonus stage objects (e.g. Flying pots or Bull charging)
    float bonus_obj_x_{16.0f};
    float bonus_obj_speed_{10.0f};
    bool bonus_obj_broken_{false};
};

} // namespace arcade
