// game_067_quoridor.h —— 目标 #067 围墙棋 (Quoridor, 1997)
// 机制: 7x7 棋子晶格与 2 格隔墙沟槽 + 越子跳跃 + BFS 双向通路反封死合法性检验 + 最短路博弈 AI
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

class Game067Quoridor : public arcade::Cartridge {
public:
    Game067Quoridor();
    ~Game067Quoridor() override = default;

    uint8_t GetId() const override { return 67; }
    const char* GetName() const override { return "围墙棋"; }
    const char* GetEnglishName() const override { return "Quoridor"; }
    uint16_t GetReleaseYear() const override { return 1997; }
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
    static const int kCells = 7;
    static const int kGrooves = 6;
    static const int kMaxWalls = 5;

    static const int kModeMove = 0;
    static const int kModeWallH = 1;
    static const int kModeWallV = 2;

    void InitBoard();
    void AddScore(uint32_t pts);
    bool IsEdgeBlocked(int c1, int r1, int c2, int r2) const;
    int ShortestPathLen(int sc, int sr, int goal_row) const;
    bool CanPlaceWall(int wc, int wr, bool horiz);
    bool ComputePawnStep(int sc, int sr, int oc, int orow, int dir, int& out_c, int& out_r) const;
    void MakeAiTurn();

    CartridgeState state_;
    bool h_walls_[kGrooves][kGrooves];
    bool v_walls_[kGrooves][kGrooves];
    int player_c_;
    int player_r_;
    int ai_c_;
    int ai_r_;
    int player_walls_;
    int ai_walls_;
    int mode_;
    int aim_dir_;
    int wall_c_;
    int wall_r_;
    bool player_turn_;
    float ai_timer_;
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
    float anim_timer_;
};

} // namespace arcade
