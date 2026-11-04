from .b3_helpers import *


class Game008JumpKing(BatchCartridge):
    game_id=8;name='蓄力跳跃';english_name='Jump King';core_mechanic='Charge then release a ballistic jump between elevated platforms; failed landings lose altitude.'
    control_type=3
    def setup(self):self.x=3.5;self.y=46.;self.vx=self.vy=self.charge=0.;self.facing=1;self.grounded=True;self.charging=False
    def tick(self,dt,down,pressed):
        keys=down|pressed
        if self.grounded:
            if keys&KEY_LEFT:self.facing=-1
            elif keys&KEY_RIGHT:self.facing=1
            if keys&KEY_A:self.charge=min(1.2,self.charge+dt);self.charging=True
            elif self.charging:self.vx=self.facing*(2+1.2*self.charge);self.vy=-(7+8*self.charge);self.charging=False;self.charge=0.;self.grounded=False;self.emit_sound('jump')
        old=self.y;self.vy+=(8,8.5,9)[self.difficulty]*dt;self.x+=self.vx*dt;self.y+=self.vy*dt
        if self.x<.5 or self.x>14.5:self.x=clamp(self.x,.5,14.5);self.vx=-self.vx*.5
        self.grounded=False
        for sy,lo,hi in ((47,2,6),(37,8,13),(27,2,7),(17,8,13),(7,2,7)):
            if self.vy>=0 and lo<=self.x<=hi and old<=sy-1<=self.y:self.y=sy-1;self.vx=self.vy=0.;self.grounded=True
        if self.grounded and self.y<=6:self.award(1000);self.finish(True)
        elif self.y>51 or self.elapsed>(100,80,65)[self.difficulty]:self.finish(False)
    def progress(self):return int((46-self.y)/40*100)
    def draw(self,fb):
        cam=clamp(int(self.y)-8,0,36)
        for sy,lo,hi in ((47,2,6),(37,8,13),(27,2,7),(17,8,13),(7,2,7)):line(fb,lo,sy-cam,hi,sy-cam,(70,185,125))
        self.px(fb,round(self.x),round(self.y)-cam,(255,235,90))
        for i in range(int(self.charge/1.2*14)):self.px(fb,i+1,0,(80,170,255))
