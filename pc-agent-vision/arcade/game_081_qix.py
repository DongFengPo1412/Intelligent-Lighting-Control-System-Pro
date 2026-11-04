from collections import deque
from .batch_cartridge import *


class Game081Qix(BatchCartridge):
    game_id=81;name='Qix圈地';english_name='Qix';core_mechanic='Draw vulnerable trails, close regions and capture the side without the moving enemy.'
    def setup(self):
        self.grid=[[1 if x in (1,14) or y in (1,14) else 0 for x in range(16)] for y in range(16)]
        self.x=1;self.y=8;self.ex=10;self.ey=8;self.vx=-1;self.vy=1;self.enemy_clock=0.;self.armed=False;self.drawing=False;self.claimed=0
    def capture(self):
        seen={(self.ex,self.ey)};todo=deque(seen)
        while todo:
            x,y=todo.popleft()
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                nx,ny=x+dx,y+dy
                if 2<=nx<=13 and 2<=ny<=13 and self.grid[ny][nx]==0 and (nx,ny) not in seen:seen.add((nx,ny));todo.append((nx,ny))
        for y in range(2,14):
            for x in range(2,14):
                if self.grid[y][x]==2 or (self.grid[y][x]==0 and (x,y) not in seen):self.grid[y][x]=1
        self.claimed=sum(self.grid[y][x]==1 for y in range(2,14) for x in range(2,14))
        self.award(10);self.emit_sound('hit');self.drawing=self.armed=False
        if self.claimed*100>=144*(50,60,70)[self.difficulty]:self.award(1000);self.finish(True)
    def tick(self,dt,down,pressed):
        if pressed&KEY_A and not self.drawing:self.armed=not self.armed;self.emit_sound('action')
        dx,dy=self.direction(down,pressed);nx=self.x+dx;ny=self.y+dy
        if (dx or dy) and 1<=nx<=14 and 1<=ny<=14:
            t=self.grid[ny][nx]
            if t==2:self.finish(False);self.emit_sound('collision');return
            if t==1:
                self.x,self.y=nx,ny
                if self.drawing:self.capture()
            elif self.armed:
                self.grid[ny][nx]=2;self.x,self.y=nx,ny;self.drawing=True
        if self.state!=STATE_PLAYING:return
        self.enemy_clock+=dt
        if self.enemy_clock>=(.10,.08,.06)[self.difficulty]:
            self.enemy_clock=0.
            if self.grid[self.ey][self.ex+self.vx]==1:self.vx=-self.vx
            if self.grid[self.ey+self.vy][self.ex]==1:self.vy=-self.vy
            nx=self.ex+self.vx;ny=self.ey+self.vy
            if self.grid[ny][nx]==2:self.emit_sound('collision');self.finish(False);return
            if self.grid[ny][nx]==0:self.ex,self.ey=nx,ny
        if self.elapsed>(90,70,55)[self.difficulty]:self.finish(False)
    def progress(self):return self.claimed*100//144
    def draw(self,fb):
        palette=((7,12,25),(25,90,150),(245,190,30))
        for y in range(1,15):
            for x in range(1,15):self.px(fb,x,y,palette[self.grid[y][x]])
        self.px(fb,self.ex,self.ey,(255,50,130));self.px(fb,self.x,self.y,(255,210,60) if self.armed else (230,255,255))
