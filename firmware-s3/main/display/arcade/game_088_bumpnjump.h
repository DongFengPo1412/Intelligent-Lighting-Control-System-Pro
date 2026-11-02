#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game088BumpNJump : public Cartridge {
public:
    Game088BumpNJump();
    ~Game088BumpNJump() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 88; }
    std::string GetName() const override { return "Bump 'n' Jump (1982)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_DRIVING = 0,
        STATE_CRASHED = 1,
        STATE_LEVEL_CLEAR = 2,
        STATE_GAME_OVER = 3
    };

    enum EnemyType {
        ENEMY_CAR = 0,
        ENEMY_TRUCK = 1,
        ENEMY_OBSTACLE = 2
    };

    struct Enemy {
        float x{0.0f};
        float y{0.0f}; // 0 = far ahead, 16 = past screen
        float speed{80.0f};
        EnemyType type{ENEMY_CAR};
        bool active{false};
        float respawn_timer{0.0f};
    };

    GameState GetState() const { return state_; }
    int GetScore() const { return score_; }
    int GetLives() const { return lives_; }
    float GetPlayerX() const { return px_; }
    float GetPlayerY() const { return py_; }
    float GetPlayerSpeed() const { return speed_; }
    float GetJumpZ() const { return jump_z_; }
    bool IsJumping() const { return is_jumping_; }
    float GetDistance() const { return distance_; }
    float GetWaterGapDist() const { return water_gap_dist_; }
    bool IsWaterGapVisible() const { return water_gap_dist_ <= 16.0f && water_gap_dist_ >= -4.0f; }
    int GetCrushedCount() const { return crushed_count_; }
    int GetLevel() const { return level_; }

    static constexpr int MAX_ENEMIES = 4;
    const Enemy& GetEnemy(int i) const { return enemies_[i]; }

private:
    void ResetStage(bool hard_reset);
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateEnemies(float dt);
    void UpdateRoadHazards(float dt);
    void CheckCollisions();

    GameState state_{STATE_DRIVING};
    float state_timer_{0.0f};
    int score_{0};
    int lives_{3};
    int level_{1};
    int crushed_count_{0};

    // Player Buggy
    float px_{7.5f};
    float py_{13.0f};
    float speed_{100.0f}; // 0 to 180 km/h
    float jump_z_{0.0f};  // 0.0 ground, >0 airborne
    float jump_vz_{0.0f};
    bool is_jumping_{false};
    float bump_vx_{0.0f}; // lateral bump impulse
    float bump_boost_cooldown_{0.0f};

    // Road & Progression
    float distance_{0.0f};
    float stage_length_{600.0f};
    float road_scroll_{0.0f};
    float water_gap_dist_{180.0f}; // distance ahead for next broken bridge/water
    float water_gap_length_{6.0f};

    Enemy enemies_[MAX_ENEMIES];
};

} // namespace arcade
