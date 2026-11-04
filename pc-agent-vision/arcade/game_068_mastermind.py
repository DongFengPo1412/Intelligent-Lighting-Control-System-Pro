from .b3_helpers import *


class Game068Mastermind(BatchCartridge):
    game_id=68;name='颜色密码';english_name='Mastermind';core_mechanic='Guess a hidden four-colour code; exact and misplaced matches account for duplicates without double counting.'
    control_type=3
    def setup(self):
        seed=0x68ad;self.secret=[]
        for _ in range(4):seed=rng(seed);self.secret.append(seed%6)
        self.guess=[0]*4;self.slot=0;self.tries=(10,8,6)[self.difficulty];self.exact=self.near=0
    def tick(self,dt,down,pressed):
        dx,dy=self.direction(down,pressed);self.slot=int(clamp(self.slot+dx,0,3))
        if dy:self.guess[self.slot]=(self.guess[self.slot]+dy)%6;self.emit_sound('action')
        if pressed&KEY_A:
            self.exact=sum(a==b for a,b in zip(self.secret,self.guess));self.near=sum(min(self.secret.count(c),self.guess.count(c)) for c in range(6))-self.exact;self.tries-=1;self.emit_sound('hit',self.exact)
            if self.exact==4:self.award(1000+self.tries*50);self.finish(True)
            elif not self.tries:self.finish(False)
        if self.elapsed>(180,150,120)[self.difficulty]:self.finish(False)
    def progress(self):return self.exact*25
    def draw(self,fb):
        colors=((235,65,80),(65,170,240),(80,220,100),(245,205,60),(170,90,230),(245,140,65))
        for i,v in enumerate(self.guess):self.cell(fb,i,1,colors[v],3,1)
        self.px(fb,2+self.slot*3,3,(255,255,255))
        for i in range(self.exact):self.cell(fb,i,3,(245,245,245),2,1)
        for i in range(self.near):self.cell(fb,i,5,(245,180,40),2,1)
        for i in range(self.tries):self.px(fb,i+1,14,(65,180,130))
