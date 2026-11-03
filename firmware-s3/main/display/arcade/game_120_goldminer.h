#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game120GoldMiner : public Cartridge {
public:
    Game120GoldMiner();
    ~Game120GoldMiner() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 120; }
    std::string GetName() const override { return "Gold Miner (2003)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_MINING = 0,
        STATE_ROUND_CLEAR = 1,
        STATE_TIME_UP = 2,
        STATE_GAME_OVER = 3
    };

    enum ClawState {
        CLAW_SWINGING = 0,
        CLAW_EXTENDING = 1,
        CLAW_RETRACTING = 2
    };

    enum ItemType {
        ITEM_SMALL_GOLD = 0,
        ITEM_LARGE_GOLD = 1,
        ITEM_DIAMOND = 2,
        ITEM_ROCK = 3,
        ITEM_TNT_BARREL = 4
    };

    struct MineItem {
        float x{0.0f};
        float y{0.0f};
        ItemType type{ITEM_SMALL_GOLD};
        int value{100};
        float mass{1.0f};
        float radius{0.7f};
        bool active{true};
    };

    static constexpr int MAX_ITEMS = 8;

    GameState GetState() const { return state_; }
    ClawState GetClawState() const { return claw_state_; }
    int GetScore() const { return score_; }
    int GetTargetQuota() const { return target_quota_; }
    int GetDynamite() const { return dynamite_count_; }
    float GetTimeRemaining() const { return time_remaining_; }
    float GetWinchAngle() const { return winch_angle_; }
    float GetClawX() const { return claw_x_; }
    float GetClawY() const { return claw_y_; }
    int GetHookedItemIdx() const { return hooked_item_idx_; }

    const MineItem& GetItem(int i) const { return items_[i]; }

    void LaunchClaw();
    void UseDynamite();

private:
    GameState state_{STATE_MINING};
    float state_timer_{0.0f};
    int score_{0};
    int round_{1};
    int target_quota_{650};
    int dynamite_count_{2};
    float time_remaining_{45.0f};

    // Winch & Claw
    float winch_x_{7.5f};
    float winch_y_{1.5f};
    float winch_angle_{0.0f};
    float swing_time_{0.0f};
    ClawState claw_state_{CLAW_SWINGING};

    float claw_x_{7.5f};
    float claw_y_{1.5f};
    float claw_dist_{1.0f};
    float claw_dir_x_{0.0f};
    float claw_dir_y_{1.0f};
    int hooked_item_idx_{-1};

    MineItem items_[MAX_ITEMS];

    void InitLevel();
    void SpawnItems();
    void UpdateWinch(float dt, uint32_t buttons, uint32_t prev_buttons);
    void CheckClawCollisions();
};

} // namespace arcade
