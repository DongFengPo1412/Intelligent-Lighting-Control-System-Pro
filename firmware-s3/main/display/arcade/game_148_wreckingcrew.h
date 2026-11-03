#pragma once

#include <cstdint>

namespace arcade {

// Game #148: 拆迁队 (Wrecking Crew 1985 / Nintendo Vs. System)
// 街机历史上最具策略深度的无跳跃重锤拆迁动作解谜经典：
// 玩家化身拆迁工马力欧手持重型大锤敲碎砖墙与混凝土立柱、
// 敲击炸药桶引发整层连续爆破链式塌陷、穿梭多层脚手架梯子规避扳手怪与工头巡逻。

class Game148WreckingCrew {
public:
    static constexpr uint8_t GAME_ID = 148;
    static constexpr const char* NAME = "拆迁队";
    static constexpr const char* ENGLISH_NAME = "Wrecking Crew";
    static constexpr uint16_t RELEASE_YEAR = 1985;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_PLAYER_HIT = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int MAX_WALLS = 12;
    static constexpr int MAX_DYNAMITE = 4;
    static constexpr int MAX_LADDERS = 4;
    static constexpr int MAX_ENEMIES = 3;

    struct Wall {
        int8_t x;
        int8_t y;
        int8_t hp;
        bool is_pillar;
    };

    struct Dynamite {
        int8_t x;
        int8_t y;
        bool active;
    };

    struct Ladder {
        int8_t x;
        int8_t y_top;
        int8_t y_bot;
    };

    struct Enemy {
        float x;
        float y;
        float vx;
        bool alive;
    };

    Game148WreckingCrew();
    ~Game148WreckingCrew() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetLevel() const { return level_; }

private:
    void InitLevel();
    void StrikeHammer();
    void DetonateDynamite(int floor_y);
    void LoseLife();
    bool IsOnLadder(float x, float y) const;
    int GetNearestFloor(float y) const;

    uint8_t state_;
    float state_timer_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t level_;

    float px_;
    float py_;
    int8_t facing_;
    float hammer_timer_;

    Wall walls_[MAX_WALLS];
    int num_walls_;

    Dynamite dynamite_[MAX_DYNAMITE];
    int num_dynamite_;

    Ladder ladders_[MAX_LADDERS];
    int num_ladders_;

    Enemy enemies_[MAX_ENEMIES];
    int num_enemies_;
};

} // namespace arcade

