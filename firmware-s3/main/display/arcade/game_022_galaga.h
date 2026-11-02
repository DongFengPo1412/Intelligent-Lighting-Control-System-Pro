// game_022_galaga.h —— 星际双子战机 1981 (Galaga 1981)
// 编号: #022 | 机制: 弧形翻滚俯冲 + 牵引光束捕获战机 + 击坠蜂后解救 + 双战机合体火力加倍
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

enum AlienType : uint8_t {
    ALIEN_ZAKO = 0,     // 蓝色工蜂
    ALIEN_GOEI = 1,     // 红色蝴蝶
    ALIEN_BOSS = 2,     // 绿色蜂后 (发射牵引光束)
};

struct GalagaAlien {
    bool active;
    AlienType type;
    float home_x;
    float home_y;
    float x;
    float y;
    float vx;
    float vy;
    bool is_diving;
    float dive_timer;
    bool has_captured_fighter; // 携带有俘虏战机
};

struct GalagaBullet {
    bool active;
    float x;
    float y;
    float vy;
    bool is_player;
};

class Game022Galaga : public Cartridge {
public:
    Game022Galaga();
    ~Game022Galaga() override = default;

    uint8_t GetId() const override { return 22; }
    const char* GetName() const override { return "星际双子战机"; }
    const char* GetEnglishName() const override { return "Galaga 1981"; }
    uint16_t GetReleaseYear() const override { return 1981; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    void Init() override;
    void Reset() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

private:
    void InitFormation();
    void FirePlayerBullet();
    void UpdateAliens(float dt);
    void UpdateBullets(float dt);
    void TriggerTractorBeam(int boss_idx);

    CartridgeState state_;

    float player_x_;
    int lives_;
    bool is_dual_;              // 双联装双子合体
    bool is_being_captured_;    // 正在被牵引光束吸取
    float capture_timer_;
    float shoot_cooldown_;

    bool beam_active_;
    float beam_x_;
    float beam_y_;
    int beam_boss_idx_;

    static constexpr int MAX_ALIENS = 12; // 3行 x 4列
    GalagaAlien aliens_[MAX_ALIENS];

    static constexpr int MAX_BULLETS = 8;
    GalagaBullet bullets_[MAX_BULLETS];

    float dive_cycle_timer_;
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
};

} // namespace arcade
