from .b3_helpers import *


class Game056SlidingPuzzle(BatchCartridge):
    game_id=56;name='数字华容道';english_name='Sliding Puzzle';core_mechanic='Slide the empty cell of a legally scrambled 3x3 numbered board back into ordered 1 through 8.'
    control_type=2
    def setup(self):
        self.board=list(range(1,9))+[0];self.blank=8;self.moves=0;seed=0x56fa;previous=-1
        for _ in range((10,18,26)[self.difficulty]):
            options=[n for n in (self.blank-1 if self.blank%3 else -1,self.blank+1 if self.blank%3<2 else -1,self.blank-3,self.blank+3) if 0<=n<9 and n!=previous];seed=rng(seed);n=options[seed%len(options)];self.board[self.blank],self.board[n]=self.board[n],self.board[self.blank];previous=self.blank;self.blank=n
    def tick(self,dt,down,pressed):
        dx,dy=self.direction(down,pressed);x=self.blank%3+dx;y=self.blank//3+dy
        if (dx or dy) and 0<=x<3 and 0<=y<3:n=y*3+x;self.board[self.blank],self.board[n]=self.board[n],self.board[self.blank];self.blank=n;self.moves+=1;self.emit_sound('action')
        if self.board==list(range(1,9))+[0]:self.award(max(100,1500-self.moves*10));self.finish(True)
        elif self.moves>=(90,70,50)[self.difficulty] or self.elapsed>(180,150,120)[self.difficulty]:self.finish(False)
    def progress(self):return sum(v==i+1 for i,v in enumerate(self.board[:8]))*100//8
    def draw(self,fb):
        from .arcade_result_screen import draw_digit_3x5
        for i,v in enumerate(self.board):
            if v:draw_digit_3x5(fb,v,(i%3)*5+1,(i//3)*5,235,190,65)
