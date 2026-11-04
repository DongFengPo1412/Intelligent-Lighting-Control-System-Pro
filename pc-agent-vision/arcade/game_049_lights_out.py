from .b3_helpers import *


class Game049LightsOut(BatchCartridge):
    game_id=49;name='灭灯';english_name='Lights Out';core_mechanic='Toggle a lamp and its orthogonal neighbours on a solvable 5x5 board; turn every light off within a move budget.'
    control_type=3
    def toggle(self,x,y):
        for dx,dy in ((0,0),(-1,0),(1,0),(0,-1),(0,1)):
            if 0<=x+dx<5 and 0<=y+dy<5:self.mask^=1<<((y+dy)*5+x+dx)
    def setup(self):
        self.mask=0;self.x=self.y=2;self.moves=0
        for p in (0,6,12,18,24,2,10,14,22,4,8,16,20)[:(5,9,13)[self.difficulty]]:self.toggle(p%5,p//5)
    def tick(self,dt,down,pressed):
        dx,dy=self.direction(down,pressed);self.x=int(clamp(self.x+dx,0,4));self.y=int(clamp(self.y+dy,0,4))
        if pressed&KEY_A:self.toggle(self.x,self.y);self.moves+=1;self.emit_sound('action')
        if not self.mask:self.award(1000+max(0,(30,24,20)[self.difficulty]-self.moves)*10);self.finish(True)
        elif self.moves>=(30,24,20)[self.difficulty] or self.elapsed>(90,75,60)[self.difficulty]:self.finish(False)
    def progress(self):return (25-self.mask.bit_count())*4
    def draw(self,fb):
        for y in range(5):
            for x in range(5):self.cell(fb,x,y,(245,190,45) if self.mask&(1<<(y*5+x)) else (15,25,40),3,0)
        self.px(fb,self.x*3+1,self.y*3+1,(255,255,255))
