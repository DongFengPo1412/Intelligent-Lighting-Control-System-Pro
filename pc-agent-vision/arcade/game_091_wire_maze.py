from .b3_helpers import *


class Game091WireMaze(BatchCartridge):
    game_id=91;name='电线迷宫';english_name='Wire Maze';core_mechanic='Guide an electrical contact along a one-pixel conducting wire; touching a non-wire cell breaks the circuit.'
    control_type=2
    def setup(self):
        self.wire=[False]*256;self.x=2;self.y=13;self.steps=0;points=((2,13),(2,9),(7,9),(7,12),(12,12),(12,3),(5,3),(5,6),(3,6),(3,1),(13,1))
        for (x,y),(tx,ty) in zip(points,points[1:]):
            while (x,y)!=(tx,ty):self.wire[y*16+x]=True;x+=(tx>x)-(tx<x);y+=(ty>y)-(ty<y)
            self.wire[y*16+x]=True
    def tick(self,dt,down,pressed):
        dx,dy=self.direction(down,pressed)
        if dx or dy:
            x=self.x+dx;y=self.y+dy
            if not(0<=x<16 and 0<=y<16) or not self.wire[y*16+x]:self.emit_sound('collision');self.finish(False);return
            self.x=x;self.y=y;self.steps+=1;self.award(2);self.emit_sound('action')
        if (self.x,self.y)==(13,1):self.award(1000);self.finish(True)
        elif self.elapsed>(60,40,25)[self.difficulty]:self.finish(False)
    def progress(self):return 100 if self.state==STATE_VICTORY else min(90,self.steps)
    def draw(self,fb):
        for p,v in enumerate(self.wire):
            if v:self.px(fb,p%16,p//16,(65,135,170))
        self.px(fb,13,1,(60,245,100));self.px(fb,self.x,self.y,(255,245,120))
