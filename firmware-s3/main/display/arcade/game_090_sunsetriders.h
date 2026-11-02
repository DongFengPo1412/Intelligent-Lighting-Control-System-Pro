#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game090SunsetRiders : public Cartridge {
public:
    Game090SunsetRiders();
    ~Game090SunsetRiders() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 90; }
    std::string GetName() const override { return "Sunset Riders (1991)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_SALOON_BRAWL = 0,
        STATE_STAMPEDE = 1,
        STATE_HERO_HIT = 2,
        STATE_STAGE_CLEAR = 3,
        STATE_GAME_OVER = 4
    };

    struct Bullet {
        float x{0.0f};
        float y{0.0f};
        float vx{0.0f};
        float vy{0.0f};
        bool is_enemy{false};
        bool active{false};
    };

    struct Bandit {
        float x{0.0f};
        float y{0.0f};
        float shoot_timer{1.2f};
        int hp{1};
        bool active{false};
        float respawn_timer{0.0f};
    };

    struct Bull {
        float x{0.0f};
        float y{13.0f};
        float vx{-4.0f};
        bool active{false};
    };

    static constexpr int MAX_BULLETS = 8;
    static constexpr int MAX_BANDITS = 3;
    static constexpr int MAX_BULLS = 3;

    GameState GetState() const { return state_; }
    int GetScore() const { return score_; }
    int GetLives() const { return lives_; }
    float GetPlayerX() const { return px_; }
    float GetPlayerY() const { return py_; }
    bool IsSliding() const { return is_sliding_; }
    bool HasDualGuns() const { return has_dual_guns_; }
    bool HasRapidFire() const { return has_rapid_fire_; }
    int GetBanditsDefeated() const { return bandits_defeated_; }

    const Bandit& GetBandit(int i) const { return bandits_[i]; }
    const Bull& GetBull(int i) const { return bulls_[i]; }

private:
    void ResetMission(bool hard_reset);
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateBandits(float dt);
    void UpdateBulls(float dt);
    void UpdateBullets(float dt);
    void CheckCombat();

    GameState state_{STATE_SALOON_BRAWL};
    float state_timer_{0.0f};
    int score_{0};
    int lives_{3};
    int stage_{1};
    int bandits_defeated_{0};

    // Cowboy Hero
    float px_{2.5f};
    float py_{13.0f};
    float vy_{0.0f};
    int facing_{1};
    bool on_ground_{true};
    bool is_sliding_{false};
    float slide_timer_{0.0f};
    bool has_dual_guns_{false};
    bool has_rapid_fire_{false};
    float fire_cooldown_{0.0f};

    // Sheriff Badge pickup item
    float badge_x_{8.0f};
    float badge_y_{8.0f};
    bool badge_active_{true};
    int badge_type_{0}; // 0 = Gold (Dual Guns), 1 = Silver (Rapid Fire)

    Bullet bullets_[MAX_BULLETS];
    Bandit bandits_[MAX_BANDITS];
    Bull bulls_[MAX_BULLS];
};

} // namespace arcade
