#include "game_100_memory_match.h"
namespace arcade {

void Game100MemoryMatch::Setup() {
    for (int i = 0; i < 16; ++i)
        cards[i] = i / 2;
    uint32_t seed = 0x100fa;
    for (int i = 15; i > 0; --i) {
        int j = (B3Random(seed) >> 16) % (i + 1);
        std::swap(cards[i], cards[j]);
    }
    x = y = pairs = turns = matched = 0;
    first = second = -1;
    wait = 0;
}
void Game100MemoryMatch::Tick(float dt, uint16_t down, uint16_t pressed) {
    if (wait > 0) {
        wait = std::max(0., wait - std::round(double(dt) * 1000000) / 1000000);
        if (wait == 0)
            first = second = -1;
    } else {
        int dx, dy;
        Direction(down, pressed, dx, dy);
        x = std::max(0, std::min(3, x + dx));
        y = std::max(0, std::min(3, y + dy));
        int p = y * 4 + x;
        if ((pressed & KEY_A) && !(matched & (1 << p)) && p != first) {
            if (first < 0) {
                first = p;
                SoundEvent(Sound::Action);
            } else {
                second = p;
                ++turns;
                if (cards[p] == cards[first]) {
                    matched |= (1 << p) | (1 << first);
                    ++pairs;
                    Award(100);
                    SoundEvent(Sound::Hit);
                    first = second = -1;
                } else {
                    wait = .5;
                    SoundEvent(Sound::Collision);
                }
            }
        }
    }
    const int budget[] = {24, 20, 16}, limit[] = {180, 120, 90};
    if (pairs == 8) {
        Award(std::max(0, 500 - turns * 10));
        Finish(true);
    } else if ((wait == 0 && turns >= budget[difficulty_]) || elapsed_ > limit[difficulty_])
        Finish(false);
}
int Game100MemoryMatch::Progress() const { return pairs * 100 / 8; }
void Game100MemoryMatch::Draw(uint8_t *fb) {
    const int colors[][3] = {{235, 70, 85},  {70, 170, 235}, {80, 215, 115}, {240, 195, 60},
                             {165, 90, 230}, {240, 135, 65}, {60, 210, 205}, {190, 140, 180}};
    for (int p = 0; p < 16; ++p)
        if ((matched & (1 << p)) || p == first || p == second) {
            auto c = colors[cards[p]];
            Cell(fb, p % 4, p / 4, c[0], c[1], c[2], 3, 1);
        } else
            Cell(fb, p % 4, p / 4, 30, 45, 65, 3, 1);
    Px(fb, 2 + x * 3, 2 + y * 3, 255, 255, 255);
}

} // namespace arcade
