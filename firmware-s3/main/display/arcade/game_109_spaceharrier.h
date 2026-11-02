#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game109SpaceHarrier : public Cartridge {
public:
    Game109SpaceHarrier();
    ~Game109SpaceHarrier() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 109; }
    std::string GetName() const override { return "Space Harrier (1985)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_FLYING = 0,
        STATE_BOSS_DRAGON = 1,
        STATE_HERO_HIT = 2,
        STATE_STAGE_CLEAR = 3,
        STATE_GAME_OVER = 4
    };

    struct Shot {
        float x{0.0f};
        float y{0.0f};
        float z{0.0f}; // 0 = at hero, 10 = deep horizon
        bool active{false};
    };

    struct ScaledEntity {
        float x{0.0f};
        float y{0.0f};
        float z{10.0f}; // 10 = deep horizon, 0 = at screen camera
        int type{0};    // 0 = Flying Drone, 1 = Tree Pillar, 2 = Stone Head
        int hp{1};
        bool active{false};
    };

    static constexpr int MAX_SHOTS = 4;
    static constexpr int MAX_ENTITIES = 4;

    GameState GetState() const { return state_; }
    int GetScore() const { return score_; }
    int GetLives() const { return lives_; }
    int GetStage() const { return stage_; }
    float GetHeroX() const { return hero_x_; }
    float GetHeroY() const { return hero_y_; }
    int GetDragonHP() const { return dragon_hp_; }

    const ScaledEntity& GetEntity(int i) const { return entities_[i]; }

    void SpawnDragonBoss();

private:
    GameState state_{STATE_FLYING};
    float state_timer_{0.0f};
    int score_{0};
    int lives_{3};
    int stage_{1};
    float horizon_scroll_{0.0f};
    int enemies_defeated_{0};

    // Harrier Hero
    float hero_x_{8.0f};
    float hero_y_{11.0f};
    float shot_cooldown_{0.0f};
    float roll_timer_{0.0f};

    // Chinese Dragon Boss (Uriah)
    float dragon_x_{8.0f};
    float dragon_y_{6.0f};
    float dragon_z_{5.0f};
    int dragon_hp_{8};
    float dragon_angle_{0.0f};

    Shot shots_[MAX_SHOTS];
    ScaledEntity entities_[MAX_ENTITIES];

    void InitStage();
    void UpdateHero(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateShots(float dt);
    void UpdateEntities(float dt);
    void UpdateDragonBoss(float dt);
    void CheckCollisions();
};

} // namespace arcade
