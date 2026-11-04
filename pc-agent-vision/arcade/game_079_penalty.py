from .b3_helpers import *


class Game079Penalty(BatchCartridge):
    game_id=79;name='足球点球';english_name='Penalty Shootout';core_mechanic='Aim and charge a shot against a moving goalkeeper; five attempts decide a three-goal challenge.'
    control_type=3
    def setup(self):self.aim=self.impact=self.keeper=8.;self.power=self.flight=0.;self.charging=self.flying=False;self.shots=self.goals=0
    def tick(self,dt,down,pressed):
        self.keeper=8+4*math.sin(self.elapsed*(2,3,4)[self.difficulty])
        if not self.flying:
            self.aim=clamp(self.aim+5*dt*(bool(down&KEY_RIGHT)-bool(down&KEY_LEFT)),3,12)
            if down&KEY_A:self.charging=True;self.power=min(1.2,self.power+dt)
            elif self.charging:self.charging=False;self.flying=True;self.impact=self.aim+(3 if self.power>1 else 0);self.flight=.5;self.power=0.;self.emit_sound('action')
        else:
            self.flight-=dt
            if self.flight<=0:
                self.shots+=1;self.flying=False
                if 3<=self.impact<=12 and abs(self.impact-self.keeper)>(2,2.5,3)[self.difficulty]:self.goals+=1;self.award(100);self.emit_sound('hit')
                else:self.emit_sound('collision')
                if self.shots==5:self.finish(self.goals>=3)
        if self.elapsed>(90,75,60)[self.difficulty]:self.finish(False)
    def progress(self):return self.shots*20
    def draw(self,fb):
        line(fb,2,1,13,1,(220,220,220));line(fb,2,1,2,5,(220,220,220));line(fb,13,1,13,5,(220,220,220));line(fb,int(self.keeper)-1,3,int(self.keeper)+1,3,(245,90,80));disc(fb,self.impact if self.flying else self.aim,4+self.flight*18 if self.flying else 13,.7,(245,230,170))
