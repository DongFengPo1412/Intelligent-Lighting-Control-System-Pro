#include "game_037_qbert.h"
namespace arcade {

void Game037Qbert::Setup() {
    row = col = 0;
    er = 4;
    ec = 2;
    const int h[] = {3, 2, 1};
    hp = h[difficulty_];
    mask = 1;
    hop = 0;
    chase = -8;
}
void Game037Qbert::Tick(float dt, uint16_t down, uint16_t pressed) {
    hop = std::max(0.f, hop - dt);
    unsigned keys = down | pressed;
    if (hop <= 0 && (keys & 15)) {
        int dr = keys & KEY_LEFT    ? 1
                 : keys & KEY_RIGHT ? -1
                 : keys & KEY_UP    ? -1
                                    : 1,
            dc = keys & KEY_LEFT    ? 0
                 : keys & KEY_RIGHT ? 0
                 : keys & KEY_UP    ? -1
                                    : 1,
            nr = row + dr, nc = col + dc;
        hop = .14f;
        if (nr < 0 || nr >= 5 || nc < 0 || nc > nr) {
            --hp;
            row = col = 0;
            SoundEvent(Sound::Collision);
        } else {
            row = nr;
            col = nc;
            int bit = 1 << (nr * (nr + 1) / 2 + nc);
            if (!(mask & bit)) {
                mask |= bit;
                Award(20);
            }
            SoundEvent(Sound::Jump);
        }
    }
    chase += dt;
    const float interval[] = {1.5f, .9f, .5f};
    if (chase >= interval[difficulty_]) {
        chase = 0;
        const int dr[] = {1, 1, -1, -1}, dc[] = {0, 1, 0, -1};
        int br = er, bc = ec, best = 100;
        for (int i = 0; i < 4; ++i) {
            int nr = er + dr[i], nc = ec + dc[i], d = std::abs(nr - row) + std::abs(nc - col);
            if (nr >= 0 && nr < 5 && nc >= 0 && nc <= nr && d < best) {
                best = d;
                br = nr;
                bc = nc;
            }
        }
        er = br;
        ec = bc;
        if (er == row && ec == col) {
            --hp;
            row = col = 0;
            er = 4;
            ec = 2;
            SoundEvent(Sound::Collision);
        }
    }
    const int limit[] = {90, 70, 55};
    if (mask == 32767) {
        Award(500);
        Finish(true);
    } else if (hp <= 0 || elapsed_ > limit[difficulty_])
        Finish(false);
}
int Game037Qbert::Progress() const {
    int n = 0;
    for (int i = 0; i < 15; ++i)
        if (mask & (1 << i))
            ++n;
    return n * 100 / 15;
}
void Game037Qbert::Draw(uint8_t *fb) {
    for (int r = 0; r < 5; ++r)
        for (int c = 0; c <= r; ++c) {
            bool on = mask & (1 << (r * (r + 1) / 2 + c));
            int xx = int(std::round(7 + (2 * c - r) * 1.4f)), yy = 2 + r * 2;
            Px(fb, xx, yy, on ? 245 : 90, on ? 195 : 55, on ? 40 : 145);
            Px(fb, xx + 1, yy, on ? 245 : 90, on ? 195 : 55, on ? 40 : 145);
        }
    Px(fb, int(std::round(7 + (2 * ec - er) * 1.4f)), 1 + er * 2, 255, 65, 90);
    Px(fb, int(std::round(7 + (2 * col - row) * 1.4f)), 1 + row * 2, 245, 245, 255);
}

} // namespace arcade
