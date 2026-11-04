from .b3_helpers import *


class Game080Tron(BatchCartridge):
    game_id=80;name='光线摩托';english_name='Tron Light Cycles';core_mechanic='Two continuous riders leave solid trails; turning avoids walls and traps the opponent, with a survival milestone.'
    control_type=2
    def setup(self):self.board=[0]*256;self.x=3;self.y=12;self.dir=0;self.ex=12;self.ey=3;self.edir=2;self.steps=0;self.clock=0.;self.board[195]=1;self.board[60]=2;self.board_hash=0
    def tick(self,dt,down,pressed):
        keys=down|pressed
        for k,d in ((KEY_UP,0),(KEY_RIGHT,1),(KEY_DOWN,2),(KEY_LEFT,3)):
            if keys&k and d!=(self.dir+2)%4:self.dir=d;break
        self.clock+=dt
        if self.clock<( .16,.13,.10)[self.difficulty]:return
        self.clock-=(.16,.13,.10)[self.difficulty];delta=((0,-1),(1,0),(0,1),(-1,0))
        for d in (self.edir,(self.edir+1)%4,(self.edir+3)%4):
            dx,dy=delta[d];nx=self.ex+dx;ny=self.ey+dy
            if 1<=nx<=14 and 1<=ny<=14 and not self.board[ny*16+nx]:self.edir=d;break
        dx,dy=delta[self.dir];nx=self.x+dx;ny=self.y+dy;dx,dy=delta[self.edir];mx=self.ex+dx;my=self.ey+dy
        dead=not(1<=nx<=14 and 1<=ny<=14) or (0<=nx<16 and 0<=ny<16 and self.board[ny*16+nx]) or (nx,ny)==(mx,my)
        enemy=not(1<=mx<=14 and 1<=my<=14) or (0<=mx<16 and 0<=my<16 and self.board[my*16+mx])
        if dead:self.finish(False);return
        self.x=nx;self.y=ny;self.board[ny*16+nx]=1;self.steps+=1;self.award(10)
        if enemy or self.steps>=(50,65,80)[self.difficulty]:self.award(500);self.finish(True)
        else:self.ex=mx;self.ey=my;self.board[my*16+mx]=2
        self.board_hash=2166136261
        for v in self.board:self.board_hash=((self.board_hash^v)*16777619)&0xffffffff
    def progress(self):return min(100,self.steps*100//(50,65,80)[self.difficulty])
    def draw(self,fb):
        for p,v in enumerate(self.board):
            if v:self.px(fb,p%16,p//16,(60,160,220) if v==1 else (220,70,125))
        self.px(fb,self.x,self.y,(170,245,255));self.px(fb,self.ex,self.ey,(255,190,190))
