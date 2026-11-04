from .batch_cartridge import *


class Game057RushHour(BatchCartridge):
    game_id=57;name='堵车';english_name='Rush Hour';core_mechanic='Slide fixed-axis cars to free the red target car.'
    def setup(self):
        self.cars=[[0,2,2,0],[2,0,3,1],[3,0,3,0],[5,2,2,1],[1,4,2,0],[0,4,2,1],[3,5,2,0]]
        self.selected=0;self.moves=0
    def occupied(self,x,y,ignore):
        for i,(cx,cy,n,v) in enumerate(self.cars):
            if i!=ignore and any((cx+(0 if v else k),cy+(k if v else 0))==(x,y) for k in range(n)):return True
        return False
    def tick(self,dt,down,pressed):
        if pressed&KEY_A:self.selected=(self.selected+1)%7;self.emit_sound('action',self.selected)
        elif pressed&KEY_B:self.selected=(self.selected+6)%7;self.emit_sound('action',self.selected)
        dx,dy=self.direction(down,pressed);c=self.cars[self.selected]
        delta=dy if c[3] else dx
        if delta:
            x,y,n,v=c;nx=x+(0 if v else delta);ny=y+(delta if v else 0)
            cells=[(nx+(0 if v else k),ny+(k if v else 0)) for k in range(n)]
            if all(0<=a<6 and 0<=b<6 and not self.occupied(a,b,self.selected) for a,b in cells):
                c[0]=nx;c[1]=ny;self.moves+=1;self.emit_sound('hit',self.selected)
                if self.cars[0][0]==4:self.award(max(100,1200-self.moves*20));self.finish(True);return
        if self.moves>=(50,30,16)[self.difficulty] or self.elapsed>(120,90,60)[self.difficulty]:self.finish(False)
    def progress(self):return self.cars[0][0]*25
    def draw(self,fb):
        palette=((245,55,55),(40,180,255),(245,200,35),(140,70,230),(40,220,120),(230,100,40),(200,80,160))
        for y in range(6):
            for x in range(6):self.cell(fb,x,y,(20,25,32))
        for i,(x,y,n,v) in enumerate(self.cars):
            for k in range(n):self.cell(fb,x+(0 if v else k),y+(k if v else 0),palette[i])
        c=self.cars[self.selected];self.px(fb,2+c[0]*2,2+c[1]*2,(255,255,255))
        self.px(fb,15,6,(30,255,70));self.px(fb,15,7,(30,255,70))
