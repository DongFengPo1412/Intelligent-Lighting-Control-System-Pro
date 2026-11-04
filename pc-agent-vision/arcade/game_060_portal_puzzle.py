from .b3_helpers import *

class Game060PortalPuzzle(BatchCartridge):
    game_id=60;name='传送门谜题';english_name='Portal Puzzle';core_mechanic='Three linked-portal chambers with distinct switches, obstacles and a per-room move budget.'
    control_type=3
    PORTALS=(((1,1),(6,6)),((3,2),(5,6)),((2,5),(6,4)))
    SWITCHES=((5,5),(6,5),(5,4));EXITS=((6,1),(5,1),(6,1));BLOCKS=(None,(5,4),(6,5))
    def load_stage(self):self.x=1;self.y=6;self.gate=False;self.stage_moves=0
    def setup(self):self.stage=self.moves=self.teleports=0;self.load_stage()
    def wall(self,x,y):return not (1<=x<=6 and 1<=y<=6) or x==4 or (y==3 and x>=5 and not self.gate) or (x,y)==self.BLOCKS[min(self.stage,2)]
    def tick(self,dt,down,pressed):
        dx,dy=self.direction(down,pressed);x=self.x+dx;y=self.y+dy
        if (dx or dy) and not self.wall(x,y):self.x=x;self.y=y;self.moves+=1;self.stage_moves+=1;self.emit_sound('action')
        a,b=self.PORTALS[self.stage]
        if pressed&KEY_A and (self.x,self.y) in (a,b):self.x,self.y=b if (self.x,self.y)==a else a;self.moves+=1;self.stage_moves+=1;self.teleports+=1;self.emit_sound('hit')
        if (self.x,self.y)==self.SWITCHES[self.stage]:self.gate=True
        if (self.x,self.y)==self.EXITS[self.stage] and self.gate:
            self.award(max(100,1500-self.stage_moves*10));self.stage+=1
            if self.stage==3:self.finish(True)
            else:self.load_stage()
        elif self.stage_moves>=(60,45,30)[self.difficulty] or self.elapsed>(270,210,150)[self.difficulty]:self.finish(False)
    def progress(self):return min(100,self.stage*100//3+(16 if self.gate else 0))
    def draw(self,fb):
        shown=min(self.stage,2)
        for y in range(8):
            for x in range(8):
                if self.wall(x,y):self.cell(fb,x,y,(70,80,95),2,0)
        for p,c in zip(self.PORTALS[shown],((50,120,255),(245,130,45))):self.cell(fb,*p,c,2,0)
        self.cell(fb,*self.SWITCHES[shown],(100,220,160) if self.gate else (180,60,150),2,0);self.cell(fb,*self.EXITS[shown],(40,220,80),2,0);self.cell(fb,self.x,self.y,(255,245,160),2,0)
