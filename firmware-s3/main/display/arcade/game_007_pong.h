// game_007_pong.h —— 双人乒乓 1972 (Pong 1972)
// 编号: #007 | 机制: 刚体小球双向反弹 + 挡板切角改变斜率 + 漏接失分 + 回合速度递增
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

class Game007Pong : public Cartridge {
public:
    Game007Pong();
    ~Game007Pong() override = default;

    uint8_t GetId() const override { return 7; }
    const char* GetName() const override { return "双人乒乓"; }
    const char* GetEnglishName() const override { return "Pong 1972"; }
    uint16_t GetReleaseYear() const override { return 1972; }
    ControlType GetControlType() const override { return CTRL_VERSUS_DUAL; }

    void Init() override;
    void Reset() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

private:
    void ResetBall(bool serve_to_right);

    CartridgeState state_;
    float p1_y_;            // 左侧玩家挡板顶部 Y (0 ~ 12)
    float p2_y_;            // 右侧玩家/AI 挡板顶部 Y (0 ~ 12)
    float paddle_h_;        // 挡板高度 (4 像素)

    float ball_x_;          // 小球位置 X
    float ball_y_;          // 小球位置 Y
    float ball_vx_;         // 小球水平速度
    float ball_vy_;         // 小球垂直速度

    uint8_t p1_score_;      // 左侧得分
    uint8_t p2_score_;      // 右侧得分
    static const uint8_t kWinningScore = 5;

    bool p2_is_ai_;         // 是否开启右侧 AI 伴随对打
    float serve_delay_;     // 进球后发球短暂停顿
    float state_timer_;
};

} // namespace arcade
