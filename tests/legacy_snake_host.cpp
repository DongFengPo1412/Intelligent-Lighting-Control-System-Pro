// Production legacy GameEngine rules with a clock/display adapter, not hardware.
#include <cassert>
#include <iostream>
#include "game_engine.h"
static int64_t clock_ms=1000;
int64_t esp_timer_get_time(){return clock_ms*1000;}
uint32_t esp_random(){return 0;} // deterministic food at (0,0)
DisplayHAL& DisplayHAL::GetInstance(){static DisplayHAL hal;return hal;}
static void step(GameEngine& game){clock_ms+=1000;game.RunSnake();}
int main(){
    GameEngine game;
    // Legal input-only paths reach all four walls. No state injection.
    for(int side=0;side<4;++side){
        game.InitSnake();
        if(side==1)game.SnakeSetDirection(0,-1);
        if(side==2)game.SnakeSetDirection(0,1);
        if(side==3){game.SnakeSetDirection(0,-1);step(game);game.SnakeSetDirection(-1,0);}
        int safe_steps=side==0?10:side==1?7:side==2?8:5;
        for(int i=0;i<safe_steps;++i){step(game);assert(!game.IsSnakeGameOver());}
        step(game);assert(game.IsSnakeGameOver());
        game.RunSnake();assert(game.IsSnakeGameOver()); // result is stable
        game.InitSnake();assert(!game.IsSnakeGameOver());assert(game.GetSnakeScore()==0);
    }
    // Reverse input is ignored, rather than turning into the body.
    game.InitSnake();game.SnakeSetDirection(-1,0);step(game);assert(!game.IsSnakeGameOver());
    game.InitSnake();game.SnakeSetDirection(0,-1);
    for(int i=0;i<7;++i)step(game);
    game.SnakeSetDirection(-1,0);for(int i=0;i<5;++i)step(game);
    assert(game.GetSnakeScore()==1);
    game.SnakeSetDirection(0,1);step(game);
    game.SnakeSetDirection(1,0);for(int i=0;i<4;++i)step(game);
    game.SnakeSetDirection(0,-1);step(game);
    assert(game.GetSnakeScore()==2);
    game.SnakeSetDirection(-1,0);step(game);
    game.SnakeSetDirection(0,1);step(game);
    assert(game.IsSnakeGameOver());
    std::cout<<"Legacy Snake: four wall collisions, restart, result and reverse-input contracts passed\n";
}
