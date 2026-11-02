#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game089SnowBros2 : public Cartridge {
public:
    Game089SnowBros2();
    ~Game089SnowBros2() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 89; }
    std::string GetName() const override { return "Snow Bros. 2 (1994)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_PLAYING = 0,
        STATE_HERO_HIT = 1,
        STATE_STAGE_CLEAR = 2,
        STATE_GAME_OVER = 3
    };

    enum ElementType {
        ELEM_SNOW = 0,       // Nick (Snow frost)
        ELEM_WATER = 1,      // Roy (Water balloon)
        ELEM_LIGHTNING = 2,  // Ching (Electric plasma)
        ELEM_WIND = 3        // Shin-Shin (Cyclone gust)
    };

    struct Projectile {
        float x{0.0f};
        float y{0.0f};
        float vx{0.0f};
        ElementType elem{ELEM_SNOW};
        bool active{false};
    };

    struct Monster {
        float x{0.0f};
        float y{0.0f};
        float vx{1.5f};
        int inflate_level{0}; // 0 = normal, 1 = puffed, 2 = spherical, 3 = fully charged ball
        ElementType sphere_elem{ELEM_SNOW};
        bool is_kicked{false};
        float kick_vx{0.0f};
        float kick_vy{0.0f};
        bool active{false};
        float respawn_timer{0.0f};
    };

    static constexpr int MAX_PROJECTILES = 4;
    static constexpr int MAX_MONSTERS = 4;

    GameState GetState() const { return state_; }
    int GetScore() const { return score_; }
    int GetLives() const { return lives_; }
    ElementType GetElement() const { return current_element_; }
    float GetPlayerX() const { return px_; }
    float GetPlayerY() const { return py_; }
    int GetMonstersDefeated() const { return monsters_defeated_; }

    const Monster& GetMonster(int i) const { return monsters_[i]; }

private:
    void ResetLevel(bool hard_reset);
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateProjectiles(float dt);
    void UpdateMonsters(float dt);
    void CheckCombat();

    GameState state_{STATE_PLAYING};
    float state_timer_{0.0f};
    int score_{0};
    int lives_{3};
    int stage_{1};
    int monsters_defeated_{0};

    // Hero Elf
    float px_{2.0f};
    float py_{13.0f};
    float vx_{0.0f};
    float vy_{0.0f};
    int facing_{1}; // 1 = right, -1 = left
    bool on_ground_{true};
    ElementType current_element_{ELEM_SNOW};

    Projectile projectiles_[MAX_PROJECTILES];
    Monster monsters_[MAX_MONSTERS];
};

} // namespace arcade
