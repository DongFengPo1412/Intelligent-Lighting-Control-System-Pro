#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game068MetalGear : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_PLAYING = 1;
    static constexpr uint8_t STATE_DEAD = 2;
    static constexpr uint8_t STATE_VICTORY = 3;

    // Alert Status
    static constexpr uint8_t ALERT_NORMAL = 0;
    static constexpr uint8_t ALERT_CAUTION = 1;
    static constexpr uint8_t ALERT_EVASION = 2;

    static constexpr int MAX_GUARDS = 3;
    static constexpr int MAX_DARTS = 2;
    static constexpr int MAX_CAMERAS = 2;

    struct Guard {
        float x;
        float y;
        int dir;           // 0: Up, 1: Right, 2: Down, 3: Left
        float patrol_timer;
        bool alert;
        bool active;
    };

    struct Dart {
        float x;
        float y;
        float vx;
        float vy;
        bool active;
    };

    struct Camera {
        float x;
        float y;
        int dir;           // Sweeping angle direction
        float sweep_timer;
        bool active;
    };

    Game068MetalGear();
    ~Game068MetalGear() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "Metal Gear (1987)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    int GetLives() const { return lives_; }
    float GetPlayerX() const { return px_; }
    float GetPlayerY() const { return py_; }
    int GetPlayerDir() const { return player_dir_; }
    bool InCardboardBox() const { return in_box_; }
    uint8_t GetAlertLevel() const { return alert_level_; }
    bool HasKeycard() const { return has_keycard_; }
    int GetGuardsNeutralized() const { return guards_neutralized_; }

    void FireSilencedDart();
    void ToggleCardboardBox();

private:
    void InitStage();
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateGuards(float dt);
    void UpdateDarts(float dt);
    void CheckLineOfSight();
    void CheckCollisions();

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;
    int lives_;

    // Solid Snake state
    float px_;
    float py_;
    int player_dir_;        // 0: Up, 1: Right, 2: Down, 3: Left
    bool in_box_;
    bool is_moving_;
    float dart_cooldown_;
    bool has_keycard_;

    // Alert system
    uint8_t alert_level_;
    float alert_timer_;
    int guards_neutralized_;

    // Compound layout
    Guard guards_[MAX_GUARDS];
    Dart darts_[MAX_DARTS];
    Camera cameras_[MAX_CAMERAS];
};

} // namespace arcade
