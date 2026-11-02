// game_018_minesweeper.h —— 像素扫雷 1990 (Minesweeper 1990)
// 编号: #018 | 机制: 网格光标探测 + 首按防爆生成 + 洪水填充零区翻开 + 八邻域计数与插旗
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

struct MineCell {
    bool has_mine;
    bool revealed;
    bool flagged;
    uint8_t neighbor_mines;
};

class Game018Minesweeper : public Cartridge {
public:
    Game018Minesweeper();
    ~Game018Minesweeper() override = default;

    uint8_t GetId() const override { return 18; }
    const char* GetName() const override { return "像素扫雷"; }
    const char* GetEnglishName() const override { return "Minesweeper 1990"; }
    uint16_t GetReleaseYear() const override { return 1990; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    void Init() override;
    void Reset() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

private:
    void GenerateMines(int safe_x, int safe_y);
    void Reveal(int x, int y);
    void ToggleFlag(int x, int y);
    void CheckVictory();

    CartridgeState state_;
    int cursor_x_;
    int cursor_y_;
    bool first_click_;

    static const int kTotalMines = 25;
    MineCell grid_[16][16];
    int remaining_hidden_safe_;
    int flags_placed_;

    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
    float cursor_blink_timer_;
};

} // namespace arcade
