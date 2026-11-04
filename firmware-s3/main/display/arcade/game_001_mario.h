// game_001_mario.h —— 超级马里奥 (Super Mario Bros. 16)
#pragma once

#include "../mario_game.h"
#include "arcade_cartridge.h"

namespace arcade {

class Game001Mario : public Cartridge {
  public:
    Game001Mario();
    ~Game001Mario() override = default;

    uint8_t GetId() const override { return 1; }
    const char *GetName() const override { return "超级马里奥"; }
    const char *GetEnglishName() const override { return "Super Mario Bros."; }
    uint16_t GetReleaseYear() const override { return 1985; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    void Init() override;
    void Reset() override;
    void Start() override;
    void Pause() override;
    void Resume() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t *fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

  private:
    mario16::Game game_;
    uint32_t high_score_ = 0;
    float anim_timer_ = 0.0f;
    bool wrapper_paused_ = false;
};

} // namespace arcade
