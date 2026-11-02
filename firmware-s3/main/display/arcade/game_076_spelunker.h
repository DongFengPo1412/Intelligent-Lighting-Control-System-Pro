#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game076Spelunker : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_PLAYING = 1;
    static constexpr uint8_t STATE_DEAD = 2;
    static constexpr uint8_t STATE_VICTORY = 3;

    static constexpr int MAX_GHOSTS = 2;
    static constexpr int MAX_FLARES = 2;
    static constexpr int MAX_TREASURES = 4;

    struct Ghost {
        float x;
        float y;
        float vx;
        float vy;
        bool active;
    };

    struct Flare {
        float x;
        float y;
        float vy;
        float duration;
        bool active;
    };

    struct Item {
        float x;
        float y;
        int type;       // 0: Gold Idol, 1: Oxygen Tank, 2: Key
        bool active;
    };

    Game076Spelunker();
    ~Game076Spelunker() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "Spelunker (1983)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    int GetLives() const { return lives_; }
    float GetPlayerX() const { return px_; }
    float GetPlayerY() const { return py_; }
    float GetOxygen() const { return oxygen_; }
    bool OnRope() const { return on_rope_; }
    int GetFlares() const { return flares_count_; }
    int GetTreasuresRemaining() const;

    void FireFlare();
    void Jump();

private:
    void InitStage();
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateFlares(float dt);
    void UpdateGhosts(float dt);
    void CheckCollisions();

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;
    int lives_;

    // Spelunker explorer state
    float px_;
    float py_;
    float pvy_;
    float fall_start_y_;
    bool on_ground_;
    bool on_rope_;
    int facing_;
    float oxygen_;
    int flares_count_;
    int treasures_collected_;

    Ghost ghosts_[MAX_GHOSTS];
    Flare flares_[MAX_FLARES];
    Item items_[MAX_TREASURES];
};

} // namespace arcade
