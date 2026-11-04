from .b3_helpers import *


class Game060PortalPuzzle(BatchCartridge):
    game_id=60;name='传送门谜题';english_name='Portal Puzzle';core_mechanic='Linked floor portals cross a sealed wall; a remote switch unlocks the exit gate.'
    control_type=3
    def setup(self):self.x=1;self.y=6;self.moves=self.teleports=0;self.gate=False
    def tick(self,dt,down,pressed):
        dx,dy=self.direction(down,pressed);x=self.x+dx;y=self.y+dy
        if (dx or dy) and 1<=x<=6 and 1<=y<=6 and x!=4 and not (y==3 and x>=5 and not self.gate):self.x=x;self.y=y;self.moves+=1;self.emit_sound('action')
        if pressed&KEY_A and (self.x,self.y) in ((1,1),(6,6)):
            self.x,self.y=(6,6) if self.x==1 else (1,1);self.teleports+=1;self.moves+=1;self.emit_sound('hit')
        if (self.x,self.y)==(5,5):self.gate=True
        if (self.x,self.y)==(6,1) and self.gate:self.award(1500-self.moves*10);self.finish(True)
        elif self.moves>=(60,45,30)[self.difficulty] or self.elapsed>(90,70,50)[self.difficulty]:self.finish(False)
    def progress(self):return 100 if self.state==STATE_VICTORY else 50 if self.gate else 20 if self.teleports else 0
    def draw(self,fb):
        for y in range(8):
            for x in range(8):
                if x in (0,4,7) or y in (0,7) or (y==3 and x>=5 and not self.gate):self.cell(fb,x,y,(70,80,95),2,0)
        self.cell(fb,1,1,(50,120,255),2,0);self.cell(fb,6,6,(245,130,45),2,0);self.cell(fb,5,5,(100,220,160) if self.gate else (180,60,150),2,0);self.cell(fb,6,1,(40,220,80),2,0);self.cell(fb,self.x,self.y,(255,245,160),2,0)
