"""Legal triangle solver and actual sports/duel feedback controllers."""
import copy,math
from collections import deque
from arcade.base_cartridge import *
DT=16667/1000000

def peg(g,won,c):
    if not won:return 0,0
    if 'plan' not in c:
        jumps=[]
        for y in range(5):
            for x in range(y+1):
                for d,(dx,dy) in enumerate(((1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,-1))):
                    mx=x+dx;my=y+dy;tx=x+2*dx;ty=y+2*dy
                    if 0<=my<5 and 0<=mx<=my and 0<=ty<5 and 0<=tx<=ty:jumps.append((x,y,d,y*(y+1)//2+x,my*(my+1)//2+mx,ty*(ty+1)//2+tx))
        failed=set()
        def dfs(mask):
            if mask.bit_count()==1:return []
            if mask in failed:return None
            for x,y,d,a,b,t in jumps:
                if mask&(1<<a) and mask&(1<<b) and not mask&(1<<t):
                    p=dfs(mask^(1<<a)^(1<<b)^(1<<t))
                    if p is not None:return [(x,y,d)]+p
            failed.add(mask);return None
        c['plan']=dfs(g.mask);assert c['plan']
    x,y,d=c['plan'][0]
    if g.y!=y:return 0,KEY_DOWN if g.y<y else KEY_UP
    if g.x!=x:return 0,KEY_RIGHT if g.x<x else KEY_LEFT
    if g.dir!=d:return 0,KEY_B
    c['plan'].pop(0);return 0,KEY_A

def bowling(g,won,c):
    if g.flying:return 0,0
    if not won:
        if g.aim<.999:return KEY_RIGHT,0
        return KEY_A if g.power<.15 else 0,0
    if c.get('nroll')!=g.nroll:
        best=None
        for target in [i*.05 for i in range(-20,21)]:
            n=round(abs(target-g.aim)/DT);key=KEY_RIGHT if target>g.aim else KEY_LEFT;t=copy.deepcopy(g)
            for _ in range(n):t.update(DT,key,0)
            for _ in range(36):t.update(DT,KEY_A,0)
            t.update(DT,0,0)
            for _ in range(240):
                if not t.flying:break
                t.update(DT,0,0)
            knocked=t.rolls[-1] if t.nroll>g.nroll else -1
            value=(knocked,-n)
            if best is None or value>best[0]:best=(value,n,key)
        _,n,key=best;c.update(nroll=g.nroll,plan=[(key,0)]*n+[(KEY_A,0)]*36+[(0,0)])
    return c['plan'].pop(0) if c['plan'] else (0,0)

def baseball(g,won,c):return (0,KEY_A if g.active and g.ball_y>=11.9 else 0) if won else (0,0)

def penalty(g,won,c):
    if not won:return 0,0
    if g.flying:return 0,0
    if g.aim<11.9:return KEY_RIGHT,0
    # Release only when the moving keeper will be at the other side on arrival.
    if g.charging:
        keeper=8+4*math.sin((g.elapsed+.5+DT)*(2,3,4)[g.difficulty])
        if g.power>=.1 and abs(g.aim-keeper)>(2,2.5,3)[g.difficulty]+.4:return 0,0
        if g.power>.95:return 0,0
        return KEY_A,0
    keeper=8+4*math.sin((g.elapsed+.7)*(2,3,4)[g.difficulty])
    return (KEY_A,0) if keeper<7 else (0,0)

def tron(g,won,c):
    if not won:return 0,0
    if g.clock+DT<(.16,.13,.10)[g.difficulty]:return 0,0
    options=[]
    for d,key in enumerate((KEY_UP,KEY_RIGHT,KEY_DOWN,KEY_LEFT)):
        if d==(g.dir+2)%4:continue
        t=copy.deepcopy(g);t.update(DT,0,key)
        if t.state==STATE_GAMEOVER:continue
        seen={(t.x,t.y)};q=deque(seen)
        while q:
            x,y=q.popleft()
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                p=(x+dx,y+dy)
                if 1<=p[0]<=14 and 1<=p[1]<=14 and p not in seen and not t.board[p[1]*16+p[0]]:seen.add(p);q.append(p)
        options.append(((10000 if t.state==STATE_VICTORY else len(seen)),d==g.dir,key))
    return 0,max(options)[2] if options else 0

def artillery(g,won,c):
    if not won or g.flying:return 0,0
    if c.get('shots')!=g.shots:
        best=None
        for angle in [.35+i*.025 for i in range(40)]:
            for power in [6+i*.25 for i in range(19)]:
                t=copy.deepcopy(g);n=round(abs(angle-g.angle)/DT);k=KEY_RIGHT if angle>g.angle else KEY_LEFT
                for _ in range(n):t.update(DT,k,0)
                m=round(abs(power-t.power)/(3*DT));p=KEY_UP if power>t.power else KEY_DOWN
                for _ in range(m):t.update(DT,p,0)
                t.update(DT,0,KEY_A)
                for steps in range(300):
                    t.update(DT,0,0)
                    if t.owner or t.state!=STATE_PLAYING:break
                if t.enemy_hp<g.enemy_hp:
                    value=n+m
                    if best is None or value<best[0]:best=(value,n,k,m,p)
        assert best,('no ballistic solution',g.terrain)
        _,n,k,m,p=best;c.update(shots=g.shots,plan=[(k,0)]*n+[(p,0)]*m+[(0,KEY_A)])
    return c['plan'].pop(0)
POLICIES={71:peg,77:bowling,78:baseball,79:penalty,80:tron,82:artillery}
