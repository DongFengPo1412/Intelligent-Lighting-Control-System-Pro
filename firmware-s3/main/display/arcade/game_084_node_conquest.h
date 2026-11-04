// game_084_node_conquest.h —— 目标 #084 节点征服 (Node Conquest)
// 机制: 7节点实时兵力增殖 + 50%舰队分派与全军突击 + 节点攻占翻转对决
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

enum NodeOwner : uint8_t {
    NODE_NEUTRAL = 0,
    NODE_PLAYER  = 1,
    NODE_AI      = 2,
};

struct ConquestNode {
    int x;  // 左上角 X (占据 2x2)
    int y;  // 左上角 Y (占据 2x2)
    uint8_t owner;
    float troops;
};

struct ConquestFleet {
    bool active;
    uint8_t owner;
    int target_node;
    float troops;
    float x;
    float y;
    float vx;
    float vy;
};

class Game084NodeConquest : public arcade::Cartridge {
public:
    Game084NodeConquest();
    ~Game084NodeConquest() override = default;

    uint8_t GetId() const override { return 84; }
    const char* GetName() const override { return "节点征服"; }
    const char* GetEnglishName() const override { return "Node Conquest"; }
    uint16_t GetReleaseYear() const override { return 2008; }
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
    void MoveCursorDir(int dx, int dy);
    void DispatchFleet(int src_idx, int dst_idx);
    void UpdateAI(float dt);
    void AddScore(uint32_t pts);

    static const int kNumNodes = 7;
    static const int kMaxFleets = 24;

    CartridgeState state_;
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
    float anim_timer_;
    int cursor_node_;
    int selected_node_;
    float ai_timer_;
    ConquestNode nodes_[kNumNodes];
    ConquestFleet fleets_[kMaxFleets];
};

} // namespace arcade
