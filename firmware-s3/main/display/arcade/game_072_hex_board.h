// game_072_hex_board.h —— 目标 #072 Hex连通棋 (Hex Connection, 1985)
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

class Game072HexBoard : public Cartridge {
public:
    Game072HexBoard();
    ~Game072HexBoard() override = default;

    uint8_t GetId() const override { return 72; }
    const char* GetName() const override { return "Hex连通棋"; }
    const char* GetEnglishName() const override { return "Hex Connection"; }
    uint16_t GetReleaseYear() const override { return 1985; }
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
    static const int kBoardSize = 7;

    void InitGameData();
    uint32_t NextRand();
    void AddScore(uint32_t pts);
    bool CheckConnectivity(uint8_t who) const;
    int ComputeShortestCost(uint8_t who) const;
    void ChooseAIMove(int& out_r, int& out_c);

    CartridgeState state_;
    uint8_t board_[kBoardSize][kBoardSize];
    int cursor_r_;
    int cursor_c_;
    bool turn_player_;
    float ai_timer_;
    int moves_count_;
    int last_ai_r_;
    int last_ai_c_;
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
    float anim_timer_;
    uint32_t rng_state_;
};

} // namespace arcade
