#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game077Windjammers : public Cartridge {
public:
    Game077Windjammers();
    ~Game077Windjammers() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 77; }
    std::string GetName() const override { return "Windjammers (1994)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_SERVE = 0,
        STATE_RALLY = 1,
        STATE_GOAL = 2,
        STATE_MATCH_OVER = 3
    };

    struct Disc {
        float x{4.0f};
        float y{7.5f};
        float vx{0.0f};
        float vy{0.0f};
        float speed{10.0f};
        bool is_super{false};
        int held_by{0}; // 0 = free, 1 = player, 2 = AI
        float hold_timer{0.0f};
    };

    GameState GetState() const { return state_; }
    int GetPlayerScore() const { return player_score_; }
    int GetAiScore() const { return ai_score_; }
    float GetPlayerX() const { return px_; }
    float GetPlayerY() const { return py_; }
    float GetDiscX() const { return disc_.x; }
    float GetDiscY() const { return disc_.y; }
    float GetCharge() const { return player_charge_; }

private:
    void ResetPoint(int server);
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateAI(float dt);
    void UpdateDisc(float dt);
    void CheckGoals();

    GameState state_{STATE_SERVE};
    float state_timer_{0.0f};
    float match_timer_{60.0f};

    int player_score_{0};
    int ai_score_{0};

    // Player (Left court: x in [1.0, 7.0], y in [1.0, 14.0])
    float px_{3.0f};
    float py_{7.5f};
    float p_dash_vx_{0.0f};
    float p_dash_vy_{0.0f};
    float p_dash_timer_{0.0f};
    float player_charge_{0.0f};

    // AI Opponent (Right court: x in [8.0, 14.0], y in [1.0, 14.0])
    float aix_{12.0f};
    float aiy_{7.5f};
    float ai_dash_timer_{0.0f};
    float ai_charge_{0.0f};

    Disc disc_;
    int last_scorer_{0};
};

} // namespace arcade
