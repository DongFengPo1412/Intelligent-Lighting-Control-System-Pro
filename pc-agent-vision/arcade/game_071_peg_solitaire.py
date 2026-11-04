from .b3_helpers import *


class Game071PegSolitaire(BatchCartridge):
    game_id=71;name='单人孔明棋';english_name='Peg Solitaire';core_mechanic='Jump over adjacent pegs into an empty triangle hole, removing the jumped peg; leave exactly one.'
    control_type=3
    def setup(self):self.mask=32766;self.x=self.y=self.dir=self.moves=0
    def jump(self,x,y,d):
        dx,dy=((1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,-1))[d];a=y*(y+1)//2+x;mx=x+dx;my=y+dy;tx=x+2*dx;ty=y+2*dy
        if not (0<=my<5 and 0<=mx<=my and 0<=ty<5 and 0<=tx<=ty):return None
        b=my*(my+1)//2+mx;c=ty*(ty+1)//2+tx
        return (a,b,c) if self.mask&(1<<a) and self.mask&(1<<b) and not self.mask&(1<<c) else None
    def tick(self,dt,down,pressed):
        dx,dy=self.direction(down,pressed);self.y=int(clamp(self.y+dy,0,4));self.x=int(clamp(self.x+dx,0,self.y))
        if pressed&KEY_B:self.dir=(self.dir+1)%6
        if pressed&KEY_A:
            jump=self.jump(self.x,self.y,self.dir)
            if jump:
                for p in jump:self.mask^=1<<p
                self.moves+=1;self.award(50);self.emit_sound('hit')
        if self.mask.bit_count()==1:self.award(1000);self.finish(True)
        elif not any(self.jump(x,y,d) for y in range(5) for x in range(y+1) for d in range(6)) or self.elapsed>(240,180,120)[self.difficulty]:self.finish(False)
    def progress(self):return self.moves*100//13
    def draw(self,fb):
        for y in range(5):
            for x in range(y+1):self.cell(fb,x,y,(70,190,225) if self.mask&(1<<(y*(y+1)//2+x)) else (35,40,50),2,2)
        self.px(fb,2+self.x*2,2+self.y*2,(255,255,255));self.px(fb,2+self.dir*2,14,(245,160,50))
