#include "game_024_peggle.h"
namespace arcade {

void Game024Peggle::Setup() {
    aim = 0;
    x = 8;
    y = 2;
    vx = vy = 0;
    mask = 255;
    const int b[] = {10, 8, 6};
    balls = b[difficulty_];
    flying = false;
}
void Game024Peggle::Tick(float dt, uint16_t down, uint16_t pressed) {
    double step = std::round(double(dt) * 1000000.0) / 1000000.0;
    unsigned keys = down | pressed;
    const int speed[] = {6, 7, 8}, limit[] = {90, 75, 60};
    if (!flying) {
        aim = std::max(-1.0, std::min(1.0, aim + step * 1.2 *
                                                     ((keys & KEY_RIGHT ? 1 : 0) -
                                                      (keys & KEY_LEFT ? 1 : 0))));
        if ((pressed & KEY_A) && balls) {
            x = 8;
            y = 2;
            vx = std::sin(aim) * speed[difficulty_];
            vy = std::cos(aim) * speed[difficulty_];
            --balls;
            flying = true;
            SoundEvent(Sound::Shot);
        }
    } else {
        vy += 2.5 * step;
        x += vx * step;
        y += vy * step;
        if (x < .7 || x > 14.3) {
            x = std::max(.7, std::min(14.3, x));
            vx = -vx;
        }
        const int pegs[][2] = {{4, 6},  {7, 6},  {10, 6}, {13, 6},
                               {3, 10}, {6, 10}, {9, 10}, {12, 10}};
        for (int i = 0; i < 8; ++i) {
            double dx = x - pegs[i][0], dy = y - pegs[i][1], dist = std::hypot(dx, dy);
            if ((mask & (1 << i)) && dist < 1.05) {
                mask &= ~(1 << i);
                Award(50);
                SoundEvent(Sound::Hit, i);
                double nx = dx / std::max(.01, dist), ny = dy / std::max(.01, dist),
                       dot = vx * nx + vy * ny;
                if (dot < 0) {
                    vx -= 1.8 * dot * nx;
                    vy -= 1.8 * dot * ny;
                }
            }
        }
        if (!mask) {
            Award(500);
            Finish(true);
        } else if (y > 15) {
            flying = false;
            if (!balls)
                Finish(false);
        }
    }
    if (elapsed_ > limit[difficulty_])
        Finish(false);
    aim = B3Quantize(aim);
    x = B3Quantize(x);
    y = B3Quantize(y);
    vx = B3Quantize(vx);
    vy = B3Quantize(vy);
}
int Game024Peggle::Progress() const {
    int remaining = 0;
    for (int i = 0; i < 8; ++i)
        if (mask & (1 << i))
            ++remaining;
    return (8 - remaining) * 100 / 8;
}
void Game024Peggle::Draw(uint8_t *fb) {
    const int pegs[][2] = {{4, 6}, {7, 6}, {10, 6}, {13, 6}, {3, 10}, {6, 10}, {9, 10}, {12, 10}};
    for (int i = 0; i < 8; ++i)
        if (mask & (1 << i))
            Px(fb, pegs[i][0], pegs[i][1], 255, 150, 40);
    if (flying)
        Px(fb, int(std::round(x)), int(std::round(y)), 245, 245, 255);
    else
        B3Line(fb, 8, 1, int(std::round(8 + std::sin(aim) * 3)),
               int(std::round(1 + std::cos(aim) * 3)), 80, 180, 255);
    for (int i = 0; i < balls; ++i)
        Px(fb, i + 1, 0, 40, 150, 240);
}

} // namespace arcade
