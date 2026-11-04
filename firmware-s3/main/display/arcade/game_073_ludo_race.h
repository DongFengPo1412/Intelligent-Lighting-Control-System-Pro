// game_073_ludo_race.h —— 目标 #073 飞行棋 (Ludo Race, 1986)
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

enum LudoPhase : uint8_t {
    LUDO_WAIT_ROLL = 0,
    LUDO_ROLL_ANIM = 1,
    LUDO_SELECT_TOKEN = 2,
    LUDO_PASS_DELAY = 3,
    LUDO_AI_THINK = 4,
    LUDO_AI_MOVE = 5,
};

class Game073LudoRace : public Cartridge {
public:
    Game073LudoRace();
    ~Game073LudoRace() override = default;

    uint8_t GetId() const override { return 73; }
    const char* GetName() const override { return "飞行棋"; }
    const char* GetEnglishName() const override { return "Ludo Race"; }
    uint16_t GetReleaseYear() const override { return 1986; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    void Init() override;
    void Reset() override;
    void Start() override;
    void Pause() override;
    void Resume() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

private:
    void InitGameData();
    uint32_t NextRand();
    void AddScore(uint32_t pts);
    bool CanMoveToken(int step, int die_val) const;
    void ApplyMove(bool is_player, int tok_idx);
    int ChooseAIToken() const;
    void GetTokenPixel(bool is_player, int tok_idx, int& out_x, int& out_y) const;
    void DrawDie3x3(uint8_t* fb, int val, bool is_player_turn) const;

    CartridgeState state_;
    LudoPhase phase_;
    int p_step_[2];
    int ai_step_[2];
    int dice_;
    int anim_die_;
    int selected_token_;
    float phase_timer_;
    float capture_flash_timer_;
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
    float anim_timer_;
    uint32_t rng_state_;
};

} // namespace arcade
