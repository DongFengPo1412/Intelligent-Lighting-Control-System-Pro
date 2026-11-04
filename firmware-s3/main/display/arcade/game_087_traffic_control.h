// game_087_traffic_control.h —— 目标 #087 交通灯管理 (Traffic Control)
// 机制: 十字路口双向车流排队 + 红绿灯相位切换/全红清空 + T字碰撞与压车路怒双重危机
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

struct TrafficControlCar087 {
    bool active;
    uint8_t lane;   // 0=Southbound(x=6), 1=Northbound(x=9), 2=Eastbound(y=9), 3=Westbound(y=6)
    float prog;     // 0.0 (spawn) -> 5.0 (stop line) -> 10.0 (clear box) -> 15.6 (exit)
    float speed;
    uint8_t color_id;
};

class Game087TrafficControl : public arcade::Cartridge {
public:
    Game087TrafficControl();
    ~Game087TrafficControl() override = default;

    uint8_t GetId() const override { return 87; }
    const char* GetName() const override { return "交通灯管理"; }
    const char* GetEnglishName() const override { return "Traffic Control"; }
    uint16_t GetReleaseYear() const override { return 1992; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    void Init() override;
    void Reset() override;
    void Start() override;
    void Pause() override;
    void Resume() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

private:
    void SetupMatch(CartridgeState new_state);
    void SpawnCar(uint8_t lane);
    void CarXY(const TrafficControlCar087& c, float& out_x, float& out_y) const;
    bool IsAxisGreen(uint8_t axis) const; // axis 0 = N-S, axis 1 = E-W
    void RecordIncident(int fx, int fy);
    void AddScore(uint32_t pts);

    static const int kMaxCars = 16;
    static const int kTargetCars = 30;

    CartridgeState state_;
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
    float anim_timer_;
    uint8_t phase_;          // 0 = N-S Green / E-W Red, 1 = N-S Red / E-W Green
    float all_red_timer_;    // >0 means temporary All-Red clearance active
    uint8_t passed_cars_;
    uint8_t incidents_;      // 3 incidents -> STATE_GAMEOVER
    float spawn_timer_;
    uint32_t rng_seed_;
    float crash_flash_timer_;
    int crash_x_;
    int crash_y_;
    float lane_rage_timer_[4];
    TrafficControlCar087 cars_[kMaxCars];
};

} // namespace arcade
