from .b3_helpers import *


class Game059CutRope(BatchCartridge):
    game_id=59;name='割绳子';english_name='Cut the Rope';core_mechanic='A rope constrains a swinging candy; cut at the correct time and preserve tangential momentum to feed the target.'
    control_type=0
    def setup(self):self.x=8.;self.y=8.;self.vx=self.vy=self.theta=0.;self.cut=False;self.tries=(3,2,1)[self.difficulty]
    def tick(self,dt,down,pressed):
        speed=(1.2,1.5,1.8)[self.difficulty];a=math.sin(self.elapsed*speed)*1.1;rate=math.cos(self.elapsed*speed)*1.1*speed
        if not self.cut:
            self.theta=a;self.x=8+5*math.sin(a);self.y=2+5*math.cos(a);self.vx=5*math.cos(a)*rate;self.vy=-5*math.sin(a)*rate
            if pressed&KEY_A:self.cut=True;self.emit_sound('action')
        else:
            self.vy+=5*dt;self.x+=self.vx*dt;self.y+=self.vy*dt
            if self.y>=13:
                if abs(self.x-12)<(1.8,1.3,.9)[self.difficulty]:self.award(1000+self.tries*50);self.finish(True)
                else:self.tries-=1;self.cut=False;self.emit_sound('collision')
        if self.tries<=0 or self.elapsed>(60,45,30)[self.difficulty]:self.finish(False)
    def progress(self):return 100 if self.state==STATE_VICTORY else 0
    def draw(self,fb):
        line(fb,10,14,14,14,(70,220,100));disc(fb,12,14,1,(70,220,100))
        if not self.cut:line(fb,8,2,int(self.x),int(self.y),(100,110,130))
        disc(fb,self.x,self.y,.8,(245,180,65))
    def get_status(self):
        s=super().get_status();s["lives"]=max(0,self.tries);return s
