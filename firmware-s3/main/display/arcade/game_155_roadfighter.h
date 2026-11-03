#pragma once

#include <cstdint>

namespace arcade {

// Game #155: 公路争霸 (Road Fighter 1984 / Konami)
// 街机历史上最著名的极速飙车与打盘救车甩尾竞速经典：
// 高低双档极速升档轰油至400公里/小时、高速擦碰引发剧烈鱼尾侧滑、
// 极速反向打舵漂移救车回正、追赶超车彩虹奖励车补充燃油狂飙冲线。

class Game155RoadFighter {
public:
    static constexpr uint8_t GAME_ID = 155;
    static constexpr const char* NAME = "公路争霸";
    static constexpr const char* ENGLISH_NAME = "Road Fighter";
    static constexpr uint16_t RELEASE_YEAR = 1984;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_CAR_CRASHED = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr float ROAD_LEFT = 2.5f;
    static constexpr float ROAD_RIGHT = 12.5f;
    static constexpr float TOTAL_DISTANCE = 1000.0f;

    static constexpr int MAX_TRAFFIC = 3;
    static constexpr int MAX_OIL = 2;

    struct TrafficCar {
        float x;
        float y;
        float speed;
        bool is_truck;
    };

    struct OilSlick {
        float x;
        float y;
    };

    struct BonusCar {
        float x;
        float y;
        float speed;
        bool active;
    };

    Game155RoadFighter();
    ~Game155RoadFighter() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetLevel() const { return level_; }

private:
    void InitRace();
    void Crash();

    uint8_t state_;
    float state_timer_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t level_;

    float px_;
    float speed_;
    float distance_;
    float fuel_;

    bool is_slipping_;
    float slip_dir_;
    float slip_counter_steer_time_;

    TrafficCar traffic_[MAX_TRAFFIC];
    OilSlick oil_slicks_[MAX_OIL];
    BonusCar rainbow_car_;

    float road_scroll_;
};

} // namespace arcade
