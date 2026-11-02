#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game099Joust : public Cartridge {
public:
    Game099Joust();
    ~Game099Joust() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 99; }
    std::string GetName() const override { return "Joust (1982)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_JOUSTING = 0,
        STATE_KNIGHT_DOWN = 1,
        STATE_WAVE_CLEAR = 2,
        STATE_GAME_OVER = 3
    };

    struct BuzzardKnight {
        float x{0.0f};
        float y{0.0f};
        float vx{2.0f};
        float vy{0.0f};
        float flap_timer{0.0f};
        int rank{0}; // 0 = Bounder, 1 = Shadow
        bool active{false};
        float respawn_timer{0.0f};
    };

    struct Egg {
        float x{0.0f};
        float y{0.0f};
        float hatch_timer{0.0f};
        bool active{false};
    };

    static constexpr int MAX_ENEMIES = 3;
    static constexpr int MAX_EGGS = 3;

    GameState GetState() const { return state_; }
    int GetScore() const { return score_; }
    int GetLives() const { return lives_; }
    float GetPlayerX() const { return px_; }
    float GetPlayerY() const { return py_; }
    float GetPlayerVY() const { return vy_; }
    bool IsLavaGrabbed() const { return grabbed_by_lava_; }
    int GetKnightsDefeated() const { return knights_defeated_; }

    const BuzzardKnight& GetEnemy(int i) const { return enemies_[i]; }
    const Egg& GetEgg(int i) const { return eggs_[i]; }

private:
    void ResetArena(bool hard_reset);
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateEnemies(float dt);
    void UpdateEggs(float dt);
    void CheckJoustCollisions();

    GameState state_{STATE_JOUSTING};
    float state_timer_{0.0f};
    int score_{0};
    int lives_{3};
    int wave_{1};
    int knights_defeated_{0};

    // Ostrich Knight Hero
    float px_{4.0f};
    float py_{12.0f};
    float vx_{0.0f};
    float vy_{0.0f};
    int facing_{1};
    bool on_platform_{true};
    bool grabbed_by_lava_{false};
    int lava_escape_flaps_{0};

    BuzzardKnight enemies_[MAX_ENEMIES];
    Egg eggs_[MAX_EGGS];
};

} // namespace arcade
