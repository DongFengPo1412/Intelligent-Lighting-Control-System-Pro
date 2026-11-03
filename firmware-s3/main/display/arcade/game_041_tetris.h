// game_041_tetris.h —— 俄罗斯方块 (Tetris)
// 编号: #041 | 机制: 四联方块旋转、平移堆叠与满行消除
#pragma once

#include "arcade_cartridge.h"
#include <stdint.h>
#include <stdbool.h>

namespace arcade {

class Game041Tetris : public Cartridge {
public:
    Game041Tetris();
    ~Game041Tetris() override = default;

    uint8_t GetId() const override { return 41; }
    const char* GetName() const override { return "俄罗斯方块"; }
    const char* GetEnglishName() const override { return "Tetris"; }
    uint16_t GetReleaseYear() const override { return 1984; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    void Init() override;
    void Reset() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

private:
    static const int kBoardLeft = 3;
    static const int kBoardRight = 12;

    bool CheckCollision(int type, int rot, int x, int y);
    void SpawnPiece();
    void LockPiece();
    void ClearLines();

    uint8_t field_[16][16]; // 0: empty, 1..7: piece color
    int piece_type_;
    int piece_rot_;
    int piece_x_;
    int piece_y_;

    float drop_timer_;
    float drop_interval_;
    uint32_t score_;
    uint16_t lines_cleared_;
    CartridgeState state_;
};

} // namespace arcade
