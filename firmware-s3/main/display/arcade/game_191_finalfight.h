#pragma once

#include <cstdint>

namespace arcade {

// Game #191: 快打旋风 (Final Fight - 1989 / Capcom)
// 近身抓投螺旋打桩机、消耗生命值释放旋风双截拳绝对无敌击飞、
// 破坏铁桶获取烤鸡。

class Game191FinalFight {
public:
    static constexpr uint8_t GAME_ID = 191;
    static constexpr const char* NAME = "快打旋风";
    static constexpr const char* ENGLISH_NAME = "Final Fight";
    static constexpr uint16_t RELEASE_YEAR = 1989;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_HAGGAR_KO = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int MAX_ENEMIES = 3;

    struct Enemy {
        float x;
        float y;
        float hp;
        float max_hp;
        uint8_t type; // 0: thug, 1: boss
        bool alive;
        uint8_t state; // 0: normal, 1: knockdown, 2: grabbed
        float kd_timer;
    };

    struct Barrel {
        float x;
        float y;
        bool broken;
        bool item_active;
        float item_x;
        float item_y;
    };

    Game191FinalFight();
    ~Game191FinalFight() = default;

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
    float GetHp() const { return hp_; }
    bool IsSpinning() const { return is_spinning_; }
    bool IsPiledriving() const { return is_piledriving_; }

private:
    void InitStage();

    uint8_t state_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t stage_;
    float state_timer_;

    // Mike Haggar
    float px_;
    float py_;
    int8_t facing_;
    float speed_;
    float hp_;
    float max_hp_;

    bool is_punching_;
    float punch_timer_;
    bool is_spinning_;
    float spin_timer_;

    int8_t grabbed_enemy_idx_;
    bool is_piledriving_;
    float piledrive_timer_;
    float piledrive_height_;

    Enemy enemies_[MAX_ENEMIES];
    Barrel barrel_;
};

} // namespace arcade
