from .b3_helpers import *


class Game061ConnectFour(BatchCartridge):
    game_id=61;name='四子棋';english_name='Connect Four';core_mechanic='Seven columns obey gravity; alternating player and tactical AI must connect four before the opponent.'
    control_type=3
    def setup(self):self.board=[0]*42;self.column=3;self.turns=0
    def drop(self,col,side):
        for y in range(5,-1,-1):
            if not self.board[y*7+col]:self.board[y*7+col]=side;return y*7+col
        return -1
    def won(self,side):
        return any(all(0<=x+i*dx<7 and 0<=y+i*dy<6 and self.board[(y+i*dy)*7+x+i*dx]==side for i in range(4)) for y in range(6) for x in range(7) for dx,dy in ((1,0),(0,1),(1,1),(1,-1)))
    def choose(self):
        order=(3,2,4,1,5,0,6)
        for side in ((2,1) if self.difficulty else (2,)):
            for col in order:
                p=self.drop(col,side)
                if p<0:continue
                win=self.won(side);self.board[p]=0
                if win:return col
        if self.difficulty==2:
            best=(-10000,3)
            for col in order:
                p=self.drop(col,2)
                if p<0:continue
                # Prefer supporting our lines, penalise immediate two-way human threats.
                value=0
                for c in order:
                    q=self.drop(c,1)
                    if q>=0:
                        value-=100 if self.won(1) else 0;self.board[q]=0
                value+=sum(self.board[y*7+3]==2 for y in range(6))*2;self.board[p]=0
                if value>best[0]:best=(value,col)
            return best[1]
        return next(c for c in order if self.board[c]==0)
    def tick(self,dt,down,pressed):
        dx,_=self.direction(down,pressed);self.column=int(clamp(self.column+dx,0,6))
        if pressed&KEY_A:
            p=self.drop(self.column,1)
            if p>=0:
                self.turns+=1;self.award(5);self.emit_sound('action')
                if self.won(1):self.award(1000);self.finish(True);return
                if all(self.board):self.finish(False);return
                self.drop(self.choose(),2)
                if self.won(2) or all(self.board):self.finish(False)
        if self.elapsed>(180,150,120)[self.difficulty]:self.finish(False)
    def progress(self):return 100 if self.state==STATE_VICTORY else min(90,self.turns*4)
    def draw(self,fb):
        for y in range(6):
            for x in range(7):self.cell(fb,x,y,((15,30,55),(245,200,60),(235,75,100))[self.board[y*7+x]],2,1)
        self.px(fb,1+self.column*2,0,(255,255,255))
