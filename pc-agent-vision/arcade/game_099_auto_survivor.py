from .b3_helpers import *


class Game099AutoSurvivor(BatchCartridge):
    game_id=99;name='自动攻击生存';english_name='Auto Attack Survivor';core_mechanic='Move through a pursuing horde while automatically attacking nearby enemies; kills grant a damage or firing-rate upgrade.'
    control_type=3
    def setup(self):self.x=self.y=8.;self.ex=[0.]*12;self.ey=[0.]*12;self.ehp=[0]*12;self.ex[0]=8.;self.ey[0]=3.;self.ehp[0]=1;self.spawn=self.attack=self.invul=0.;self.hp=(5,4,3)[self.difficulty];self.kills=0;self.damage=1;self.upgrades=0;self.rate_bonus=0;self.seed=0x99ab
    def tick(self,dt,down,pressed):
        self.x=clamp(self.x+3*dt*(bool(down&KEY_RIGHT)-bool(down&KEY_LEFT)),1,14);self.y=clamp(self.y+3*dt*(bool(down&KEY_DOWN)-bool(down&KEY_UP)),1,14)
        if self.kills>=3*(self.upgrades+1) and self.upgrades<2 and pressed&(KEY_A|KEY_B):
            self.upgrades+=1
            if pressed&KEY_A:self.damage+=1
            else:self.rate_bonus+=1
            self.emit_sound('hit',self.upgrades)
        self.spawn+=dt;self.attack-=dt;self.invul=max(0.,self.invul-dt)
        if self.spawn>=(.9,.7,.5)[self.difficulty] and 0 in self.ehp:
            i=self.ehp.index(0);self.seed=rng(self.seed);side=(self.seed>>16)%4;self.seed=rng(self.seed);p=1+(self.seed>>16)%14;self.ex[i]=1. if side==0 else 14. if side==1 else float(p);self.ey[i]=1. if side==2 else 14. if side==3 else float(p);self.ehp[i]=(2,2,3)[self.difficulty];self.spawn=0.
        for i,hp in enumerate(self.ehp):
            if not hp:continue
            dx=self.x-self.ex[i];dy=self.y-self.ey[i];distance=math.hypot(dx,dy)
            if distance>.001:self.ex[i]+=dx/distance*(.8,1.,1.2)[self.difficulty]*dt;self.ey[i]+=dy/distance*(.8,1.,1.2)[self.difficulty]*dt
            if distance<.65 and not self.invul:self.hp-=1;self.invul=.6;self.emit_sound('collision')
        target=min((i for i,h in enumerate(self.ehp) if h),key=lambda i:math.hypot(self.x-self.ex[i],self.y-self.ey[i]),default=-1)
        if self.attack<=0 and target>=0 and math.hypot(self.x-self.ex[target],self.y-self.ey[target])<=4:
            self.ehp[target]=max(0,self.ehp[target]-self.damage);self.attack=max(.18,.65-.1*self.upgrades-.1*self.rate_bonus);self.emit_sound('action')
            if not self.ehp[target]:self.kills+=1;self.award(25)
        if self.hp<=0:self.finish(False)
        elif self.elapsed>=(30,40,50)[self.difficulty] and self.kills>=8:self.award(1000);self.finish(True)
        elif self.elapsed>=(60,70,80)[self.difficulty]:self.finish(False)
    def progress(self):return min(100,int(self.elapsed*100/(30,40,50)[self.difficulty]))
    def draw(self,fb):
        for i,h in enumerate(self.ehp):
            if h:self.px(fb,int(self.ex[i]),int(self.ey[i]),(235,70,95))
        self.px(fb,int(self.x),int(self.y),(95,220,240))
        for i in range(max(0,self.hp)):self.px(fb,i,0,(65,220,100))
        if self.kills>=3*(self.upgrades+1) and self.upgrades<2:self.px(fb,15,0,(245,215,55))
    def get_status(self):
        s=super().get_status();s["lives"]=max(0,self.hp);return s
