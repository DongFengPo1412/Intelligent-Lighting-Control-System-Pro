from .b3_helpers import *


class Game007Downwell(BatchCartridge):
    game_id=7;name='向下射击';english_name='Downwell';core_mechanic='Fall through a vertical shaft, fire downward with finite ammo, reload on shelves and defeat enemies before landing.'
    control_type=3
    def setup(self):
        self.x=8.;self.y=2.;self.vy=0.;self.ammo=(4,3,2)[self.difficulty];self.kills=0;self.hp=(3,2,1)[self.difficulty];self.grounded=False;self.bullets=[];self.enemy=[True]*3
    def tick(self,dt,down,pressed):
        keys=down|pressed;self.x=clamp(self.x+dt*4*((bool(keys&KEY_RIGHT))-(bool(keys&KEY_LEFT))),1,14)
        if pressed&KEY_A and self.ammo and len(self.bullets)<8:
            self.ammo-=1;self.bullets.append([self.x,self.y+1]);self.vy-=1.2;self.emit_sound('shot')
        for b in self.bullets:
            b[1]+=14*dt
            for i,ey in enumerate((10,22,34)):
                if self.enemy[i] and abs(b[0]-8)<.8 and ey<=b[1]<=ey+1:self.enemy[i]=False;self.kills+=1;self.award(100);b[1]=100;self.emit_sound('hit',i)
        self.bullets=[b for b in self.bullets if b[1]<48]
        old=self.y;self.vy=min(6.,self.vy+(7,8,9)[self.difficulty]*dt);self.y+=self.vy*dt;self.grounded=False
        for sy,lo,hi in ((12,2,6),(24,9,13),(36,2,6),(46,1,14)):
            if self.vy>=0 and lo<=self.x<=hi and old<=sy-1<=self.y:self.y=sy-1;self.vy=0.;self.ammo=(4,3,2)[self.difficulty];self.grounded=True
        for i,ey in enumerate((10,22,34)):
            if self.enemy[i] and abs(self.x-8)<.8 and abs(self.y-ey)<.8:self.enemy[i]=False;self.hp-=1;self.emit_sound('collision')
        if self.hp<=0 or self.elapsed>60:self.finish(False)
        elif self.y>=45:self.award(500 if self.kills==3 else 0);self.finish(self.kills==3)
    def progress(self):return int((self.y-2)/43*100)
    def draw(self,fb):
        cam=max(0,int(self.y)-7)
        for yy in range(16):self.px(fb,0,yy,(40,45,60));self.px(fb,15,yy,(40,45,60))
        for sy,lo,hi in ((12,2,6),(24,9,13),(36,2,6),(46,1,14)):line(fb,lo,sy-cam,hi,sy-cam,(55,190,180))
        for i,ey in enumerate((10,22,34)):
            if self.enemy[i]:self.px(fb,8,ey-cam,(255,60,80))
        for bx,by in self.bullets:self.px(fb,round(bx),round(by)-cam,(255,210,40))
        self.px(fb,round(self.x),round(self.y)-cam,(240,245,255))
        for i in range(self.ammo):self.px(fb,i+1,0,(240,195,30))
    def get_status(self):
        s=super().get_status();s["lives"]=max(0,self.hp);return s
