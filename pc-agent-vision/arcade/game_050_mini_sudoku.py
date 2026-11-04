from .b3_helpers import *


class Game050MiniSudoku(BatchCartridge):
    game_id=50;name='四色迷你数独';english_name='Mini Sudoku';core_mechanic='Fill four colours under row, column and 2x2 box constraints; checking a conflicting or incomplete board costs an attempt.'
    control_type=3
    def setup(self):
        self.board=[0]*16;self.x=self.y=self.edits=0;self.attempts=(3,2,1)[self.difficulty];self.fixed=0;self.conflict=0.
        for p in (0,3,5,6,9,10,12,15)[:(8,6,4)[self.difficulty]]:self.board[p]=(p//4*2+p//8+p%4)%4+1;self.fixed|=1<<p
    def tick(self,dt,down,pressed):
        dx,dy=self.direction(down,pressed);self.x=int(clamp(self.x+dx,0,3));self.y=int(clamp(self.y+dy,0,3));p=self.y*4+self.x;self.conflict=max(0.,self.conflict-dt)
        if pressed&KEY_A and not self.fixed&(1<<p):self.board[p]=(self.board[p]+1)%5;self.edits+=1;self.emit_sound('action',self.board[p])
        if pressed&KEY_B:
            groups=[[self.board[y*4+x] for x in range(4)] for y in range(4)]+[[self.board[y*4+x] for y in range(4)] for x in range(4)]+[[self.board[(by+y)*4+bx+x] for y in range(2) for x in range(2)] for by in (0,2) for bx in (0,2)]
            if all(set(g)=={1,2,3,4} for g in groups):self.award(max(100,1200+self.attempts*50-self.edits*2));self.finish(True)
            else:self.attempts-=1;self.conflict=.6;self.emit_sound('collision')
        if self.attempts<=0 or self.elapsed>(180,150,120)[self.difficulty]:self.finish(False)
    def progress(self):return 100 if self.state==STATE_VICTORY else sum(v>0 for v in self.board)*100//16
    def draw(self,fb):
        colors=((10,20,30),(240,75,80),(65,170,240),(75,215,110),(245,205,55))
        for y in range(4):
            for x in range(4):
                for yy in range(3):
                    for xx in range(3):self.px(fb,x*4+xx,y*4+yy,colors[self.board[y*4+x]])
                if self.fixed&(1<<(y*4+x)):self.px(fb,x*4,y*4,(150,150,150))
        self.px(fb,self.x*4+1,self.y*4+1,(255,40,40) if self.conflict else (255,255,255))
    def get_status(self):
        s=super().get_status();s["lives"]=max(0,self.attempts);return s
