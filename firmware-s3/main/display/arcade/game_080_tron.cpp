#include "game_080_tron.h"
namespace arcade {

void Game080Tron::Setup() {
    memset(board, 0, sizeof(board));
    x = 3;
    y = 12;
    dir = 0;
    ex = 12;
    ey = 3;
    edir = 2;
    steps = 0;
    clock = 0;
    board[195] = 1;
    board[60] = 2;
    board_hash = 0;
}
void Game080Tron::Tick(float dt, uint16_t down, uint16_t pressed) {
    uint16_t keys = down | pressed;
    const int k[] = {KEY_UP, KEY_RIGHT, KEY_DOWN, KEY_LEFT}, dx[] = {0, 1, 0, -1},
              dy[] = {-1, 0, 1, 0}, goal[] = {50, 65, 80};
    for (int d = 0; d < 4; ++d)
        if ((keys & k[d]) && d != (dir + 2) % 4) {
            dir = d;
            break;
        }
    const double period[] = {.16, .13, .10};
    clock += std::round(double(dt) * 1000000) / 1000000;
    if (clock < period[difficulty_])
        return;
    clock -= period[difficulty_];
    int order[] = {edir, (edir + 1) % 4, (edir + 3) % 4};
    for (auto d : order) {
        int xx = ex + dx[d], yy = ey + dy[d];
        if (xx >= 1 && xx <= 14 && yy >= 1 && yy <= 14 && !board[yy * 16 + xx]) {
            edir = d;
            break;
        }
    }
    int nx = x + dx[dir], ny = y + dy[dir], mx = ex + dx[edir], my = ey + dy[edir];
    bool dead = nx < 1 || nx > 14 || ny < 1 || ny > 14 ||
                (nx >= 0 && nx < 16 && ny >= 0 && ny < 16 && board[ny * 16 + nx]) ||
                (nx == mx && ny == my);
    bool enemy = mx < 1 || mx > 14 || my < 1 || my > 14 ||
                 (mx >= 0 && mx < 16 && my >= 0 && my < 16 && board[my * 16 + mx]);
    if (dead) {
        Finish(false);
        return;
    }
    x = nx;
    y = ny;
    board[ny * 16 + nx] = 1;
    ++steps;
    Award(10);
    if (enemy || steps >= goal[difficulty_]) {
        Award(500);
        Finish(true);
    } else {
        ex = mx;
        ey = my;
        board[my * 16 + mx] = 2;
    }
    board_hash = 2166136261u;
    for (auto v : board)
        board_hash = (board_hash ^ v) * 16777619u;
}
int Game080Tron::Progress() const {
    const int goal[] = {50, 65, 80};
    return std::min(100, steps * 100 / goal[difficulty_]);
}
void Game080Tron::Draw(uint8_t *fb) {
    for (int p = 0; p < 256; ++p)
        if (board[p])
            Px(fb, p % 16, p / 16, board[p] == 1 ? 60 : 220, board[p] == 1 ? 160 : 70,
               board[p] == 1 ? 220 : 125);
    Px(fb, x, y, 170, 245, 255);
    Px(fb, ex, ey, 255, 190, 190);
}

} // namespace arcade
