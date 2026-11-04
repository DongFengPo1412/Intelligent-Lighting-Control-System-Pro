from .b3_helpers import *


class Game096IceMaze(BatchCartridge):
    game_id=96;name='冰面滑行迷宫';english_name='Ice Maze';core_mechanic='A directional push slides until a wall, not just one tile; reach the exit at rest before the slide budget expires.'
    control_type=2
    MAP=('#######','#..#..#','#.....#','##.#..#','#..#..#','#.....#','#######')
    def setup(self):self.x=1;self.y=5;self.dx=self.dy=self.moves=0;self.clock=0.;self.sliding=False
    def tick(self,dt,down,pressed):
        if not self.sliding:
            dx,dy=self.direction(down,pressed)
            if (dx or dy) and self.MAP[self.y+dy][self.x+dx]!='#':self.dx=dx;self.dy=dy;self.sliding=True;self.moves+=1;self.emit_sound('action')
        if self.sliding:
            self.clock+=dt
            if self.clock>=.06:
                self.clock=0.;nx=self.x+self.dx;ny=self.y+self.dy
                if self.MAP[ny][nx]=='#':self.sliding=False
                else:self.x=nx;self.y=ny
        if not self.sliding and (self.x,self.y)==(5,1):self.award(1500-self.moves*20);self.finish(True)
        elif (not self.sliding and self.moves>=(16,12,8)[self.difficulty]) or self.elapsed>(90,70,50)[self.difficulty]:self.finish(False)
    def progress(self):return 100 if self.state==STATE_VICTORY else min(80,self.moves*5)
    def draw(self,fb):
        for y,row in enumerate(self.MAP):
            for x,v in enumerate(row):self.cell(fb,x,y,(80,95,115) if v=='#' else (20,65,95),2,1)
        self.cell(fb,5,1,(65,215,130),2,1);self.cell(fb,self.x,self.y,(245,245,255),2,1)
