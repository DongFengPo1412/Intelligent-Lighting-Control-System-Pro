#include "game_069_nim.h"
namespace arcade {
void Game069Nim::LoadRound() {
    for (int i = 0; i < 3; ++i)
        piles[i] = 3 + round + i;
    pile = 0;
    take = 1;
    thinking = 0;
}
void Game069Nim::Setup() {
    turns = human_wins = ai_wins = round = 0;
    LoadRound();
}
void Game069Nim::EndRound(bool human) {
    if (human) {
        ++human_wins;
        Award(300);
    } else
        ++ai_wins;
    SoundEvent(human ? Sound::Hit : Sound::Collision);
    if (human_wins == 2) {
        Award(500);
        Finish(true);
    } else if (ai_wins == 2)
        Finish(false);
    else {
        ++round;
        LoadRound();
    }
}
void Game069Nim::Tick(float dt, uint16_t down, uint16_t pressed) {
    if (thinking > 0) {
        thinking = std::max(0., thinking - std::round(double(dt) * 1000000) / 1000000);
        if (thinking == 0) {
            int v = piles[0] ^ piles[1] ^ piles[2], target = 0, amount = 1;
            while (!piles[target])
                ++target;
            if (difficulty_)
                for (int i = 0; i < 3; ++i)
                    if ((piles[i] ^ v) < piles[i]) {
                        target = i;
                        amount = piles[i] - (piles[i] ^ v);
                        break;
                    }
            piles[target] -= amount;
            take = 1;
            SoundEvent(Sound::Action, 1);
            if (piles[0] + piles[1] + piles[2] == 0)
                EndRound(false);
        }
    } else {
        int dx, dy;
        Direction(down, pressed, dx, dy);
        pile = std::max(0, std::min(2, pile + dx));
        take = std::max(1, std::min(std::max(1, piles[pile]), take + dy));
        if ((pressed & KEY_A) && piles[pile] >= take) {
            piles[pile] -= take;
            ++turns;
            Award(take * 10);
            SoundEvent(Sound::Action);
            if (piles[0] + piles[1] + piles[2] == 0)
                EndRound(true);
            else
                thinking = .35;
        }
    }
    const int limit[] = {120, 90, 60};
    if (elapsed_ > limit[difficulty_])
        Finish(false);
}
int Game069Nim::Progress() const { return state_ == STATE_VICTORY ? 100 : human_wins * 50; }
void Game069Nim::Draw(uint8_t *fb) {
    for (int i = 0; i < 3; ++i)
        for (int j = 0; j < piles[i]; ++j)
            if (i == pile && j < take)
                Cell(fb, i, j, 245, 200, 60, 2, 2);
            else
                Cell(fb, i, j, 65, 175, 220, 2, 2);
    Px(fb, 2 + pile * 2, 0, 255, thinking ? 100 : 255, thinking ? 100 : 255);
    for (int i = 0; i < human_wins; ++i)
        Px(fb, 10 + i, 3, 65, 220, 100);
    for (int i = 0; i < ai_wins; ++i)
        Px(fb, 10 + i, 5, 245, 80, 100);
}
} // namespace arcade
