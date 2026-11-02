// game_029_slither_arena.h —— 像素贪吃蛇大作战 2016 (Slither Arena 2016)
// 编号: #029 | 机制: 多蛇竞技追尾拦截 + 蛇头触身暴毙粉碎 + 残骸爆裂光子化吞食 + 损躯超速冲刺超车
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

struct SnakeSegment {
    int8_t x;
    int8_t y;
};

struct EnergyOrb {
    bool active;
    int8_t x;
    int8_t y;
    uint8_t value; // 营养价值 (提供长度与积分)
};

class Game029SlitherArena : public Cartridge {
public:
    Game029SlitherArena();
    ~Game029SlitherArena() override = default;

    uint8_t GetId() const override { return 29; }
    const char* GetName() const override { return "蛇蛇大作战"; }
    const char* GetEnglishName() const override { return "Slither Arena 2016"; }
    uint16_t GetReleaseYear() const override { return 2016; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    void Init() override;
    void Reset() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

private:
    void InitArena();
    void SpawnRandomOrb();
    void DissolveSnake(bool is_player);
    void RespawnEnemyAI();
    void UpdatePlayer(float dt, uint16_t keys_down, uint16_t keys_pressed);
    void UpdateEnemyAI(float dt);
    void CheckInterSnakeCollisions();

    CartridgeState state_;

    static constexpr int MAX_LEN = 28;

    // 玩家蛇
    SnakeSegment player_body_[MAX_LEN];
    int player_len_;
    int player_dir_; // 0:UP, 1:RIGHT, 2:DOWN, 3:LEFT
    float player_timer_;
    bool player_boosting_;
    float player_boost_cost_timer_;
    int lives_;

    // 竞争敌方 AI 蛇
    SnakeSegment ai_body_[MAX_LEN];
    int ai_len_;
    int ai_dir_;
    float ai_timer_;
    bool ai_alive_;
    float ai_respawn_timer_;

    // 光子能量点
    static constexpr int MAX_ORBS = 18;
    EnergyOrb orbs_[MAX_ORBS];

    int kill_count_;
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
};

} // namespace arcade
