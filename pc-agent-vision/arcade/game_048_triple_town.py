from .b3_helpers import *


class Game048TripleTown(BatchCartridge):
    game_id=48;name='三合镇';english_name='Triple Town';core_mechanic='Place grass; three connected equal objects merge at the placed cell and can cascade into a house.'
    control_type=3
    def setup(self):
        self.board=[0]*25;self.x=self.y=self.moves=self.best=0
        for i in (24,20,4,0)[:(0,2,4)[self.difficulty]]:self.board[i]=9
        self.board_hash=2166136261
        for v in self.board:self.board_hash=((self.board_hash^v)*16777619)&0xffffffff
    def tick(self,dt,down,pressed):
        dx,dy=self.direction(down,pressed);self.x=int(clamp(self.x+dx,0,4));self.y=int(clamp(self.y+dy,0,4));pos=self.y*5+self.x
        if pressed&KEY_A and not self.board[pos]:
            self.board[pos]=1;self.moves+=1;self.award(5);self.emit_sound('action')
            while self.board[pos]<3:
                value=self.board[pos];seen={pos};stack=[pos]
                while stack:
                    p=stack.pop()
                    for n in (p-1 if p%5 else -1,p+1 if p%5<4 else -1,p-5,p+5):
                        if 0<=n<25 and n not in seen and self.board[n]==value:seen.add(n);stack.append(n)
                if len(seen)<3:break
                for p in seen:self.board[p]=0
                self.board[pos]=value+1;self.award((1<<(value+1))*10);self.emit_sound('hit',value)
            self.best=max(v for v in self.board if v!=9)
        self.board_hash=2166136261
        for v in self.board:self.board_hash=((self.board_hash^v)*16777619)&0xffffffff
        if self.best>=3:self.award(500);self.finish(True)
        elif not any(v==0 for v in self.board) or self.moves>=(40,30,20)[self.difficulty] or self.elapsed>(120,100,80)[self.difficulty]:self.finish(False)
    def progress(self):return self.best*100//3
    def draw(self,fb):
        colors={0:(10,18,25),1:(55,200,95),2:(45,160,235),3:(245,190,50),9:(90,95,105)}
        for y in range(5):
            for x in range(5):self.cell(fb,x,y,colors[self.board[y*5+x]],3,0)
        self.px(fb,self.x*3+1,self.y*3+1,(255,255,255))
