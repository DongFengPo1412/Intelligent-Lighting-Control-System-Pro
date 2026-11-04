from .b3_helpers import *


class Game011DinoRunner(BatchCartridge):
    game_id=11;name='恐龙跑酷';english_name='Dino Runner';core_mechanic='Automatic running, grounded jump timing, accelerating obstacles and a twelve-obstacle survival milestone.'
    control_type=0
    def setup(self):self.y=12.;self.vy=0.;self.distance=0.;self.ob=[20.,36.,52.];self.cleared=0
    def tick(self,dt,down,pressed):
        if pressed&(KEY_A|KEY_UP) and self.y>=11.999:self.vy=-9.;self.emit_sound('jump')
        self.vy+=(8,9,10)[self.difficulty]*dt;self.y=min(12.,self.y+self.vy*dt)
        if self.y>=12:self.vy=0.
        speed=min(8.,(3,4,5)[self.difficulty]+self.elapsed*.04);self.distance+=speed*dt
        for i in range(3):
            self.ob[i]-=speed*dt
            if abs(self.ob[i]-3)<.85 and self.y>12-(1,2,3)[self.difficulty]:self.emit_sound('collision');self.finish(False);return
            if self.ob[i]<0:self.ob[i]+=48;self.cleared+=1;self.award(10)
        if self.cleared>=12:self.award(500);self.finish(True)
    def progress(self):return self.cleared*100//12
    def draw(self,fb):
        line(fb,0,13,15,13,(60,100,65));self.px(fb,3,round(self.y),(220,240,230));self.px(fb,3,round(self.y)-1,(220,240,230))
        for x in self.ob:
            for h in range((1,2,3)[self.difficulty]):self.px(fb,round(x),12-h,(110,220,90))
