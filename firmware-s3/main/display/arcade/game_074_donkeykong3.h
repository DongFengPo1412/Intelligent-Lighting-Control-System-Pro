#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game074DonkeyKong3 : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_PLAYING = 1;
    static constexpr uint8_t STATE_DEAD = 2;
    static constexpr uint8_t STATE_VICTORY = 3;

    static constexpr int MAX_SPRAYS = 3;
    static constexpr int MAX_BUGS = 4;
    static constexpr int MAX_FLOWERS = 4;

    struct Spray {
        float x;
        float y;
        float vy;
        bool is_super;
        bool active;
    };

    struct Bug {
        float x;
        float y;
        float vx;
        float vy;
        int type;          // 0: Buzzbee, 1: Beespies butterfly
        bool has_flower;   // Carrying a stolen flower
        bool active;
    };

    struct Flower {
        float x;
        float y;
        bool active;
    };

    Game074DonkeyKong3();
    ~Game074DonkeyKong3() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "Donkey Kong 3 (1983)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    int GetLives() const { return lives_; }
    float GetPlayerX() const { return px_; }
    float GetPlayerY() const { return py_; }
    float GetDkY() const { return dk_y_; }
    bool HasSuperSpray() const { return has_super_spray_; }
    int GetFlowersRemaining() const;

    void SprayUpward();
    void Jump();

private:
    void InitStage();
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateSprays(float dt);
    void UpdateDonkeyKong(float dt);
    void UpdateBugs(float dt);
    void CheckCollisions();

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;
    int lives_;

    // Stanley the exterminator
    float px_;
    float py_;
    float pvy_;
    bool on_ground_;
    float spray_cooldown_;
    bool has_super_spray_;
    float super_spray_timer_;

    // Donkey Kong suspended on ropes
    float dk_x_;
    float dk_y_;
    float dk_drop_speed_;

    // Power spray can drop
    bool super_can_active_;
    float super_can_x_;
    float super_can_y_;

    Spray sprays_[MAX_SPRAYS];
    Bug bugs_[MAX_BUGS];
    Flower flowers_[MAX_FLOWERS];
};

} // namespace arcade
