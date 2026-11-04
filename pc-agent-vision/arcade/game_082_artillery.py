from .b3_helpers import *


class Game082Artillery(BatchCartridge):
    game_id=82;name='坦克抛物线对轰';english_name='Artillery';core_mechanic='Choose elevation and power, fire a gravity shell over terrain, damage the enemy and deform impact terrain before its return shot.'
    control_type=3
    def setup(self):self.angle=.8;self.power=8.;self.x=2.;self.y=10.;self.vx=self.vy=0.;self.terrain=[13]*16;self.terrain[7]=self.terrain[8]=11;self.hp=self.enemy_hp=3;self.owner=self.shots=0;self.flying=False
    def tick(self,dt,down,pressed):
        if not self.flying:
            self.angle=clamp(self.angle+dt*(bool(down&KEY_RIGHT)-bool(down&KEY_LEFT)),.2,1.4);self.power=clamp(self.power+3*dt*(bool(down&KEY_UP)-bool(down&KEY_DOWN)),4,11)
            if pressed&KEY_A:self.x=2.;self.y=self.terrain[2]-1.;self.vx=math.cos(self.angle)*self.power;self.vy=-math.sin(self.angle)*self.power;self.flying=True;self.owner=0;self.shots+=1;self.emit_sound('action')
        else:
            self.vy+=5*dt;self.x+=self.vx*dt;self.y+=self.vy*dt;ix=int(self.x)
            if self.x<0 or self.x>=16 or (0<=ix<16 and self.y>=self.terrain[ix]):
                target=13 if self.owner==0 else 2
                if abs(self.x-target)<1.5:
                    if self.owner==0:self.enemy_hp-=1;self.award(100)
                    else:self.hp-=1
                    self.emit_sound('hit')
                if 0<=ix<16:self.terrain[ix]=min(15,self.terrain[ix]+1)
                if not self.enemy_hp:self.award(500);self.finish(True);return
                if not self.hp:self.finish(False);return
                if self.owner==0:
                    self.owner=1;self.x=13.;self.y=self.terrain[13]-1.;target=2+(2,1,.25)[self.difficulty];duration=2.;self.vx=(target-13)/duration;self.vy=(self.terrain[2]-self.y-2.5*duration*duration)/duration
                else:self.flying=False
        if self.elapsed>(120,100,80)[self.difficulty]:self.finish(False)
    def progress(self):return (3-self.enemy_hp)*100//3
    def draw(self,fb):
        for x,h in enumerate(self.terrain):line(fb,x,h,x,15,(65,90,55))
        self.px(fb,2,self.terrain[2]-1,(70,190,240));self.px(fb,13,self.terrain[13]-1,(245,80,90))
        if self.flying:self.px(fb,int(self.x),int(self.y),(255,230,120))
    def get_status(self):
        s=super().get_status();s["lives"]=max(0,self.hp);return s
