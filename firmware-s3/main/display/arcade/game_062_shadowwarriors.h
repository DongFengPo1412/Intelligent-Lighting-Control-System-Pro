#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game062ShadowWarriors : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_PLAYING = 1;
    static constexpr uint8_t STATE_DEAD = 2;
    static constexpr uint8_t STATE_VICTORY = 3;

    static constexpr int MAX_ENEMIES = 4;
    static constexpr int MAX_CLONES = 2;
    static constexpr int HISTORY_LEN = 20;

    struct Enemy {
        float x;
        float y;
        float vx;
        int health;
        bool active;
    };

    struct Fireball {
        float x;
        float y;
        float vx;
        float vy;
        bool active;
    };

    Game062ShadowWarriors();
    ~Game062ShadowWarriors() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "Shadow Warriors (1988)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    int GetLives() const { return lives_; }
    int GetNumClones() const { return num_clones_; }
    bool IsDogActive() const { return dog_active_; }
    float GetPlayerX() const { return player_x_; }
    float GetPlayerY() const { return player_y_; }

    void SummonDog();
    void AddShadowClone();
    void TriggerFireDragon();

private:
    void InitStage();
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateClones();
    void UpdateDog(float dt);
    void UpdateFireball(float dt);
    void UpdateEnemies(float dt);
    void CheckCollisions();

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;
    int lives_;
    int player_health_;
    int enemies_defeated_;
    int total_enemies_;

    // Player position & history for shadow clones
    float player_x_;
    float player_y_;
    float player_vx_;
    float player_vy_;
    int player_facing_;
    bool is_slashing_;
    float slash_timer_;
    bool is_wall_clinging_;

    float history_x_[HISTORY_LEN];
    float history_y_[HISTORY_LEN];
    int history_facing_[HISTORY_LEN];
    bool history_slashing_[HISTORY_LEN];
    int history_idx_;
    int num_clones_;

    // Ninja Hound
    bool dog_active_;
    float dog_x_;
    float dog_y_;
    float dog_vx_;
    float dog_timer_;

    Fireball fireball_;
    Enemy enemies_[MAX_ENEMIES];
};

} // namespace arcade
