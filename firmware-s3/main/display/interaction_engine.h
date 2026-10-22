#pragma once
#include "display_hal.h"

// All operations run inside DisplayManager's render-state lock.
class InteractionEngine {
public:
    void Reset();
    void FeedHand(float x, float y, float z, bool pinch, bool visible);
    void FeedMusic(float energy, float flux, bool onset, float tempo,float phase=0);
    void SetPixel(int x, int y, ColorRGB color);
    void ClearCanvas();
    uint32_t Render(DisplayMode mode);
    void Celebrate() { celebration_ms_=get_millis();celebrating_=true; }
    bool RenderCelebration();
private:
    ColorRGB canvas_[256] = {};
    float wave_[16][16] = {}, previous_[16][16] = {};
    float x_ = 7.5f, y_ = 7.5f, vx_ = 0, vy_ = 0;
    float hand_x_ = 7.5f, hand_y_ = 7.5f, hand_z_ = 0, energy_ = 0, flux_ = 0, tempo_ = 120;
    bool grabbed_ = false, had_hand_ = false;
    uint32_t hand_ms_ = 0, step_ms_ = 0, start_ms_ = 0;
    uint32_t music_ms_=0;
    uint32_t onset_ms_=0;
    bool has_onset_=false;
    float music_phase_=0;
    uint32_t celebration_ms_=0;
    bool celebrating_=false;
    void Ripple(int x, int y, float strength);
};
