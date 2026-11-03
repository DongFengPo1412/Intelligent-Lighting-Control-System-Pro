#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game122Bosconian : public Cartridge {
public:
    Game122Bosconian();
    ~Game122Bosconian() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 122; }
    std::string GetName() const override { return "Bosconian (1981)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_FLYING = 0,
        STATE_PLAYER_EXPLODING = 1,
        STATE_SECTOR_CLEAR = 2,
        STATE_GAME_OVER = 3
    };

    enum AlertCondition {
        ALERT_GREEN = 0,
        ALERT_YELLOW = 1,
        ALERT_RED = 2
    };

    struct SpaceStation {
        float x{0.0f}; // World X [0..48)
        float y{0.0f}; // World Y [0..48)
        bool core_alive{true};
        bool pods_alive[6]{true, true, true, true, true, true};
        bool active{true};
    };

    struct Bullet {
        float x{0.0f};
        float y{0.0f};
        float vx{0.0f};
        float vy{0.0f};
        float life{0.0f};
        bool active{false};
    };

    struct Interceptor {
        float x{0.0f};
        float y{0.0f};
        float vx{0.0f};
        float vy{0.0f};
        bool is_spy{false};
        bool active{false};
    };

    static constexpr int WORLD_SIZE = 48;
    static constexpr int MAX_STATIONS = 3;
    static constexpr int MAX_BULLETS = 6;
    static constexpr int MAX_INTERCEPTORS = 4;

    GameState GetState() const { return state_; }
    AlertCondition GetAlert() const { return alert_; }
    int GetScore() const { return score_; }
    int GetLives() const { return lives_; }
    float GetPlayerX() const { return px_; }
    float GetPlayerY() const { return py_; }
    int GetFacingDirX() const { return dir_x_; }
    int GetFacingDirY() const { return dir_y_; }

    const SpaceStation& GetStation(int i) const { return stations_[i]; }
    const Interceptor& GetInterceptor(int i) const { return interceptors_[i]; }

    void FireTwinCannons();

private:
    GameState state_{STATE_FLYING};
    AlertCondition alert_{ALERT_GREEN};
    float state_timer_{0.0f};
    int score_{0};
    int lives_{3};
    int round_{1};

    // Starfighter
    float px_{24.0f};
    float py_{24.0f};
    float vx_{0.0f};
    float vy_{0.0f};
    int dir_x_{0};
    int dir_y_{-1}; // Facing UP initially

    SpaceStation stations_[MAX_STATIONS];
    Bullet bullets_[MAX_BULLETS];
    Interceptor interceptors_[MAX_INTERCEPTORS];
    float spawn_timer_{0.0f};

    void InitSector();
    void UpdateShip(float dt, uint32_t buttons);
    void UpdateStations(float dt);
    void UpdateInterceptors(float dt);
    void UpdateBullets(float dt);
    void CheckCollisions();
    void CheckSectorClear();
};

} // namespace arcade