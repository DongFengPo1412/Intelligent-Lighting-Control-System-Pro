// game_085_lemmings_rescue.h —— 目标 #085 旅鼠拯救 (Lemmings Rescue)
// 机制: 多层地形自动行进 + 高空坠落致死(>6px)/熔岩陷阱 + 三大经典技能(拦截/搭梯/挖掘)
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

enum LemTile : uint8_t {
    LEM_EMPTY = 0,
    LEM_DIRT  = 1,
    LEM_STEEL = 2,
    LEM_STAIR = 3,
    LEM_LAVA  = 4,
};

enum LemState : uint8_t {
    LEM_STATE_WALKING = 0,
    LEM_STATE_FALLING = 1,
    LEM_STATE_BLOCKER = 2,
    LEM_STATE_BUILDER = 3,
    LEM_STATE_DIGGER  = 4,
};

struct LemmingUnit {
    bool spawned;
    bool alive;
    bool saved;
    int x;
    int y;
    int dir;          // +1 right, -1 left
    uint8_t state;
    int fall_cells;
    int bricks_left;
    float move_accum;
    float skill_timer;
};

class Game085LemmingsRescue : public arcade::Cartridge {
public:
    Game085LemmingsRescue();
    ~Game085LemmingsRescue() override = default;

    uint8_t GetId() const override { return 85; }
    const char* GetName() const override { return "旅鼠拯救"; }
    const char* GetEnglishName() const override { return "Lemmings Rescue"; }
    uint16_t GetReleaseYear() const override { return 1991; }
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
    void LoadStage(uint8_t stg);
    bool IsSolid(int x, int y) const;
    bool HasBlockerAt(int x, int y, int ignore_idx) const;
    void AssignSkillAtCursor();
    void UpdateLemming(int idx, float dt);
    void AddScore(uint32_t pts);

    static const int kNumLemmings = 5;

    CartridgeState state_;
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
    float anim_timer_;
    uint8_t stage_;
    uint8_t spawned_count_;
    uint8_t saved_count_;
    uint8_t dead_count_;
    float spawn_timer_;
    float stage_timer_;
    int hatch_x_;
    int hatch_y_;
    int exit_x_;
    int exit_y_;
    int cursor_x_;
    int cursor_y_;
    uint8_t selected_skill_;  // 0=BLOCKER, 1=BUILDER, 2=DIGGER
    float move_cooldown_;
    uint8_t terrain_[16][16];
    LemmingUnit lemmings_[kNumLemmings];
};

} // namespace arcade
