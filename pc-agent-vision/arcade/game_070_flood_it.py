from .b3_helpers import *


class Game070FloodIt(BatchCartridge):
    game_id=70;name='连通染色';english_name='Flood-It';core_mechanic='Recolour the connected top-left region, expanding only across adjacent matching cells within a move limit.'
    control_type=3
    def setup(self):
        seed=0x70a;self.board=[]
        for _ in range(36):seed=rng(seed);self.board.append((seed>>16)%4)
        self.color=self.board[0];self.selected=0;self.moves=0;self.flooded=1;self.expand()
    def expand(self):
        old=-1
        while old!=self.flooded:
            old=self.flooded
            for p,v in enumerate(self.board):
                if self.flooded&(1<<p):continue
                if v==self.color and any(0<=n<36 and self.flooded&(1<<n) for n in (p-1 if p%6 else -1,p+1 if p%6<5 else -1,p-6,p+6)):self.flooded|=1<<p
        self.count=self.flooded.bit_count()
    def tick(self,dt,down,pressed):
        dx,_=self.direction(down,pressed);self.selected=(self.selected+dx)%4
        if pressed&KEY_A and self.selected!=self.color:
            self.color=self.selected;self.moves+=1;self.expand();self.award(5);self.emit_sound('action')
        if self.count==36:self.award(1500-self.moves*20);self.finish(True)
        elif self.moves>=(20,16,12)[self.difficulty] or self.elapsed>(120,100,80)[self.difficulty]:self.finish(False)
    def progress(self):return self.count*100//36
    def draw(self,fb):
        colors=((235,75,90),(70,170,235),(80,220,110),(240,200,50))
        for y in range(6):
            for x in range(6):p=y*6+x;self.cell(fb,x,y,colors[self.color if self.flooded&(1<<p) else self.board[p]])
        for i in range(4):self.px(fb,2+i*3,0,(255,255,255) if self.selected==i else colors[i])
