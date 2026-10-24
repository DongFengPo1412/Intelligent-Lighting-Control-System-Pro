#include "interaction_engine.h"
#include <string.h>
#include <algorithm>
#include <cmath>

namespace {
float bounded(float x, float lo, float hi) { return std::isfinite(x) ? std::max(lo, std::min(hi, x)) : lo; }
}

void InteractionEngine::Reset() {
    celebrating_=false;
    has_onset_=false;energy_=flux_=0;
    smooth_energy_=smooth_flux_=0;music_ms_=onset_ms_=0;
    memset(music_bands_,0,sizeof(music_bands_));memset(smooth_bands_,0,sizeof(smooth_bands_));
    memset(wave_, 0, sizeof(wave_)); memset(previous_, 0, sizeof(previous_));
    x_=y_=7.5f; vx_=vy_=0; grabbed_=had_hand_=false;
    start_ms_=step_ms_=get_millis();
}
void InteractionEngine::FeedHand(float x, float y, float z, bool pinch, bool visible) {
    uint32_t now=get_millis();
    if (!visible) { grabbed_=false; had_hand_=false; return; }
    float nx=bounded(x,0,1)*15, ny=bounded(y,0,1)*15;
    float dt=std::max(.01f, (now-hand_ms_)/1000.f);
    if (grabbed_ && !pinch) {
        vx_=bounded((nx-hand_x_)/dt,-35,35); vy_=bounded((ny-hand_y_)/dt,-35,35);
        // Relative landmark z is a gesture cue, not metric depth.
        if (z < hand_z_-.02f) vy_-=8;
    }
    hand_x_=nx; hand_y_=ny; hand_z_=bounded(z,-2,2); hand_ms_=now;
    grabbed_=pinch; had_hand_=true;
    if (grabbed_) { x_=nx; y_=ny; vx_=vy_=0; }
}
void InteractionEngine::Ripple(int x,int y,float strength) {
    if(x>0&&x<15&&y>0&&y<15)wave_[y][x]+=bounded(strength,-2,2);
}
void InteractionEngine::FeedMusic(float energy,float flux,bool onset,float tempo,float phase,const float* bands) {
    music_ms_=get_millis();music_phase_=bounded(phase,0,1);
    energy_=bounded(energy,0,1); flux_=bounded(flux,0,1); tempo_=bounded(tempo,30,240);
    for(int i=0;i<16;i++)music_bands_[i]=bands?bounded(bands[i],0,1):energy_;
    if(onset){onset_ms_=music_ms_;has_onset_=true;}
}
void InteractionEngine::SetPixel(int x,int y,ColorRGB color) { if(x>=0&&x<16&&y>=0&&y<16)canvas_[y*16+x]=color; }
void InteractionEngine::ClearCanvas() { memset(canvas_,0,sizeof(canvas_)); }

bool InteractionEngine::RenderCelebration() {
    if(!celebrating_)return false;
    uint32_t elapsed=get_millis()-celebration_ms_;
    if(elapsed>=2400){celebrating_=false;return false;}
    auto& hal=DisplayHAL::GetInstance();hal.Clear();
    for(int burst=0;burst<3;burst++) {
        int age=(int)elapsed-burst*400;if(age<0||age>1400)continue;
        float t=age/1000.f;
        for(int ray=0;ray<12;ray++) {
            float angle=ray*6.283185f/12;
            int x=(int)roundf(4+burst*4+cosf(angle)*t*5);
            int y=(int)roundf(6+sinf(angle)*t*5+1.5f*t*t);
            uint8_t level=(uint8_t)bounded(255*(1-t/1.4f),0,255);
            hal.SetPixel(x,y,hsv2rgb_fast(ColorHSV(burst*80+ray*3,220,level)));
        }
    }
    hal.Show();return true;
}

uint32_t InteractionEngine::Render(DisplayMode mode) {
    auto& hal=DisplayHAL::GetInstance(); uint32_t now=get_millis();
    float dt=bounded((now-step_ms_)/1000.f,.001f,.05f); step_ms_=now;
    if(now-music_ms_>300){
        const float decay=expf(-dt*8);energy_*=decay;flux_*=decay;
        for(float& band:music_bands_)band*=decay;
    }
    if(had_hand_ && now-hand_ms_>500){grabbed_=had_hand_=false;}
    hal.Clear();
    if(mode==DisplayMode::PIXEL_CANVAS) {
        for(int y=0;y<16;y++)for(int x=0;x<16;x++)hal.SetPixel(x,y,canvas_[y*16+x]);
    } else if(mode==DisplayMode::WORLDLINE) {
        const int locked[]={1,0,4,8,5,9,6};
        bool rolling=now-start_ms_<3000;
        for(int i=0;i<7;i++) {
            int digit=rolling ? ((now/65+i*7)%10) : locked[i];
            hal.DrawDigit(digit, i<4 ? i*4 : 2+(i-4)*4, i<4 ? 1 : 9, ColorRGB(255,90,5));
        }
        hal.SetPixel(3,6,ColorRGB(255,90,5));
        const uint8_t percent[5]={5,1,2,4,5};
        for(int y=0;y<5;y++)for(int x=0;x<3;x++)if(percent[y]&(1<<(2-x)))hal.SetPixel(13+x,9+y,ColorRGB(255,90,5));
    } else if(mode==DisplayMode::AMBIENT) {
        uint8_t v=beatsin8(6,8,45);
        hal.FillSolid(ColorRGB(v,v/3,0));
    } else if(mode==DisplayMode::MUSIC_FLUID) {
        // One coherent, deterministic light field: spectrum selects radius,
        // musical phase moves the field, and detected attacks launch a ring.
        const float attack=1-expf(-dt/.025f),release=1-expf(-dt/.16f);
        smooth_energy_+=(energy_-smooth_energy_)*(energy_>smooth_energy_?attack:release);
        smooth_flux_+=(flux_-smooth_flux_)*release;
        for(int i=0;i<16;i++)smooth_bands_[i]+=(music_bands_[i]-smooth_bands_[i])*
            (music_bands_[i]>smooth_bands_[i]?attack:release);
        const float level=sqrtf(bounded(smooth_energy_,0,1));
        const float phase=music_phase_+(now-music_ms_)*tempo_/60000.f;
        const float age=has_onset_?(now-onset_ms_)/1000.f:1000.f;
        const float hit=age<.75f?(1-age/.75f)*bounded(level*1.8f+smooth_flux_*.15f,0,1):0;
        for(int y=0;y<16;y++)for(int x=0;x<16;x++) {
            const float radius=std::max(fabsf(x-7.5f),fabsf(y-7.5f));
            const int band=std::min(14,(int)((radius-.5f)*2));
            const float spectrum=std::max(smooth_bands_[band],smooth_bands_[band+1]);
            const float flow=.5f+.5f*cosf(radius*1.25f-phase*6.283185f);
            const float distance=radius-(.25f+age*12);
            const float pulse=hit*expf(-distance*distance/1.1f);
            float value=.10f*smooth_energy_+spectrum*level*.85f*(.18f+.82f*flow);
            value=std::max(value,pulse*.95f);
            if(smooth_energy_<.002f && age>.75f)value=0;
            const uint8_t hue=(uint8_t)(220-radius/7.5f*100+smooth_flux_*18);
            hal.SetPixel(x,y,hsv2rgb_fast(ColorHSV(hue,(uint8_t)(235-pulse*30),
                (uint8_t)(bounded(value,0,1)*255))));
        }
    } else {
        if(mode==DisplayMode::LIGHT_SANDBOX && !grabbed_) {
            vy_+=4*dt; x_+=vx_*dt; y_+=vy_*dt;
            if(x_<0||x_>15){x_=bounded(x_,0,15);vx_=-vx_*.8f;Ripple((int)bounded(x_,1,14),(int)bounded(y_,1,14),1);}
            if(y_<0||y_>15){y_=bounded(y_,0,15);vy_=-vy_*.8f;Ripple((int)bounded(x_,1,14),(int)bounded(y_,1,14),1);}
            vx_*=.997f;
        }
        float next[16][16]={};
        for(int y=1;y<15;y++)for(int x=1;x<15;x++)
            next[y][x]=bounded(((wave_[y-1][x]+wave_[y+1][x]+wave_[y][x-1]+wave_[y][x+1])*.5f-previous_[y][x])*.97f,-3,3);
        memcpy(previous_,wave_,sizeof(wave_));memcpy(wave_,next,sizeof(wave_));
        for(int y=0;y<16;y++)for(int x=0;x<16;x++) {
            float v=bounded(fabsf(wave_[y][x]),0,1);
            hal.SetPixel(x,y,hsv2rgb_fast(ColorHSV((uint8_t)(150+x*3+flux_*70),220,(uint8_t)(v*255))));
        }
        if(mode==DisplayMode::LIGHT_SANDBOX) {
            hal.SetPixel((int)roundf(x_),(int)roundf(y_),grabbed_?ColorRGB(255,90,200):ColorRGB(150,240,255));
        }
    }
    hal.Show(); return 16;
}
