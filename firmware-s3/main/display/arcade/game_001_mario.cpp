// game_001_mario.cpp —— 超级马里奥 (Super Mario Bros. 16)
#include "game_001_mario.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"

namespace arcade {

Game001Mario::Game001Mario()
{
    Init();
}

void Game001Mario::Init()
{
    game_.begin();
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    anim_timer_ = 0.0f;
}

void Game001Mario::Reset()
{
    game_.resetAll();
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    anim_timer_ = 0.0f;
}

void Game001Mario::Start()
{
    auto s = game_.status();
    if (s.state == mario16::ST_TITLE) {
        mario16::Input in{ mario16::KEY_A, mario16::KEY_A };
        game_.update(0.016f, in);
    } else if (s.state == mario16::ST_PAUSE) {
        Resume();
    } else if (s.state == mario16::ST_GAMEOVER) {
        Reset();
        mario16::Input in{ mario16::KEY_A, mario16::KEY_A };
        game_.update(0.016f, in);
    }
}

void Game001Mario::Pause()
{
    if (game_.status().state == mario16::ST_PLAY) {
        game_.setPaused(true);
    }
}

void Game001Mario::Resume()
{
    if (game_.isPaused()) {
        game_.setPaused(false);
    }
}

void Game001Mario::Update(float dt, uint16_t keys_down, uint16_t keys_pressed)
{
    mario16::Input in;
    in.down = keys_down;
    in.pressed = keys_pressed;
    game_.update(dt, in);

    auto s = game_.status();
    if (s.state == mario16::ST_GAMEOVER || s.state == mario16::ST_DEAD || s.state == mario16::ST_WIN) {
        anim_timer_ += dt;
        if (s.score > high_score_) {
            high_score_ = s.score;
            ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
        }
    } else {
        if (s.score > high_score_) {
            high_score_ = s.score;
        }
    }
}

void Game001Mario::Render(uint8_t* fb_rgb24)
{
    auto s = game_.status();
    if (s.state == mario16::ST_GAMEOVER || s.state == mario16::ST_DEAD || s.state == mario16::ST_WIN) {
        bool is_victory = (s.state == mario16::ST_WIN);
        ArcadeResultScreen::RenderResult(fb_rgb24, is_victory, s.score, high_score_, anim_timer_);
        return;
    }
    game_.render(fb_rgb24);
}

CartridgeStatus Game001Mario::GetStatus() const
{
    auto s = game_.status();
    CartridgeStatus st;
    st.score = s.score;
    st.high_score = high_score_;
    st.lives = s.lives;
    st.progress = s.progress;

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
