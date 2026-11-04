#include "game_056_sliding_puzzle.h"
namespace arcade {

void Game056SlidingPuzzle::Setup() {
    for (int i = 0; i < 8; ++i)
        board[i] = i + 1;
    board[8] = 0;
    blank = 8;
    moves = 0;
    uint32_t seed = 0x56fa;
    int previous = -1;
    const int count[] = {10, 18, 26};
    for (int t = 0; t < count[difficulty_]; ++t) {
        int neighbors[] = {blank % 3 ? blank - 1 : -1, blank % 3 < 2 ? blank + 1 : -1, blank - 3,
                           blank + 3},
            options[4], n = 0;
        for (auto v : neighbors)
            if (v >= 0 && v < 9 && v != previous)
                options[n++] = v;
        int target = options[B3Random(seed) % n];
        std::swap(board[blank], board[target]);
        previous = blank;
        blank = target;
    }
}
void Game056SlidingPuzzle::Tick(float, uint16_t down, uint16_t pressed) {
    int dx, dy;
    Direction(down, pressed, dx, dy);
    int x = blank % 3 + dx, y = blank / 3 + dy;
    if ((dx || dy) && x >= 0 && x < 3 && y >= 0 && y < 3) {
        int n = y * 3 + x;
        std::swap(board[blank], board[n]);
        blank = n;
        ++moves;
        SoundEvent(Sound::Action);
    }
    bool solved = board[8] == 0;
    for (int i = 0; i < 8; ++i)
        solved &= board[i] == i + 1;
    const int budget[] = {90, 70, 50}, limit[] = {180, 150, 120};
    if (solved) {
        Award(std::max(100, 1500 - moves * 10));
        Finish(true);
    } else if (moves >= budget[difficulty_] || elapsed_ > limit[difficulty_])
        Finish(false);
}
int Game056SlidingPuzzle::Progress() const {
    int n = 0;
    for (int i = 0; i < 8; ++i)
        if (board[i] == i + 1)
            ++n;
    return n * 100 / 8;
}
void Game056SlidingPuzzle::Draw(uint8_t *fb) {
    for (int i = 0; i < 9; ++i)
        if (board[i])
            ArcadeResultScreen::DrawDigit3x5(fb, board[i], (i % 3) * 5 + 1, (i / 3) * 5, 235, 190,
                                             65);
}

} // namespace arcade
