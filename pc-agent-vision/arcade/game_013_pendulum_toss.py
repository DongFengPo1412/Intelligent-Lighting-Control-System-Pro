from .b3_helpers import *


class Game013PendulumToss(BatchCartridge):
    game_id=13;name='摆锤投球';english_name='Pendulum Toss';core_mechanic='Release a swinging bob with its tangential velocity and land inside three baskets with limited balls.'
    control_type=0
    def setup(self):self.x=8.;self.y=6.;self.vx=self.vy=self.phase=0.;self.flying=False;self.hits=0;self.balls=(6,5,4)[self.difficulty]
    def tick(self,dt,down,pressed):
        speed=(1.3,1.7,2.1)[self.difficulty];self.phase+=speed*dt;angle=.9*math.sin(self.phase);omega=.9*speed*math.cos(self.phase)
        if not self.flying:
            self.x=8+5*math.sin(angle);self.y=1+5*math.cos(angle)
            if pressed&KEY_A:self.vx=5*math.cos(angle)*omega;self.vy=-5*math.sin(angle)*omega;self.flying=True;self.balls-=1;self.emit_sound('action')
        else:
            self.vy+=5*dt;self.x+=self.vx*dt;self.y+=self.vy*dt
            if self.y>=13 or self.x<0 or self.x>15:
                target=(4,11,7)[self.hits%3];good=self.y>=13 and abs(self.x-target)<(2.5,2.,1.5)[self.difficulty];self.flying=False
                if good:self.hits+=1;self.award(100);self.emit_sound('hit')
                else:self.emit_sound('collision')
                if self.hits>=3:self.finish(True)
                elif self.balls<=0:self.finish(False)
        if self.elapsed>(45,35,30)[self.difficulty]:self.finish(False)
    def progress(self):return self.hits*100//3
    def draw(self,fb):
        if not self.flying:line(fb,8,1,round(self.x),round(self.y),(90,110,150))
        self.px(fb,round(self.x),round(self.y),(255,220,55));target=(4,11,7)[self.hits%3];w=(2.5,2.,1.5)[self.difficulty]
        for x in range(16):
            if abs(x-target)<w:self.px(fb,x,14,(40,220,130))
        for i in range(self.balls):self.px(fb,i+1,0,(120,180,255))
    def get_status(self):
        s=super().get_status();s["lives"]=max(0,self.balls);return s
