from .batch_cartridge import *


class Game058ProgramRobot(BatchCartridge):
    game_id=58;name='编程机器人';english_name='Program Robot';core_mechanic='Queue relative movement instructions, trigger a switch and execute through a locked gate.'
    def setup(self):
        self.program=[];self.attempts=3;self.reset_robot()
    def reset_robot(self):
        self.x=1;self.y=6;self.heading=0;self.door=False;self.running=False;self.pc=0;self.clock=0.
    def wall(self,x,y):return not (1<=x<=6 and 1<=y<=6) or (y==2 and x!=3) or (x==3 and y==2 and not self.door)
    def fail_program(self):
        self.attempts-=1;self.emit_sound('collision');self.reset_robot()
        if not self.attempts:self.finish(False)
    def tick(self,dt,down,pressed):
        if pressed&KEY_B:
            if self.running:self.reset_robot()
            elif self.program:self.program.pop()
        if not self.running:
            for bit,cmd in ((KEY_UP,0),(KEY_LEFT,1),(KEY_RIGHT,2),(KEY_DOWN,3)):
                if pressed&bit and len(self.program)<(20,17,14)[self.difficulty]:self.program.append(cmd);self.emit_sound('action',cmd)
            if pressed&KEY_A and self.program:self.reset_robot();self.running=True
        else:
            self.clock+=dt
            if self.clock>=(.30,.24,.18)[self.difficulty]:
                self.clock=0.
                if self.pc>=len(self.program):self.fail_program();return
                cmd=self.program[self.pc];self.pc+=1
                if cmd==1:self.heading=(self.heading+3)%4
                elif cmd==2:self.heading=(self.heading+1)%4
                elif cmd==0:
                    dx,dy=((0,-1),(1,0),(0,1),(-1,0))[self.heading];nx=self.x+dx;ny=self.y+dy
                    if self.wall(nx,ny):self.fail_program();return
                    self.x,self.y=nx,ny
                    if (nx,ny)==(3,4):self.door=True;self.emit_sound('hit')
                    if (nx,ny)==(6,1) and self.door:self.award(1000+50*self.attempts);self.finish(True);return
        if self.elapsed>(100,75,50)[self.difficulty]:self.finish(False)
    def progress(self):return 100 if self.state==STATE_VICTORY else 50 if self.door else 0
    def get_status(self):
        status=super().get_status();status['lives']=self.attempts
        return status
    def draw(self,fb):
        for y in range(8):
            for x in range(8):self.cell(fb,x,y,(55,65,85) if self.wall(x,y) else (8,16,25),2,0)
        self.cell(fb,3,4,(245,190,20),2,0);self.cell(fb,3,2,(20,160,170) if self.door else (190,45,45),2,0)
        self.cell(fb,6,1,(40,220,70),2,0);self.cell(fb,self.x,self.y,(245,245,245),2,0)
        for i in range(2):
            dx,dy=((i,0),(1,i),(i,1),(0,i))[self.heading]
            self.px(fb,self.x*2+dx,self.y*2+dy,(60,180,255))
        palette=((40,230,100),(255,180,20),(40,160,255),(150,70,200))
        offset=max(0,len(self.program)-16)
        for i,cmd in enumerate(self.program[offset:]):self.px(fb,i,0,(255,255,255) if self.running and offset+i==self.pc else palette[cmd])
