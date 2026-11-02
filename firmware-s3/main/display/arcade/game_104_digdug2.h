#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game104DigDug2 : public Cartridge {
public:
    Game104DigDug2();
    ~Game104DigDug2() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 104; }
    std::string GetName() const override { return "Dig Dug II (1985)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_EXPLORING = 0,
        STATE_DRILLING_FAULT = 1,
        STATE_ISLAND_COLLAPSE = 2,
        STATE_PLAYER_DROWN = 3,
        STATE_STAGE_CLEAR = 4,
        STATE_GAME_OVER = 5
    };

    struct Peg {
        int x{0};
        int y{0};
        bool drilled{false};
        bool active{true};
    };

    struct Monster {
        float x{0.0f};
        float y{0.0f};
        float vx{2.0f};
        float vy{0.0f};
        bool is_fygar{false}; // Fygar breathes flame; Pooka chases
        float stun_timer{0.0f};
        bool active{false};
    };

    struct CrackLine {
        int x1{0}, y1{0};
        int x2{0}, y2{0};
        bool active{false};
    };

    static constexpr int MAX_PEGS = 6;
    static constexpr int MAX_MONSTERS = 3;
    static constexpr int MAX_CRACKS = 6;

    GameState GetState() const { return state_; }
    int GetScore() const { return score_; }
    int GetLives() const { return lives_; }
    int GetStage() const { return stage_; }
    float GetPlayerX() const { return px_; }
    float GetPlayerY() const { return py_; }
    int GetMonstersDefeated() const { return monsters_defeated_; }

    const Monster& GetMonster(int i) const { return monsters_[i]; }
    const Peg& GetPeg(int i) const { return pegs_[i]; }

    void TriggerDrillAtNearestPeg();

private:
    GameState state_{STATE_EXPLORING};
    float state_timer_{0.0f};
    int score_{0};
    int lives_{3};
    int stage_{1};
    int monsters_defeated_{0};

    // Taizo Hori
    float px_{8.0f};
    float py_{8.0f};
    int facing_x_{1};
    int facing_y_{0};
    float pump_timer_{0.0f};
    int active_peg_idx_{-1};

    // Island land grid: true = green land, false = blue ocean
    bool island_grid_[16][16];
    bool collapse_mask_[16][16];

    Peg pegs_[MAX_PEGS];
    Monster monsters_[MAX_MONSTERS];
    CrackLine cracks_[MAX_CRACKS];

    void InitIsland();
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateMonsters(float dt);
    void UpdateCracksAndCollapse(float dt);
    void CheckCollisions();
    void ExecuteFaultLineBreak(int peg_idx);
};

} // namespace arcade
