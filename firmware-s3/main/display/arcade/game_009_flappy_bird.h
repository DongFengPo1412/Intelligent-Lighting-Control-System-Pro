// game_009_flappy_bird.h —— 目标 #009 飞翔小鸟 16 (Flappy Bird 16)
// 机制: 持续重力下坠 + 单键脉冲拍翅上升 + 管道上下窄缝穿行
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

struct PipeObstacle {
    float x;          // 水平位置 (从右侧 16 移向左侧 -3)
    int gap_y;        // 间隙顶部起始 Y 坐标 (2 ~ 9)
    int gap_height;   // 间隙高度 (通常 4 ~ 5 像素)
    bool scored;      // 是否已被主角穿越计分
};

class Game009FlappyBird : public Cartridge {
public:
    Game009FlappyBird();
    ~Game009FlappyBird() override = default;

    uint8_t GetId() const override { return 9; }
    const char* GetName() const override { return "飞翔小鸟"; }
    const char* GetEnglishName() const override { return "Flappy Bird 16"; }
    uint16_t GetReleaseYear() const override { return 2013; }
    ControlType GetControlType() const override { return CTRL_TAP_SINGLE; }

    void Init() override;
    void Reset() override;
    void Start() override;
    void Pause() override;
    void Resume() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

private:
    void SpawnPipe(PipeObstacle& pipe, float start_x);
    void DrawBird(uint8_t* fb, int bx, int by, bool flap_up);

    CartridgeState state_;
    float bird_x_;
    float bird_y_;
    float bird_vy_;
    bool flap_anim_;
    float flap_timer_;

    static const int kMaxPipes = 2;
    PipeObstacle pipes_[kMaxPipes];

    uint32_t score_;
    uint32_t high_score_;
    float ground_scroll_;
    float state_timer_;
    float anim_timer_;
};

} // namespace arcade

