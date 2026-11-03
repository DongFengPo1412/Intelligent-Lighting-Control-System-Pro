#pragma once

#include <cstdint>
#include "esp_timer.h"

namespace arcade {

// Game #130: 丛林探险 (Jungle Hunt 1982 / Taito)
// 街机历史上开创多阶段连续野外探险的传奇冒险动作鼻祖：
// 树冠摇摆藤条跳跃、鳄鱼狂澜潜水刺杀与氧气管理、滚石坡道翻跳规避、土著部落绳索大营救。

class Game130JungleHunt {
public:
    static constexpr uint8_t GAME_ID = 130;
    static constexpr const char* NAME = "丛林探险";
    static constexpr const char* ENGLISH_NAME = "Jungle Hunt";
    static constexpr uint16_t RELEASE_YEAR = 1982;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STAGE_VINES = 0;
    static constexpr uint8_t STAGE_RIVER = 1;
    static constexpr uint8_t STAGE_BOULDERS = 2;
    static constexpr uint8_t STAGE_RESCUE = 3;

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_PLAYER_DYING = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    Game130JungleHunt();
    ~Game130JungleHunt() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint8_t GetStage() const { return stage_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    float GetProgress() const { return progress_; }
    float GetOxygen() const { return oxygen_; }

private:
    void InitStage(uint8_t stage);
    void UpdateVines(float dt, uint16_t buttons, uint16_t prev_buttons);
    void UpdateRiver(float dt, uint16_t buttons, uint16_t prev_buttons);
    void UpdateBoulders(float dt, uint16_t buttons, uint16_t prev_buttons);
    void UpdateRescue(float dt, uint16_t buttons, uint16_t prev_buttons);

    uint8_t state_;
    float state_timer_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t stage_; // 0: Vines, 1: River, 2: Boulders, 3: Rescue
    uint8_t expedition_round_;
    float progress_; // 0.0 to 100.0%

    // Player coordinates & dynamics
    float px_;
    float py_;
    float pvx_;
    float pvy_;
    bool is_jumping_;
    bool is_ducking_;

    // Stage 0: Vines
    float vine_angle_[2]; // Sways between -0.8 and +0.8
    float vine_x_[2];
    int current_vine_;
    bool in_air_;

    // Stage 1: River
    float oxygen_;
    float croc_x_[3];
    float croc_y_[3];
    float croc_vx_[3];
    bool croc_mouth_open_[3];
    bool is_stabbing_;
    float stab_timer_;

    // Stage 2: Boulders
    float boulder_x_[3];
    float boulder_y_[3];
    float boulder_vx_[3];
    bool boulder_is_high_[3]; // High bouncing or low rolling

    // Stage 3: Rescue
    float native_x_;
    float native_vx_;
    float maiden_y_;
    bool maiden_rescued_;
};

} // namespace arcade
