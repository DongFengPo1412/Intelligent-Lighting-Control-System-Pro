#include "game_039_fog_maze.h"
namespace arcade {

void Game039FogMaze::Setup() {
    x = y = 1;
    moves = 0;
    explored = 1;
    memset(grid, 1, sizeof(grid));
    memset(seen, 0, sizeof(seen));
    memset(visited, 0, sizeof(visited));
    visited[1][1] = 1;
    int sx[64], sy[64], n = 1;
    sx[0] = sy[0] = 1;
    grid[1][1] = 0;
    uint32_t seed = 0x39cf;
    const int dx[] = {0, 2, 0, -2}, dy[] = {-2, 0, 2, 0};
    while (n) {
        int xx = sx[n - 1], yy = sy[n - 1], options[4], count = 0;
        for (int i = 0; i < 4; ++i) {
            int nx = xx + dx[i], ny = yy + dy[i];
            if (nx >= 1 && nx <= 13 && ny >= 1 && ny <= 13 && grid[ny][nx])
                options[count++] = i;
        }
        if (!count) {
            --n;
            continue;
        }
        int d = options[B3Random(seed) % count];
        grid[yy + dy[d] / 2][xx + dx[d] / 2] = 0;
        grid[yy + dy[d]][xx + dx[d]] = 0;
        sx[n] = xx + dx[d];
        sy[n] = yy + dy[d];
        ++n;
    }
    layout_hash = 2166136261u;
    for (auto &row : grid)
        for (auto tile : row)
            layout_hash = (layout_hash ^ tile) * 16777619u;
}
void Game039FogMaze::Tick(float, uint16_t down, uint16_t pressed) {
    int dx, dy;
    Direction(down, pressed, dx, dy);
    int nx = x + dx, ny = y + dy;
    if ((dx || dy) && !grid[ny][nx]) {
        x = nx;
        y = ny;
        ++moves;
        if (!visited[ny][nx]) {
            visited[ny][nx] = 1;
            ++explored;
            SoundEvent(Sound::Action);
        }
    }
    const int radius[] = {3, 2, 1}, limit[] = {90, 70, 55};
    for (int yy = 0; yy < 16; ++yy)
        for (int xx = 0; xx < 16; ++xx)
            if (std::abs(xx - x) + std::abs(yy - y) <= radius[difficulty_])
                seen[yy][xx] = 1;
    if (x == 13 && y == 13) {
        Award(std::max(100, 1500 - moves * 5));
        Finish(true);
    } else if (elapsed_ > limit[difficulty_])
        Finish(false);
}
int Game039FogMaze::Progress() const { return state_ == STATE_VICTORY ? 100 : explored * 100 / 97; }
void Game039FogMaze::Draw(uint8_t *fb) {
    const int radius[] = {3, 2, 1};
    for (int yy = 0; yy < 16; ++yy)
        for (int xx = 0; xx < 16; ++xx) {
            bool near = std::abs(xx - x) + std::abs(yy - y) <= radius[difficulty_];
            if (near || seen[yy][xx]) {
                if (near && grid[yy][xx])
                    Px(fb, xx, yy, 75, 90, 110);
                else if (grid[yy][xx])
                    Px(fb, xx, yy, 18, 24, 35);
                else
                    Px(fb, xx, yy, 10, 30, 40);
            }
        }
    if (seen[13][13])
        Px(fb, 13, 13, 40, 230, 100);
    Px(fb, x, y, 245, 245, 255);
}

} // namespace arcade
