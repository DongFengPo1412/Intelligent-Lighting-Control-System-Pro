#include "game_065_punchout.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game065PunchOut::Game065PunchOut()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(5000),
      player_stamina_(100),
      player_action_(ACT_IDLE),
      action_timer_(0.0f),
      player_downs_(0),
      stars_(0),
      dodge_offset_x_(0.0f),
      duck_offset_y_(0.0f),
      opp_stamina_(100),
      opp_action_(OPP_IDLE),
      opp_timer_(1.2f),
      opp_downs_(0),
      opp_attack_type_(1),
      ref_count_timer_(0.0f),
      count_num_(1) {
}

void Game065PunchOut::Init() {
    Reset();
}

void Game065PunchOut::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    player_downs_ = 0;
    opp_downs_ = 0;
    stars_ = 0;
    InitRound();
}

void Game065PunchOut::InitRound() {
    player_stamina_ = 100;
    player_action_ = ACT_IDLE;
    action_timer_ = 0.0f;
    dodge_offset_x_ = 0.0f;
    duck_offset_y_ = 0.0f;

    opp_stamina_ = 100;
    opp_action_ = OPP_IDLE;
    opp_timer_ = 1.0f;
    opp_attack_type_ = 1;
    ref_count_timer_ = 0.0f;
    count_num_ = 1;
}

void Game065PunchOut::Dodge(int direction) {
    if (player_action_ != ACT_IDLE && player_action_ != ACT_BLOCK) return;

    if (direction == -1) {
        player_action_ = ACT_DODGE_LEFT;
        dodge_offset_x_ = -3.0f;
        action_timer_ = 0.35f;
    } else if (direction == 1) {
        player_action_ = ACT_DODGE_RIGHT;
        dodge_offset_x_ = 3.0f;
        action_timer_ = 0.35f;
    } else if (direction == 0) {
        player_action_ = ACT_DUCK;
        duck_offset_y_ = 2.0f;
        action_timer_ = 0.35f;
    }
}

void Game065PunchOut::Punch(int hand) {
    if (player_action_ != ACT_IDLE) return;

    player_action_ = (hand == 0) ? ACT_PUNCH_LEFT : ACT_PUNCH_RIGHT;
    action_timer_ = 0.22f;

    // Check hit on opponent
    if (opp_action_ == OPP_STUNNED || opp_action_ == OPP_PREP_LEFT_HOOK ||
        opp_action_ == OPP_PREP_RIGHT_HOOK || opp_action_ == OPP_PREP_BULL_CHARGE) {
        
        bool is_star_punch = (stars_ > 0 && hand == 1);
        int damage = is_star_punch ? 40 : 20;
        if (is_star_punch) stars_--;

        opp_stamina_ -= damage;
        score_ += is_star_punch ? 300 : 100;

        // Reward star on perfect counter of charge/hook
        if (opp_action_ != OPP_STUNNED && stars_ < 3) {
            stars_++;
            score_ += 150;
        }

        opp_action_ = OPP_HURT;
        opp_timer_ = 0.28f;

        if (opp_stamina_ <= 0) {
            KnockdownOpponent();
        }
    } else if (opp_action_ == OPP_IDLE) {
        // Blocked by opponent guard
        score_ += 10;
    }
}

void Game065PunchOut::KnockdownPlayer() {
    player_action_ = ACT_DOWN;
    player_stamina_ = 0;
    player_downs_++;
    action_timer_ = 0.0f;
    ref_count_timer_ = 0.0f;
    count_num_ = 1;

    if (player_downs_ >= 3) {
        state_ = STATE_DEAD;
        state_timer_ = 0.0f;
    }
}

void Game065PunchOut::KnockdownOpponent() {
    opp_action_ = OPP_DOWN;
    opp_stamina_ = 0;
    opp_downs_++;
    opp_timer_ = 0.0f;
    ref_count_timer_ = 0.0f;
    count_num_ = 1;
    score_ += 1000;

    if (opp_downs_ >= 3) {
        state_ = STATE_VICTORY;
        state_timer_ = 0.0f;
        score_ += 3000;
        if (score_ > high_score_) high_score_ = score_;
    }
}

void Game065PunchOut::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_DEAD) {
        if (state_timer_ > 3.0f) {
            state_ = STATE_START;
        }
        return;
    }

    if (state_ == STATE_VICTORY) {
        if (state_timer_ > 3.0f) {
            state_ = STATE_PLAYING;
            state_timer_ = 0.0f;
            Reset();
        }
        return;
    }

    UpdatePlayer(dt, buttons, prev_buttons);
    UpdateOpponent(dt);
}

void Game065PunchOut::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (player_action_ == ACT_DOWN) {
        ref_count_timer_ += dt;
        // Tapping A helps player get up
        if ((buttons & BUTTON_A) && !(prev_buttons & BUTTON_A)) {
            player_stamina_ += 15;
            if (player_stamina_ >= 50) {
                player_action_ = ACT_IDLE;
                dodge_offset_x_ = 0.0f;
                duck_offset_y_ = 0.0f;
            }
        }
        if (ref_count_timer_ >= 1.0f) {
            ref_count_timer_ = 0.0f;
            count_num_++;
            if (count_num_ > 10 && player_action_ == ACT_DOWN) {
                state_ = STATE_DEAD;
                state_timer_ = 0.0f;
            }
        }
        return;
    }

    if (player_action_ != ACT_IDLE) {
        action_timer_ -= dt;
        if (action_timer_ <= 0.0f) {
            player_action_ = ACT_IDLE;
            dodge_offset_x_ = 0.0f;
            duck_offset_y_ = 0.0f;
        }
    }

    // Input handlers
    if (player_action_ == ACT_IDLE) {
        if (buttons & BUTTON_LEFT) {
            Dodge(-1);
        } else if (buttons & BUTTON_RIGHT) {
            Dodge(1);
        } else if (buttons & BUTTON_DOWN) {
            Dodge(0); // Duck
        } else if (buttons & BUTTON_UP) {
            player_action_ = ACT_BLOCK;
            action_timer_ = 0.25f;
        } else if ((buttons & BUTTON_A) && !(prev_buttons & BUTTON_A)) {
            Punch(0); // Left jab
        } else if ((buttons & BUTTON_B) && !(prev_buttons & BUTTON_B)) {
            Punch(1); // Right hook / Star uppercut
        }
    }
}

void Game065PunchOut::UpdateOpponent(float dt) {
    if (opp_action_ == OPP_DOWN) {
        ref_count_timer_ += dt;
        if (ref_count_timer_ >= 1.0f) {
            ref_count_timer_ = 0.0f;
            count_num_++;
            if (count_num_ >= 7 && opp_downs_ < 3) {
                // Opponent gets back up
                opp_action_ = OPP_IDLE;
                opp_stamina_ = 60;
                opp_timer_ = 1.0f;
            } else if (count_num_ > 10) {
                state_ = STATE_VICTORY;
                state_timer_ = 0.0f;
                score_ += 3000;
                if (score_ > high_score_) high_score_ = score_;
            }
        }
        return;
    }

    opp_timer_ -= dt;

    if (opp_action_ == OPP_IDLE) {
        if (opp_timer_ <= 0.0f) {
            // Choose attack
            int r = rand() % 3;
            if (r == 0) {
                opp_action_ = OPP_PREP_LEFT_HOOK;
                opp_attack_type_ = 1;
                opp_timer_ = 0.40f; // Telegraph window
            } else if (r == 1) {
                opp_action_ = OPP_PREP_RIGHT_HOOK;
                opp_attack_type_ = 2;
                opp_timer_ = 0.40f; // Telegraph window
            } else {
                opp_action_ = OPP_PREP_BULL_CHARGE;
                opp_attack_type_ = 3;
                opp_timer_ = 0.55f; // Telegraph window
            }
        }
    } else if (opp_action_ == OPP_PREP_LEFT_HOOK ||
               opp_action_ == OPP_PREP_RIGHT_HOOK ||
               opp_action_ == OPP_PREP_BULL_CHARGE) {
        if (opp_timer_ <= 0.0f) {
            // Opponent swings punch!
            opp_action_ = OPP_SWING;
            opp_timer_ = 0.20f;

            // Check if player successfully dodged
            bool evaded = false;
            if (opp_attack_type_ == 1 && player_action_ == ACT_DODGE_RIGHT) evaded = true;
            if (opp_attack_type_ == 2 && player_action_ == ACT_DODGE_LEFT)  evaded = true;
            if (opp_attack_type_ == 3 && (player_action_ == ACT_DODGE_LEFT || player_action_ == ACT_DODGE_RIGHT)) evaded = true;
            if (player_action_ == ACT_DUCK) evaded = true;

            if (evaded) {
                // Opponent misses and gets stunned!
                opp_action_ = OPP_STUNNED;
                opp_timer_ = 0.75f;
            } else if (player_action_ == ACT_BLOCK) {
                // Partial block
                player_stamina_ -= 8;
                if (player_stamina_ <= 0) KnockdownPlayer();
            } else {
                // Direct heavy hit on player!
                int damage = (opp_attack_type_ == 3) ? 35 : 25;
                player_stamina_ -= damage;
                player_action_ = ACT_HURT;
                action_timer_ = 0.35f;
                if (player_stamina_ <= 0) {
                    KnockdownPlayer();
                }
            }
        }
    } else if (opp_action_ == OPP_SWING) {
        if (opp_timer_ <= 0.0f) {
            opp_action_ = OPP_IDLE;
            opp_timer_ = 0.8f;
        }
    } else if (opp_action_ == OPP_STUNNED || opp_action_ == OPP_HURT) {
        if (opp_timer_ <= 0.0f) {
            opp_action_ = OPP_IDLE;
            opp_timer_ = 0.7f;
        }
    }
}

void Game065PunchOut::Render(uint8_t* fb) {
    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // 1. Boxing ring ropes & canvas
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (y == 1) {
                // Top rope (red)
                set_pixel(x, y, 200, 20, 20);
            } else if (y == 2) {
                // Middle rope (white)
                set_pixel(x, y, 220, 220, 220);
            } else if (y == 3) {
                // Bottom rope (blue)
                set_pixel(x, y, 20, 40, 180);
            } else if (y > 3) {
                // Ring mat blue canvas
                set_pixel(x, y, 15, 30, 70);
            } else {
                // Crowd darkness
                set_pixel(x, y, 5, 5, 12);
            }
        }
    }

    // Corner turnbuckle posts
    set_pixel(0, 1, 255, 255, 0);
    set_pixel(15, 1, 255, 255, 0);

    // 2. HUD: Player & Opponent stamina bars (y=0)
    int p_bars = std::max(0, std::min(6, (player_stamina_ * 6) / 100));
    for (int i = 0; i < p_bars; ++i) {
        set_pixel(i, 0, 40, 220, 40); // Green player stamina
    }

    int o_bars = std::max(0, std::min(6, (opp_stamina_ * 6) / 100));
    for (int i = 0; i < o_bars; ++i) {
        set_pixel(15 - i, 0, 220, 30, 30); // Red opponent stamina
    }

    // Stars display
    for (int s = 0; s < stars_; ++s) {
        set_pixel(7 + s, 0, 255, 215, 0); // Gold stars
    }

    // 3. Opponent Rendering (Bald Bull archetype)
    if (opp_action_ == OPP_DOWN) {
        // Opponent knocked down on canvas
        for (int x = 5; x <= 11; ++x) {
            set_pixel(x, 6, 220, 150, 120);
            set_pixel(x, 7, 180, 40, 40);
        }
    } else {
        int opp_base_y = 4;
        bool flash_prep = (opp_action_ == OPP_PREP_LEFT_HOOK ||
                           opp_action_ == OPP_PREP_RIGHT_HOOK ||
                           opp_action_ == OPP_PREP_BULL_CHARGE) &&
                          (int(state_timer_ * 20.0f) % 2 == 0);
        bool flash_stun = (opp_action_ == OPP_STUNNED) && (int(state_timer_ * 15.0f) % 2 == 0);

        uint8_t skin_r = flash_prep ? 255 : (flash_stun ? 240 : 210);
        uint8_t skin_g = flash_prep ? 220 : (flash_stun ? 240 : 140);
        uint8_t skin_b = flash_prep ? 30  : (flash_stun ? 255 : 100);

        // Head (Bald peach)
        for (int dy = 0; dy <= 2; ++dy) {
            for (int dx = 7; dx <= 9; ++dx) {
                set_pixel(dx, opp_base_y + dy, skin_r, skin_g, skin_b);
            }
        }
        // Mustache
        set_pixel(7, opp_base_y + 2, 40, 20, 10);
        set_pixel(9, opp_base_y + 2, 40, 20, 10);

        // Torso / shoulders
        for (int dy = 3; dy <= 4; ++dy) {
            for (int dx = 6; dx <= 10; ++dx) {
                set_pixel(dx, opp_base_y + dy, skin_r - 20, skin_g - 20, skin_b);
            }
        }

        // Trunks (black/red belt)
        for (int dx = 6; dx <= 10; ++dx) {
            set_pixel(dx, opp_base_y + 5, 200, 20, 20);
        }

        // Gloves
        if (opp_action_ == OPP_SWING) {
            // Forward punch extended
            if (opp_attack_type_ == 1) {
                set_pixel(6, opp_base_y + 5, 255, 30, 30);
                set_pixel(6, opp_base_y + 6, 255, 30, 30);
            } else {
                set_pixel(10, opp_base_y + 5, 255, 30, 30);
                set_pixel(10, opp_base_y + 6, 255, 30, 30);
            }
        } else {
            // Guard gloves
            set_pixel(5, opp_base_y + 3, 220, 20, 20);
            set_pixel(11, opp_base_y + 3, 220, 20, 20);
        }
    }

    // 4. Player Rendering (Little Mac wireframe / green back view)
    if (player_action_ == ACT_DOWN) {
        // Player knocked down
        for (int x = 6; x <= 10; ++x) {
            set_pixel(x, 14, 40, 180, 60);
        }
    } else {
        int px = 8 + int(std::round(dodge_offset_x_));
        int py = 12 + int(std::round(duck_offset_y_));

        // Hair (black)
        set_pixel(px - 1, py - 2, 20, 20, 20);
        set_pixel(px,     py - 2, 20, 20, 20);
        set_pixel(px + 1, py - 2, 20, 20, 20);

        // Shoulders / Back (green vest / skin outline)
        set_pixel(px - 1, py - 1, 30, 160, 50);
        set_pixel(px,     py - 1, 40, 180, 60);
        set_pixel(px + 1, py - 1, 30, 160, 50);

        // Waist / Trunks
        set_pixel(px - 1, py, 20, 120, 40);
        set_pixel(px,     py, 20, 120, 40);
        set_pixel(px + 1, py, 20, 120, 40);

        // Green Gloves & Punching arms
        if (player_action_ == ACT_PUNCH_LEFT) {
            set_pixel(px - 1, py - 4, 80, 255, 80); // Left glove extended upward
            set_pixel(px - 1, py - 3, 40, 200, 50);
            set_pixel(px + 1, py - 1, 40, 200, 50); // Right guard
        } else if (player_action_ == ACT_PUNCH_RIGHT) {
            set_pixel(px + 1, py - 4, 80, 255, 80); // Right glove extended upward
            set_pixel(px + 1, py - 3, 40, 200, 50);
            set_pixel(px - 1, py - 1, 40, 200, 50); // Left guard
        } else if (player_action_ == ACT_BLOCK) {
            set_pixel(px - 1, py - 3, 80, 255, 80); // Guard high
            set_pixel(px + 1, py - 3, 80, 255, 80);
        } else {
            // Normal stance gloves
            set_pixel(px - 2, py - 1, 80, 255, 80);
            set_pixel(px + 2, py - 1, 80, 255, 80);
        }
    }
}

} // namespace arcade
