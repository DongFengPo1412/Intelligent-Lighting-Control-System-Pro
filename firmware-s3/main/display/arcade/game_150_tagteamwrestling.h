#pragma once

#include <cstdint>

namespace arcade {

// Game #150: 双打职业摔角 (Tag Team Wrestling 1983 / Data East & Technos)
// 街机历史上摔角格斗游戏的奠基鼻祖：
// 擂台围绳弹性反弹冲撞、缠斗角力极速按键拼力摔投、
// 边绳拍手换人交替休息恢复体力、击倒压制裁判三秒数秒绝杀取胜。

class Game150TagTeamWrestling {
public:
    static constexpr uint8_t GAME_ID = 150;
    static constexpr const char* NAME = "双打职业摔角";
    static constexpr const char* ENGLISH_NAME = "Tag Team Wrestling";
    static constexpr uint16_t RELEASE_YEAR = 1983;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_NEUTRAL = 0;
    static constexpr uint8_t STATE_REBOUNDING = 1;
    static constexpr uint8_t STATE_GRAPPLE = 2;
    static constexpr uint8_t STATE_DOWNED = 3;
    static constexpr uint8_t STATE_PINFALL = 4;
    static constexpr uint8_t STATE_MATCH_WON = 5;
    static constexpr uint8_t STATE_MATCH_LOST = 6;

    Game150TagTeamWrestling();
    ~Game150TagTeamWrestling() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetLevel() const { return level_; }

private:
    void InitMatch();

    uint8_t state_;
    float state_timer_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t level_;

    float px_;
    float py_;
    float pvx_;
    float pvy_;
    float p_hp_;
    float p_stamina_;
    float partner_hp_;
    bool partner_active_;

    float ox_;
    float oy_;
    float ovx_;
    float ovy_;
    float o_hp_;
    float o_stamina_;

    float grapple_meter_;
    float pin_count_;
    bool pinning_player_;
};

} // namespace arcade
