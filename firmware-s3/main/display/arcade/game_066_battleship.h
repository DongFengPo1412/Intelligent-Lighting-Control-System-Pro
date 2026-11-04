// game_066_battleship.h —— 目标 #066 海战棋 (Battleship, 1979)
// 机制: 双 8x8 海战雷达/己方舰队切换 + 四舰隐蔽部署 + 命中连射与击沉闪光 + 猎杀锁定 AI
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

class Game066Battleship : public arcade::Cartridge {
public:
    Game066Battleship();
    ~Game066Battleship() override = default;

    uint8_t GetId() const override { return 66; }
    const char* GetName() const override { return "海战棋"; }
    const char* GetEnglishName() const override { return "Battleship"; }
    uint16_t GetReleaseYear() const override { return 1979; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    void Init() override;
    void Reset() override;
    void Start() override;
    void Pause() override;
    void Resume() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

private:
    static const int kGridSize = 8;
    static const int kNumShips = 4;
    static const int kTotalDeckCells = 11; // 4 + 3 + 2 + 2

    struct NavalShip {
        uint8_t x;
        uint8_t y;
        uint8_t len;
        uint8_t horiz;
        uint8_t hits;
    };

    uint32_t NextRand();
    void AddScore(uint32_t pts);
    bool CanPlaceShip(const uint8_t grid[kGridSize][kGridSize], int x, int y, int len, bool horiz) const;
    void PlaceFleet(uint8_t grid[kGridSize][kGridSize], NavalShip ships[kNumShips]);
    void MarkShipSunk(uint8_t shots[kGridSize][kGridSize], const NavalShip& s);
    void InitMatch();
    void MakeAiShot();

    CartridgeState state_;
    uint8_t player_grid_[kGridSize][kGridSize];
    uint8_t ai_grid_[kGridSize][kGridSize];
    uint8_t player_shots_[kGridSize][kGridSize];
    uint8_t ai_shots_[kGridSize][kGridSize];
    NavalShip player_ships_[kNumShips];
    NavalShip ai_ships_[kNumShips];
    int cursor_x_;
    int cursor_y_;
    int player_hits_;
    int ai_hits_;
    int ai_ships_sunk_;
    int player_ships_sunk_;
    bool player_turn_;
    bool hold_peek_;
    float peek_timer_;
    float sink_flash_timer_;
    float ai_timer_;
    uint32_t rng_seed_;
    uint32_t match_count_;
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
    float anim_timer_;
};

} // namespace arcade
