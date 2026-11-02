#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game041CrushRoller : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_PLAYING = 1;
    static constexpr uint8_t STATE_DEAD = 2;
    static constexpr uint8_t STATE_VICTORY = 3;

    static constexpr int MAX_ENEMIES = 2;
    static constexpr int MAX_ROLLERS = 2;

    struct Roller {
        float x;
        float y;
        int dir; // 0: Idle, 1: Moving Right, 2: Moving Down, 3: Moving Left, 4: Moving Up
        bool active;
        float cooldown;
    };

    struct Monster {
        float x;
        float y;
        int dir;
        bool active;
        float respawn_timer;
    };

    Game041CrushRoller();
    ~Game041CrushRoller() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "Crush Roller (1981)"; }
    uint8_t GetControlScheme() const override { return CTRL_DPAD_4WAY; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    int GetLives() const { return lives_; }
    int GetUnpaintedTiles() const { return unpainted_tiles_; }
    int GetTotalTiles() const { return total_paint_tiles_; }

    float GetPlayerX() const { return player_x_; }
    float GetPlayerY() const { return player_y_; }

    void SetPlayerPos(float x, float y) { player_x_ = x; player_y_ = y; }
    void PaintTile(int x, int y);
    bool TriggerRoller(int roller_idx);

private:
    void InitMaze();
    void UpdatePlayer(float dt, uint32_t buttons);
    void UpdateRollers(float dt);
    void UpdateMonsters(float dt);
    void CheckCollisions();

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;
    int lives_;
    int unpainted_tiles_;
    int total_paint_tiles_;

    float player_x_;
    float player_y_;
    int player_dir_;
    int next_dir_;

    Roller rollers_[MAX_ROLLERS];
    Monster monsters_[MAX_ENEMIES];

    uint8_t maze_[16][16]; // 0: Wall, 1: Unpainted Road, 2: Painted Road
};

} // namespace arcade
