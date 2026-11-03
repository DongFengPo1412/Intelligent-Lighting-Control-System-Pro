#pragma once

#include <cstdint>

namespace arcade {

// Game #156: 西游降魔 (SonSon 1984 / Capcom)
// 街机历史上首款六层平台变轨跳跃与西游神话横版射击开山鼻祖：
// 小灵猴孙悟空在六层悬空竹简平台间敏捷上下变轨飞跃、
// 平射金箍棒法力魔弹击溃各层妖魔群落、吞食四溢瓜果盛宴挺进天竺胜境。

class Game156SonSon {
public:
    static constexpr uint8_t GAME_ID = 156;
    static constexpr const char* NAME = "西游降魔";
    static constexpr const char* ENGLISH_NAME = "SonSon";
    static constexpr uint16_t RELEASE_YEAR = 1984;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_PLAYER_HIT = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int NUM_LANES = 6;
    static constexpr float MAX_DISTANCE = 100.0f;
    static constexpr int MAX_SHOTS = 5;
    static constexpr int MAX_ENEMIES = 4;
    static constexpr int MAX_FRUITS = 4;

    struct Shot {
        float x;
        float y;
        uint8_t lane;
        float vx;
        bool active;
    };

    struct Enemy {
        float x;
        uint8_t lane;
        float vx;
        uint8_t type; // 0: bat, 1: imp, 2: boar
        float respawn_timer;
        bool alive;
    };

    struct Fruit {
        float x;
        uint8_t lane;
        bool is_melon;
        bool active;
    };

    Game156SonSon();
    ~Game156SonSon() = default;

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

    float px_;
    float py_;
    uint8_t lane_idx_;
    float distance_;

    Shot shots_[MAX_SHOTS];
    Enemy enemies_[MAX_ENEMIES];
    Fruit fruits_[MAX_FRUITS];
};

} // namespace arcade
