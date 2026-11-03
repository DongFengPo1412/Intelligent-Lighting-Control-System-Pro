#pragma once

#include <cstdint>

namespace arcade {

// Game #172: 伐木工 (Timber - 1984 / Bally Midway)
// 左右双向巨树快斧砍伐、落木倾倒反向闪避防砸、
// 伐木压扁游荡黑熊与限时清林。

class Game172Timber {
public:
    static constexpr uint8_t GAME_ID = 172;
    static constexpr const char* NAME = "伐木工";
    static constexpr const char* ENGLISH_NAME = "Timber";
    static constexpr uint16_t RELEASE_YEAR = 1984;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_PLAYER_CRUSHED = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr uint8_t TREE_STANDING = 0;
    static constexpr uint8_t TREE_FALLING = 1;
    static constexpr uint8_t TREE_FELLED = 2;

    Game172Timber();
    ~Game172Timber() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetStage() const { return stage_; }

    float GetPx() const { return px_; }
    int8_t GetLeftChops() const { return left_chops_; }
    int8_t GetRightChops() const { return right_chops_; }
    uint8_t GetLeftTreeState() const { return left_tree_state_; }
    uint8_t GetRightTreeState() const { return right_tree_state_; }

private:
    uint8_t state_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t stage_;
    float state_timer_;

    float px_;
    float py_;
    int8_t facing_;
    float axe_timer_;

    int8_t max_chops_;
    int8_t left_chops_;
    int8_t right_chops_;
    uint8_t left_tree_state_;
    uint8_t right_tree_state_;
    float left_fall_timer_;
    float right_fall_timer_;

    float bear_x_;
    bool bear_alive_;
    float bear_dir_;
    float bear_speed_;

    float bee_x_;
    float bee_y_;
    bool bee_alive_;
    float bee_speed_;

    void InitStage();
    void CheckStageClear();
};

} // namespace arcade
