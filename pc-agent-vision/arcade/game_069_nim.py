from .b3_helpers import *

class Game069Nim(BatchCartridge):
    game_id=69;name='取石子';english_name='Nim';core_mechanic='First to two rounds of normal-play Nim; visible AI turns and growing heaps.'
    control_type=3
    def load_round(self):self.piles=[3+self.round,4+self.round,5+self.round];self.pile=0;self.take=1;self.thinking=0.
    def setup(self):self.turns=self.human_wins=self.ai_wins=self.round=0;self.load_round()
    def end_round(self,human):
        if human:self.human_wins+=1;self.award(300)
        else:self.ai_wins+=1
        self.emit_sound('hit' if human else 'collision')
        if self.human_wins==2:self.award(500);self.finish(True)
        elif self.ai_wins==2:self.finish(False)
        else:self.round+=1;self.load_round()
    def tick(self,dt,down,pressed):
        if self.thinking>0:
            self.thinking=max(0.,self.thinking-dt)
            if not self.thinking:
                xor=self.piles[0]^self.piles[1]^self.piles[2];target=next(i for i,v in enumerate(self.piles) if v);amount=1
                if self.difficulty:
                    for i,v in enumerate(self.piles):
                        if (v^xor)<v:target=i;amount=v-(v^xor);break
                self.piles[target]-=amount;self.take=1;self.emit_sound('action',1)
                if not any(self.piles):self.end_round(False)
        else:
            dx,dy=self.direction(down,pressed);self.pile=int(clamp(self.pile+dx,0,2));self.take=int(clamp(self.take+dy,1,max(1,self.piles[self.pile])))
            if pressed&KEY_A and self.piles[self.pile]>=self.take:
                self.piles[self.pile]-=self.take;self.turns+=1;self.award(self.take*10);self.emit_sound('action')
                if not any(self.piles):self.end_round(True)
                else:self.thinking=.35
        if self.elapsed>(120,90,60)[self.difficulty]:self.finish(False)
    def progress(self):return 100 if self.state==STATE_VICTORY else self.human_wins*50
    def draw(self,fb):
        for i,n in enumerate(self.piles):
            for j in range(n):self.cell(fb,i,j,(245,200,60) if i==self.pile and j<self.take else (65,175,220),2,2)
        self.px(fb,2+self.pile*2,0,(255,100,100) if self.thinking else (255,255,255))
        for i in range(self.human_wins):self.px(fb,10+i,3,(65,220,100))
        for i in range(self.ai_wins):self.px(fb,10+i,5,(245,80,100))
