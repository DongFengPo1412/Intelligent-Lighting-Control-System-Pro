#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game096Pooyan : public Cartridge {
public:
    Game096Pooyan();
    ~Game096Pooyan() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 96; }
    std::string GetName() const override { return "Pooyan (1982)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_DEFENDING = 0,
        STATE_MAMA_HIT = 1,
        STATE_STAGE_CLEAR = 2,
        STATE_GAME_OVER = 3
    };

    struct Arrow {
        float x{0.0f};
        float y{0.0f};
        float vx{-14.0f};
        bool active{false};
    };

    struct Wolf {
        float x{0.0f};
        float y{0.0f};
        float vy{1.2f};
        int balloon_hp{1};
        bool is_falling{false};
        bool active{false};
        float respawn_timer{0.0f};
    };

    static constexpr int MAX_ARROWS = 4;
    static constexpr int MAX_WOLVES = 3;

    GameState GetState() const { return state_; }
    int GetScore() const { return score_; }
    int GetLives() const { return lives_; }
    float GetBasketY() const { return basket_y_; }
    bool IsMeatAvailable() const { return meat_available_; }
    bool IsMeatFlying() const { return meat_active_; }
    int GetWolvesDefeated() const { return wolves_defeated_; }

    const Wolf& GetWolf(int i) const { return wolves_[i]; }

private:
    void ResetCanyon(bool hard_reset);
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateArrows(float dt);
    void UpdateMeat(float dt);
    void UpdateWolves(float dt);
    void CheckCombat();

    GameState state_{STATE_DEFENDING};
    float state_timer_{0.0f};
    int score_{0};
    int lives_{3};
    int round_{1};
    int wolves_defeated_{0};

    // Mama Pig in Rope Elevator Basket
    float basket_y_{8.0f};
    float shoot_cooldown_{0.0f};

    // Meat Chuck Slab
    bool meat_available_{true};
    bool meat_active_{false};
    float meat_x_{0.0f};
    float meat_y_{0.0f};
    float meat_vx_{0.0f};
    float meat_vy_{0.0f};
    float meat_reload_timer_{0.0f};

    Arrow arrows_[MAX_ARROWS];
    Wolf wolves_[MAX_WOLVES];
};

} // namespace arcade
