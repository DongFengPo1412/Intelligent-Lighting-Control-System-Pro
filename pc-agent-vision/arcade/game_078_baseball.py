from .b3_helpers import *


class Game078Baseball(BatchCartridge):
    game_id=78;name='棒球击打';english_name='Baseball';core_mechanic='A pitched ball approaches the plate; a timed swing earns hits or home runs, while missed pitches accumulate strikes.'
    control_type=0
    def setup(self):self.ball_y=1.;self.wait=.5;self.pitches=self.runs=self.strikes=0;self.active=False
    def tick(self,dt,down,pressed):
        if not self.active:
            self.wait-=dt
            if self.wait<=0:self.active=True;self.ball_y=1.;self.pitches+=1
        else:
            self.ball_y+=(5,6,7)[self.difficulty]*dt
            if pressed&KEY_A:
                if abs(self.ball_y-12)<(1.1,.8,.55)[self.difficulty]:self.runs+=2 if abs(self.ball_y-12)<.25 else 1;self.award(100);self.emit_sound('hit')
                else:self.strikes+=1;self.emit_sound('collision')
                self.active=False;self.wait=.5
            elif self.ball_y>14:self.strikes+=1;self.active=False;self.wait=.5;self.emit_sound('collision')
        if self.runs>=6:self.award(500);self.finish(True)
        elif self.strikes>=3 or (self.pitches>=10 and not self.active) or self.elapsed>60:self.finish(False)
    def progress(self):return self.runs*100//6
    def draw(self,fb):
        line(fb,8,1,8,14,(30,55,60));line(fb,5,13,11,13,(230,190,70));self.px(fb,8,int(self.ball_y),(255,255,255))
        for i in range(self.runs):self.px(fb,i+1,0,(60,220,110))
        for i in range(self.strikes):self.px(fb,i+1,15,(245,60,80))
