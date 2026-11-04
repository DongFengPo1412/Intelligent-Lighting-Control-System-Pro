from .b3_helpers import *


class Game023AirHockey(BatchCartridge):
    game_id=23;name='空气曲棍球';english_name='Air Hockey';core_mechanic='Move a two-dimensional paddle, deflect a puck, use a close-range power strike and score three goals against bounded AI.'
    control_type=3
    def setup(self):self.paddle_x=8.;self.paddle_y=13.;self.ax=8.;self.x=8.;self.y=8.;self.vx=1.;self.vy=3.;self.cooldown=0.;self.goals=self.against=0
    def tick(self,dt,down,pressed):
        keys=down|pressed;self.paddle_x=clamp(self.paddle_x+5*dt*(bool(keys&KEY_RIGHT)-bool(keys&KEY_LEFT)),2,14);self.paddle_y=clamp(self.paddle_y+5*dt*(bool(keys&KEY_DOWN)-bool(keys&KEY_UP)),8,14)
        self.ax+=clamp(self.x-self.ax,-(.8,1.3,1.8)[self.difficulty]*dt,(.8,1.3,1.8)[self.difficulty]*dt);self.cooldown=max(0.,self.cooldown-dt)
        if keys&KEY_A and self.cooldown<=0 and math.hypot(self.x-self.paddle_x,self.y-self.paddle_y)<3:
            self.vy=-9.;self.vx=4. if self.ax<8 else -4.;self.cooldown=.3;self.emit_sound('shot')
        self.x+=self.vx*dt;self.y+=self.vy*dt
        if self.x<1 or self.x>14:self.x=clamp(self.x,1,14);self.vx=-self.vx;self.emit_sound('collision')
        if self.vy>0 and math.hypot(self.x-self.paddle_x,self.y-self.paddle_y)<1.5:self.vy=-5.;self.vx=(self.x-self.paddle_x)*3;self.emit_sound('hit')
        if self.vy<0 and math.hypot(self.x-self.ax,self.y-3)<1.4:self.vy=5.+self.difficulty;self.vx=(self.x-self.ax)*3;self.emit_sound('hit')
        if self.y<1 or self.y>15:
            if 2<=self.x<=14:
                if self.y<1:self.goals+=1;self.award(100)
                else:self.against+=1
                self.x=self.y=8.;self.vx=-1. if self.goals%2 else 1.;self.vy=3.
            else:self.y=clamp(self.y,1,15);self.vy=-self.vy
        if self.goals>=3:self.finish(True)
        elif self.against>=3 or self.elapsed>(80,65,50)[self.difficulty]:self.finish(False)
    def progress(self):return self.goals*100//3
    def draw(self,fb):
        line(fb,1,1,14,1,(35,70,70));line(fb,1,15,14,15,(35,70,70));line(fb,1,8,14,8,(15,35,40));disc(fb,self.paddle_x,self.paddle_y,1.1,(60,170,255));disc(fb,self.ax,3,1.1,(255,80,95))
        BatchCartridge.px(fb,round(self.x),round(self.y),(245,245,245))
    def get_status(self):
        s=super().get_status();s["lives"]=max(0,3-self.against);return s
