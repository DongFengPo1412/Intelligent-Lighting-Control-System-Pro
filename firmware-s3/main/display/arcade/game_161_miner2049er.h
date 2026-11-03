#pragma once

#include <cstdint>

namespace arcade {

// Game #161: 矿工2049 (Miner 2049er 1982 / Big Five Software & Bill Hogue)
// 街机与早期动作平台最负盛名的矿区框架踏步染色开山名作：
// 操控赏金猎人鲍勃踩踏矿区各层钢梁将其逐一染色圈地、攀爬梯子穿梭多层平台、
// 单向放射性滑道极速俯冲、避让巡逻变异生物并达成100%全域染色通关。

class Game161Miner2049er {
public:
    static constexpr uint8_t GAME_ID = 161;
    static constexpr const char* NAME = "矿工2049";
    static constexpr const char* ENGLISH_NAME = "Miner 2049er";
    static constexpr uint16_t RELEASE_YEAR = 1982;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_BOB_DIED = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int MAX_MUTANTS = 2;

    struct Mutant {
        float x;
        float y;
        float vx;
        float min_x;
        float max_x;
    };

    Game161Miner2049er();
    ~Game161Miner2049er() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetLevel() const { return level_; }
    float GetCoveragePct() const;

private:
    uint8_t state_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t level_;
    float state_timer_;

    float px_;
    float py_;
    float vx_;
    float vy_;
    bool on_ground_;
    bool on_ladder_;
    bool sliding_;

    // Tile claims: 16x16 bitmask (256 bits = 32 bytes)
    uint8_t colored_tiles_[32];
    uint8_t total_claimable_;
    uint8_t claimed_count_;

    Mutant mutants_[MAX_MUTANTS];

    void InitLevel();
    bool IsPlatform(int x, int y) const;
    bool IsLadder(int x, int y) const;
    bool IsSlide(int x, int y) const;
    void ClaimTile(int x, int y);
    bool IsTileClaimed(int x, int y) const;
};

} // namespace arcade
