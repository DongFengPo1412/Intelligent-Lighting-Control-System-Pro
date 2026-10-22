"""Run the real C++ engines against a fake clock/LED HAL, without ESP32 I/O."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def run(a,out):
    source=Path(__file__).parents[1]/'firmware-s3/main/display'
    out.mkdir(parents=True,exist_ok=True)
    for name in ('spectrum_engine.cc','spectrum_engine.h','spectrum_packet.h','game_engine.cc','game_engine.h','display_types.h','matrix_layout.h'):
        shutil.copyfile(source/name,out/name)
    (out/'esp_random.h').write_text('#pragma once\n#include <stdint.h>\nuint32_t esp_random();\n',encoding='utf-8')
    (out/'esp_timer.h').write_text('#pragma once\n#include <stdint.h>\nint64_t esp_timer_get_time();\n',encoding='utf-8')
    (out/'display_hal.h').write_text(r'''
#pragma once
#include "display_types.h"
class DisplayHAL {
public:
  ColorRGB buffer[TOTAL_LEDS]={};
  static DisplayHAL& GetInstance();
  void Clear(){for(int i=0;i<TOTAL_LEDS;++i)buffer[i]=ColorRGB();}
  void SetPixel(int x,int y,const ColorRGB& c){if(x>=0&&x<16&&y>=0&&y<16)buffer[y*16+x]=c;}
  void FadeToBlackBy(uint8_t n){fade_to_black_by(buffer,TOTAL_LEDS,n);}
  void DrawDigit(int,int,int,const ColorRGB&){}
  ColorRGB* GetBuffer(){return buffer;}
  void Show(){}
};
''',encoding='utf-8')
    cpp=r'''
#include <stdint.h>
#include <stddef.h>
#include <string.h>
extern "C" void *memset(void*p,int v,size_t n){unsigned char*q=(unsigned char*)p;for(size_t i=0;i<n;++i)q[i]=v;return p;}
extern "C" void *memcpy(void*p,const void*s,size_t n){unsigned char*q=(unsigned char*)p;const unsigned char*r=(const unsigned char*)s;for(size_t i=0;i<n;++i)q[i]=r[i];return p;}
extern "C" int strncmp(const char*a,const char*b,size_t n){for(size_t i=0;i<n;++i){unsigned char x=a[i],y=b[i];if(x!=y)return (int)x-(int)y;if(!x)return 0;}return 0;}
uint32_t test_now=0;
uint32_t esp_random(){return 0;}
int64_t esp_timer_get_time(){return (int64_t)test_now*1000;}
#define private public
#include "game_engine.h"
#include "spectrum_engine.h"
#undef private
DisplayHAL fake_hal;
DisplayHAL& DisplayHAL::GetInstance(){return fake_hal;}
#include "game_engine.cc"
#include "spectrum_engine.cc"
extern "C" int run_tests(){
  GameEngine game;game.InitSnake();game.snake_len_=255;
  for(int i=0;i<255;i++){game.snake_x_[i]=i%16;game.snake_y_[i]=i/16;}
  if(!game.PlaceSnakeFood()||game.food_x_!=15||game.food_y_!=15)return 1;
  game.snake_x_[255]=15;game.snake_y_[255]=15;game.snake_len_=256;
  if(game.PlaceSnakeFood())return 2;
  game.InitSnake();game.food_x_=6;game.food_y_=7;test_now+=500;game.RunSnake();
  if(game.snake_len_!=4||game.snake_x_[3]!=3||game.snake_y_[3]!=7)return 3;
  game.InitSnake();game.SnakeSetDirection(0,-1);game.SnakeSetDirection(-1,0);
  test_now+=500;game.RunSnake();if(game.snake_dx_!=1||game.snake_dy_!=0)return 4;
  // A late-game speed update cannot undershoot the 80 ms floor.
  game.InitSnake();game.snake_score_=24;game.food_x_=6;game.food_y_=7;
  test_now+=500;game.RunSnake();if(game.snake_speed_ms_!=80)return 5;
  game.InitTetris();game.tetris_speed_ms_=110;game.piece_type_=0;
  game.piece_rot_=0;game.piece_x_=6;game.piece_y_=13;
  for(int x=3;x<=12;++x)game.tetris_field_[15][x]=1;
  test_now+=200;game.RunTetris();if(game.tetris_speed_ms_!=100||game.tetris_score_!=1)return 6;
  SpectrumEngine spectrum;int bands[16]={};bands[1]=15;spectrum.FeedBands(1,bands);
  if(spectrum.bands_[0]>15)return 7;
  int before=spectrum.bands_[1];bands[1]=99;spectrum.FeedBands(0,bands);
  if(spectrum.bands_[1]!=before)return 8;
  // Clock advances without any new packets; peaks and columns must disappear.
  spectrum.RenderFrame();test_now+=501;
  for(int i=0;i<80;++i){spectrum.RenderFrame();test_now+=20;}
  for(int i=0;i<256;++i)if(fake_hal.buffer[i].r||fake_hal.buffer[i].g||fake_hal.buffer[i].b)return 9;
  int beat=0,out[16];
  if(ParseSpectrumPacket("f,0,0",beat,out)||ParseSpectrumPacket("f,0,99,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0",beat,out))return 10;
  if(spectrum.ParseSerialCommand("f,0,0"))return 11;
  return 0;
}
'''
    path=out/'tests.cpp';wasm=out/'tests.wasm';path.write_text(cpp,encoding='utf-8')
    env=os.environ.copy();env['TMP']=env['TEMP']=str(out.resolve())
    subprocess.run([a.clang,'--target=wasm32','-std=c++17','-fno-builtin','-nostdlib','-nostdinc++','--sysroot='+a.sysroot,'-I',str(out),'-Wl,--no-entry','-Wl,--export=run_tests',str(path),'-o',str(wasm)],check=True,env=env)
    js='WebAssembly.instantiate(require("fs").readFileSync(process.argv[1])).then(x=>{let n=x.instance.exports.run_tests();console.log({cases:11,failedCase:n});process.exitCode=n;})'
    subprocess.run([a.node,'-e',js,str(wasm)],check=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--clang',required=True);p.add_argument('--sysroot',required=True);p.add_argument('--node',default='node');p.add_argument('--output-dir');a=p.parse_args()
    if a.output_dir:run(a,Path(a.output_dir))
    else:
        with tempfile.TemporaryDirectory(prefix='lighting-pro-tests-') as t:run(a,Path(t))
