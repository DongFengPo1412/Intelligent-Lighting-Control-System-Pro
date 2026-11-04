"""Hose routing, belt programming, maze solvers, horde feedback and visible-card memory."""
from collections import deque
import math
from arcade.base_cartridge import *

def fire(g,won,c):
    if not won:return 0,0
    def spray(x,y,face):
        dx,dy=((1,0),(-1,0),(0,1),(0,-1))[face]
        return any(0<=x+dx*n<8 and 0<=y+dy*n<8 and g.fire[(y+dy*n)*8+x+dx*n] for n in range(1,4))
    if not g.water:
        if (g.x,g.y)==(1,6):return 0,KEY_B
        return 0,KEY_RIGHT if g.x<1 else KEY_LEFT if g.x>1 else KEY_DOWN if g.y<6 else KEY_UP
    initial=(g.x,g.y,g.face)
    if spray(*initial):return 0,KEY_A
    q=deque([initial]);parent={initial:None};goal=None
    while q:
        x,y,face=q.popleft()
        if spray(x,y,face):goal=(x,y,face);break
        for dx,dy,f,k in ((1,0,0,KEY_RIGHT),(-1,0,1,KEY_LEFT),(0,1,2,KEY_DOWN),(0,-1,3,KEY_UP)):
            a=(max(0,min(7,x+dx)),max(0,min(7,y+dy)),f)
            if a not in parent:parent[a]=((x,y,face),k);q.append(a)
    assert goal;path=[]
    while parent[goal]:goal,k=parent[goal];path.append(k)
    return 0,path[-1]

def factory(g,won,c):
    if not won:return 0,0
    for x,y,d in ((3,3,3),(3,2,3),(3,1,0),(6,1,1),(6,2,1)):
        if g.belt[y*7+x]!=d:
            return 0,KEY_RIGHT if g.x<x else KEY_LEFT if g.x>x else KEY_DOWN if g.y<y else KEY_UP if g.y>y else KEY_A
    return 0,0

def wire(g,won,c):
    if not won:return 0,KEY_LEFT
    if 'path' not in c:
        initial=(g.x,g.y);goal=(13,1);q=deque([initial]);parent={initial:None}
        while q:
            x,y=q.popleft()
            if (x,y)==goal:break
            for dx,dy,k in ((1,0,KEY_RIGHT),(-1,0,KEY_LEFT),(0,1,KEY_DOWN),(0,-1,KEY_UP)):
                p=x+dx,y+dy
                if 0<=p[0]<16 and 0<=p[1]<16 and g.wire[p[1]*16+p[0]] and p not in parent:parent[p]=((x,y),k);q.append(p)
        path=[]
        while parent[goal]:goal,k=parent[goal];path.append(k)
        c['path']=path[::-1]
    return 0,c['path'].pop(0)

def ice(g,won,c):
    if g.sliding:return 0,0
    if not won:return 0,KEY_RIGHT if g.x==1 else KEY_LEFT
    if 'path' not in c:
        initial=(g.x,g.y);goal=(5,1);q=deque([initial]);parent={initial:None}
        while q:
            x,y=q.popleft()
            if (x,y)==goal:break
            for dx,dy,k in ((1,0,KEY_RIGHT),(-1,0,KEY_LEFT),(0,1,KEY_DOWN),(0,-1,KEY_UP)):
                xx=x;yy=y
                while g.MAP[yy+dy][xx+dx]!='#':xx+=dx;yy+=dy
                p=xx,yy
                if p not in parent:parent[p]=((x,y),k);q.append(p)
        assert goal in parent,'ice unsolvable';path=[]
        while parent[goal]:goal,k=parent[goal];path.append(k)
        c['path']=path[::-1];assert len(c['path'])<=8
    return 0,c['path'].pop(0)

def survivor(g,won,c):
    if won:
        tx=8+4*math.cos(g.elapsed*.6);ty=8+4*math.sin(g.elapsed*.6);options=[]
        for dx in (-1,0,1):
            for dy in (-1,0,1):
                x=max(1,min(14,g.x+dx*2));y=max(1,min(14,g.y+dy*2))
                distance=min((math.hypot(x-g.ex[i],y-g.ey[i]) for i,h in enumerate(g.ehp) if h),default=10)
                edge=sum(1/(v+.3) for v in (x-1,14-x,y-1,14-y))
                value=distance*2-edge*.6-math.hypot(x-tx,y-ty)*.15
                key=(KEY_RIGHT if dx>0 else KEY_LEFT if dx<0 else 0)|(KEY_DOWN if dy>0 else KEY_UP if dy<0 else 0)
                options.append((value,key))
        return max(options)[1],KEY_A
    # Deliberately intercept visible enemies rather than kite them.
    targets=[i for i,h in enumerate(g.ehp) if h]
    if not targets:return KEY_UP,0
    i=min(targets,key=lambda i:math.hypot(g.x-g.ex[i],g.y-g.ey[i]));dx=g.ex[i]-g.x;dy=g.ey[i]-g.y
    return (KEY_RIGHT if dx>.03 else KEY_LEFT if dx<-.03 else 0)|(KEY_DOWN if dy>.03 else KEY_UP if dy<-.03 else 0),0

def memory(g,won,c):
    if not won:return 0,0
    known=c.setdefault('known',{})
    # Only face-up cards may be observed. Never inspect hidden entries to choose a card.
    for p in (g.first,g.second):
        if p>=0:known[p]=g.cards[p]
    if g.wait:return 0,0
    available=[p for p in range(16) if not g.matched&(1<<p) and p!=g.first]
    if g.first>=0:
        target=next((p for p in available if p in known and known[p]==known[g.first]),None)
        if target is None:target=next((p for p in available if p not in known),available[0])
    else:
        target=None
        for p in available:
            if p in known and any(q!=p and q in known and known[p]==known[q] for q in available):target=p;break
        if target is None:target=next((p for p in available if p not in known),available[0])
    x=target%4;y=target//4
    return 0,KEY_LEFT if g.x>x else KEY_RIGHT if g.x<x else KEY_UP if g.y>y else KEY_DOWN if g.y<y else KEY_A
POLICIES={89:fire,90:factory,91:wire,96:ice,99:survivor,100:memory}
