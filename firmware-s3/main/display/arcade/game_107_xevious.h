#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game107Xevious : public Cartridge {
public:
    Game107Xevious();
    ~Game107Xevious() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 107; }
    std::string GetName() const override { return "Xevious (1982)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_FLYING = 0,
        STATE_BOSS_ANDOR = 1,
        STATE_SHIP_EXPLODED = 2,
        STATE_AREA_CLEAR = 3,
        STATE_GAME_OVER = 4
    };

    struct AirBullet {
        float x{0.0f};
        float y{0.0f};
        float vy{-18.0f};
        bool is_enemy{false};
        bool active{false};
    };

    struct GroundBomb {
        float x{0.0f};
        float y{0.0f};
        float target_x{0.0f};
        float target_y{0.0f};
        float timer{0.0f};
        bool active{false};
    };

    struct AirEnemy {
        float x{0.0f};
        float y{0.0f};
        float vx{0.0f};
        float vy{3.5f};
        int type{0}; // 0 = Toroid, 1 = Zakato
        bool active{false};
    };

    struct GroundTarget {
        float x{0.0f};
        float y{0.0f};
        int type{0}; // 0 = Barra pyramid, 1 = Zolbak radar, 2 = Sol citadel
        int hp{1};
        bool active{false};
    };

    static constexpr int MAX_PLAYER_BULLETS = 3;
    static constexpr int MAX_ENEMY_BULLETS = 3;
    static constexpr int MAX_GROUND_BOMBS = 2;
    static constexpr int MAX_AIR_ENEMIES = 3;
    static constexpr int MAX_GROUND_TARGETS = 4;

    GameState GetState() const { return state_; }
    int GetScore() const { return score_; }
    int GetLives() const { return lives_; }
    int GetArea() const { return area_; }
    float GetPlayerX() const { return px_; }
    float GetPlayerY() const { return py_; }
    float GetCrosshairX() const { return px_; }
    float GetCrosshairY() const { return py_ - 3.5f; }
    int GetAndorHP() const { return andor_hp_; }

    const AirEnemy& GetAirEnemy(int i) const { return air_enemies_[i]; }
    const GroundTarget& GetGroundTarget(int i) const { return ground_targets_[i]; }

    void SpawnAndorGenesis();

private:
    GameState state_{STATE_FLYING};
    float state_timer_{0.0f};
    int score_{0};
    int lives_{3};
    int area_{1};
    float scroll_y_{0.0f};
    int enemies_downed_{0};

    // Solvalou Ship
    float px_{8.0f};
    float py_{13.0f};
    float zapper_cooldown_{0.0f};
    float blaster_cooldown_{0.0f};

    // Andor Genesis Floating Mothership
    float andor_x_{5.0f};
    float andor_y_{-4.0f};
    float andor_vx_{1.5f};
    int andor_hp_{6};

    AirBullet player_bullets_[MAX_PLAYER_BULLETS];
    AirBullet enemy_bullets_[MAX_ENEMY_BULLETS];
    GroundBomb ground_bombs_[MAX_GROUND_BOMBS];
    AirEnemy air_enemies_[MAX_AIR_ENEMIES];
    GroundTarget ground_targets_[MAX_GROUND_TARGETS];

    void InitArea();
    void UpdateShip(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateAirEntities(float dt);
    void UpdateGroundEntities(float dt);
    void UpdateAndorGenesis(float dt);
    void CheckAirCollisions();
    void CheckGroundBombCollisions();
};

} // namespace arcade
