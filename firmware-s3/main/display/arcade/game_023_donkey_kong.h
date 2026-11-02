// game_023_donkey_kong.h —— 经典大金刚 1981 (Donkey Kong 1981)
// 编号: #023 | 机制: 多层倾斜钢梁 + 梯子垂直攀爬 + 滚木桶跳跃规避 + 铁锤破击拯救
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

struct Barrel {
    bool active;
    float x;
    float y;
    float vx;
    int layer;         // 当前所在层 (3=顶层, 2, 1, 0=底层)
    bool falling_ladder;
};

class Game023DonkeyKong : public Cartridge {
public:
    Game023DonkeyKong();
    ~Game023DonkeyKong() override = default;

    uint8_t GetId() const override { return 23; }
    const char* GetName() const override { return "经典大金刚"; }
    const char* GetEnglishName() const override { return "Donkey Kong 1981"; }
    uint16_t GetReleaseYear() const override { return 1981; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    void Init() override;
    void Reset() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

private:
    void InitLevel();
    void SpawnBarrel();
    void UpdateBarrels(float dt);
    bool IsOnLadder(int x, int y) const;

    CartridgeState state_;

    float player_x_;
    float player_y_;
    float player_vy_;
    float jump_base_y_;
    bool is_climbing_;
    bool is_jumping_;
    int lives_;
    float hammer_timer_; // 铁锤威力倒计时

    static constexpr int MAX_BARRELS = 4;
    Barrel barrels_[MAX_BARRELS];
    float barrel_spawn_timer_;

    // 铁锤道具坐标
    int hammer_x_;
    int hammer_y_;
    bool hammer_available_;

    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
};

} // namespace arcade
