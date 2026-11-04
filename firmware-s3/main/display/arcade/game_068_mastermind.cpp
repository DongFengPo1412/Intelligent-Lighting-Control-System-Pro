#include "game_068_mastermind.h"
namespace arcade {

void Game068Mastermind::Setup() {
    uint32_t seed = 0x68ad;
    for (int i = 0; i < 4; ++i)
        secret[i] = B3Random(seed) % 6;
    memset(guess, 0, sizeof(guess));
    slot = exact = near = 0;
    const int n[] = {10, 8, 6};
    tries = n[difficulty_];
}
void Game068Mastermind::Tick(float, uint16_t down, uint16_t pressed) {
    int dx, dy;
    Direction(down, pressed, dx, dy);
    slot = std::max(0, std::min(3, slot + dx));
    if (dy) {
        guess[slot] = (guess[slot] + dy + 6) % 6;
        SoundEvent(Sound::Action);
    }
    if (pressed & KEY_A) {
        exact = near = 0;
        int a[6]{}, b[6]{};
        for (int i = 0; i < 4; ++i) {
            exact += guess[i] == secret[i];
            ++a[secret[i]];
            ++b[guess[i]];
        }
        for (int i = 0; i < 6; ++i)
            near += std::min(a[i], b[i]);
        near -= exact;
        --tries;
        SoundEvent(Sound::Hit, exact);
        if (exact == 4) {
            Award(1000 + tries * 50);
            Finish(true);
        } else if (!tries)
            Finish(false);
    }
    const int limit[] = {180, 150, 120};
    if (elapsed_ > limit[difficulty_])
        Finish(false);
}
int Game068Mastermind::Progress() const { return exact * 25; }
void Game068Mastermind::Draw(uint8_t *fb) {
    const int colors[][3] = {{235, 65, 80},  {65, 170, 240}, {80, 220, 100},
                             {245, 205, 60}, {170, 90, 230}, {245, 140, 65}};
    for (int i = 0; i < 4; ++i) {
        auto c = colors[guess[i]];
        Cell(fb, i, 1, c[0], c[1], c[2], 3, 1);
    }
    Px(fb, 2 + slot * 3, 3, 255, 255, 255);
    for (int i = 0; i < exact; ++i)
        Cell(fb, i, 3, 245, 245, 245, 2, 1);
    for (int i = 0; i < near; ++i)
        Cell(fb, i, 5, 245, 180, 40, 2, 1);
    for (int i = 0; i < tries; ++i)
        Px(fb, i + 1, 14, 65, 180, 130);
}

} // namespace arcade
