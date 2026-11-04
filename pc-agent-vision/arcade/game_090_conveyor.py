from .b3_helpers import *


class Game090Conveyor(BatchCartridge):
    game_id=90;name='传送带工厂';english_name='Conveyor Factory';core_mechanic='Rotate belt tiles to route raw products through a processor to a coloured order sink, without wasting three items.'
    control_type=3
    def setup(self):self.belt=[0]*49;self.item=[-1]*4;self.processed=[0]*4;self.x=self.y=self.delivered=self.waste=0;self.clock=self.spawn=0.
    def tick(self,dt,down,pressed):
        dx,dy=self.direction(down,pressed);self.x=int(clamp(self.x+dx,0,6));self.y=int(clamp(self.y+dy,0,6))
        if pressed&KEY_A:self.belt[self.y*7+self.x]=(self.belt[self.y*7+self.x]+1)%4;self.emit_sound('action')
        self.spawn+=dt;self.clock+=dt
        if self.spawn>=(1.2,.9,.6)[self.difficulty] and -1 in self.item and 21 not in self.item:i=self.item.index(-1);self.item[i]=21;self.processed[i]=0;self.spawn=0.
        if self.clock>=(.3,.24,.18)[self.difficulty]:
            self.clock=0.;old=self.item[:]
            for i,p in enumerate(old):
                if p<0:continue
                if p==10:self.processed[i]=1
                if p==27:
                    if self.processed[i]:self.delivered+=1;self.award(100);self.emit_sound('hit')
                    else:self.waste+=1;self.emit_sound('collision')
                    self.item[i]=-1;continue
                dx,dy=((1,0),(0,1),(-1,0),(0,-1))[self.belt[p]];xx=p%7+dx;yy=p//7+dy
                if not (0<=xx<7 and 0<=yy<7):self.item[i]=-1;self.waste+=1
                elif yy*7+xx not in self.item:self.item[i]=yy*7+xx
        if self.delivered>=(3,4,5)[self.difficulty]:self.award(500);self.finish(True)
        elif self.waste>=3 or self.elapsed>60:self.finish(False)
    def progress(self):return self.delivered*100//(3,4,5)[self.difficulty]
    def draw(self,fb):
        for p,d in enumerate(self.belt):self.cell(fb,p%7,p//7,(20+d*10,45,65),2,0);dx,dy=((1,0),(0,1),(-1,0),(0,-1))[d];self.px(fb,p%7*2+(dx>0),p//7*2+(dy>0),(90,120,140))
        self.cell(fb,3,1,(140,70,190),2,0);self.cell(fb,6,3,(50,190,100),2,0)
        for i,p in enumerate(self.item):
            if p>=0:self.cell(fb,p%7,p//7,(65,185,245) if self.processed[i] else (245,170,55),2,0)
        self.px(fb,self.x*2,self.y*2,(255,255,255))
