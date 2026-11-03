#pragma once

#include <cstdint>

namespace arcade {

// Game #186: 冠军棒球 (Champion Baseball - 1983 / Sega & Alpha Denshi)
// 投球手九宫格变化球速控投球、击球员分寸时机挥棒推打安打、全垒跑垒盗垒触杀与三振出局。

class Game186ChampionBaseball {
public:
    static constexpr uint8_t GAME_ID = 186;
    static constexpr const char* NAME = "冠军棒球";
    static constexpr const char* ENGLISH_NAME = "Champion Baseball";
    static constexpr uint16_t RELEASE_YEAR = 1983;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PITCHING = 0;
    static constexpr uint8_t STATE_BALL_IN_PLAY = 1;
    static constexpr uint8_t STATE_INNING_END = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    Game186ChampionBaseball();
    ~Game186ChampionBaseball() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetInning() const { return inning_; }
    uint8_t GetOuts() const { return outs_; }
    uint8_t GetStrikes() const { return strikes_; }
    uint8_t GetBalls() const { return balls_; }

    float GetBatterX() const { return batter_x_; }
    float GetBallX() const { return ball_x_; }
    float GetBallY() const { return ball_y_; }
    bool IsBallActive() const { return ball_active_; }
    bool IsBaseOccupied(int base_idx) const {
        return (base_idx >= 0 && base_idx < 3) ? bases_[base_idx] : false;
    }

private:
    void InitAtBat();
    void PitchBall();
    void AdvanceRunners(int bases_hit);

    uint8_t state_;
    uint32_t score_;
    uint8_t inning_;
    uint8_t outs_;
    uint8_t strikes_;
    uint8_t balls_;
    float state_timer_;

    // Batter
    float batter_x_;
    float batter_y_;
    bool is_swinging_;
    float swing_timer_;

    // Pitcher & Ball
    float pitcher_x_;
    float pitcher_y_;
    float ball_x_;
    float ball_y_;
    float ball_vx_;
    float ball_vy_;
    bool ball_active_;
    float ball_air_timer_;
    bool is_hit_;

    // Bases: 1st, 2nd, 3rd
    bool bases_[3];
    float pitch_cooldown_;
};

} // namespace arcade

