#include "game_048_triple_town.h"
namespace arcade {

void Game048TripleTown::Setup() {
    memset(board, 0, sizeof(board));
    x = y = moves = best = 0;
    const int n[] = {0, 2, 4}, rocks[] = {24, 20, 4, 0};
    for (int i = 0; i < n[difficulty_]; ++i)
        board[rocks[i]] = 9;
    board_hash = 2166136261u;
    for (auto v : board)
        board_hash = (board_hash ^ v) * 16777619u;
}
void Game048TripleTown::Tick(float, uint16_t down, uint16_t pressed) {
    int dx, dy;
    Direction(down, pressed, dx, dy);
    x = std::max(0, std::min(4, x + dx));
    y = std::max(0, std::min(4, y + dy));
    int pos = y * 5 + x;
    if ((pressed & KEY_A) && !board[pos]) {
        board[pos] = 1;
        ++moves;
        Award(5);
        SoundEvent(Sound::Action);
        while (board[pos] < 3) {
            int value = board[pos], stack[25], count = 1, read = 0;
            bool seen[25]{};
            seen[pos] = true;
            stack[0] = pos;
            while (read < count) {
                int p = stack[read++],
                    neighbors[] = {p % 5 ? p - 1 : -1, p % 5 < 4 ? p + 1 : -1, p - 5, p + 5};
                for (auto n : neighbors)
                    if (n >= 0 && n < 25 && !seen[n] && board[n] == value) {
                        seen[n] = true;
                        stack[count++] = n;
                    }
            }
            if (count < 3)
                break;
            for (int i = 0; i < count; ++i)
                board[stack[i]] = 0;
            board[pos] = value + 1;
            Award((1 << (value + 1)) * 10);
            SoundEvent(Sound::Hit, value);
        }
        best = 0;
        for (auto v : board)
            if (v != 9)
                best = std::max(best, v);
    }
    board_hash = 2166136261u;
    bool empty = false;
    for (auto v : board) {
        board_hash = (board_hash ^ v) * 16777619u;
        empty |= v == 0;
    }
    const int budget[] = {40, 30, 20}, limit[] = {120, 100, 80};
    if (best >= 3) {
        Award(500);
        Finish(true);
    } else if (!empty || moves >= budget[difficulty_] || elapsed_ > limit[difficulty_])
        Finish(false);
}
int Game048TripleTown::Progress() const { return best * 100 / 3; }
void Game048TripleTown::Draw(uint8_t *fb) {
    const int colors[][3] = {{10, 18, 25}, {55, 200, 95}, {45, 160, 235}, {245, 190, 50}};
    for (int yy = 0; yy < 5; ++yy)
        for (int xx = 0; xx < 5; ++xx) {
            int v = board[yy * 5 + xx];
            if (v == 9)
                Cell(fb, xx, yy, 90, 95, 105, 3, 0);
            else {
                auto c = colors[v];
                Cell(fb, xx, yy, c[0], c[1], c[2], 3, 0);
            }
        }
    Px(fb, x * 3 + 1, y * 3 + 1, 255, 255, 255);
}

} // namespace arcade
