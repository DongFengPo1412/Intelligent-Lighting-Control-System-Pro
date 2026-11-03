#pragma once

#include <cstdint>

namespace arcade {

// Game #158: 划线天蚕变 (Qix 1981 / Taito)
// 街机历史上开创划线圈地与空间切割玩法的里程碑鼻祖：
// 沿边界谨慎推进、按键A慢速画线斩获双倍积分、按键B快速画线抢占先机、
// 切割封闭空间孤立游荡旋动光束Qix、规避巡界电火花占领75%领地胜出。

class Game158Qix {
public:
    static constexpr uint8_t GAME_ID = 158;
    static constexpr const char* NAME = "划线天蚕变";
    static constexpr const char* ENGLISH_NAME = "Qix";
    static constexpr uint16_t RELEASE_YEAR = 1981;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_PLAYER_HIT = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr uint8_t CELL_EMPTY = 0;
    static constexpr uint8_t CELL_BORDER = 1;
    static constexpr uint8_t CELL_CLAIMED = 2;
    static constexpr uint8_t CELL_DRAWING = 3;

    static constexpr float WIN_PERCENTAGE = 70.0f;
    static constexpr int MAX_DRAW_PATH = 64;
    static constexpr int NUM_SPARX = 2;

    struct Sparx {
        float x;
        float y;
        int8_t dir;
    };

    Game158Qix();
    ~Game158Qix() = default;

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
    void ClaimTerritory();
    float CalcPercent() const;

    uint8_t state_;
    float state_timer_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t level_;

    int8_t px_;
    int8_t py_;
    bool is_drawing_;
    bool draw_slow_;

    uint8_t grid_[16][16];

    int8_t draw_path_x_[MAX_DRAW_PATH];
    int8_t draw_path_y_[MAX_DRAW_PATH];
    int draw_path_len_;

    float qx_;
    float qy_;
    float qvx_;
    float qvy_;

    Sparx sparx_[NUM_SPARX];
    float percent_claimed_;
};

} // namespace arcade
