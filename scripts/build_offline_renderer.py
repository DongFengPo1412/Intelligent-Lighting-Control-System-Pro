"""Compile real firmware display engines to a hardware-free WASM renderer.

Requires Clang/WebAssembly and a WASI/Emscripten sysroot. All copied sources,
stubs and binaries are written to an explicit directory outside the repository.
The generated module is consumed by pc-agent-vision/offline_renderer.js.
"""

import argparse
from pathlib import Path
import shutil
import subprocess


HAL = r"""
#pragma once
#include "display_types.h"
#include "font_5x3.h"
class DisplayHAL {
public:
    ColorRGB buffer[256]={};
    static DisplayHAL& GetInstance();
    void Clear(){for(int i=0;i<256;i++)buffer[i]=ColorRGB();}
    void SetPixel(int x,int y,const ColorRGB& c){if(x>=0&&x<16&&y>=0&&y<16)buffer[y*16+x]=c;}
    ColorRGB GetPixel(int x,int y){return x>=0&&x<16&&y>=0&&y<16?buffer[y*16+x]:ColorRGB();}
    void FillSolid(ColorRGB c){for(int i=0;i<256;i++)buffer[i]=c;}
    void FadeToBlackBy(uint8_t n){fade_to_black_by(buffer,256,n);}
    void DrawDigit(int n,int x,int y,const ColorRGB& c){if(n<0||n>9)return;for(int r=0;r<5;r++)for(int k=0;k<3;k++)if(numFont5x3[n][r]&(1<<(2-k)))SetPixel(x+k,y+r,c);}
    ColorRGB* GetBuffer(){return buffer;}
    void Show(uint8_t brightness=100,bool srgb=false){}
};
"""

DRIVER = r"""
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <algorithm>
#include <cmath>
extern "C" void* memset(void*p,int c,size_t n){auto*q=(unsigned char*)p;for(size_t i=0;i<n;i++)q[i]=c;return p;}
extern "C" void* memcpy(void*p,const void*s,size_t n){auto*q=(unsigned char*)p;auto*r=(const unsigned char*)s;for(size_t i=0;i<n;i++)q[i]=r[i];return p;}
extern "C" int strncmp(const char*a,const char*b,size_t n){for(size_t i=0;i<n;i++){unsigned char x=a[i],y=b[i];if(x!=y)return x-y;if(!x)return 0;}return 0;}
static uint32_t now_ms=1000,seed=12345;
uint32_t esp_random(){seed=1664525*seed+1013904223;return seed;}
int64_t esp_timer_get_time(){return (int64_t)now_ms*1000;}
#define private public
#include "effect_engine.h"
#include "game_engine.h"
#include "spectrum_engine.h"
#include "interaction_engine.h"
#include "fingertip_tracker.h"
#undef private
DisplayHAL fake;
DisplayHAL& DisplayHAL::GetInstance(){return fake;}
#include "effect_engine.cc"
#include "game_engine.cc"
#include "spectrum_engine.cc"
#include "interaction_engine.cc"
#include "fingertip_tracker.cc"
static EffectEngine effect;
static GameEngine game;
static SpectrumEngine spectrum;
static InteractionEngine interaction;
static FingertipTracker finger;
static int last_mode=-1;
static float music_bands[16]={};static bool pending_music_bands=false;
extern "C" void set_clock(int n){now_ms=(uint32_t)n;}
extern "C" void input(int kind,float a,float b,float c,float d,float e){
    switch(kind){
    case 1:finger.FeedTarget(a,b,c!=0,d);break;
    case 2:interaction.FeedHand(a,b,c,d!=0,e!=0);break;
    case 3:interaction.FeedMusic(a,b,c!=0,d,e,pending_music_bands?music_bands:nullptr);pending_music_bands=false;break;
    case 4:interaction.SetPixel((int)a%16,(int)a/16,ColorRGB(b,c,d));break;
    case 5:game.SnakeSetDirection(a,b);break;
    case 6:if(a==0)game.TetrisMove(-1);else if(a==1)game.TetrisMove(1);else if(a==2)game.TetrisRotate();else game.TetrisDrop();break;
    case 7:effect.FeedPet(a,b,c!=0,d!=0);break;
    case 8:game.ConfigureDifficulty(a,b!=0);break;
    case 9:game.FeedPerformance(a,b,c!=0);break;
    case 10:interaction.Celebrate();break;
    case 11:finger.SetInputWindow(a,b,c,d);break;
    case 12:finger.SetInvert(a!=0,b!=0);break;
    case 13:if(a>=0&&a<16){music_bands[(int)a]=b/15.f;pending_music_bands=true;}break;
    }
}
extern "C" int render(int mode,int time){
    set_clock(time);
    if(mode!=last_mode){
        fake.Clear();
        if(mode==19)game.InitSnake();else if(mode==21)game.InitTetris();
        else if(mode==15)spectrum.Reset();else if(mode==26)finger.Reset();
        else if(mode>=27)interaction.Reset();
        last_mode=mode;
    }
    if(mode==17&&interaction.RenderCelebration())return (int)fake.buffer;
    if(mode==19){game.RunSnake();if(game.IsSnakeGameOver())game.DrawScore(game.GetSnakeScore());}
    else if(mode==20)game.DrawScore(game.GetSnakeScore());
    else if(mode==21){game.RunTetris();if(game.IsTetrisGameOver())game.DrawScore(game.GetTetrisScore());}
    else if(mode==22)game.DrawScore(game.GetTetrisScore());
    else if(mode==15)spectrum.RenderFrame();
    else if(mode==26)finger.RenderFrame();
    else if(mode>=27)interaction.Render((DisplayMode)mode);
    else effect.RenderFrame((DisplayMode)mode);
    return (int)fake.buffer;
}
extern "C" void band(int index,int value,int beat){static int bands[16]={};if(index<0||index>15)return;bands[index]=value;if(index==15)spectrum.FeedBands(beat,bands);}
extern "C" int run_tests(){
    GameEngine g;g.ConfigureDifficulty(.8f,false);g.FeedPerformance(100,0,true);
    if(fabsf(g.GetDifficulty()-.8f)>.001f)return 1;
    g.ConfigureDifficulty(.5f,true);for(int i=0;i<100;i++)g.FeedPerformance(100,0,true);
    if(g.GetDifficulty()!=1||g.EffectiveDelay(80,80)!=80)return 2;
    for(int i=0;i<100;i++)g.FeedPerformance(1000,1,false);
    if(g.GetDifficulty()!=0||g.EffectiveDelay(450,80)<600)return 3;
    InteractionEngine x;x.Reset();x.SetPixel(3,4,ColorRGB(12,34,56));x.Render(DisplayMode::PIXEL_CANVAS);
    if(fake.GetPixel(3,4).g!=34||fake.GetPixel(0,0).r!=0)return 4;
    x.Reset();x.Render(DisplayMode::PIXEL_CANVAS);if(fake.GetPixel(3,4).b!=56)return 5;
    x.FeedHand(1,0,0,true,true);if(x.x_!=15||x.y_!=0||!x.grabbed_)return 6;
    now_ms+=20;x.FeedHand(.5f,.5f,-.2f,false,true);
    for(int i=0;i<500;i++){now_ms+=16;x.Render(DisplayMode::LIGHT_SANDBOX);}
    if(!std::isfinite(x.x_)||x.x_<0||x.x_>15||x.y_<0||x.y_>15)return 7;
    x.FeedMusic(1,.5f,true,120,.25f);now_ms+=1000;
    for(int i=0;i<200;i++){now_ms+=16;x.Render(DisplayMode::MUSIC_FLUID);}
    if(x.energy_>.0001f)return 8;
    x.Celebrate();if(!x.RenderCelebration())return 9;now_ms+=2401;if(x.RenderCelebration())return 10;
    FingertipTracker f;f.SetInvert(true,false);f.FeedTarget(0,1,true,1);
    if(f.target_x_!=15||f.target_y_!=15)return 11;
    f.RenderFrame();now_ms+=6000;f.RenderFrame();if(fake.GetPixel(15,15).r!=0)return 12;
    EffectEngine p;p.FeedPet(12,0,true,false);p.RenderFrame(DisplayMode::KURISU_DESK_PET);
    for(int y=0;y<16;y++)for(int x=0;x<16;x++){auto a=fake.GetPixel(x,y),b=KURISU_FRAME_IDLE[y][x];if(a.r!=b.r||a.g!=b.g||a.b!=b.b)return 13;}
    p.FeedPet(1,0,true,false);p.RenderFrame(DisplayMode::KURISU_DESK_PET);
    if(fake.GetPixel(7,0).r>KURISU_FRAME_IDLE[0][7].r)return 14;
    return 0;
}
"""


def build(clang, sysroot, out):
    root = Path(__file__).resolve().parents[1]
    out = Path(out).resolve()
    sysroot = Path(sysroot).resolve()
    if out == root or root in out.parents:
        raise ValueError("Output must be outside the repository")
    out.mkdir(parents=True, exist_ok=True)
    source = root / "firmware-s3/main/display"
    for stem in (
        "effect_engine",
        "game_engine",
        "spectrum_engine",
        "interaction_engine",
        "fingertip_tracker",
    ):
        for suffix in (".h", ".cc"):
            shutil.copyfile(source / (stem + suffix), out / (stem + suffix))
    for name in (
        "display_types.h",
        "matrix_layout.h",
        "font_5x3.h",
        "kurisu_sprites.h",
        "spectrum_packet.h",
    ):
        shutil.copyfile(source / name, out / name)
    (out / "display_hal.h").write_text(HAL)
    (out / "esp_random.h").write_text("#pragma once\n#include <stdint.h>\nuint32_t esp_random();\n")
    (out / "esp_timer.h").write_text(
        "#pragma once\n#include <stdint.h>\nint64_t esp_timer_get_time();\n"
    )
    (out / "audio_hal.h").write_text(
        "#pragma once\nclass AudioHAL {public:static AudioHAL& GetInstance(){static AudioHAL a;return a;}bool IsSpeakerEnabled(){return false;}};\n"
    )
    (out / "freertos").mkdir(exist_ok=True)
    (out / "freertos/FreeRTOS.h").write_text(
        "#pragma once\ntypedef int portMUX_TYPE;\n#define portMUX_INITIALIZER_UNLOCKED 0\n#define portENTER_CRITICAL(x) ((void)0)\n#define portEXIT_CRITICAL(x) ((void)0)\n"
    )
    cpp = out / "driver.cpp"
    cpp.write_text(DRIVER)
    command = [
        clang,
        "--target=wasm32",
        "-D_LIBCPP_HAS_NO_THREADS=1",
        "-std=c++17",
        "-O1",
        "-fno-builtin",
        "-fno-exceptions",
        "-fno-rtti",
        "-nostdlib",
        "-nostdinc++",
        "--sysroot=" + str(sysroot),
        "-isystem",
        str(sysroot / "include/c++/v1"),
        "-I",
        str(out),
        "-Wl,--no-entry",
        "-Wl,--allow-undefined",
    ]
    command += [
        "-Wl,--export=" + name
        for name in ("__wasm_call_ctors", "run_tests", "render", "input", "band", "set_clock")
    ]
    import os

    env = os.environ.copy()
    env["TMP"] = env["TEMP"] = str(out)
    subprocess.run(command + [str(cpp), "-o", str(out / "engine.wasm")], check=True, env=env)
    return out / "engine.wasm"


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--clang", required=True)
    p.add_argument("--sysroot", required=True)
    p.add_argument("--output-dir", required=True)
    a = p.parse_args()
    print(build(a.clang, a.sysroot, a.output_dir))
