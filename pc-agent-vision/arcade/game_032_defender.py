from .b3_helpers import *


class Game032Defender(BatchCartridge):
    game_id=32;name='横向防卫';english_name='Defender';core_mechanic='Wraparound horizontal flight and lasers protect four humans from abducting landers.'
    control_type=3
    def setup(self):
        self.x=8.;self.y=6.;self.facing=1;self.hp=(3,2,1)[self.difficulty];self.kills=0;self.ex=[4.,12.,20.,28.];self.ey=[2.]*4;self.enemy=[True]*4;self.carrying=[False]*4;self.human=[True]*4;self.bullets=[];self.shot=0.
    def tick(self,dt,down,pressed):
        keys=down|pressed;dx=bool(keys&KEY_RIGHT)-bool(keys&KEY_LEFT);dy=bool(keys&KEY_DOWN)-bool(keys&KEY_UP);self.x=(self.x+6*dt*dx)%32;self.y=clamp(self.y+5*dt*dy,1,12)
        if dx:self.facing=dx
        self.shot=max(0.,self.shot-dt)
        if keys&KEY_A and self.shot<=0 and len(self.bullets)<8:self.bullets.append([self.x,self.y,self.facing*14.,2.5]);self.shot=.2;self.emit_sound('shot')
        for b in self.bullets:
            b[0]=(b[0]+b[2]*dt)%32;b[3]-=dt
            for i in range(4):
                if self.enemy[i] and abs((b[0]-self.ex[i]+16)%32-16)<.8 and abs(b[1]-self.ey[i])<.8:
                    self.enemy[i]=False;self.human[i]=True;self.kills+=1;self.award(200);b[2]=0.;self.emit_sound('hit',i)
        self.bullets=[b for b in self.bullets if b[2]!=0 and b[3]>0]
        for i in range(4):
            if not self.enemy[i]:continue
            self.ey[i]+=(-1. if self.carrying[i] else (.45,.6,.8)[self.difficulty])*dt
            if self.ey[i]>=13:self.carrying[i]=True;self.human[i]=False
            if self.ey[i]<1:self.enemy[i]=False
            if abs((self.x-self.ex[i]+16)%32-16)<.8 and abs(self.y-self.ey[i])<.8:self.hp-=1;self.enemy[i]=False;self.emit_sound('collision')
        if self.kills==4 and any(self.human):self.award(500);self.finish(True)
        elif self.hp<=0 or not any(self.human) or not any(self.enemy) or self.elapsed>(90,70,55)[self.difficulty]:self.finish(False)
    def progress(self):return self.kills*25
    def draw(self,fb):
        for xx in range(16):self.px(fb,xx,14,(25,80,65))
        for i in range(4):
            xx=round((self.ex[i]-self.x+8)%32)
            if self.enemy[i]:self.px(fb,xx,round(self.ey[i]),(255,75,90))
            if self.human[i]:self.px(fb,xx,13,(60,240,130))
        for bx,by,bv,life in self.bullets:self.px(fb,round((bx-self.x+8)%32),round(by),(255,210,50))
        self.px(fb,8,round(self.y),(230,240,255));self.px(fb,8+self.facing,round(self.y),(90,170,255))
    def get_status(self):
        s=super().get_status();s["lives"]=max(0,self.hp);return s
