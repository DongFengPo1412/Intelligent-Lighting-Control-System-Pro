#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game117SuperOffRoad : public Cartridge {
public:
    Game117SuperOffRoad();
    ~Game117SuperOffRoad() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 117; }
    std::string GetName() const override { return "Super Off Road (1989)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_RACING = 0,
        STATE_LAP_COMPLETE = 1,
        STATE_RACE_FINISHED = 2,
        STATE_GAME_OVER = 3
    };

    struct Truck {
        float x{2.5f};
        float y{13.0f};
        float angle{0.0f}; // Heading in radians
        float speed{0.0f};
        float jump_z{0.0f};
        float jump_vz{0.0f};
        bool is_airborne{false};
        int current_waypoint{0};
        int laps_completed{0};
    };

    struct Collectible {
        float x{0.0f};
        float y{0.0f};
        int type{0}; // 0 = Nitro, 1 = Cash
        bool active{false};
    };

    static constexpr int TOTAL_LAPS = 3;
    static constexpr int NUM_WAYPOINTS = 4;
    static constexpr int MAX_ITEMS = 3;

    GameState GetState() const { return state_; }
    int GetScore() const { return score_; }
    int GetNitroCharges() const { return nitro_charges_; }
    int GetPlayerLaps() const { return player_.laps_completed; }
    float GetPlayerX() const { return player_.x; }
    float GetPlayerY() const { return player_.y; }
    float GetPlayerAngle() const { return player_.angle; }
    float GetPlayerSpeed() const { return player_.speed; }
    bool IsPlayerAirborne() const { return player_.is_airborne; }
    const Truck& GetRival() const { return rival_; }

    void ActivateNitro();

private:
    GameState state_{STATE_RACING};
    float state_timer_{0.0f};
    int score_{0};
    int nitro_charges_{3};
    float nitro_timer_{0.0f};

    Truck player_;
    Truck rival_;

    // Stadium Circuit Waypoints: Loop along the rectangular track
    // (2.5, 13.0) -> (13.5, 13.0) -> (13.5, 2.5) -> (2.5, 2.5) -> (2.5, 13.0)
    float waypoints_[NUM_WAYPOINTS][2] = {
        {13.0f, 13.0f}, // Waypoint 0 (East straight)
        {13.0f, 2.5f},  // Waypoint 1 (North-East turn)
        {2.5f, 2.5f},   // Waypoint 2 (West straight)
        {2.5f, 13.0f}   // Waypoint 3 (Finish line / South-West)
    };

    Collectible items_[MAX_ITEMS];

    void InitRace();
    void UpdatePlayerTruck(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateRivalTruck(float dt);
    void UpdateJumps(Truck& t, float dt);
    void CheckRampsAndMud(Truck& t);
    void CheckWaypoints(Truck& t, bool is_player);
    void CheckCollisions();
};

} // namespace arcade
