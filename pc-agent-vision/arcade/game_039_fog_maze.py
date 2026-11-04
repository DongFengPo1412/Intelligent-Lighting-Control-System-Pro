from .b3_helpers import *


class Game039FogMaze(BatchCartridge):
    game_id=39;name='迷雾探索迷宫';english_name='Fog Maze';core_mechanic='A deterministic perfect maze with restricted vision, remembered explored walls and a hidden exit.'
    control_type=2
    def setup(self):
        self.x=self.y=1;self.moves=0;self.explored=1;self.grid=[[1]*16 for _ in range(16)];self.seen=[[False]*16 for _ in range(16)];self.visited=[[False]*16 for _ in range(16)];self.visited[1][1]=True
        seed=0x39cf;stack=[(1,1)];self.grid[1][1]=0
        while stack:
            x,y=stack[-1];options=[(dx,dy) for dx,dy in ((0,-2),(2,0),(0,2),(-2,0)) if 1<=x+dx<=13 and 1<=y+dy<=13 and self.grid[y+dy][x+dx]]
            if not options:stack.pop();continue
            seed=rng(seed);dx,dy=options[seed%len(options)];self.grid[y+dy//2][x+dx//2]=0;self.grid[y+dy][x+dx]=0;stack.append((x+dx,y+dy))
        self.layout_hash=2166136261
        for row in self.grid:
            for tile in row:self.layout_hash=((self.layout_hash^tile)*16777619)&0xffffffff
    def tick(self,dt,down,pressed):
        dx,dy=self.direction(down,pressed);nx=self.x+dx;ny=self.y+dy
        if (dx or dy) and not self.grid[ny][nx]:
            self.x,self.y=nx,ny;self.moves+=1
            if not self.visited[ny][nx]:self.visited[ny][nx]=True;self.explored+=1;self.emit_sound('action')
        radius=(3,2,1)[self.difficulty]
        for y in range(16):
            for x in range(16):
                if abs(x-self.x)+abs(y-self.y)<=radius:self.seen[y][x]=True
        if (self.x,self.y)==(13,13):self.award(max(100,1500-self.moves*5));self.finish(True)
        elif self.elapsed>(90,70,55)[self.difficulty]:self.finish(False)
    def progress(self):return 100 if self.state==STATE_VICTORY else self.explored*100//97
    def draw(self,fb):
        radius=(3,2,1)[self.difficulty]
        for y in range(16):
            for x in range(16):
                near=abs(x-self.x)+abs(y-self.y)<=radius
                if near or self.seen[y][x]:self.px(fb,x,y,(75,90,110) if near and self.grid[y][x] else (18,24,35) if self.grid[y][x] else (10,30,40))
        if self.seen[13][13]:self.px(fb,13,13,(40,230,100))
        self.px(fb,self.x,self.y,(245,245,255))
