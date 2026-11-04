from .batch_cartridge import *


class Game098LunarLander(BatchCartridge):
    game_id=98;name='月球着陆';english_name='Lunar Lander';core_mechanic='Rotate and thrust against gravity; land slowly and upright inside the pad with limited fuel.'
    def setup(self):
        self.x=4.;self.y=2.;self.vx=self.vy=self.angle=0.;self.fuel=(45.,35.,25.)[self.difficulty];self.thrusting=False
    def tick(self,dt,down,pressed):
        keys=down|pressed
        self.angle=max(-.8,min(.8,self.angle+dt*1.8*((1 if keys&KEY_RIGHT else 0)-(1 if keys&KEY_LEFT else 0))))
        was_thrusting=self.thrusting
        self.thrusting=bool(keys&(KEY_A|KEY_UP)) and self.fuel>0
        thrust=3.8 if self.thrusting else 0.
        if self.thrusting:
            self.fuel=max(0.,self.fuel-2*dt)
            if not was_thrusting:self.emit_sound('shot')
        self.vx+=(math.sin(self.angle)*thrust+(.0,.03,.05)[self.difficulty])*dt
        self.vy+=((1.6,1.8,2.)[self.difficulty]-math.cos(self.angle)*thrust)*dt
        self.x+=self.vx*dt;self.y+=self.vy*dt
        half=(3.,2.,1.)[self.difficulty]
        onpad=8-half<=self.x<=8+half
        ground=13 if onpad else 10+int(max(0,min(15,self.x)))%3
        if self.y>=ground:
            safe=onpad and 0<=self.vy<=(1.4,1.1,.8)[self.difficulty] and abs(self.vx)<=(.7,.55,.4)[self.difficulty] and abs(self.angle)<=.25
            if safe:self.award(1000+int(self.fuel*10))
            self.emit_sound('hit' if safe else 'collision');self.finish(safe)
        elif self.x<.5 or self.x>14.5 or self.y<.5 or self.elapsed>60:self.finish(False)
    def progress(self):return int(max(0,min(100,(self.y-2)/11*100)))
    def draw(self,fb):
        half=(3,2,1)[self.difficulty]
        for x in range(16):
            pad=8-half<=x<=8+half;ground=13 if pad else 10+x%3
            for y in range(ground,16):self.px(fb,x,y,(40,220,130) if pad and y==13 else (45,50,65))
        x,y=round(self.x),round(self.y);self.px(fb,x,y,(245,245,255));self.px(fb,x+(-1 if self.angle<0 else 1),y,(100,160,255))
        if self.thrusting:self.px(fb,x,y+1,(255,130,25))
        for i in range(int(self.fuel/(45,35,25)[self.difficulty]*14)):self.px(fb,i+1,0,(255,200,40))
