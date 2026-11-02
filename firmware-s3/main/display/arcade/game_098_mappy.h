#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game098Mappy : public Cartridge {
public:
    Game098Mappy();
    ~Game098Mappy() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 98; }
    std::string GetName() const override { return "Mappy (1983)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_IN_MANSION = 0,
        STATE_MAPPY_HIT = 1,
        STATE_ROUND_CLEAR = 2,
        STATE_GAME_OVER = 3
    };

    struct StolenLoot {
        int x{0};
        int floor_y{0};
        int type{0}; // 0 = Radio, 1 = TV, 2 = Safe
        bool collected{false};
    };

    struct CatEnemy {
        float x{0.0f};
        int floor_y{3};
        float vx{1.2f};
        bool is_blasted{false};
        bool active{false};
        float respawn_timer{0.0f};
    };

    struct MicrowaveWave {
        float x{0.0f};
        int floor_y{0};
        float vx{0.0f};
        bool active{false};
    };

    static constexpr int NUM_FLOORS = 4;
    static constexpr int MAX_LOOT = 6;
    static constexpr int MAX_CATS = 3;

    GameState GetState() const { return state_; }
    int GetScore() const { return score_; }
    int GetLives() const { return lives_; }
    float GetPlayerX() const { return px_; }
    float GetPlayerY() const { return py_; }
    bool IsOnTrampoline() const { return is_on_trampoline_; }
    int GetTrampolineWear(int t_idx) const { return (t_idx == 0) ? tramp_wear_left_ : tramp_wear_right_; }
    int GetLootCollected() const { return loot_collected_; }

    const CatEnemy& GetCat(int i) const { return cats_[i]; }
    const StolenLoot& GetLoot(int i) const { return loot_[i]; }

private:
    void ResetMansion(bool hard_reset);
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateMicrowaveWave(float dt);
    void UpdateCats(float dt);
    void CheckLootAndCombat();

    GameState state_{STATE_IN_MANSION};
    float state_timer_{0.0f};
    int score_{0};
    int lives_{3};
    int round_{1};
    int loot_collected_{0};

    // Police Mouse Mappy
    float px_{4.0f};
    float py_{13.0f};
    float vy_{0.0f};
    int facing_{1};
    bool is_on_trampoline_{false};
    int active_tramp_idx_{-1}; // 0 = left (x=2), 1 = right (x=13)
    int continuous_bounces_{0};

    // Trampolines wear state (0=green, 1=blue, 2=yellow, 3=red, 4=broken)
    int tramp_wear_left_{0};
    int tramp_wear_right_{0};

    // Microwave door positions
    int door_floor_{6};
    int door_x_{7};
    bool door_opened_{false};

    MicrowaveWave wave_;
    StolenLoot loot_[MAX_LOOT];
    CatEnemy cats_[MAX_CATS];
};

} // namespace arcade
