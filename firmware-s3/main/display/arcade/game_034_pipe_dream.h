#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game034PipeDream : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_PLAYING = 1;
    static constexpr uint8_t STATE_DEAD = 2;
    static constexpr uint8_t STATE_VICTORY = 3;

    static constexpr int GRID_W = 8;
    static constexpr int GRID_H = 8;
    static constexpr int QUEUE_SIZE = 4;

    enum PipeType : uint8_t {
        PIPE_EMPTY = 0,
        PIPE_HORIZ = 1,      // 左右贯通
        PIPE_VERT = 2,       // 上下贯通
        PIPE_CORNER_UR = 3,  // 上 <-> 右
        PIPE_CORNER_RD = 4,  // 右 <-> 下
        PIPE_CORNER_DL = 5,  // 下 <-> 左
        PIPE_CORNER_LU = 6,  // 左 <-> 上
        PIPE_CROSS = 7,      // 十字双向跨越
        PIPE_START = 8,      // 进水龙头
        PIPE_END = 9,        // 出水排水槽
    };

    struct Cell {
        PipeType pipe;
        bool filled;
        bool cross_h_filled;
        bool cross_v_filled;
    };

    Game034PipeDream();
    ~Game034PipeDream() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "Pipe Dream (1989)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    int GetPipesFilled() const { return pipes_filled_; }
    float GetFlowCountdown() const { return flow_start_countdown_; }

    int GetCursorX() const { return cursor_x_; }
    int GetCursorY() const { return cursor_y_; }
    int GetCurrentFlowX() const { return flow_x_; }
    int GetCurrentFlowY() const { return flow_y_; }
    PipeType GetNextPipe() const { return pipe_queue_[0]; }

    void SetCursor(int x, int y) { cursor_x_ = x; cursor_y_ = y; }
    bool PlacePipe();
    void FastForwardFlow();

private:
    void InitBoard();
    void PushQueue();
    PipeType GenerateRandomPipe();
    bool CanConnect(PipeType pipe, int enter_dir, int& exit_dir) const;
    void AdvanceFlow();

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;
    int pipes_filled_;
    int required_pipes_;

    int cursor_x_;
    int cursor_y_;

    float flow_start_countdown_;
    float flow_step_timer_;
    float flow_step_interval_;

    int flow_x_;
    int flow_y_;
    int flow_dir_; // 0: Up, 1: Right, 2: Down, 3: Left
    bool flow_started_;

    Cell grid_[GRID_H][GRID_W];
    PipeType pipe_queue_[QUEUE_SIZE];
};

} // namespace arcade
