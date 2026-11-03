// game_001_mario.cpp —— 超级马里奥 (Super Mario Bros. 16)
#include "game_001_mario.h"

namespace arcade {

Game001Mario::Game001Mario()
{
    Init();
}

void Game001Mario::Init()
{
    game_.begin();
}

void Game001Mario::Reset()
{
    game_.resetAll();
}

void Game001Mario::Update(float dt, uint16_t keys_down, uint16_t keys_pressed)
{
    mario16::Input in;
    in.down = keys_down;
    in.pressed = keys_pressed;
    game_.update(dt, in);
}

void Game001Mario::Render(uint8_t* fb_rgb24)
{
    game_.render(fb_rgb24);
}

CartridgeStatus Game001Mario::GetStatus() const
{
    auto s = game_.status();
    CartridgeStatus st;
    st.score = s.score;
    st.lives = s.lives;
    st.progress = s.progress;

    // 映射状态枚举
    if (s.state == mario16::ST_TITLE) {
        st.state = STATE_TITLE;
    } else if (s.state == mario16::ST_PAUSE) {
        st.state = STATE_PAUSED;
    } else if (s.state == mario16::ST_GAMEOVER || s.state == mario16::ST_DEAD) {
        st.state = STATE_GAMEOVER;
    } else if (s.state == mario16::ST_WIN) {
        st.state = STATE_VICTORY;
    } else {
        st.state = STATE_PLAYING;
    }

    return st;
}

} // namespace arcade
