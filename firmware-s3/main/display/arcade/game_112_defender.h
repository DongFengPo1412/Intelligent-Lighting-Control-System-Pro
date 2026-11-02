#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game112Defender : public Cartridge {
public:
    Game112Defender();
    ~Game112Defender() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 112; }
    std::string GetName() const override { return "Defender (1981)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_PLAYING = 0,
        STATE_PLAYER_DYING = 1,
        STATE_WAVE_CLEAR = 2,
        STATE_GAME_OVER = 3
    };

    struct Humanoid {
        float x{0.0f}; // World X [0..48)
        float y{14.0f};
        bool alive{true};
        bool being_abducted{false};
        bool is_falling{false};
        bool being_carried{false};
    };

    struct Alien {
        float x{0.0f}; // World X [0..48)
        float y{2.0f};
        float vx{0.0f};
        float vy{0.0f};
        bool active{false};
        bool is_mutant{false};
        int abducted_human_idx{-1};
    };

    struct Laser {
        float x{0.0f}; // World X [0..48)
        float y{0.0f};
        float vx{0.0f};
        bool active{false};
    };

    static constexpr int WORLD_WIDTH = 48;
    static constexpr int MAX_HUMANS = 4;
    static constexpr int MAX_ALIENS = 6;
    static constexpr int MAX_LASERS = 4;

    GameState GetState() const { return state_; }
    int GetScore() const { return score_; }
    int GetLives() const { return lives_; }
    int GetSmartBombs() const { return smart_bombs_; }
    int GetWave() const { return wave_; }
    float GetPlayerX() const { return px_; }
    float GetPlayerY() const { return py_; }
    int GetFacingDir() const { return facing_dir_; }

    const Humanoid& GetHumanoid(int i) const { return humans_[i]; }
    const Alien& GetAlien(int i) const { return aliens_[i]; }

    void TriggerSmartBomb();

private:
    GameState state_{STATE_PLAYING};
    float state_timer_{0.0f};
    int score_{0};
    int lives_{3};
    int smart_bombs_{2};
    int wave_{1};

    // Defender Ship
    float px_{8.0f}; // World X [0..48)
    float py_{8.0f}; // Y [1..14]
    float vx_{0.0f};
    float vy_{0.0f};
    int facing_dir_{1}; // 1 = Right, -1 = Left
    int carried_human_idx_{-1};

    Humanoid humans_[MAX_HUMANS];
    Alien aliens_[MAX_ALIENS];
    Laser lasers_[MAX_LASERS];

    void InitWave();
    void FireLaser();
    void UpdatePlayer(float dt, uint32_t buttons);
    void UpdateAliens(float dt);
    void UpdateLasers(float dt);
    void UpdateHumans(float dt);
    void CheckCollisions();
    void CheckWaveClear();
};

} // namespace arcade