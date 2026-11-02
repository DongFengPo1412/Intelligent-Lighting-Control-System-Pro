#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game084WarriorsOfFate : public Cartridge {
public:
    Game084WarriorsOfFate();
    ~Game084WarriorsOfFate() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 84; }
    std::string GetName() const override { return "Warriors of Fate (1992)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_BATTLE = 0,
        STATE_EATING_BONUS = 1,
        STATE_STAGE_CLEAR = 2,
        STATE_HERO_DEAD = 3
    };

    struct EnemySoldier {
        float x{16.0f};
        float y{10.0f};
        float vx{-2.5f};
        int hp{2};
        bool is_boss{false};
        bool active{false};
    };

    GameState GetState() const { return state_; }
    int GetScore() const { return score_; }
    int GetHeroHp() const { return hero_hp_; }
    int GetLives() const { return lives_; }
    bool IsMounted() const { return mounted_; }
    float GetHeroX() const { return hx_; }
    float GetHeroY() const { return hy_; }
    int GetBaoziCount() const { return baozi_eaten_; }

private:
    void ResetBattle();
    void StartBonusStage();
    void UpdateHero(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateEnemies(float dt);
    void UpdateEating(float dt, uint32_t buttons, uint32_t prev_buttons);
    void CheckAttacks();

    GameState state_{STATE_BATTLE};
    float state_timer_{0.0f};
    int score_{0};
    int high_score_{25000};
    int lives_{3};
    int hero_hp_{100};
    int enemies_defeated_{0};

    // Hero Guan Yu / Zhao Yun
    float hx_{3.0f};
    float hy_{10.0f};
    int facing_{1};
    bool mounted_{true}; // On red hare warhorse
    bool charging_{false};
    float charge_timer_{0.0f};
    float atk_timer_{0.0f};

    static constexpr int MAX_ENEMIES = 3;
    EnemySoldier enemies_[MAX_ENEMIES];

    // Eating bonus stage
    int baozi_total_{20};
    int baozi_eaten_{0};
    float eating_timer_{8.0f};
};

} // namespace arcade
