// game_011_frogger.h —— 像素青蛙过河 1981 (Frogger 1981)
// 编号: #011 | 机制: 垂直多车道公路闪避 + 水流浮木动态附着漂移 + 五穴安全进驻清屏
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

struct LaneObstacle {
    float x;        // 障碍物/浮木左端 X
    float width;    // 宽度 (格数)
};

struct Lane {
    float speed;    // 速度 (+向右, -向左)
    int num_items;  // 该车道障碍物数 (通常 2~3 个均匀分布)
    float item_w;   // 障碍物宽度
    LaneObstacle items[3];
    bool is_river;  // true=河流浮木 (站上安全, 没站溺亡); false=公路汽车 (撞击致死)
    uint8_t r, g, b;// 颜色
};

class Game011Frogger : public Cartridge {
public:
    Game011Frogger();
    ~Game011Frogger() override = default;

    uint8_t GetId() const override { return 11; }
    const char* GetName() const override { return "青蛙过河"; }
    const char* GetEnglishName() const override { return "Frogger 1981"; }
    uint16_t GetReleaseYear() const override { return 1981; }
    ControlType GetControlType() const override { return CTRL_DPAD_4WAY; }

    void Init() override;
    void Reset() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

private:
    void ResetFrogPosition();
    void SetupLanes();
    void KillFrog();

    CartridgeState state_;
    float frog_x_;          // 青蛙 X (0.0 ~ 15.0)
    int frog_y_;            // 青蛙网格 Y (0 ~ 14)
    uint8_t lives_;         // 剩余生命 (初始 3)
    uint32_t score_;
    uint32_t high_score_;
    float round_timer_;     // 关卡倒计时 (初始 30s)
    float state_timer_;

    // 终点五个荷叶洞穴状态 (x = 1, 4, 7, 10, 13)
    static const int kNumHomes = 5;
    bool homes_[kNumHomes];
    int homes_occupied_;

    // 车道配置: 12 条动态车道 (Row 1..5 河流, Row 7..12 公路)
    static const int kTotalLanes = 16;
    Lane lanes_[kTotalLanes];
};

} // namespace arcade
