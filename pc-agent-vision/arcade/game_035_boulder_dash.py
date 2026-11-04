from .batch_cartridge import *


class Game035BoulderDash(BatchCartridge):
    control_type=CTRL_DPAD_4WAY
    game_id=35; name='落石夺宝'; english_name='Boulder Dash'; core_mechanic='Dig, push horizontal boulders, collect gems and escape falling rocks.'
    def setup(self):
        self.grid=[[1 if x in (0,15) or y in (0,15) else 2 for x in range(16)] for y in range(16)]
        for x in range(1,15): self.grid[2][x]=0
        for x,y in ((5,3),(9,3),(5,8),(9,8)): self.grid[y][x]=3
        for x,y in ((3,2),(12,2),(3,5),(12,5),(3,9),(12,9),(3,12),(12,12)): self.grid[y][x]=4
        self.grid[13][13]=5; self.x=2; self.y=2; self.gems=0; self.fall=0.
    def tick(self,dt,down,pressed):
        dx,dy=self.direction(down,pressed);nx=self.x+dx;ny=self.y+dy
        tile=self.grid[ny][nx]
        if (dx or dy) and tile==3 and dx and self.grid[ny][nx+dx]==0:
            self.grid[ny][nx+dx]=3;self.grid[ny][nx]=0;tile=0
            self.emit_sound('action')
        if (dx or dy) and tile not in (1,3):
            if tile==4:self.gems+=1;self.award(100);self.emit_sound('hit',self.gems)
            if tile!=5:self.grid[ny][nx]=0
            self.x,self.y=nx,ny
            if tile==5 and self.gems==8:self.award(500);self.finish(True);return
        self.fall+=dt
        if self.fall>=(.18,.14,.10)[self.difficulty]:
            self.fall=0.
            for y in range(14,0,-1):
                for x in range(1,15):
                    if self.grid[y][x]!=3:continue
                    nx=x;ny=y+1
                    if self.grid[ny][nx]==3:
                        nx=next((x+d for d in (-1,1) if self.grid[y][x+d]==0 and self.grid[y+1][x+d]==0),x)
                    if self.grid[ny][nx]==0:
                        self.grid[y][x]=0;self.grid[ny][nx]=3
                        if (self.x,self.y)==(nx,ny):self.emit_sound('collision');self.finish(False);return
        if self.elapsed>(90,65,45)[self.difficulty]:self.finish(False)
    def progress(self):return self.gems*100//8
    def draw(self,fb):
        colors=((8,10,16),(65,80,100),(65,40,16),(150,155,170),(25,230,255),(40,220,70) if self.gems==8 else (30,65,35))
        for y,row in enumerate(self.grid):
            for x,t in enumerate(row):self.px(fb,x,y,colors[t])
        self.px(fb,self.x,self.y,(255,200,40))
        for x in range(self.gems):self.px(fb,x+1,0,(20,255,255))
