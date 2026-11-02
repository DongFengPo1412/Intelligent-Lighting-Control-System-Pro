#include "../firmware-s3/main/display/mario_game.h"
#include <cstdlib>
#include <cstring>

#if defined(_MSC_VER)
#define MARIO_EXPORT __declspec(dllexport)
#else
#define MARIO_EXPORT __attribute__((visibility("default")))
#endif

extern "C" {

MARIO_EXPORT void* mario_create() {
    auto* game = new mario16::Game();
    game->begin();
    return game;
}

MARIO_EXPORT void mario_destroy(void* g) {
    if (g) {
        delete static_cast<mario16::Game*>(g);
    }
}

MARIO_EXPORT void mario_reset(void* g) {
    if (g) {
        static_cast<mario16::Game*>(g)->resetAll();
    }
}

MARIO_EXPORT void mario_update(void* g, float dt, uint16_t down, uint16_t pressed) {
    if (g) {
        mario16::Input in{ down, pressed };
        static_cast<mario16::Game*>(g)->update(dt, in);
    }
}

MARIO_EXPORT void mario_render(void* g, uint8_t* rgb768) {
    if (g && rgb768) {
        static_cast<mario16::Game*>(g)->render(rgb768);
    }
}

MARIO_EXPORT void mario_get_status(void* g, uint16_t* score, uint8_t* lives, uint8_t* coins, uint8_t* state, uint8_t* progress) {
    if (g) {
        auto st = static_cast<mario16::Game*>(g)->status();
        if (score) *score = st.score;
        if (lives) *lives = st.lives;
        if (coins) *coins = st.coins;
        if (state) *state = st.state;
        if (progress) *progress = st.progress;
    }
}

}

