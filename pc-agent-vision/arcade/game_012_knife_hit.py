from .b3_helpers import *


class Game012KnifeHit(BatchCartridge):
    game_id=12;name='旋盘投刀';english_name='Knife Hit';core_mechanic='Throw knives into a rotating target while avoiding all already embedded blade angles.'
    control_type=0
    def setup(self):self.theta=0.;self.knife_y=14.;self.angles=[0.,math.pi];self.hits=0;self.flying=False
    def tick(self,dt,down,pressed):
        self.theta=wrap(self.theta+( (.8,1.1,1.5)[self.difficulty]+.2*math.sin(self.elapsed*.5))*dt)
        if pressed&KEY_A and not self.flying:self.flying=True;self.knife_y=14.;self.emit_sound('shot')
        if self.flying:
            self.knife_y-=20*dt
            if self.knife_y<=10:
                local=wrap(math.pi/2-self.theta);self.flying=False
                if any(angle_distance(local,a)<(.4,.35,.30)[self.difficulty] for a in self.angles):self.emit_sound('collision');self.finish(False);return
                self.angles.append(local);self.hits+=1;self.award(50);self.emit_sound('hit',self.hits)
                if self.hits>=(8,10,12)[self.difficulty]:self.award(500);self.finish(True)
        if self.elapsed>(60,45,35)[self.difficulty]:self.finish(False)
    def progress(self):return self.hits*100//(8,10,12)[self.difficulty]
    def draw(self,fb):
        disc(fb,8,7,2.6,(100,65,35))
        for a in self.angles:
            a+=self.theta;line(fb,round(8+math.cos(a)*2.5),round(7+math.sin(a)*2.5),round(8+math.cos(a)*4),round(7+math.sin(a)*4),(220,230,245))
        if self.flying:line(fb,8,round(self.knife_y),8,round(self.knife_y)+2,(255,210,55))
