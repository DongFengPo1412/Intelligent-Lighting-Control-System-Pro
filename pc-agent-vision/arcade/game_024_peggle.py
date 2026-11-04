from .b3_helpers import *


class Game024Peggle(BatchCartridge):
    game_id=24;name='弹珠撞靶';english_name='Peggle';core_mechanic='Aim a finite supply of gravity-driven balls; collide with and remove every peg.'
    control_type=3
    def setup(self):self.aim=0.;self.x=8.;self.y=2.;self.vx=self.vy=0.;self.mask=255;self.balls=(10,8,6)[self.difficulty];self.flying=False
    def tick(self,dt,down,pressed):
        keys=down|pressed
        if not self.flying:
            self.aim=clamp(self.aim+dt*1.2*(bool(keys&KEY_RIGHT)-bool(keys&KEY_LEFT)),-1,1)
            if pressed&KEY_A and self.balls:self.x=8.;self.y=2.;self.vx=math.sin(self.aim)*(6,7,8)[self.difficulty];self.vy=math.cos(self.aim)*(6,7,8)[self.difficulty];self.balls-=1;self.flying=True;self.emit_sound('shot')
        else:
            self.vy+=2.5*dt;self.x+=self.vx*dt;self.y+=self.vy*dt
            if self.x<.7 or self.x>14.3:self.x=clamp(self.x,.7,14.3);self.vx=-self.vx
            for i,(px,py) in enumerate(((4,6),(7,6),(10,6),(13,6),(3,10),(6,10),(9,10),(12,10))):
                dx=self.x-px;dy=self.y-py;dist=math.hypot(dx,dy)
                if self.mask&(1<<i) and dist<1.05:
                    self.mask&=~(1<<i);self.award(50);self.emit_sound('hit',i)
                    nx=dx/max(.01,dist);ny=dy/max(.01,dist);dot=self.vx*nx+self.vy*ny
                    if dot<0:self.vx-=1.8*dot*nx;self.vy-=1.8*dot*ny
            if not self.mask:self.award(500);self.finish(True)
            elif self.y>15:
                self.flying=False
                if not self.balls:self.finish(False)
        if self.elapsed>(90,75,60)[self.difficulty]:self.finish(False)
        self.aim=quantize(self.aim);self.x=quantize(self.x);self.y=quantize(self.y);self.vx=quantize(self.vx);self.vy=quantize(self.vy)
    def progress(self):return (8-self.mask.bit_count())*100//8
    def draw(self,fb):
        for i,(px,py) in enumerate(((4,6),(7,6),(10,6),(13,6),(3,10),(6,10),(9,10),(12,10))):
            if self.mask&(1<<i):self.px(fb,px,py,(255,150,40))
        if self.flying:self.px(fb,round(self.x),round(self.y),(245,245,255))
        else:line(fb,8,1,round(8+math.sin(self.aim)*3),round(1+math.cos(self.aim)*3),(80,180,255))
        for i in range(self.balls):self.px(fb,i+1,0,(40,150,240))
    def get_status(self):
        s=super().get_status();s["lives"]=max(0,self.balls);return s
