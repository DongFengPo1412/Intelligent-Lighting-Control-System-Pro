from .b3_helpers import *


class Game037Qbert(BatchCartridge):
    game_id=37;name='染色跳格';english_name='Qbert';core_mechanic='Diagonal hops on a triangular pyramid, persistent tile colours and a pursuing chaser.'
    control_type=2
    def setup(self):self.row=self.col=0;self.er=4;self.ec=2;self.hp=(3,2,1)[self.difficulty];self.mask=1;self.hop=0.;self.chase=-8.
    def tick(self,dt,down,pressed):
        self.hop=max(0.,self.hop-dt);keys=down|pressed
        if self.hop<=0 and keys&15:
            dr,dc=(1,0) if keys&KEY_LEFT else (-1,0) if keys&KEY_RIGHT else (-1,-1) if keys&KEY_UP else (1,1);nr=self.row+dr;nc=self.col+dc;self.hop=.14
            if nr<0 or nr>=5 or nc<0 or nc>nr:self.hp-=1;self.row=self.col=0;self.emit_sound('collision')
            else:
                self.row,self.col=nr,nc;bit=1<<(nr*(nr+1)//2+nc)
                if not self.mask&bit:self.mask|=bit;self.award(20)
                self.emit_sound('jump')
        self.chase+=dt
        if self.chase>=(1.5,.9,.5)[self.difficulty]:
            self.chase=0.;options=[(self.er+dr,self.ec+dc) for dr,dc in ((1,0),(1,1),(-1,0),(-1,-1)) if 0<=self.er+dr<5 and 0<=self.ec+dc<=self.er+dr]
            self.er,self.ec=min(options,key=lambda p:abs(p[0]-self.row)+abs(p[1]-self.col))
            if (self.er,self.ec)==(self.row,self.col):self.hp-=1;self.row=self.col=0;self.er=4;self.ec=2;self.emit_sound('collision')
        if self.mask==32767:self.award(500);self.finish(True)
        elif self.hp<=0 or self.elapsed>(90,70,55)[self.difficulty]:self.finish(False)
    def progress(self):return self.mask.bit_count()*100//15
    def draw(self,fb):
        for r in range(5):
            for c in range(r+1):
                color=(245,195,40) if self.mask&(1<<(r*(r+1)//2+c)) else (90,55,145);x=round(7+(2*c-r)*1.4);y=2+r*2
                self.px(fb,x,y,color);self.px(fb,x+1,y,color)
        self.px(fb,round(7+(2*self.ec-self.er)*1.4),1+self.er*2,(255,65,90));self.px(fb,round(7+(2*self.col-self.row)*1.4),1+self.row*2,(245,245,255))
    def get_status(self):
        s=super().get_status();s["lives"]=max(0,self.hp);return s
