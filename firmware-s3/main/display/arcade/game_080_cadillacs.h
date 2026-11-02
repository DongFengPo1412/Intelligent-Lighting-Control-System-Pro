#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>
#include <vector>

namespace arcade {

class Game080Cadillacs : public Cartridge {
public:
    Game080Cadillacs();
    ~Game080Cadillacs() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 80; }
    std::string GetName() const override { return "Cadillacs and Dinosaurs (1993)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_PLAYING = 0,
        STATE_CADILLAC_DRIVE = 1,
        STATE_PLAYER_DEAD = 2,
        STATE_VICTORY = 3
    };

    enum WeaponType {
        WEAPON_FIST = 0,
        WEAPON_UZI = 1,       // Rapid fire
        WEAPON_SHOTGUN = 2,   // Spread pellet blast
        WEAPON_BAZOOKA = 3    // Heavy explosive missile
    };

    struct Dinosaur {
        float x{12.0f};
        float y{10.0f};
        float vx{-1.5f};
        bool enraged{false};
        float calm_timer{0.0f};
        int hp{4};
        bool active{true};
    };

    struct Enemy {
        float x{15.0f};
        float y{9.0f};
        float vx{-2.0f};
        int hp{2};
        bool active{true};
        float respawn_timer{0.0f};
    };

    struct WeaponDrop {
        float x{0.0f};
        float y{0.0f};
        WeaponType type{WEAPON_UZI};
        int ammo{15};
        bool active{false};
    };

    struct Bullet {
        float x{0.0f};
        float y{0.0f};
        float vx{18.0f};
        bool is_bazooka{false};
        bool active{false};
    };

    GameState GetState() const { return state_; }
    int GetScore() const { return score_; }
    int GetLives() const { return lives_; }
    int GetPlayerHp() const { return player_hp_; }
    WeaponType GetCurrentWeapon() const { return current_weapon_; }
    int GetAmmo() const { return weapon_ammo_; }
    float GetPlayerX() const { return px_; }
    float GetPlayerY() const { return py_; }
    bool IsDinoEnraged() const { return dino_.enraged; }

private:
    void ResetStage();
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateEnemies(float dt);
    void UpdateDino(float dt);
    void UpdateBullets(float dt);
    void FireWeapon();
    void TriggerCadillacRaid();
    void CheckCollisions();

    GameState state_{STATE_PLAYING};
    float state_timer_{0.0f};
    int score_{0};
    int high_score_{15000};
    int lives_{3};
    int player_hp_{100};
    int enemies_defeated_{0};

    // Mustapha Cairo / Jack Tenrec coordinates
    float px_{3.0f};
    float py_{10.0f};
    int facing_{1};
    bool in_air_{false};
    float pvy_{0.0f};
    float atk_timer_{0.0f};

    // Weapon
    WeaponType current_weapon_{WEAPON_FIST};
    int weapon_ammo_{0};

    // Entities
    Dinosaur dino_;

    static constexpr int MAX_ENEMIES = 3;
    Enemy enemies_[MAX_ENEMIES];

    static constexpr int MAX_BULLETS = 6;
    Bullet bullets_[MAX_BULLETS];

    static constexpr int MAX_DROPS = 2;
    WeaponDrop drops_[MAX_DROPS];

    // Cadillac vehicle raid
    float caddy_x_{-6.0f};
    float caddy_speed_{20.0f};
};

} // namespace arcade
