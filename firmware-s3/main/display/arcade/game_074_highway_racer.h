// game_074_highway_racer.h —— 目标 #074 变道赛车 (Highway Racer 1979)
// 机制: 极速三车道逆向慢车冲刷 + 左右变道超车 + 油门加减速 + 护栏碰撞损毁
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

struct TrafficCar {
    bool active;
    float x;
    float y;
    int lane;
    int width;
    int height;
    float speed;
    uint8_t r, g, b;
};

class Game074HighwayRacer : public Cartridge {
public:
    Game074HighwayRacer();
    ~Game074HighwayRacer() override = default;

    uint8_t GetId() const override { return 74; }
    const char* GetName() const override { return "变道赛车"; }
    const char* GetEnglishName() const override { return "Highway Racer 1979"; }
    uint16_t GetReleaseYear() const override { return 1979; }
    ControlType GetControlType() const override { return CTRL_TWO_BUTTON; }

    void Init() override;
    void Reset() override;
    void Start() override;
    void Pause() override;
    void Resume() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

private:
    void ResetPlayerCar();
    void SpawnTraffic();
    void CrashCar();

    CartridgeState state_;
    float car_x_;
    float speed_;
    float road_scroll_y_;
    float distance_m_;
    float target_distance_;

    uint8_t lives_;
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
    float anim_timer_;
    float spawn_timer_;

    static const int kMaxTraffic = 4;
    TrafficCar traffic_[kMaxTraffic];

    float crash_anim_timer_;
};

} // namespace arcade

