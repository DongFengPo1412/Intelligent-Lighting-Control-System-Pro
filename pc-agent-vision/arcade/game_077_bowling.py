from .b3_helpers import *


class Game077Bowling(BatchCartridge):
    game_id=77;name='保龄球';english_name='Bowling';core_mechanic='Aim and charge a rolling ball, knock down a rack, and play ten frames with strike/spare bonuses including tenth-frame extra rolls.'
    control_type=3
    def setup(self):self.aim=self.power=0.;self.x=8.;self.y=14.;self.vx=self.vy=0.;self.charging=self.flying=False;self.pins=1023;self.frame=self.shot=self.first=self.nroll=0;self.rolls=[];self.before=10
    def total(self):return bowling_total(self.rolls)
    def resolve(self):
        knocked=self.before-self.pins.bit_count()
        knocked=max(0,knocked);self.rolls.append(knocked);self.nroll=len(self.rolls);self._score=self.total();self._high_score=max(self._high_score,self.score);self.emit_sound('hit',knocked);self.flying=False
        if self.frame<9:
            if self.shot==0 and knocked<10:self.first=knocked;self.shot=1
            else:self.frame+=1;self.shot=0;self.first=0;self.pins=1023
        else:
            if self.shot==0:self.first=knocked;self.shot=1;self.pins=1023 if knocked==10 else self.pins
            elif self.shot==1:
                if self.first==10 or self.first+knocked==10:self.shot=2;self.pins=1023 if knocked==10 or self.first<10 else self.pins;self.first=0
                else:self.frame=10
            else:self.frame=10
        if self.frame==10:self.finish(self.score>=(60,90,120)[self.difficulty])
    def tick(self,dt,down,pressed):
        if not self.flying:
            self.aim=clamp(self.aim+dt*(bool(down&KEY_RIGHT)-bool(down&KEY_LEFT)),-1,1)
            if down&KEY_A:self.charging=True;self.power=min(1.2,self.power+dt)
            elif self.charging:self.charging=False;self.flying=True;self.before=self.pins.bit_count();self.x=8.;self.y=14.;self.vx=self.aim*3;self.vy=-(6+6*self.power);self.power=0.;self.emit_sound('action')
        else:
            self.x+=self.vx*dt;self.y+=self.vy*dt
            locations=((8,2),(7,3),(9,3),(6,4),(8,4),(10,4),(5,5),(7,5),(9,5),(11,5))
            for i,(x,y) in enumerate(locations):
                if self.pins&(1<<i) and math.hypot(self.x-x,self.y-y)<(1.1,.95,.8)[self.difficulty]:
                    self.pins&=~(1<<i)
                    frontier={i}
                    for _ in range(3 if abs(self.vy)>9 else 1):
                        next_set={j for j,(xx,yy) in enumerate(locations) if self.pins&(1<<j) and any(yy<=locations[k][1] and math.hypot(xx-locations[k][0],yy-locations[k][1])<=2.3 for k in frontier)}
                        for j in next_set:self.pins&=~(1<<j)
                        frontier=next_set
            if self.y<0 or self.x<0 or self.x>15:self.resolve()
        if self.elapsed>(300,240,180)[self.difficulty]:self.finish(False)
    def progress(self):return self.frame*10
    def draw(self,fb):
        line(fb,3,0,3,15,(45,65,95));line(fb,13,0,13,15,(45,65,95))
        for i,(x,y) in enumerate(((8,2),(7,3),(9,3),(6,4),(8,4),(10,4),(5,5),(7,5),(9,5),(11,5))):
            if self.pins&(1<<i):self.px(fb,x,y,(245,245,245))
        disc(fb,self.x if self.flying else 8+self.aim*4,self.y if self.flying else 14,.7,(80,190,240))
