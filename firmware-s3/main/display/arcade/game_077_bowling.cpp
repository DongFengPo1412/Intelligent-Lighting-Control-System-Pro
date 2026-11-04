#include "game_077_bowling.h"
namespace arcade {

void Game077Bowling::Setup() {
    aim = power = vx = vy = 0;
    x = 8;
    y = 14;
    charging = flying = false;
    pins = 1023;
    frame = shot = first = nroll = 0;
    before = 10;
    memset(rolls, 0, sizeof(rolls));
}
int Game077Bowling::Total() const { return B3BowlingTotal(rolls, nroll); }
void Game077Bowling::Resolve() {
    int standing = 0;
    for (int i = 0; i < 10; ++i)
        standing += (pins >> i) & 1;
    int knocked = std::max(0, before - standing);
    if (nroll < 21)
        rolls[nroll++] = knocked;
    score_ = Total();
    high_ = std::max(high_, score_);
    ArcadeScoreStore::SaveHighScore(GetId(), high_);
    SoundEvent(Sound::Hit, knocked);
    flying = false;
    if (frame < 9) {
        if (shot == 0 && knocked < 10) {
            first = knocked;
            shot = 1;
        } else {
            ++frame;
            shot = first = 0;
            pins = 1023;
        }
    } else {
        if (shot == 0) {
            first = knocked;
            shot = 1;
            if (knocked == 10)
                pins = 1023;
        } else if (shot == 1) {
            if (first == 10 || first + knocked == 10) {
                shot = 2;
                if (knocked == 10 || first < 10)
                    pins = 1023;
                first = 0;
            } else
                frame = 10;
        } else
            frame = 10;
    }
    if (frame == 10) {
        const int goal[] = {60, 90, 120};
        Finish(score_ >= goal[difficulty_]);
    }
}
void Game077Bowling::Tick(float dt, uint16_t down, uint16_t) {
    double t = std::round(double(dt) * 1000000) / 1000000;
    if (!flying) {
        aim =
            std::max(-1., std::min(1., aim + t * (bool(down & KEY_RIGHT) - bool(down & KEY_LEFT))));
        if (down & KEY_A) {
            charging = true;
            power = std::min(1.2, power + t);
        } else if (charging) {
            charging = false;
            flying = true;
            before = 0;
            for (int i = 0; i < 10; ++i)
                before += (pins >> i) & 1;
            x = 8;
            y = 14;
            vx = aim * 3;
            vy = -(6 + 6 * power);
            power = 0;
            SoundEvent(Sound::Action);
        }
    } else {
        x += vx * t;
        y += vy * t;
        const int xx[] = {8, 7, 9, 6, 8, 10, 5, 7, 9, 11}, yy[] = {2, 3, 3, 4, 4, 4, 5, 5, 5, 5};
        const double radius[] = {1.1, .95, .8};
        for (int i = 0; i < 10; ++i)
            if ((pins & (1 << i)) && std::hypot(x - xx[i], y - yy[i]) < radius[difficulty_]) {
                pins &= ~(1 << i);
                int frontier = 1 << i;
                for (int step = 0; step < (std::abs(vy) > 9 ? 3 : 1); ++step) {
                    int next = 0;
                    for (int j = 0; j < 10; ++j)
                        if (pins & (1 << j))
                            for (int k = 0; k < 10; ++k)
                                if ((frontier & (1 << k)) && yy[j] <= yy[k] &&
                                    std::hypot(double(xx[j] - xx[k]), double(yy[j] - yy[k])) <=
                                        2.3) {
                                    next |= 1 << j;
                                    break;
                                }
                    pins &= ~next;
                    frontier = next;
                }
            }
        if (y < 0 || x < 0 || x > 15)
            Resolve();
    }
    const int limit[] = {300, 240, 180};
    if (elapsed_ > limit[difficulty_])
        Finish(false);
}
int Game077Bowling::Progress() const { return frame * 10; }
void Game077Bowling::Draw(uint8_t *fb) {
    B3Line(fb, 3, 0, 3, 15, 45, 65, 95);
    B3Line(fb, 13, 0, 13, 15, 45, 65, 95);
    const int xx[] = {8, 7, 9, 6, 8, 10, 5, 7, 9, 11}, yy[] = {2, 3, 3, 4, 4, 4, 5, 5, 5, 5};
    for (int i = 0; i < 10; ++i)
        if (pins & (1 << i))
            Px(fb, xx[i], yy[i], 245, 245, 245);
    B3Disc(fb, flying ? x : 8 + aim * 4, flying ? y : 14, .7, 80, 190, 240);
}

} // namespace arcade
