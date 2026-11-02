#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game043Centipede : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_PLAYING = 1;
    static constexpr uint8_t STATE_DEAD = 2;
    static constexpr uint8_t STATE_VICTORY = 3;

    static constexpr int MAX_SEGMENTS = 12;
    static constexpr int MAX_BULLETS = 3;
    static constexpr int MAX_MUSHROOMS = 24;

    struct Segment {
        float x;
        float y;
        int dir_x;   // +1 (right) or -1 (left)
        bool is_head;
        bool active;
    };

    struct Bullet {
        float x;
        float y;
        bool active;
    };

    struct Mushroom {
        int x;
        int y;
        int health; // 2 hits to destroy
        bool active;
    };

    struct Spider {
        float x;
        float y;
        float vx;
        float vy;
        bool active;
    };

    Game043Centipede();
    ~Game043Centipede() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "Centipede (1980)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    int GetLives() const { return lives_; }
    int GetActiveSegmentCount() const;

    float GetPlayerX() const { return player_x_; }
    float GetPlayerY() const { return player_y_; }
    void SetPlayerPos(float x, float y) { player_x_ = x; player_y_ = y; }

    void FireBullet();
    void SpawnMushroom(int x, int y);
    void HitCentipedeSegment(int seg_idx);

private:
    void InitArena();
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateCentipede(float dt);
    void UpdateBullets(float dt);
    void UpdateSpider(float dt);
    void CheckCollisions();

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;
    int lives_;

    float player_x_;
    float player_y_;
    float fire_cooldown_;

    float centipede_step_timer_;
    float centipede_step_interval_;

    Segment segments_[MAX_SEGMENTS];
    Bullet bullets_[MAX_BULLETS];
    Mushroom mushrooms_[MAX_MUSHROOMS];
    Spider spider_;
    float spider_spawn_timer_;
};

} // namespace arcade
