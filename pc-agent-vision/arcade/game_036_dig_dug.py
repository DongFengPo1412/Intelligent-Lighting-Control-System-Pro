from .b3_helpers import *


class Game036DigDug(BatchCartridge):
    game_id=36;name='地下充气战';english_name='Dig Dug';core_mechanic='Dig tunnels, aim a held pump at pursuing monsters, maintain inflation until they burst.'
    control_type=3
    def setup(self):
        self.x=self.y=7;self.face=0;self.hp=(3,2,1)[self.difficulty];self.kills=0;self.ex=[3,12,13];self.ey=[3,2,13];self.inflate=[0.]*3;self.enemy=[True]*3;self.enemy_clock=0.;self.dirt=[[True]*16 for _ in range(16)];self.dirt[7][7]=False
    def tick(self,dt,down,pressed):
        keys=down|pressed;dx,dy=self.direction(down,pressed)
        if dx or dy:
            self.face=0 if dy<0 else 1 if dx>0 else 2 if dy>0 else 3
            if not keys&KEY_A:self.x=int(clamp(self.x+dx,1,14));self.y=int(clamp(self.y+dy,1,14));self.dirt[self.y][self.x]=False
        fx,fy=((0,-1),(1,0),(0,1),(-1,0))[self.face];target=-1
        if keys&KEY_A:
            for i in range(3):
                d=(self.ex[i]-self.x)*fx+(self.ey[i]-self.y)*fy
                if self.enemy[i] and 0<d<=4 and (self.ex[i]-self.x)*fy==(self.ey[i]-self.y)*fx:target=i;break
        for i in range(3):
            self.inflate[i]=self.inflate[i]+dt/(.30,.40,.50)[self.difficulty] if i==target else max(0.,self.inflate[i]-dt*.5)
            if self.enemy[i] and self.inflate[i]>=1:self.enemy[i]=False;self.kills+=1;self.award(200);self.emit_sound('hit',i)
        self.enemy_clock+=dt
        if self.enemy_clock>=(.65,.55,.45)[self.difficulty]:
            self.enemy_clock=0.
            for i in range(3):
                if not self.enemy[i] or i==target:continue
                dx=self.x-self.ex[i];dy=self.y-self.ey[i]
                if abs(dx)>=abs(dy) and dx:self.ex[i]+=1 if dx>0 else -1
                elif dy:self.ey[i]+=1 if dy>0 else -1
                if (self.ex[i],self.ey[i])==(self.x,self.y):self.hp-=1;self.enemy[i]=False;self.emit_sound('collision')
        if self.kills==3:self.award(500);self.finish(True)
        elif self.hp<=0 or self.elapsed>60:self.finish(False)
    def progress(self):return self.kills*100//3
    def draw(self,fb):
        for y in range(1,15):
            for x in range(1,15):self.px(fb,x,y,(70,38,18) if self.dirt[y][x] else (8,12,20))
        for i in range(3):
            if self.enemy[i]:self.px(fb,self.ex[i],self.ey[i],(255,int(60+150*self.inflate[i]),80))
        self.px(fb,self.x,self.y,(245,245,255))
    def get_status(self):
        s=super().get_status();s["lives"]=max(0,self.hp);return s
