from .b3_helpers import *


class Game025MarbleMaze(BatchCartridge):
    game_id=25;name='滚珠平衡迷宫';english_name='Marble Maze';core_mechanic='Tilt acceleration and inertia, wall bounces, lethal pits and a low-speed finish.'
    control_type=3
    def setup(self):
        self.x=2.;self.y=2.;self.vx=self.vy=0.;self.grid=[[1 if x in (0,15) or y in (0,15) else 0 for x in range(16)] for y in range(16)]
        for y in range(1,12):self.grid[y][5]=0 if y==7 else 1
        for y in range(4,15):self.grid[y][10]=0 if y==10 else 1
    def tick(self,dt,down,pressed):
        keys=down|pressed;acc=(4,5,6)[self.difficulty];drag=10 if keys&KEY_A else 2
        self.vx=(self.vx+acc*dt*(bool(keys&KEY_RIGHT)-bool(keys&KEY_LEFT)))*max(0,1-drag*dt);self.vy=(self.vy+acc*dt*(bool(keys&KEY_DOWN)-bool(keys&KEY_UP)))*max(0,1-drag*dt)
        nx=clamp(self.x+self.vx*dt,.5,14.5);ny=clamp(self.y+self.vy*dt,.5,14.5)
        if self.grid[round(self.y)][round(nx)]:self.vx=-self.vx*.35;self.emit_sound('collision')
        else:self.x=nx
        if self.grid[round(ny)][round(self.x)]:self.vy=-self.vy*.35
        else:self.y=ny
        if any(math.hypot(self.x-px,self.y-py)<.55 for px,py in ((3,10),(8,4),(12,7))):self.finish(False)
        elif math.hypot(self.x-13,self.y-13)<.7 and math.hypot(self.vx,self.vy)<1.2:self.award(1000);self.finish(True)
        elif self.elapsed>(100,80,60)[self.difficulty]:self.finish(False)
    def progress(self):return int((self.x+self.y-4)/22*100)
    def draw(self,fb):
        for y in range(16):
            for x in range(16):
                if self.grid[y][x]:self.px(fb,x,y,(70,95,120))
        for x,y in ((3,10),(8,4),(12,7)):self.px(fb,x,y,(230,45,75))
        self.px(fb,13,13,(40,230,100));self.px(fb,round(self.x),round(self.y),(245,245,255))
