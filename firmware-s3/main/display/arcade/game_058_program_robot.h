#pragma once
#include "arcade_batch_cartridge.h"
namespace arcade {
class Game058ProgramRobot : public BatchCartridge {
  public:
    uint8_t GetId() const override { return 58; }
    const char *GetName() const override { return "编程机器人"; }
    const char *GetEnglishName() const override { return "Program Robot"; }
    CartridgeStatus GetStatus() const override {
        auto status = BatchCartridge::GetStatus();
        status.lives = attempts_;
        return status;
    }

  private:
    friend struct B2MechanismProbe; // deterministic host collision fixtures
    int program_[20]{}, length_ = 0, x_ = 1, y_ = 6, heading_ = 0, attempts_ = 3, pc_ = 0;
    bool running_ = false, door_ = false;
    float clock_ = 0;
    void ResetRobot();
    bool Wall(int, int) const;
    void FailProgram();
    void Setup() override;
    void Tick(float, uint16_t, uint16_t) override;
    void Draw(uint8_t *) override;
    int Progress() const override { return state_ == STATE_VICTORY ? 100 : door_ ? 50 : 0; }
};
} // namespace arcade
