#include "game_engine.h"
#include <string.h>

// 7 种俄罗斯方块的 4 种旋转姿态定义 (7, 4, 4, 2)
static const int8_t tetris_shapes[7][4][4][2] = {
    // 0: O 型 (方块)
    {{{0,0},{1,0},{0,1},{1,1}}, {{0,0},{1,0},{0,1},{1,1}}, {{0,0},{1,0},{0,1},{1,1}}, {{0,0},{1,0},{0,1},{1,1}}},
    // 1: I 型 (长条)
    {{{0,1},{1,1},{2,1},{3,1}}, {{2,0},{2,1},{2,2},{2,3}}, {{0,2},{1,2},{2,2},{3,2}}, {{1,0},{1,1},{1,2},{1,3}}},
    // 2: T 型
    {{{1,0},{0,1},{1,1},{2,1}}, {{1,0},{1,1},{2,1},{1,2}}, {{0,1},{1,1},{2,1},{1,2}}, {{1,0},{0,1},{1,1},{1,2}}},
    // 3: L 型
    {{{0,1},{1,1},{2,1},{2,0}}, {{1,0},{1,1},{1,2},{2,2}}, {{0,2},{0,1},{1,1},{2,1}}, {{0,0},{1,0},{1,1},{1,2}}},
    // 4: J 型
    {{{0,0},{0,1},{1,1},{2,1}}, {{1,2},{1,1},{1,0},{2,0}}, {{0,1},{1,1},{2,1},{2,2}}, {{0,2},{1,2},{1,1},{1,0}}},
    // 5: S 型
    {{{1,0},{2,0},{0,1},{1,1}}, {{1,0},{1,1},{2,1},{2,2}}, {{1,1},{2,1},{0,2},{1,2}}, {{0,0},{0,1},{1,1},{1,2}}},
    // 6: Z 型
    {{{0,0},{1,0},{1,1},{2,1}}, {{2,0},{2,1},{1,1},{1,2}}, {{0,1},{1,1},{1,2},{2,2}}, {{1,0},{1,1},{0,1},{0,2}}}
};

GameEngine::GameEngine()
    : snake_len_(3),
      snake_dx_(1),
      snake_dy_(0),
      food_x_(0),
      food_y_(0),
      snake_score_(0),
      snake_speed_ms_(450),
      last_snake_tick_(0),
      snake_game_over_(false),
      piece_type_(0),
      piece_rot_(0),
      piece_x_(0),
      piece_y_(0),
      tetris_score_(0),
      tetris_speed_ms_(800),
      last_tetris_tick_(0),
      tetris_game_over_(false)
{
    memset(snake_x_, 0, sizeof(snake_x_));
    memset(snake_y_, 0, sizeof(snake_y_));
    memset(tetris_field_, 0, sizeof(tetris_field_));
}

void GameEngine::DrawScore(int score)
{
    DisplayHAL& hal = DisplayHAL::GetInstance();
    hal.Clear();
    hal.DrawDigit(score / 10, 4, 5, ColorRGB::White());
    hal.DrawDigit(score % 10, 9, 5, ColorRGB::White());
    hal.Show();
}

// ------------------- 贪吃蛇 -------------------

void GameEngine::InitSnake()
{
    snake_len_ = 3;
    snake_score_ = 0;
    snake_dx_ = 1;
    snake_dy_ = 0;
    snake_speed_ms_ = 450;
    snake_game_over_ = false;

    for (int i = 0; i < 3; i++) {
        snake_x_[i] = 5 - i;
        snake_y_[i] = 7;
    }
    food_x_ = random8(16);
    food_y_ = random8(16);
    last_snake_tick_ = get_millis();
}

void GameEngine::SnakeSetDirection(int dx, int dy)
{
    // 防止直接掉头自杀
    if (snake_len_ > 1 && (snake_x_[0] + dx == snake_x_[1]) && (snake_y_[0] + dy == snake_y_[1])) {
        return;
    }
    snake_dx_ = dx;
    snake_dy_ = dy;
}

uint32_t GameEngine::RunSnake()
{
    DisplayHAL& hal = DisplayHAL::GetInstance();
    if (snake_game_over_) {
        DrawScore(snake_score_);
        return 100;
    }

    uint32_t now = get_millis();
    if (now - last_snake_tick_ >= (uint32_t)snake_speed_ms_) {
        last_snake_tick_ = now;

        // 移动蛇身
        for (int i = snake_len_ - 1; i > 0; i--) {
            snake_x_[i] = snake_x_[i - 1];
            snake_y_[i] = snake_y_[i - 1];
        }

        // 环形穿墙移动
        snake_x_[0] = (snake_x_[0] + snake_dx_ + 16) % 16;
        snake_y_[0] = (snake_y_[0] + snake_dy_ + 16) % 16;

        // 碰撞自噬检测
        for (int i = 1; i < snake_len_; i++) {
            if (snake_x_[0] == snake_x_[i] && snake_y_[0] == snake_y_[i]) {
                snake_game_over_ = true;
                return 50;
            }
        }

        // 吃到食物检测
        if (snake_x_[0] == food_x_ && snake_y_[0] == food_y_) {
            snake_score_++;
            if (snake_len_ < TOTAL_LEDS) {
                snake_len_++;
            }
            snake_speed_ms_ = (snake_speed_ms_ > 80) ? (450 - (snake_score_ * 15)) : 80;
            food_x_ = random8(16);
            food_y_ = random8(16);
        }
    }

    // 渲染画面
    hal.Clear();
    // 绘制食物 (红色)
    hal.SetPixel(food_x_, food_y_, ColorRGB::Red());
    // 绘制蛇身 (头部亮绿，身体深绿)
    for (int i = 0; i < snake_len_; i++) {
        hal.SetPixel(snake_x_[i], snake_y_[i], (i == 0) ? ColorRGB::Lime() : ColorRGB::Green());
    }
    hal.Show();
    return 33;
}

// ------------------- 俄罗斯方块 -------------------

bool GameEngine::CheckTetrisCollision(int type, int rot, int x, int y)
{
    for (int i = 0; i < 4; i++) {
        int px = x + tetris_shapes[type][rot][i][0];
        int py = y + tetris_shapes[type][rot][i][1];
        if (px < BOARD_LEFT || px > BOARD_RIGHT || py >= 16 || (py >= 0 && tetris_field_[py][px])) {
            return true;
        }
    }
    return false;
}

void GameEngine::SpawnTetrisPiece()
{
    piece_type_ = random8(7);
    piece_rot_ = 0;
    piece_x_ = BOARD_LEFT + 3;
    piece_y_ = 0;

    if (CheckTetrisCollision(piece_type_, piece_rot_, piece_x_, piece_y_)) {
        tetris_game_over_ = true;
    }
}

ColorRGB GameEngine::GetTetrisColor(int type)
{
    static const ColorRGB colors[] = {
        ColorRGB::Cyan(), ColorRGB::Blue(), ColorRGB::Orange(),
        ColorRGB::Yellow(), ColorRGB::Green(), ColorRGB::Purple(), ColorRGB::Red()
    };
    return colors[type % 7];
}

void GameEngine::InitTetris()
{
    memset(tetris_field_, 0, sizeof(tetris_field_));
    tetris_score_ = 0;
    tetris_speed_ms_ = 800;
    tetris_game_over_ = false;
    last_tetris_tick_ = get_millis();
    SpawnTetrisPiece();
}

void GameEngine::TetrisMove(int dx)
{
    if (!tetris_game_over_ && !CheckTetrisCollision(piece_type_, piece_rot_, piece_x_ + dx, piece_y_)) {
        piece_x_ += dx;
    }
}

void GameEngine::TetrisRotate()
{
    int next_rot = (piece_rot_ + 1) % 4;
    if (!tetris_game_over_ && !CheckTetrisCollision(piece_type_, next_rot, piece_x_, piece_y_)) {
        piece_rot_ = next_rot;
    }
}

void GameEngine::TetrisDrop()
{
    if (!tetris_game_over_ && !CheckTetrisCollision(piece_type_, piece_rot_, piece_x_, piece_y_ + 1)) {
        piece_y_++;
    }
}

uint32_t GameEngine::RunTetris()
{
    DisplayHAL& hal = DisplayHAL::GetInstance();
    if (tetris_game_over_) {
        DrawScore(tetris_score_);
        return 100;
    }

    uint32_t now = get_millis();
    if (now - last_tetris_tick_ >= (uint32_t)tetris_speed_ms_) {
        last_tetris_tick_ = now;

        if (!CheckTetrisCollision(piece_type_, piece_rot_, piece_x_, piece_y_ + 1)) {
            piece_y_++;
        } else {
            // 落地固化
            for (int i = 0; i < 4; i++) {
                int px = piece_x_ + tetris_shapes[piece_type_][piece_rot_][i][0];
                int py = piece_y_ + tetris_shapes[piece_type_][piece_rot_][i][1];
                if (py >= 0 && py < 16 && px >= 0 && px < 16) {
                    tetris_field_[py][px] = piece_type_ + 1;
                }
            }

            // 消除满行
            for (int y = 15; y >= 0; y--) {
                bool full = true;
                for (int x = BOARD_LEFT; x <= BOARD_RIGHT; x++) {
                    if (!tetris_field_[y][x]) full = false;
                }
                if (full) {
                    tetris_score_++;
                    tetris_speed_ms_ = (tetris_speed_ms_ > 100) ? (tetris_speed_ms_ - 30) : 100;
                    for (int ty = y; ty > 0; ty--) {
                        for (int tx = BOARD_LEFT; tx <= BOARD_RIGHT; tx++) {
                            tetris_field_[ty][tx] = tetris_field_[ty - 1][tx];
                        }
                    }
                    for (int tx = BOARD_LEFT; tx <= BOARD_RIGHT; tx++) {
                        tetris_field_[0][tx] = 0;
                    }
                    y++; // 重新检查当前行
                }
            }
            SpawnTetrisPiece();
        }
    }

    // 渲染游戏画面
    hal.Clear();
    // 左右边界线 (灰色)
    for (int y = 0; y < 16; y++) {
        hal.SetPixel(BOARD_LEFT - 1, y, ColorRGB::Gray());
        hal.SetPixel(BOARD_RIGHT + 1, y, ColorRGB::Gray());
    }

    // 绘制场地已落下方块
    for (int y = 0; y < 16; y++) {
        for (int x = BOARD_LEFT; x <= BOARD_RIGHT; x++) {
            if (tetris_field_[y][x]) {
                hal.SetPixel(x, y, GetTetrisColor(tetris_field_[y][x] - 1));
            }
        }
    }

    // 绘制正在下落的方块
    for (int i = 0; i < 4; i++) {
        int px = piece_x_ + tetris_shapes[piece_type_][piece_rot_][i][0];
        int py = piece_y_ + tetris_shapes[piece_type_][piece_rot_][i][1];
        if (py >= 0 && py < 16 && px >= 0 && px < 16) {
            hal.SetPixel(px, py, GetTetrisColor(piece_type_));
        }
    }

    hal.Show();
    return 33;
}
