#include "game_050_mini_sudoku.h"
namespace arcade {

void Game050MiniSudoku::Setup() {
    memset(board, 0, sizeof(board));
    x = y = edits = 0;
    const int a[] = {3, 2, 1}, n[] = {8, 6, 4}, pos[] = {0, 3, 5, 6, 9, 10, 12, 15};
    attempts = a[difficulty_];
    fixed = 0;
    conflict = 0;
    for (int i = 0; i < n[difficulty_]; ++i) {
        int p = pos[i];
        board[p] = (p / 4 * 2 + p / 8 + p % 4) % 4 + 1;
        fixed |= 1u << p;
    }
}
void Game050MiniSudoku::Tick(float dt, uint16_t down, uint16_t pressed) {
    int dx, dy;
    Direction(down, pressed, dx, dy);
    x = std::max(0, std::min(3, x + dx));
    y = std::max(0, std::min(3, y + dy));
    int p = y * 4 + x;
    conflict = std::max(0.f, conflict - dt);
    if ((pressed & KEY_A) && !(fixed & (1 << p))) {
        board[p] = (board[p] + 1) % 5;
        ++edits;
        SoundEvent(Sound::Action, board[p]);
    }
    if (pressed & KEY_B) {
        bool valid = true;
        for (int n = 0; n < 4; ++n) {
            int a = 0, b = 0;
            for (int i = 0; i < 4; ++i) {
                a |= 1 << board[n * 4 + i];
                b |= 1 << board[i * 4 + n];
            }
            if (a != 30 || b != 30)
                valid = false;
        }
        for (int by : {0, 2})
            for (int bx : {0, 2}) {
                int a = 0;
                for (int yy = 0; yy < 2; ++yy)
                    for (int xx = 0; xx < 2; ++xx)
                        a |= 1 << board[(by + yy) * 4 + bx + xx];
                if (a != 30)
                    valid = false;
            }
        if (valid) {
            Award(std::max(100, 1200 + attempts * 50 - edits * 2));
            Finish(true);
        } else {
            --attempts;
            conflict = .6f;
            SoundEvent(Sound::Collision);
        }
    }
    const int limit[] = {180, 150, 120};
    if (attempts <= 0 || elapsed_ > limit[difficulty_])
        Finish(false);
}
int Game050MiniSudoku::Progress() const {
    if (state_ == STATE_VICTORY)
        return 100;
    int n = 0;
    for (auto v : board)
        if (v)
            ++n;
    return n * 100 / 16;
}
void Game050MiniSudoku::Draw(uint8_t *fb) {
    const int colors[][3] = {
        {10, 20, 30}, {240, 75, 80}, {65, 170, 240}, {75, 215, 110}, {245, 205, 55}};
    for (int yy = 0; yy < 4; ++yy)
        for (int xx = 0; xx < 4; ++xx) {
            auto c = colors[board[yy * 4 + xx]];
            for (int y2 = 0; y2 < 3; ++y2)
                for (int x2 = 0; x2 < 3; ++x2)
                    Px(fb, xx * 4 + x2, yy * 4 + y2, c[0], c[1], c[2]);
            if (fixed & (1 << (yy * 4 + xx)))
                Px(fb, xx * 4, yy * 4, 150, 150, 150);
        }
    Px(fb, x * 4 + 1, y * 4 + 1, 255, conflict ? 40 : 255, conflict ? 40 : 255);
}

} // namespace arcade
