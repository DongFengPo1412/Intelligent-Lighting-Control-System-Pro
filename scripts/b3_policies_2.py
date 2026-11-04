"""Production-simulator planning only; returned values are real button masks."""
import math
import copy
from collections import deque
from arcade.base_cartridge import *
DT=16667/1_000_000


def peggle(g,won,c):
    if not won:return 0,0
    if g.flying:return 0,0
    plan=c.get('plan',[])
    if not plan:
        best=None
        for target in [i*.04 for i in range(-24,25)]:
            n=round(abs(target-g.aim)/(1.2*DT));key=KEY_RIGHT if target>g.aim else KEY_LEFT
            trial=copy.deepcopy(g)
            for _ in range(n):trial.update(DT,key,0)
            trial.update(DT,0,KEY_A)
            for ticks in range(1000):
                if trial.state!=STATE_PLAYING or not trial.flying:break
                trial.update(DT,0,0)
            value=(g.mask.bit_count()-trial.mask.bit_count(),-ticks)
            if best is None or value>best[0]:best=(value,n,key)
        assert best and best[0][0]>0,('unreachable peg',g.mask,g.balls,g.difficulty)
        _,n,key=best;plan=[(key,0)]*n+[(0,KEY_A)];c['plan']=plan
    return plan.pop(0)


def marble(g,won,c):
    if not won:return 0,0
    targets=((3,7),(7,7),(8,10),(12,10),(13,13));index=c.get('index',0);tx,ty=targets[index]
    distance=math.hypot(tx-g.x,ty-g.y)
    if distance<.25 and math.hypot(g.vx,g.vy)<.45 and index<len(targets)-1:index+=1;c['index']=index;tx,ty=targets[index]
    vx=max(-1.5,min(1.5,(tx-g.x)*2));vy=max(-1.5,min(1.5,(ty-g.y)*2))
    key=KEY_RIGHT if g.vx<vx-.07 else KEY_LEFT if g.vx>vx+.07 else 0
    key|=KEY_DOWN if g.vy<vy-.07 else KEY_UP if g.vy>vy+.07 else 0
    if distance<.45:key|=KEY_A
    return key,0


def defender(g,won,c):
    if not won:return 0,0
    live=[i for i,e in enumerate(g.enemy) if e]
    if not live:return 0,0
    target=min(live,key=lambda i:abs((g.ex[i]-g.x+16)%32-16));dx=(g.ex[target]-g.x+16)%32-16;dy=g.ey[target]-g.y
    key=KEY_RIGHT if dx>3.5 or -2.8<dx<0 else KEY_LEFT if dx< -3.5 or 0<dx<2.8 else 0
    key|=KEY_DOWN if dy>.12 else KEY_UP if dy<-.12 else 0
    if abs(dy)<.55:key|=KEY_A
    return key,0


def dig(g,won,c):
    if not won:return 0,0
    step=c.get('step',0);c['step']=step+1
    if step<28:
        return (0,(KEY_RIGHT if step<14 else KEY_LEFT)) if step%7==0 else (0,0)
    for i in range(3):
        if not g.enemy[i]:continue
        dx=g.ex[i]-g.x;dy=g.ey[i]-g.y
        if (dx==0 or dy==0) and 0<abs(dx)+abs(dy)<=4:
            key=KEY_RIGHT if dx>0 else KEY_LEFT if dx<0 else KEY_DOWN if dy>0 else KEY_UP
            return KEY_A|key,0
    return 0,0


def qbert(g,won,c):
    if not won:return 0,KEY_UP if g.hop<=0 else 0
    if 'plan' not in c:
        seen={(0,0)};path=[]
        def visit(r,col):
            for key,dr,dc,inverse in ((KEY_LEFT,1,0,KEY_RIGHT),(KEY_DOWN,1,1,KEY_UP),(KEY_UP,-1,-1,KEY_DOWN),(KEY_RIGHT,-1,0,KEY_LEFT)):
                nr,nc=r+dr,col+dc
                if 0<=nr<5 and 0<=nc<=nr and (nr,nc) not in seen:
                    seen.add((nr,nc));path.append(key);visit(nr,nc)
                    if len(seen)==15:return
                    path.append(inverse)
        visit(0,0);c['plan']=path
    if g.hop<=0 and c['plan']:return 0,c['plan'].pop(0)
    return 0,0


def fog(g,won,c):
    if not won:return 0,0
    if 'plan' not in c:
        start=(g.x,g.y);parent={start:None};todo=deque([start])
        while todo:
            x,y=todo.popleft()
            if (x,y)==(13,13):break
            for key,dx,dy in ((KEY_LEFT,-1,0),(KEY_RIGHT,1,0),(KEY_UP,0,-1),(KEY_DOWN,0,1)):
                pos=x+dx,y+dy
                if not g.grid[pos[1]][pos[0]] and pos not in parent:parent[pos]=((x,y),key);todo.append(pos)
        path=[];pos=(13,13)
        while parent[pos] is not None:pos,key=parent[pos];path.append(key)
        c['plan']=path[::-1];c['wait']=0
    if c['wait']:c['wait']-=1;return 0,0
    c['wait']=6
    return 0,c['plan'].pop(0) if c['plan'] else 0


POLICIES={24:peggle,25:marble,32:defender,36:dig,37:qbert,39:fog}
