#pragma once

#include <cstdint>

namespace arcade {

// Game #170: 矢量坦克战 (Battlezone - 1980 / Atari & Ed Rotberg)
// 街机历史上第一款3D矢量第一人称座舱坦克射击开山鼻祖：
// 顶置360度潜望镜雷达全周扫描索敌、双履带旋转航向与战术倒车、
// 借助几何金字塔掩体战术周旋避弹、远距离弹道火控炮击敌方战车与超级坦克。

class Game170Battlezone {
public:
    static constexpr uint8_t GAME_ID = 170;
    static constexpr const char* NAME = "矢量坦克战";
    static constexpr const char* ENGLISH_NAME = "Battlezone";
    static constexpr uint16_t RELEASE_YEAR = 1980;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_SECTOR_CLEAR = 1;
    static constexpr uint8_t STATE_TANK_EXPLODING = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int NUM_OBSTACLES = 3;
    static constexpr int MAX_ENEMIES = 2;
    static constexpr int MAX_SHELLS = 4;

    struct Obstacle {
        float x;
        float y;
    };

    struct EnemyTank {
        int8_t id;
        float x;
        float y;
        float angle;
        float speed;
        float fire_timer;
        bool is_supertank;
        bool alive;
    };

    struct Shell {
        float x;
        float y;
        float vx;
        float vy;
        float life;
        bool is_player;
        bool active;
    };

    Game170Battlezone();
    ~Game170Battlezone() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetSector() const { return sector_; }
    uint8_t GetKills() const { return enemies_killed_; }

private:
    uint8_t state_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t sector_;
    float state_timer_;

    float px_;
    float py_;
    float angle_;
    float speed_;
    float rot_speed_;
    float fire_cooldown_;

    Obstacle obstacles_[NUM_OBSTACLES];
    EnemyTank enemies_[MAX_ENEMIES];
    Shell shells_[MAX_SHELLS];

    uint8_t enemies_killed_;
    uint8_t target_kills_;

    void InitSector();
    void SpawnEnemy(bool is_supertank);
    void FireCannon();
    bool IsBlockedByObstacle(float x, float y) const;
};

} // namespace arcade
