#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game101SpyHunter : public Cartridge {
public:
    Game101SpyHunter();
    ~Game101SpyHunter() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 101; }
    std::string GetName() const override { return "Spy Hunter (1983)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_DRIVING = 0,
        STATE_WEAPONS_VAN_DOCK = 1,
        STATE_AMPHIBIOUS_BOATING = 2,
        STATE_CRASHED = 3,
        STATE_GAME_OVER = 4
    };

    enum WeaponType {
        WEAPON_NONE = 0,
        WEAPON_OIL_SLICK = 1,
        WEAPON_SMOKE_SCREEN = 2,
        WEAPON_MISSILE = 3
    };

    struct EnemyVehicle {
        float x{0.0f};
        float y{0.0f};
        float speed{0.0f};
        int type{0}; // 0 = Enforcer, 1 = Tire Slasher, 2 = Torpedo Boat
        bool spinning{false};
        float spin_timer{0.0f};
        bool active{false};
    };

    struct WeaponVan {
        float x{8.0f};
        float y{-5.0f};
        float speed{12.0f};
        WeaponType carrying_weapon{WEAPON_OIL_SLICK};
        bool active{false};
    };

    struct OilHazard {
        float x{0.0f};
        float y{0.0f};
        bool active{false};
    };

    struct Bullet {
        float x{0.0f};
        float y{0.0f};
        float vy{-24.0f};
        bool active{false};
    };

    static constexpr int MAX_ENEMIES = 3;
    static constexpr int MAX_BULLETS = 4;
    static constexpr int MAX_HAZARDS = 3;

    GameState GetState() const { return state_; }
    int GetScore() const { return score_; }
    int GetLives() const { return lives_; }
    float GetPlayerX() const { return px_; }
    float GetPlayerSpeed() const { return speed_; }
    WeaponType GetCurrentWeapon() const { return current_weapon_; }
    int GetWeaponAmmo() const { return weapon_ammo_; }
    bool IsBoatMode() const { return state_ == STATE_AMPHIBIOUS_BOATING; }

    const EnemyVehicle& GetEnemy(int i) const { return enemies_[i]; }
    const WeaponVan& GetVan() const { return van_; }

private:
    GameState state_{STATE_DRIVING};
    float state_timer_{0.0f};
    int score_{0};
    int lives_{3};
    float distance_traveled_{0.0f};

    // Car/Boat state
    float px_{8.0f};
    float py_{12.0f};
    float speed_{10.0f};
    WeaponType current_weapon_{WEAPON_NONE};
    int weapon_ammo_{0};
    float fire_cooldown_{0.0f};

    // Road / River Track
    float road_left_{3.0f};
    float road_width_{10.0f};

    WeaponVan van_;
    EnemyVehicle enemies_[MAX_ENEMIES];
    Bullet bullets_[MAX_BULLETS];
    OilHazard hazards_[MAX_HAZARDS];

    void ResetRoad();
    void CallWeaponVan();
    void UpdateCar(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateVan(float dt);
    void UpdateEnemies(float dt);
    void UpdateBulletsAndHazards(float dt);
    void CheckCollisions();
};

} // namespace arcade
