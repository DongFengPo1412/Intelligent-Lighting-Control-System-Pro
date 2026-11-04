#include "game_069_nim.h"
namespace arcade {

void Game069Nim::Setup() {
    piles[0] = 3;
    piles[1] = 4;
    piles[2] = 5;
    pile = turns = 0;
    take = 1;
}
void Game069Nim::Tick(float, uint16_t down, uint16_t pressed) {
    int dx, dy;
    Direction(down, pressed, dx, dy);
    pile = std::max(0, std::min(2, pile + dx));
    take = std::max(1, std::min(std::max(1, piles[pile]), take + dy));
    if ((pressed & KEY_A) && piles[pile] >= take) {
        piles[pile] -= take;
        ++turns;
        Award(take * 10);
        SoundEvent(Sound::Action);
        if (piles[0] + piles[1] + piles[2] == 0) {
            Award(1000);
            Finish(true);
            return;
        }
        int value = piles[0] ^ piles[1] ^ piles[2], target = 0, amount = 1;
        while (!piles[target])
            ++target;
        if (difficulty_)
            for (int i = 0; i < 3; ++i)
                if ((piles[i] ^ value) < piles[i]) {
                    target = i;
                    amount = piles[i] - (piles[i] ^ value);
                    break;
                }
        piles[target] -= amount;
        if (piles[0] + piles[1] + piles[2] == 0)
            Finish(false);
        take = 1;
    }
    const int limit[] = {120, 90, 60};
    if (elapsed_ > limit[difficulty_])
        Finish(false);
}
int Game069Nim::Progress() const { return (12 - piles[0] - piles[1] - piles[2]) * 100 / 12; }
void Game069Nim::Draw(uint8_t *fb) {
    for (int i = 0; i < 3; ++i)
        for (int j = 0; j < piles[i]; ++j)
            if (i == pile && j < take)
                Cell(fb, i, j, 245, 200, 60, 2, 2);
            else
                Cell(fb, i, j, 65, 175, 220, 2, 2);
    Px(fb, 2 + pile * 2, 0, 255, 255, 255);
}

} // namespace arcade
