#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game095BurgerTime : public Cartridge {
public:
    Game095BurgerTime();
    ~Game095BurgerTime() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 95; }
    std::string GetName() const override { return "BurgerTime (1982)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_COOKING = 0,
        STATE_CHEF_HIT = 1,
        STATE_STAGE_CLEAR = 2,
        STATE_GAME_OVER = 3
    };

    enum IngredientType {
        ING_BUN_TOP = 0,
        ING_LETTUCE = 1,
        ING_PATTY = 2,
        ING_BUN_BOTTOM = 3
    };

    struct BurgerLayer {
        int col{0}; // 0 = left burger (x=2..5), 1 = right burger (x=10..13)
        IngredientType type{ING_BUN_TOP};
        float y{3.0f};
        float target_y{3.0f};
        bool is_falling{false};
        bool on_plate{false};
        uint8_t stepped_mask{0}; // 4 bits for 4 segments stepped by chef
    };

    struct FoodEnemy {
        float x{0.0f};
        float y{0.0f};
        float vx{1.0f};
        float vy{0.0f};
        float stun_timer{0.0f};
        bool active{false};
        float respawn_timer{0.0f};
    };

    static constexpr int MAX_LAYERS = 6;
    static constexpr int MAX_ENEMIES = 3;

    GameState GetState() const { return state_; }
    int GetScore() const { return score_; }
    int GetLives() const { return lives_; }
    int GetPeppers() const { return peppers_left_; }
    float GetPlayerX() const { return px_; }
    float GetPlayerY() const { return py_; }
    bool IsPepperSprayActive() const { return pepper_spray_timer_ > 0.0f; }
    int GetBurgersCompleted() const { return burgers_completed_; }

    const BurgerLayer& GetLayer(int i) const { return layers_[i]; }
    const FoodEnemy& GetEnemy(int i) const { return enemies_[i]; }

private:
    void ResetKitchen(bool hard_reset);
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateBurgerLayers(float dt);
    void UpdateEnemies(float dt);
    void CheckCollisions();

    GameState state_{STATE_COOKING};
    float state_timer_{0.0f};
    int score_{0};
    int lives_{3};
    int stage_{1};
    int peppers_left_{5};
    int burgers_completed_{0};

    // Chef Peter Pepper
    float px_{4.0f};
    float py_{13.0f};
    int facing_{1}; // 1 = right, -1 = left, 0 = vertical
    float pepper_spray_timer_{0.0f};
    float move_cooldown_{0.0f};

    BurgerLayer layers_[MAX_LAYERS];
    FoodEnemy enemies_[MAX_ENEMIES];
};

} // namespace arcade
