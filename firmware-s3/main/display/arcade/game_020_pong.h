// game_020_pong.h —— 目标 #020 双人乒乓 (Pong 1972)
// 机制: 刚体小球双向反弹 + 挡板切角改变斜率 + 漏接失分 + 回合速度递增
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

class Game020Pong : public Cartridge {
public:
    Game020Pong();
    ~Game020Pong() override = default;

    uint8_t GetId() const override { return 20; }
    const char* GetName() const override { return "双人乒乓"; }
    const char* GetEnglishName() const override { return "Pong 1972"; }
    uint16_t GetReleaseYear() const override { return 1972; }
    ControlType GetControlType() const override { return CTRL_VERSUS_DUAL; }

    void Init() override;
    void Reset() override;
    void Start() override;
    void Pause() override;
    void Resume() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

private:
    void ResetBall(bool serve_to_right);

    CartridgeState state_;
    float p1_y_;
    float p2_y_;
    float paddle_h_;

    float ball_x_;
    float ball_y_;
    float ball_vx_;
    float ball_vy_;

    uint8_t p1_score_;
    uint8_t p2_score_;
    static const uint8_t kWinningScore = 5;

    bool p2_is_ai_;
    float serve_delay_;
    float state_timer_;
    float anim_timer_;
    uint32_t high_score_;

    // AI 瞄准误差: 每次 P1 回球/发球时重新抽取, 保证单人模式可被击败 (与 Python 同一 LCG)
    float AiRandError();
    static constexpr float kAiSpeed = 6.0f;
    static constexpr float kAiMaxError = 1.8f;
    uint32_t ai_seed_ = 0x1972;
    float ai_error_ = 0.0f;
};

} // namespace arcade

