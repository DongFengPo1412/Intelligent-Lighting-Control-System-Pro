#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game065PunchOut : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_PLAYING = 1;
    static constexpr uint8_t STATE_ROUND_WIN = 2;
    static constexpr uint8_t STATE_DEAD = 3;
    static constexpr uint8_t STATE_VICTORY = 4;

    // Player Actions
    static constexpr uint8_t ACT_IDLE = 0;
    static constexpr uint8_t ACT_DODGE_LEFT = 1;
    static constexpr uint8_t ACT_DODGE_RIGHT = 2;
    static constexpr uint8_t ACT_DUCK = 3;
    static constexpr uint8_t ACT_BLOCK = 4;
    static constexpr uint8_t ACT_PUNCH_LEFT = 5;
    static constexpr uint8_t ACT_PUNCH_RIGHT = 6;
    static constexpr uint8_t ACT_HURT = 7;
    static constexpr uint8_t ACT_DOWN = 8;

    // Opponent Actions
    static constexpr uint8_t OPP_IDLE = 0;
    static constexpr uint8_t OPP_PREP_LEFT_HOOK = 1;
    static constexpr uint8_t OPP_PREP_RIGHT_HOOK = 2;
    static constexpr uint8_t OPP_PREP_BULL_CHARGE = 3;
    static constexpr uint8_t OPP_SWING = 4;
    static constexpr uint8_t OPP_STUNNED = 5;
    static constexpr uint8_t OPP_HURT = 6;
    static constexpr uint8_t OPP_DOWN = 7;

    Game065PunchOut();
    ~Game065PunchOut() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "Punch-Out!! (1983)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    int GetPlayerStamina() const { return player_stamina_; }
    int GetOppStamina() const { return opp_stamina_; }
    int GetPlayerDowns() const { return player_downs_; }
    int GetOppDowns() const { return opp_downs_; }
    int GetStars() const { return stars_; }
    uint8_t GetPlayerAction() const { return player_action_; }
    uint8_t GetOppAction() const { return opp_action_; }

    void Dodge(int direction);
    void Punch(int hand);

private:
    void InitRound();
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateOpponent(float dt);
    void KnockdownPlayer();
    void KnockdownOpponent();

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;

    // Player state (Little Mac wireframe / green gloves)
    int player_stamina_;
    uint8_t player_action_;
    float action_timer_;
    int player_downs_;
    int stars_;
    float dodge_offset_x_;
    float duck_offset_y_;

    // Opponent state (Bald Bull / Piston archetype)
    int opp_stamina_;
    uint8_t opp_action_;
    float opp_timer_;
    int opp_downs_;
    int opp_attack_type_;  // 1: Left Hook, 2: Right Hook, 3: Bull Charge
    float ref_count_timer_;
    int count_num_;
};

} // namespace arcade
