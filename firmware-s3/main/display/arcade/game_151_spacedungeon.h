#pragma once

#include <cstdint>

namespace arcade {

// Game #151: 空间地牢 (Space Dungeon 1981 / Taito & Rex Battenberg)
// 街机历史上首款双摇杆多房间地牢探索与战利品撤离开山鼻祖：
// 穿梭3x3九宫格星际地牢各舱室收集稀世财宝放入背包、
// 阻击游荡神偷抢夺宝物、规避尖刺无人机并将战利品运抵升降机舱结算撤离。

class Game151SpaceDungeon {
public:
    static constexpr uint8_t GAME_ID = 151;
    static constexpr const char* NAME = "空间地牢";
    static constexpr const char* ENGLISH_NAME = "Space Dungeon";
    static constexpr uint16_t RELEASE_YEAR = 1981;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_PLAYER_HIT = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int MAX_ROOM_TREASURES = 4;
    static constexpr int MAX_ROOM_ENEMIES = 4;
    static constexpr int MAX_LASERS = 5;

    struct Treasure {
        float x;
        float y;
        bool collected;
    };

    struct Enemy {
        float x;
        float y;
        float vx;
        float vy;
        bool alive;
    };

    struct Laser {
        float x;
        float y;
        float vx;
        float vy;
        bool active;
    };

    struct Thief {
        int8_t rx;
        int8_t ry;
        float x;
        float y;
        float vx;
        float vy;
        uint8_t stolen_loot;
        bool alive;
    };

    Game151SpaceDungeon();
    ~Game151SpaceDungeon() = default;

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
    void LoseLife();

    uint8_t state_;
    float state_timer_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t level_;

    int8_t rx_;
    int8_t ry_;
    float px_;
    float py_;
    float facing_x_;
    float facing_y_;
    uint8_t treasures_carried_;
    uint8_t treasures_banked_;

    // 3x3 rooms storage
    Treasure treasures_[3][3][MAX_ROOM_TREASURES];
    int num_treasures_[3][3];

    Enemy enemies_[3][3][MAX_ROOM_ENEMIES];
    int num_enemies_[3][3];

    Laser lasers_[MAX_LASERS];
    Thief thief_;
};

} // namespace arcade
