from .b3_helpers import *


class Game046Suika(BatchCartridge):
    game_id=46;name='合成大西瓜';english_name='Suika';core_mechanic='Drop circles under gravity; equal levels merge on contact, different levels collide and a high stack overflows.'
    control_type=3
    def setup(self):self.aim=8.;self.bx=[0.]*16;self.by=[0.]*16;self.vx=[0.]*16;self.vy=[0.]*16;self.level=[0]*16;self.best=0;self.drops=0;self.active_count=0;self.cooldown=self.overflow=0.
    def tick(self,dt,down,pressed):
        keys=down|pressed;self.aim=clamp(self.aim+5*dt*(bool(keys&KEY_RIGHT)-bool(keys&KEY_LEFT)),2,13);self.cooldown=max(0.,self.cooldown-dt)
        if pressed&KEY_A and self.cooldown<=0 and self.active_count<16:
            if self.drops>=(32,24,20)[self.difficulty]:self.finish(False);return
            i=self.level.index(0);self.level[i]=1;self.bx[i]=self.aim;self.by[i]=2.;self.vx[i]=self.vy[i]=0.;self.drops+=1;self.cooldown=.4;self.emit_sound('action')
        for i in range(16):
            if not self.level[i]:continue
            r=.5+.3*self.level[i];self.vy[i]+=(6,7,8)[self.difficulty]*dt;self.bx[i]+=self.vx[i]*dt;self.by[i]+=self.vy[i]*dt
            if self.bx[i]<r or self.bx[i]>15-r:self.bx[i]=clamp(self.bx[i],r,15-r);self.vx[i]*=-.4
            if self.by[i]>14-r:self.by[i]=14-r;self.vy[i]*=-.15;self.vx[i]*=.9
        for i in range(16):
            for j in range(i+1,16):
                if not self.level[i] or not self.level[j]:continue
                dx=self.bx[j]-self.bx[i];dy=self.by[j]-self.by[i];distance=math.hypot(dx,dy);radius=1+.3*(self.level[i]+self.level[j])
                if distance>=radius:continue
                if self.level[i]==self.level[j] and self.level[i]<4:
                    self.level[i]+=1;self.level[j]=0;self.bx[i]=(self.bx[i]+self.bx[j])/2;self.by[i]=(self.by[i]+self.by[j])/2;self.vx[i]=(self.vx[i]+self.vx[j])/2;self.vy[i]=0.;self.award((1<<self.level[i])*25);self.emit_sound('hit',self.level[i])
                else:
                    if distance<.000001:dx=0.;dy=1.;distance=1.
                    nx=dx/distance;ny=dy/distance;overlap=(radius-distance)/2;self.bx[i]-=nx*overlap;self.by[i]-=ny*overlap;self.bx[j]+=nx*overlap;self.by[j]+=ny*overlap
                    relative=(self.vx[j]-self.vx[i])*nx+(self.vy[j]-self.vy[i])*ny
                    if relative<0:self.vx[i]+=relative*nx*.6;self.vy[i]+=relative*ny*.6;self.vx[j]-=relative*nx*.6;self.vy[j]-=relative*ny*.6
        self.best=max(self.level);self.active_count=sum(l>0 for l in self.level)
        top=any(l and self.by[i]<3 and abs(self.vy[i])<.5 for i,l in enumerate(self.level));self.overflow=self.overflow+dt if top else 0.
        if self.best>=4:self.award(500);self.finish(True)
        elif self.overflow>1 or self.elapsed>(120,90,70)[self.difficulty]:self.finish(False)
    def progress(self):return self.best*25
    def draw(self,fb):
        line(fb,0,1,0,15,(55,65,80));line(fb,15,1,15,15,(55,65,80));line(fb,0,15,15,15,(55,65,80));self.px(fb,round(self.aim),0,(255,255,255));colors=((0,0,0),(255,120,90),(255,205,50),(120,210,55),(55,185,220),(170,85,230))
        for i,l in enumerate(self.level):
            if l:disc(fb,self.bx[i],self.by[i],.5+.3*l,colors[l])
