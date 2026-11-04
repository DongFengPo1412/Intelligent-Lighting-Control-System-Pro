#pragma once
#include "arcade_cartridge.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <utility>
namespace arcade {
// Shared lifecycle only. Each game owns its rules, world and collision model.
class BatchCartridge : public Cartridge {
  public:
    bool SupportsDifficulty() const override { return true; }
    uint16_t GetReleaseYear() const override { return 2026; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }
    void Init() override { Reset(); }
    void Reset() override {
        high_ = ArcadeScoreStore::LoadHighScore(GetId());
        state_ = STATE_TITLE;
        score_ = 0;
        elapsed_ = timer_ = repeat_ = 0;
        Setup();
    }
    void Start() override {
        if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
            Reset();
            state_ = STATE_PLAYING;
        }
    }
    void Pause() override {
        if (state_ == STATE_PLAYING)
            state_ = STATE_PAUSED;
    }
    void Resume() override {
        if (state_ == STATE_PAUSED)
            state_ = STATE_PLAYING;
    }
    void Update(float dt, uint16_t down, uint16_t pressed) override {
        if (!std::isfinite(dt))
            return;
        dt = std::max(0.f, std::min(.05f, dt));
        down &= 255;
        pressed &= 255;
        if (state_ == STATE_PAUSED)
            return;
        if (state_ == STATE_TITLE) {
            if (pressed & 127)
                Start();
            return;
        }
        if (state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
            timer_ += dt;
            if (timer_ > .5f && (pressed & 127))
                Start();
            return;
        }
        if (pressed & KEY_START) {
            Pause();
            return;
        }
        // Preserve the canonical microsecond step in long timed challenges.
        elapsed_ += std::round(double(dt) * 1000000.0) / 1000000.0;
        repeat_ = std::max(0.f, repeat_ - dt);
        Tick(dt, down, pressed);
    }
    void Render(uint8_t *fb) override {
        if ((state_ == STATE_VICTORY || state_ == STATE_GAMEOVER) && timer_ > .8f) {
            ArcadeResultScreen::RenderResult(fb, state_ == STATE_VICTORY, score_, high_, timer_);
            return;
        }
        memset(fb, 0, 768);
        Draw(fb);
        if (state_ == STATE_PAUSED)
            for (int y = 5; y < 10; ++y) {
                Px(fb, 6, y, 255, 255, 255);
                Px(fb, 9, y, 255, 255, 255);
            }
    }
    CartridgeStatus GetStatus() const override {
        CartridgeStatus s;
        s.score = score_;
        s.high_score = high_;
        s.state = state_;
        s.lives = state_ == STATE_GAMEOVER ? 0 : 1;
        s.progress = uint8_t(std::max(0, std::min(100, Progress())));
        return s;
    }

  protected:
    CartridgeState state_ = STATE_TITLE;
    uint32_t score_ = 0, high_ = 0;
    double elapsed_ = 0;
    float timer_ = 0, repeat_ = 0;
    virtual void Setup() = 0;
    virtual void Tick(float, uint16_t, uint16_t) = 0;
    virtual void Draw(uint8_t *) = 0;
    virtual int Progress() const = 0;
    void Finish(bool won) {
        state_ = won ? STATE_VICTORY : STATE_GAMEOVER;
        timer_ = 0;
    }
    void Award(unsigned score) {
        score_ += score;
        if (score_ > high_) {
            high_ = score_;
            ArcadeScoreStore::SaveHighScore(GetId(), high_);
        }
    }
    void Direction(uint16_t down, uint16_t pressed, int &dx, int &dy) {
        auto keys = pressed & 15;
        if (!keys && repeat_ <= 0)
            keys = down & 15;
        if (keys)
            repeat_ = .12f;
        dx = dy = 0;
        if (keys & KEY_LEFT)
            dx = -1;
        else if (keys & KEY_RIGHT)
            dx = 1;
        else if (keys & KEY_UP)
            dy = -1;
        else if (keys & KEY_DOWN)
            dy = 1;
    }
    static void Px(uint8_t *fb, int x, int y, int r, int g, int b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int i = (y * 16 + x) * 3;
            fb[i] = r;
            fb[i + 1] = g;
            fb[i + 2] = b;
        }
    }
    static void Cell(uint8_t *fb, int x, int y, int r, int g, int b, int scale = 2,
                     int offset = 2) {
        for (int j = 0; j < scale; ++j)
            for (int i = 0; i < scale; ++i)
                Px(fb, offset + x * scale + i, offset + y * scale + j, r, g, b);
    }
};
} // namespace arcade
