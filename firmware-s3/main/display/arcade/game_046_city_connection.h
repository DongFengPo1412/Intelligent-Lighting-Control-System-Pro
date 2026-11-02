#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game046CityConnection : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_PLAYING = 1;
    static constexpr uint8_t STATE_DEAD = 2;
    static constexpr uint8_t STATE_VICTORY = 3;

    static constexpr int NUM_POLICE = 3;
    static constexpr int MAX_OIL_CANS = 3;
    static constexpr int NUM_TIERS = 4;

    struct PoliceCar {
        float x;
        int tier;       // 0..3 (y = 4, 8, 12, 15)
        float vx;
        bool active;
        bool is_dizzy;
        float dizzy_timer;
    };

    struct OilCanShot {
        float x;
        int tier;
        float vx;
        bool active;
    };

    Game046CityConnection();
    ~Game046CityConnection() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "City Connection (1985)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    int GetLives() const { return lives_; }
    int GetOilAmmo() const { return oil_ammo_; }
    int GetUnpaintedCount() const { return unpainted_tiles_; }
    float GetPlayerX() const { return player_x_; }
    int GetPlayerTier() const { return player_tier_; }

    void FireOilCan();
    void SetPlayerPos(float x, int tier) { player_x_ = x; player_tier_ = tier; }

private:
    void InitHighways();
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdatePolice(float dt);
    void UpdateOilCans(float dt);
    void CheckCollisions();

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;
    int lives_;
    int oil_ammo_;
    int unpainted_tiles_;

    float player_x_;
    int player_tier_;       // 0..3
    float player_vx_;
    int player_dir_;        // +1 (right) or -1 (left)
    bool is_jumping_;
    float jump_vy_;
    float jump_y_offset_;

    PoliceCar police_[NUM_POLICE];
    OilCanShot oil_shots_[MAX_OIL_CANS];

    // Highway paint states: 4 tiers x 16 columns (false = unpainted, true = painted)
    bool painted_[NUM_TIERS][16];
};

} // namespace arcade
