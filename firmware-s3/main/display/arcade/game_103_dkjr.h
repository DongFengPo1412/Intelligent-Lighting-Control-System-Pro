#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game103DKJr : public Cartridge {
public:
    Game103DKJr();
    ~Game103DKJr() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 103; }
    std::string GetName() const override { return "Donkey Kong Jr. (1982)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_CLIMBING = 0,
        STATE_KEY_INSERTED = 1,
        STATE_STAGE_CLEAR = 2,
        STATE_FALL_DOWN = 3,
        STATE_GAME_OVER = 4
    };

    struct Snapjaw {
        float x{0.0f};
        float y{0.0f};
        float vy{2.2f};
        int vine_idx{0};
        bool is_red{false}; // Red drops down only; Blue patrols
        bool active{false};
    };

    struct Fruit {
        float x{0.0f};
        float y{0.0f};
        int vine_idx{0};
        bool falling{false};
        float vy{0.0f};
        bool active{false};
    };

    static constexpr int NUM_VINES = 4;
    static constexpr int MAX_SNAPJAWS = 3;
    static constexpr int MAX_FRUITS = 2;
    static constexpr int TOTAL_KEYS = 4;

    GameState GetState() const { return state_; }
    int GetScore() const { return score_; }
    int GetLives() const { return lives_; }
    float GetPlayerX() const { return px_; }
    float GetPlayerY() const { return py_; }
    bool IsDualVine() const { return gripping_two_vines_; }
    int GetKeysInserted() const { return keys_inserted_; }

    const Snapjaw& GetSnapjaw(int i) const { return snapjaws_[i]; }
    const Fruit& GetFruit(int i) const { return fruits_[i]; }

private:
    GameState state_{STATE_CLIMBING};
    float state_timer_{0.0f};
    int score_{0};
    int lives_{3};
    int keys_inserted_{0};

    // Junior state
    float px_{2.0f};
    float py_{13.0f};
    float vx_{0.0f};
    float vy_{0.0f};
    int current_vine_{0}; // 0..3 (vines at x=2, 6, 10, 14)
    bool on_ground_{true};
    bool gripping_two_vines_{false};
    int facing_{1};

    Snapjaw snapjaws_[MAX_SNAPJAWS];
    Fruit fruits_[MAX_FRUITS];
    bool keys_unlocked_[TOTAL_KEYS];

    void ResetStage();
    void UpdateJunior(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateSnapjaws(float dt);
    void UpdateFruits(float dt);
    void CheckCollisions();
};

} // namespace arcade
