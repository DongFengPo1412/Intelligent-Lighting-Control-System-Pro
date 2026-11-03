#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game119Pitfall2 : public Cartridge {
public:
    Game119Pitfall2();
    ~Game119Pitfall2() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 119; }
    std::string GetName() const override { return "Pitfall II: Lost Caverns (1984)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_EXPLORING = 0,
        STATE_CHECKPOINT_RESPAWN = 1,
        STATE_EXPEDITION_CLEAR = 2,
        STATE_GAME_OVER = 3
    };

    struct Hazard {
        float x{0.0f};
        float y{0.0f};
        float vx{0.0f};
        int type{0}; // 0 = Scorpion, 1 = Bat, 2 = Crocodile
        bool active{true};
    };

    struct Treasure {
        float x{0.0f};
        float y{0.0f};
        int value{0};
        bool collected{false};
    };

    static constexpr int NUM_TREASURES = 3;
    static constexpr int NUM_HAZARDS = 3;

    GameState GetState() const { return state_; }
    int GetScore() const { return score_; }
    int GetLives() const { return lives_; }
    float GetPlayerX() const { return px_; }
    float GetPlayerY() const { return py_; }
    bool IsOnBalloon() const { return on_balloon_; }
    bool IsOnVine() const { return on_vine_; }
    int GetTreasuresCollected() const { return treasures_collected_; }

    const Treasure& GetTreasure(int i) const { return treasures_[i]; }
    const Hazard& GetHazard(int i) const { return hazards_[i]; }

    void SetPlayerPos(float x, float y);

private:
    GameState state_{STATE_EXPLORING};
    float state_timer_{0.0f};
    int score_{0};
    int lives_{3};
    int treasures_collected_{0};

    // Pitfall Harry
    float px_{2.0f};
    float py_{3.0f};
    float vy_{0.0f};
    bool on_ground_{true};
    bool on_ladder_{false};
    bool on_vine_{false};
    bool on_balloon_{false};

    // Checkpoint Cross coordinates
    float checkpoint_x_{2.0f};
    float checkpoint_y_{3.0f};
    bool checkpoint_active_{false};

    // Floating Balloon
    float balloon_x_{10.5f};
    float balloon_y_{13.0f};
    float balloon_dir_{-1.0f}; // Ascending / descending

    // Swinging Vine
    float vine_angle_{0.0f};
    float vine_pivot_x_{8.0f};
    float vine_pivot_y_{1.0f};

    Treasure treasures_[NUM_TREASURES];
    Hazard hazards_[NUM_HAZARDS];

    void InitCavern();
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateMechanisms(float dt);
    void UpdateHazards(float dt);
    void CheckInteractions();
};

} // namespace arcade