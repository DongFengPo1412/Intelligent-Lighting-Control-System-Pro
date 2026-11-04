#include "game_061_connect_four.h"
namespace arcade {

void Game061ConnectFour::Setup() {
    memset(board, 0, sizeof(board));
    column = 3;
    turns = 0;
}
int Game061ConnectFour::Drop(int col, int side) {
    for (int y = 5; y >= 0; --y)
        if (!board[y * 7 + col]) {
            board[y * 7 + col] = side;
            return y * 7 + col;
        }
    return -1;
}
bool Game061ConnectFour::Won(int side) const {
    const int dx[] = {1, 0, 1, 1}, dy[] = {0, 1, 1, -1};
    for (int y = 0; y < 6; ++y)
        for (int x = 0; x < 7; ++x)
            for (int d = 0; d < 4; ++d) {
                bool yes = true;
                for (int i = 0; i < 4; ++i) {
                    int xx = x + i * dx[d], yy = y + i * dy[d];
                    if (xx < 0 || xx >= 7 || yy < 0 || yy >= 6 || board[yy * 7 + xx] != side) {
                        yes = false;
                        break;
                    }
                }
                if (yes)
                    return true;
            }
    return false;
}
int Game061ConnectFour::Choose() const {
    auto *self = const_cast<Game061ConnectFour *>(this);
    const int order[] = {3, 2, 4, 1, 5, 0, 6};
    for (int side = 2; side >= (difficulty_ ? 1 : 2); --side)
        for (auto col : order) {
            int p = self->Drop(col, side);
            if (p < 0)
                continue;
            bool win = Won(side);
            self->board[p] = 0;
            if (win)
                return col;
        }
    if (difficulty_ == 2) {
        int best = -10000, result = 3;
        for (auto col : order) {
            int p = self->Drop(col, 2);
            if (p < 0)
                continue;
            int value = 0;
            for (auto c : order) {
                int q = self->Drop(c, 1);
                if (q >= 0) {
                    if (Won(1))
                        value -= 100;
                    self->board[q] = 0;
                }
            }
            for (int y = 0; y < 6; ++y)
                if (board[y * 7 + 3] == 2)
                    value += 2;
            self->board[p] = 0;
            if (value > best) {
                best = value;
                result = col;
            }
        }
        return result;
    }
    for (auto c : order)
        if (!board[c])
            return c;
    return 0;
}
void Game061ConnectFour::Tick(float, uint16_t down, uint16_t pressed) {
    int dx, dy;
    Direction(down, pressed, dx, dy);
    column = std::max(0, std::min(6, column + dx));
    if (pressed & KEY_A) {
        int p = Drop(column, 1);
        if (p >= 0) {
            ++turns;
            Award(5);
            SoundEvent(Sound::Action);
            if (Won(1)) {
                Award(1000);
                Finish(true);
                return;
            }
            bool full = true;
            for (auto v : board)
                full &= v != 0;
            if (full) {
                Finish(false);
                return;
            }
            Drop(Choose(), 2);
            full = true;
            for (auto v : board)
                full &= v != 0;
            if (Won(2) || full)
                Finish(false);
        }
    }
    const int limit[] = {180, 150, 120};
    if (elapsed_ > limit[difficulty_])
        Finish(false);
}
int Game061ConnectFour::Progress() const {
    return state_ == STATE_VICTORY ? 100 : std::min(90, turns * 4);
}
void Game061ConnectFour::Draw(uint8_t *fb) {
    const int c[][3] = {{15, 30, 55}, {245, 200, 60}, {235, 75, 100}};
    for (int y = 0; y < 6; ++y)
        for (int x = 0; x < 7; ++x) {
            auto p = c[board[y * 7 + x]];
            Cell(fb, x, y, p[0], p[1], p[2], 2, 1);
        }
    Px(fb, 1 + column * 2, 0, 255, 255, 255);
}

} // namespace arcade
