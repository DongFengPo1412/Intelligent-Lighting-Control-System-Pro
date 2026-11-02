#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game115Tempest : public Cartridge {
public:
    Game115Tempest();
    ~Game115Tempest() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 115; }
    std::string GetName() const override { return "Tempest (1981)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_PLAYING = 0,
        STATE_PLAYER_DYING = 1,
        STATE_TUBE_WARP = 2,
        STATE_GAME_OVER = 3
    };

    struct Enemy {
        int sector{0};      // Sector [0..15]
        float depth{0.0f};  // 0.0 (abyss pit) -> 1.0 (outer rim)
        float speed{0.0f};
        bool on_rim{false};
        float rim_dir{1.0f};
        bool active{false};
    };

    struct Shot {
        int sector{0};
        float depth{1.0f}; // 1.0 (rim) -> 0.0 (pit)
        float speed{0.0f};
        bool active{false};
    };

    static constexpr int NUM_SECTORS = 16;
    static constexpr int MAX_ENEMIES = 6;
    static constexpr int MAX_SHOTS = 4;

    GameState GetState() const { return state_; }
    int GetScore() const { return score_; }
    int GetLives() const { return lives_; }
    int GetSuperZappers() const { return super_zappers_; }
    int GetWave() const { return wave_; }
    int GetPlayerSector() const { return player_sector_; }

    const Enemy& GetEnemy(int i) const { return enemies_[i]; }
    void TriggerSuperZapper();

private:
    GameState state_{STATE_PLAYING};
    float state_timer_{0.0f};
    int score_{0};
    int lives_{3};
    int super_zappers_{1};
    int wave_{1};

    int player_sector_{0}; // [0..15]
    float move_timer_{0.0f};

    Enemy enemies_[MAX_ENEMIES];
    Shot shots_[MAX_SHOTS];
    int enemies_remaining_{0};
    float spawn_timer_{0.0f};

    void InitWave();
    void FireShot();
    void SpawnEnemy();
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateEnemies(float dt);
    void UpdateShots(float dt);
    void CheckCollisions();
    void CheckWaveClear();
};

} // namespace arcade