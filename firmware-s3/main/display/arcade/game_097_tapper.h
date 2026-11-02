#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game097Tapper : public Cartridge {
public:
    Game097Tapper();
    ~Game097Tapper() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 97; }
    std::string GetName() const override { return "Root Beer Tapper (1983)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_SERVING = 0,
        STATE_MUG_CRASHED = 1,
        STATE_PATRON_OVERRUN = 2,
        STATE_ROUND_CLEAR = 3,
        STATE_GAME_OVER = 4
    };

    struct Mug {
        int lane{0}; // 0 to 3
        float x{12.0f};
        float vx{-8.0f}; // negative = full beer sliding left, positive = empty mug sliding right
        bool is_empty{false};
        bool active{false};
    };

    struct Patron {
        int lane{0};
        float x{1.0f};
        float speed{1.2f};
        bool is_drinking{false};
        float drink_timer{0.0f};
        bool active{false};
        float respawn_timer{0.0f};
    };

    static constexpr int NUM_LANES = 4;
    static constexpr int MAX_MUGS = 6;
    static constexpr int MAX_PATRONS = 4;

    GameState GetState() const { return state_; }
    int GetScore() const { return score_; }
    int GetLives() const { return lives_; }
    int GetCurrentLane() const { return current_lane_; }
    float GetBartenderX() const { return bx_; }
    bool IsFillingMug() const { return is_filling_mug_; }
    int GetPatronsSatisfied() const { return patrons_satisfied_; }

    const Mug& GetMug(int i) const { return mugs_[i]; }
    const Patron& GetPatron(int i) const { return patrons_[i]; }

private:
    void ResetBar(bool hard_reset);
    void UpdateBartender(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateMugs(float dt);
    void UpdatePatrons(float dt);
    void CheckCollisions();

    GameState state_{STATE_SERVING};
    float state_timer_{0.0f};
    int score_{0};
    int lives_{3};
    int round_{1};
    int patrons_satisfied_{0};

    // Bartender
    int current_lane_{0};
    float bx_{13.0f};
    bool is_filling_mug_{false};
    float fill_timer_{0.0f};

    // Tips on bars
    bool tips_[NUM_LANES]{false, false, false, false};
    float tip_x_[NUM_LANES]{6.0f, 6.0f, 6.0f, 6.0f};

    Mug mugs_[MAX_MUGS];
    Patron patrons_[MAX_PATRONS];
};

} // namespace arcade
