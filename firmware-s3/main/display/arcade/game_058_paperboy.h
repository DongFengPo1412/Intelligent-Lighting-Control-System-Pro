#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game058Paperboy : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_PLAYING = 1;
    static constexpr uint8_t STATE_DEAD = 2;
    static constexpr uint8_t STATE_VICTORY = 3;

    static constexpr int MAX_PAPERS = 3;
    static constexpr int MAX_HOUSES = 3;
    static constexpr int MAX_HAZARDS = 3;

    struct Paper {
        float x;
        float y;
        float vx;
        float vy;
        bool active;
    };

    struct House {
        float y;                // Position down street
        bool is_subscriber;
        float mailbox_x;
        float window_x;
        bool delivered;
        bool window_broken;
    };

    struct Hazard {
        float x;
        float y;
        float vx;
        float vy;
        int type;               // 0: Barking Dog, 1: Lawnmower, 2: Skateboarder
        bool active;
    };

    Game058Paperboy();
    ~Game058Paperboy() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "Paperboy (1984)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    int GetLives() const { return lives_; }
    int GetPapersRemaining() const { return papers_remaining_; }
    int GetDeliveredCount() const { return delivered_count_; }
    float GetPlayerX() const { return player_x_; }
    float GetPlayerY() const { return player_y_; }
    float GetRouteProgress() const { return route_progress_; }

    void ThrowPaper();
    void SetPapersRemaining(int n) { papers_remaining_ = n; }

private:
    void InitRoute();
    void UpdateBicycle(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdatePapers(float dt);
    void UpdateHazards(float dt);
    void CheckCollisions();

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;
    int lives_;

    float player_x_;
    float player_y_;
    float speed_;
    int papers_remaining_;
    int delivered_count_;
    float route_progress_;

    Paper papers_[MAX_PAPERS];
    House houses_[MAX_HOUSES];
    Hazard hazards_[MAX_HAZARDS];
};

} // namespace arcade
