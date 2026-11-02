#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game053Wrestling : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_PLAYING = 1;
    static constexpr uint8_t STATE_DEAD = 2;
    static constexpr uint8_t STATE_VICTORY = 3;

    static constexpr uint8_t MODE_NEUTRAL = 0;
    static constexpr uint8_t MODE_ROPE_BOUNCE = 1;
    static constexpr uint8_t MODE_GRAPPLE = 2;
    static constexpr uint8_t MODE_DOWNED = 3;
    static constexpr uint8_t MODE_PINNING = 4;

    Game053Wrestling();
    ~Game053Wrestling() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "The Main Event (1988)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }

    uint8_t GetPlayerMode() const { return player_mode_; }
    uint8_t GetOpponentMode() const { return opp_mode_; }
    int GetPlayerStamina() const { return player_stamina_; }
    int GetOpponentStamina() const { return opp_stamina_; }
    int GetRefereeCount() const { return referee_count_; }

    float GetPlayerX() const { return player_x_; }
    float GetPlayerY() const { return player_y_; }
    float GetOpponentX() const { return opp_x_; }
    float GetOpponentY() const { return opp_y_; }

    void SetPlayerPos(float x, float y) { player_x_ = x; player_y_ = y; }
    void SetOpponentPos(float x, float y) { opp_x_ = x; opp_y_ = y; }

    void TriggerGrappleOverpower();
    void TriggerPinAttempt();

private:
    void InitMatch();
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateOpponent(float dt);
    void UpdateGrapple(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdatePinning(float dt);

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;

    // Player state
    float player_x_;
    float player_y_;
    float player_vx_;
    float player_vy_;
    uint8_t player_mode_;
    int player_stamina_;
    float player_down_timer_;

    // Opponent state
    float opp_x_;
    float opp_y_;
    float opp_vx_;
    float opp_vy_;
    uint8_t opp_mode_;
    int opp_stamina_;
    float opp_down_timer_;
    float opp_ai_timer_;

    // Grapple / Pin metrics
    int grapple_advantage_; // >0 favors player, <0 favors opponent
    float grapple_timer_;
    float pin_timer_;
    int referee_count_;     // 0, 1, 2, 3
};

} // namespace arcade
