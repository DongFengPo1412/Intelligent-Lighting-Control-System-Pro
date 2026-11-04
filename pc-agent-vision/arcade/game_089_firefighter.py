from .b3_helpers import *


class Game089Firefighter(BatchCartridge):
    game_id=89;name='消防灭火';english_name='Firefighter';core_mechanic='Fire grows and spreads on a grid; directional hose jets spend water, a station refills it, and the house must be protected.'
    control_type=3
    def setup(self):
        self.fire=[0]*64
        for p in (14,21,46):self.fire[p]=2
        self.x=1;self.y=6;self.face=0;self.water=(8,6,4)[self.difficulty];self.burned=self.extinguished=0;self.spread=0.
    def tick(self,dt,down,pressed):
        dx,dy=self.direction(down,pressed)
        if dx or dy:self.face=0 if dx>0 else 1 if dx<0 else 2 if dy>0 else 3;self.x=int(clamp(self.x+dx,0,7));self.y=int(clamp(self.y+dy,0,7))
        if pressed&KEY_B and (self.x,self.y)==(1,6):self.water=(8,6,4)[self.difficulty];self.emit_sound('action')
        if pressed&KEY_A and self.water:
            self.water-=1;dx,dy=((1,0),(-1,0),(0,1),(0,-1))[self.face]
            for distance in range(1,4):
                x=self.x+dx*distance;y=self.y+dy*distance
                if 0<=x<8 and 0<=y<8:
                    p=y*8+x
                    if self.fire[p]:self.fire[p]=max(0,self.fire[p]-2);self.extinguished+=self.fire[p]==0
            self.emit_sound('hit')
        self.spread+=dt
        if self.spread>=(1.5,1.,.7)[self.difficulty]:
            self.spread=0.;old=self.fire[:]
            for p,v in enumerate(old):
                if v:
                    self.fire[p]=min(3,self.fire[p]+1)
                    for n in (p+1 if p%8<7 else -1,p-8,p+8,p-1 if p%8 else -1):
                        if 0<=n<64 and not old[n]:self.fire[n]=1;break
        active=sum(v>0 for v in self.fire);self.burned=active
        if not active:self.award(1000+self.water*20);self.finish(True)
        elif self.fire[49] or active>=24 or self.elapsed>(120,90,60)[self.difficulty]:self.finish(False)
    def progress(self):return min(100,self.extinguished*100//3)
    def draw(self,fb):
        for p,v in enumerate(self.fire):
            if v:self.cell(fb,p%8,p//8,(245,150-v*35,30),2,0)
        self.cell(fb,1,6,(50,160,235),2,0);self.px(fb,self.x*2,self.y*2,(245,245,245))
        for i in range(self.water):self.px(fb,i,15,(70,180,245))
