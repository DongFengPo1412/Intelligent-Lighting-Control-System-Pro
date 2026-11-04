// game_053_tower_of_hanoi.h —— 目标 #053 汉诺塔 (Tower of Hanoi 1983)
// 机制: 三柱递归盘片搬运 + 小盘压大盘尺寸约束校验 + 4盘进阶5盘双关挑战
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

class Game053TowerOfHanoi : public Cartridge {
public:
    static const int kNumPegs = 3;
    static const int kMaxDisks = 5;
    static const int kNumStages = 2;

    Game053TowerOfHanoi();
    ~Game053TowerOfHanoi() override = default;

    uint8_t GetId() const override { return 53; }
    const char* GetName() const override { return "汉诺塔"; }
    const char* GetEnglishName() const override { return "Tower of Hanoi"; }
    uint16_t GetReleaseYear() const override { return 1983; }
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
    void LoadStage(int stage_idx);
    void DrawDisk(uint8_t* fb, int cx, int y, int disk_size, bool highlight_err) const;
    void AddScore(uint32_t pts);

    CartridgeState state_;
    int stage_;
    int num_disks_;
    int cursor_peg_;
    int held_disk_;
    int held_from_peg_;
    uint32_t moves_;
    uint32_t score_;
    uint32_t high_score_;
    float error_timer_;
    float state_timer_;
    float anim_timer_;

    int pegs_[kNumPegs][kMaxDisks];
    int peg_count_[kNumPegs];
};

} // namespace arcade
