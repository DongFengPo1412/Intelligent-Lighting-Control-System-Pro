// game_012_highway_racer.h —— 极速变道赛车 1982 (Highway Racer 1982)
// 编号: #012 | 机制: 极速三车道逆向慢车冲刷 + 左右变道超车 + 油门加减速 + 护栏碰撞损毁
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

struct TrafficCar {
    bool active;
    float x;        // 中心 X (3, 7, 11)
    float y;        // 头部 Y (-3 ~ 17)
    int lane;       // 0, 1, 2
    int width;      // 2
    int height;     // 2 或 3 (卡车)
    float speed;    // 自身绝对速度
    uint8_t r, g, b;// 车型颜色
};

class Game012HighwayRacer : public Cartridge {
public:
    Game012HighwayRacer();
    ~Game012HighwayRacer() override = default;

    uint8_t GetId() const override { return 12; }
    const char* GetName() const override { return "极速变道赛车"; }
    const char* GetEnglishName() const override { return "Highway Racer 1982"; }
    uint16_t GetReleaseYear() const override { return 1982; }
    ControlType GetControlType() const override { return CTRL_TWO_BUTTON; }

    void Init() override;
    void Reset() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

private:
    void ResetPlayerCar();
    void SpawnTraffic();
    void CrashCar();

    CartridgeState state_;
    float car_x_;           // 玩家赛车中心 X (2.8 ~ 11.2)
    float speed_;           // 当前速度 (10.0 ~ 30.0 像素/秒，相当于 80~240 km/h)
    float road_scroll_y_;   // 道路标线滚动相位
    float distance_m_;      // 累计行驶里程 (米)
    float target_distance_; // 目标里程 (1000m 通关)

    uint8_t lives_;         // 剩余生命 (初始 3)
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
    float spawn_timer_;

    // 道路敌车 (最多 4 辆同屏)
    static const int kMaxTraffic = 4;
    TrafficCar traffic_[kMaxTraffic];

    // 翻车特效计时
    float crash_anim_timer_;
};

} // namespace arcade
