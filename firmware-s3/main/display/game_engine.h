#pragma once

#include "display_types.h"
#include "display_hal.h"

class GameEngine {
public:
    GameEngine();
    ~GameEngine() = default;

    // 游戏重置与初始化
    void InitSnake();
    void InitTetris();

    // 帧渲染与步进
    // 返回值: 下一帧渲染建议延时 (毫秒)
    uint32_t RunSnake();
    uint32_t RunTetris();

    // 绘制计分看板 (模式 20, 22)
    void DrawScore(int score);

    // 游戏状态查询
    bool IsSnakeGameOver() const { return snake_game_over_; }
    bool IsTetrisGameOver() const { return tetris_game_over_; }
    int GetSnakeScore() const { return snake_score_; }
    int GetTetrisScore() const { return tetris_score_; }

    // 外部操作输入接口 (用于按键/串口/网络控制)
    void SnakeSetDirection(int dx, int dy);
    void TetrisMove(int dx);
    void TetrisRotate();
    void TetrisDrop();

private:
    // 贪吃蛇状态
    int snake_x_[TOTAL_LEDS];
    int snake_y_[TOTAL_LEDS];
    int snake_len_;
    int snake_dx_;
    int snake_dy_;
    int food_x_;
    int food_y_;
    int snake_score_;
    int snake_speed_ms_;
    uint32_t last_snake_tick_;
    bool snake_game_over_;

    // 俄罗斯方块状态
    uint8_t tetris_field_[16][16];
    int piece_type_;
    int piece_rot_;
    int piece_x_;
    int piece_y_;
    int tetris_score_;
    int tetris_speed_ms_;
    uint32_t last_tetris_tick_;
    bool tetris_game_over_;

    static const int BOARD_LEFT = 3;
    static const int BOARD_RIGHT = 12;

    bool CheckTetrisCollision(int type, int rot, int x, int y);
    void SpawnTetrisPiece();
    ColorRGB GetTetrisColor(int type);
};
