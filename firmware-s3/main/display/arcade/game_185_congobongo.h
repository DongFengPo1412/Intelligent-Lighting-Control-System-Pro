#pragma once

#include <cstdint>

namespace arcade {

// Game #185: 丛林大金刚 (Congo Bongo - 1983 / Sega & Ikegami Tsushinki)
// 等轴立体阶梯攀岩爬瀑布、跳跃规避滚落巨石、浮木渡河与夜袭沉睡巨猿点燃尾巴。

class Game185CongoBongo {
public:
    static constexpr uint8_t GAME_ID = 185;
    static constexpr const char* NAME = "丛林大金刚";
    static constexpr const char* ENGLISH_NAME = "Congo Bongo";
    static constexpr uint16_t RELEASE_YEAR = 1983;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_HUNTER_KILLED = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int MAX_BOULDERS = 4;
    static constexpr int MAX_LOGS = 4;
    static constexpr int MAX_RHINOS = 2;

    struct Boulder {
        float x;
        float y;
        float vx;
        float vy;
        bool active;
    };

    struct Log {
        float x;
        float y;
        float speed;
        float width;
    };

    struct Rhino {
        float x;
        float y;
        float vx;
        bool active;
    };

    Game185CongoBongo();
    ~Game185CongoBongo() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetStage() const { return stage_; }

    float GetPx() const { return px_; }
    float GetPy() const { return py_; }
    bool IsJumping() const { return is_jumping_; }
    bool IsBongoAsleep() const { return bongo_asleep_; }
    bool IsTailIgnited() const { return tail_ignited_; }

private:
    void InitStage();
    void SpawnBoulder();

    uint8_t state_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t stage_;
    float state_timer_;

    // Safari Hunter
    float px_;
    float py_;
    float speed_;
    bool is_jumping_;
    float jump_timer_;

    // Giant Gorilla Bongo
    float bongo_x_;
    float bongo_y_;
    bool bongo_asleep_;
    bool tail_ignited_;

    // Environment hazards
    Boulder boulders_[MAX_BOULDERS];
    float boulder_spawn_timer_;

    Log logs_[MAX_LOGS];
    Rhino rhinos_[MAX_RHINOS];
};

} // namespace arcade
