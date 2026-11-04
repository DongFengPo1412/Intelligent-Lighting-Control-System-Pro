#include "game_046_suika.h"
namespace arcade {

void Game046Suika::Setup() {
    aim = 8;
    for (int i = 0; i < 16; ++i) {
        bx[i] = by[i] = vx[i] = vy[i] = 0;
        level[i] = 0;
    }
    best = drops = active_count = 0;
    cooldown = overflow = 0;
}
void Game046Suika::Tick(float dt, uint16_t down, uint16_t pressed) {
    double t = std::round(double(dt) * 1e6) / 1e6;
    unsigned keys = down | pressed;
    aim = std::max(
        2., std::min(13., aim + 5 * t * ((keys & KEY_RIGHT ? 1 : 0) - (keys & KEY_LEFT ? 1 : 0))));
    cooldown = std::max(0., cooldown - t);
    const int budget[] = {32, 24, 20}, gravity[] = {6, 7, 8}, limit[] = {120, 90, 70};
    if ((pressed & KEY_A) && cooldown <= 0 && active_count < 16) {
        if (drops >= budget[difficulty_]) {
            Finish(false);
            return;
        }
        for (int i = 0; i < 16; ++i)
            if (!level[i]) {
                level[i] = 1;
                bx[i] = aim;
                by[i] = 2;
                vx[i] = vy[i] = 0;
                ++drops;
                cooldown = .4;
                SoundEvent(Sound::Action);
                break;
            }
    }
    for (int i = 0; i < 16; ++i)
        if (level[i]) {
            double r = .5 + .3 * level[i];
            vy[i] += gravity[difficulty_] * t;
            bx[i] += vx[i] * t;
            by[i] += vy[i] * t;
            if (bx[i] < r || bx[i] > 15 - r) {
                bx[i] = std::max(r, std::min(15 - r, bx[i]));
                vx[i] *= -.4;
            }
            if (by[i] > 14 - r) {
                by[i] = 14 - r;
                vy[i] *= -.15;
                vx[i] *= .9;
            }
        }
    for (int i = 0; i < 16; ++i)
        for (int j = i + 1; j < 16; ++j)
            if (level[i] && level[j]) {
                double dx = bx[j] - bx[i], dy = by[j] - by[i], distance = std::hypot(dx, dy),
                       radius = 1 + .3 * (level[i] + level[j]);
                if (distance >= radius)
                    continue;
                if (level[i] == level[j] && level[i] < 4) {
                    ++level[i];
                    level[j] = 0;
                    bx[i] = (bx[i] + bx[j]) / 2;
                    by[i] = (by[i] + by[j]) / 2;
                    vx[i] = (vx[i] + vx[j]) / 2;
                    vy[i] = 0;
                    Award((1 << level[i]) * 25);
                    SoundEvent(Sound::Hit, level[i]);
                } else {
                    if (distance < .000001) {
                        dx = 0;
                        dy = 1;
                        distance = 1;
                    }
                    double nx = dx / distance, ny = dy / distance,
                           overlap = (radius - distance) / 2;
                    bx[i] -= nx * overlap;
                    by[i] -= ny * overlap;
                    bx[j] += nx * overlap;
                    by[j] += ny * overlap;
                    double relative = (vx[j] - vx[i]) * nx + (vy[j] - vy[i]) * ny;
                    if (relative < 0) {
                        vx[i] += relative * nx * .6;
                        vy[i] += relative * ny * .6;
                        vx[j] -= relative * nx * .6;
                        vy[j] -= relative * ny * .6;
                    }
                }
            }
    best = active_count = 0;
    bool top = false;
    for (int i = 0; i < 16; ++i) {
        best = std::max(best, level[i]);
        if (level[i]) {
            ++active_count;
            if (by[i] < 3 && std::abs(vy[i]) < .5)
                top = true;
        }
    }
    overflow = top ? overflow + t : 0;
    if (best >= 4) {
        Award(500);
        Finish(true);
    } else if (overflow > 1 || elapsed_ > limit[difficulty_])
        Finish(false);
}
int Game046Suika::Progress() const { return best * 25; }
void Game046Suika::Draw(uint8_t *fb) {
    B3Line(fb, 0, 1, 0, 15, 55, 65, 80);
    B3Line(fb, 15, 1, 15, 15, 55, 65, 80);
    B3Line(fb, 0, 15, 15, 15, 55, 65, 80);
    Px(fb, int(std::round(aim)), 0, 255, 255, 255);
    const int colors[][3] = {{0, 0, 0},      {255, 120, 90}, {255, 205, 50},
                             {120, 210, 55}, {55, 185, 220}, {170, 85, 230}};
    for (int i = 0; i < 16; ++i)
        if (level[i]) {
            auto c = colors[level[i]];
            B3Disc(fb, bx[i], by[i], .5 + .3 * level[i], c[0], c[1], c[2]);
        }
}

} // namespace arcade
