// game_065_dots_and_boxes.h —— 目标 #065 点格棋 (Dots and Boxes, 1988)
// 机制: 5x5 顶点 4x4 方格网 + 封口占格连击奖励回合 + 防送三边安全策略 AI
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

class Game065DotsAndBoxes : public arcade::Cartridge {
public:
    Game065DotsAndBoxes();
    ~Game065DotsAndBoxes() override = default;

    uint8_t GetId() const override { return 65; }
    const char* GetName() const override { return "点格棋"; }
    const char* GetEnglishName() const override { return "Dots and Boxes"; }
    uint16_t GetReleaseYear() const override { return 1988; }
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
    static const int kTotalEdges = 40;
    static const uint8_t kUnclaimed = 0;
    static const uint8_t kPlayer = 1;
    static const uint8_t kAi = 2;

    void InitBoard();
    void AddScore(uint32_t pts);
    bool IsEdgeClaimed(int edge_id) const;
    void SetEdgeOwner(int edge_id, uint8_t owner);
    void EdgeCenter2x(int edge_id, int& cx2, int& cy2) const;
    int BoxEdgeCount(int br, int bc) const;
    int ClaimEdge(int edge_id, uint8_t owner);
    void SnapCursorToUnclaimed();
    void MoveCursorDir(int dx, int dy);
    void ToggleCursorOrientation();
    int ChooseAiEdge() const;

    CartridgeState state_;
    uint8_t h_edges_[5][4];
    uint8_t v_edges_[4][5];
    uint8_t boxes_[4][4];
    int cur_edge_;
    int player_boxes_;
    int ai_boxes_;
    bool player_turn_;
    float ai_timer_;
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
    float anim_timer_;
};

} // namespace arcade
