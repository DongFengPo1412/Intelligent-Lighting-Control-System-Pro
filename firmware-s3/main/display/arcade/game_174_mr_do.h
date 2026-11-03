#pragma once

#include <cstdint>

namespace arcade {

// Game #174: 挖金子小丑 (Mr. Do! - 1982 / Universal)
// 地底回旋弹跳魔球投掷回收、横向推移大苹果砸扁地底怪兽、
// 吃尽樱桃串清屏与拼写EXTRA。

class Game174MrDo {
public:
    static constexpr uint8_t GAME_ID = 174;
    static constexpr const char* NAME = "挖金子小丑";
    static constexpr const char* ENGLISH_NAME = "Mr. Do!";
    static constexpr uint16_t RELEASE_YEAR = 1982;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_PLAYER_DIED = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int NUM_APPLES = 3;
    static constexpr int NUM_MONSTERS = 2;

    struct Apple {
        float x;
        float y;
        bool falling;
        float fall_vy;
        float wobble;
    };

    struct Monster {
        int8_t id;
        float x;
        float y;
        float speed;
        bool alive;
    };

    struct PowerBall {
        bool active;
        float x;
        float y;
        float vx;
        float vy;
        float cooldown;
    };

    Game174MrDo();
    ~Game174MrDo() = default;

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
    bool IsBallActive() const { return ball_.active; }
    uint16_t GetCherriesLeft() const { return cherries_left_; }

private:
    uint8_t state_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t stage_;
    float state_timer_;

    float px_;
    float py_;
    float facing_x_;
    float facing_y_;
    float speed_;

    uint8_t dirt_mask_[32]; // 256 bits for 16x16 dirt
    uint8_t cherry_mask_[32]; // 256 bits for cherries
    uint16_t cherries_left_;

    Apple apples_[NUM_APPLES];
    Monster monsters_[NUM_MONSTERS];
    PowerBall ball_;

    void InitStage();
    bool IsDirt(int x, int y) const;
    void ClearDirt(int x, int y);
    bool IsCherry(int x, int y) const;
    void RemoveCherry(int x, int y);
    void CheckMonstersEliminated();
};

} // namespace arcade
