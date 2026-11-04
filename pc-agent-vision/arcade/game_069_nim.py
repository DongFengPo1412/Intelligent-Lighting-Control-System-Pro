from .b3_helpers import *


class Game069Nim(BatchCartridge):
    game_id=69;name='取石子';english_name='Nim';core_mechanic='Choose one heap and a positive take count; alternating normal-play Nim rewards taking the last stone.'
    control_type=3
    def setup(self):self.piles=[3,4,5];self.pile=0;self.take=1;self.turns=0
    def tick(self,dt,down,pressed):
        dx,dy=self.direction(down,pressed);self.pile=int(clamp(self.pile+dx,0,2));self.take=int(clamp(self.take+dy,1,max(1,self.piles[self.pile])))
        if pressed&KEY_A and self.piles[self.pile]>=self.take:
            self.piles[self.pile]-=self.take;self.turns+=1;self.award(self.take*10);self.emit_sound('action')
            if not any(self.piles):self.award(1000);self.finish(True);return
            xor=self.piles[0]^self.piles[1]^self.piles[2];target=next(i for i,v in enumerate(self.piles) if v);amount=1
            if self.difficulty:
                for i,v in enumerate(self.piles):
                    if (v^xor)<v:target=i;amount=v-(v^xor);break
            self.piles[target]-=amount
            if not any(self.piles):self.finish(False)
            self.take=1
        if self.elapsed>(120,90,60)[self.difficulty]:self.finish(False)
    def progress(self):return (12-sum(self.piles))*100//12
    def draw(self,fb):
        for i,n in enumerate(self.piles):
            for j in range(n):self.cell(fb,i,j,(245,200,60) if i==self.pile and j<self.take else (65,175,220),2,2)
        self.px(fb,2+self.pile*2,0,(255,255,255))
