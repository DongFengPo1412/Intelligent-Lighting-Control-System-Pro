from .b3_helpers import *
import secrets


class Game100MemoryMatch(BatchCartridge):
    game_id=100;name='翻牌配对';english_name='Memory Match';core_mechanic='Reveal two hidden cards, remember mismatches, and clear eight pairs before the turn or time budget.'
    control_type=3
    def set_replay_seed(self,seed):
        if type(seed) is not int or not 0<=seed<=0xffffffff:return False
        self._replay_seed=seed;return True
    def use_random_seeds(self):self._replay_seed=None
    def setup(self):
        self.cards=[i//2 for i in range(16)];seed=getattr(self,'_replay_seed',None)
        if seed is None:
            seed=secrets.randbits(32)
            if seed==getattr(self,'_last_seed',None):seed=(seed+1)&0xffffffff
        self._last_seed=seed
        for i in range(15,0,-1):seed=rng(seed);j=(seed>>16)%(i+1);self.cards[i],self.cards[j]=self.cards[j],self.cards[i]
        self.x=self.y=self.pairs=self.turns=self.matched=0;self.first=self.second=-1;self.wait=0.
    def tick(self,dt,down,pressed):
        if self.wait>0:
            self.wait=max(0.,self.wait-dt)
            if not self.wait:self.first=self.second=-1
        else:
            dx,dy=self.direction(down,pressed);self.x=int(clamp(self.x+dx,0,3));self.y=int(clamp(self.y+dy,0,3));p=self.y*4+self.x
            if pressed&KEY_A and not self.matched&(1<<p) and p!=self.first:
                if self.first<0:self.first=p;self.emit_sound('action')
                else:
                    self.second=p;self.turns+=1
                    if self.cards[p]==self.cards[self.first]:self.matched|=(1<<p)|(1<<self.first);self.pairs+=1;self.award(100);self.emit_sound('hit');self.first=self.second=-1
                    else:self.wait=.5;self.emit_sound('collision')
        if self.pairs==8:self.award(max(0,500-self.turns*10));self.finish(True)
        elif (not self.wait and self.turns>=(24,20,16)[self.difficulty]) or self.elapsed>(180,120,90)[self.difficulty]:self.finish(False)
    def progress(self):return self.pairs*100//8
    def draw(self,fb):
        colors=((235,70,85),(70,170,235),(80,215,115),(240,195,60),(165,90,230),(240,135,65),(60,210,205),(190,140,180))
        for p,v in enumerate(self.cards):self.cell(fb,p%4,p//4,colors[v] if (self.matched&(1<<p) or p in (self.first,self.second)) else (30,45,65),3,1)
        self.px(fb,2+self.x*3,2+self.y*3,(255,255,255))
