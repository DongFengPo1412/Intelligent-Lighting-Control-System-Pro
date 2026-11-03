#pragma once

#include <cstdint>

namespace arcade {

// Game #175: 创战纪飞盘决斗 (Discs of Tron - 1983 / Bally Midway)
// 悬空光环平台对决、多重边界反弹回旋能量飞盘、
// 按键激活能量偏转护盾与打落萨克坠入深渊。

class Game175DiscsOfTron {
public:
    static constexpr uint8_t GAME_ID = 175;
    static constexpr const char* NAME = "创战纪飞盘决斗";
    static constexpr const char* ENGLISH_NAME = "Discs of Tron";
    static constexpr uint16_t RELEASE_YEAR = 1983;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_SARK_FALLING = 1;
    static constexpr uint8_t STATE_PLAYER_DIED = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int MAX_DISCS = 6;

    struct Disc {
        float x;
        float y;
        float vx;
        float vy;
        bool is_player;
        bool active;
    };

    Game175DiscsOfTron();
    ~Game175DiscsOfTron() = default;

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
    float GetSx() const { return sx_; }
    int8_t GetSarkHp() const { return sark_hp_; }
    bool IsShieldActive() const { return shield_active_; }
    float GetShieldEnergy() const { return shield_energy_; }

private:
    uint8_t state_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t stage_;
    float state_timer_;

    float px_;
    float py_;
    float speed_;
    bool shield_active_;
    float shield_energy_;

    float sx_;
    float sy_;
    int8_t sark_hp_;
    float sark_dir_;
    float sark_speed_;
    float sark_throw_timer_;

    Disc discs_[MAX_DISCS];

    void InitStage();
};

} // namespace arcade
