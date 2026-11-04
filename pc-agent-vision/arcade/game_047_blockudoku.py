from .b3_helpers import *


class Game047Blockudoku(BatchCartridge):
    game_id=47;name='自由方块消除';english_name='Blockudoku';core_mechanic='Place a three-piece rack freely on a 6x6 board; clear full rows, columns or 3x3 regions.'
    control_type=3
    def setup(self):self.board=0;self.x=self.y=self.selected=self.placed=self.cleared=0;self.rack=7
    def shape(self,kind,x,y):
        cells=(((0,0),(1,0),(2,0)),((0,0),(0,1),(0,2)),((0,0),))[kind]
        if any(x+dx>=6 or y+dy>=6 for dx,dy in cells):return 0
        return sum(1<<((y+dy)*6+x+dx) for dx,dy in cells)
    def tick(self,dt,down,pressed):
        dx,dy=self.direction(down,pressed);self.x=int(clamp(self.x+dx,0,5));self.y=int(clamp(self.y+dy,0,5))
        if pressed&KEY_B:
            for n in range(1,4):
                if self.rack&(1<<((self.selected+n)%3)):self.selected=(self.selected+n)%3;break
        if pressed&KEY_A:
            shape=self.shape(self.selected,self.x,self.y)
            if shape and not shape&self.board:
                self.board|=shape;self.placed+=1;self.rack&=~(1<<self.selected);remove=0;count=0
                masks=[sum(1<<(y*6+x) for x in range(6)) for y in range(6)]+[sum(1<<(y*6+x) for y in range(6)) for x in range(6)]+[sum(1<<((by+y)*6+bx+x) for y in range(3) for x in range(3)) for by in (0,3) for bx in (0,3)]
                for mask in masks:
                    if self.board&mask==mask:remove|=mask;count+=1
                self.board&=~remove;self.cleared+=count;self.award(10+count*50);self.emit_sound('hit' if count else 'action')
                if not self.rack:self.rack=7
                if not self.rack&(1<<self.selected):self.selected=next(i for i in range(3) if self.rack&(1<<i))
        if self.cleared>=(4,5,6)[self.difficulty]:self.award(500);self.finish(True)
        elif self.placed>=(36,30,24)[self.difficulty] or self.elapsed>(120,100,80)[self.difficulty] or not any((self.rack&(1<<k)) and (m:=self.shape(k,x,y)) and not m&self.board for k in range(3) for y in range(6) for x in range(6)):self.finish(False)
    def progress(self):return self.cleared*100//(4,5,6)[self.difficulty]
    def draw(self,fb):
        for y in range(6):
            for x in range(6):self.cell(fb,x,y,(60,180,225) if self.board&(1<<(y*6+x)) else (15,25,40))
        self.px(fb,2+self.x*2,2+self.y*2,(255,255,255))
        for i in range(3):self.px(fb,3+i*4,0,(255,210,50) if i==self.selected else (70,200,120) if self.rack&(1<<i) else (25,25,30))
