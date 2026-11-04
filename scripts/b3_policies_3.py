"""Legal solvers and feedback inputs for the B3 puzzle cartridges; no state writes."""
from collections import deque
from arcade.base_cartridge import *

def cursor(g,x,y):
    return KEY_LEFT if g.x>x else KEY_RIGHT if g.x<x else KEY_UP if g.y>y else KEY_DOWN if g.y<y else 0

def suika(g,won,c):
    if not won:return 0,0
    plan=c.get('plan',[])
    if not plan:
        import copy
        best=None
        for target in [2+i*.5 for i in range(23)]:
            trial=copy.deepcopy(g);n=round(abs(target-g.aim)/(5*16667/1000000));k=KEY_RIGHT if target>g.aim else KEY_LEFT
            for _ in range(n):trial.update(16667/1000000,k,0)
            trial.update(16667/1000000,0,KEY_A)
            for _ in range(120):trial.update(16667/1000000,0,0)
            value=(trial.state==STATE_VICTORY,trial.score,-sum((15-trial.by[i])*(1+l) for i,l in enumerate(trial.level) if l))
            if best is None or value>best[0]:best=(value,n,k)
        _,n,k=best;c['plan']=plan=[(k,0)]*n+[(0,KEY_A)]+[(0,0)]*120
    return plan.pop(0)

def block_plan(g):
    masks=[sum(1<<(y*6+x) for x in range(6)) for y in range(6)]+[sum(1<<(y*6+x) for y in range(6)) for x in range(6)]+[sum(1<<((by+y)*6+bx+x) for y in range(3) for x in range(3)) for by in (0,3) for bx in (0,3)]
    options=[(k,x,y,g.shape(k,x,y)) for k in range(3) for y in range(6) for x in range(6) if g.shape(k,x,y)]
    beam=[(g.board,g.rack,g.cleared,[])];goal=(4,5,6)[g.difficulty]
    for depth in range(24):
        candidates={}
        for board,rack,cleared,path in beam:
            for k,x,y,m in options:
                if not rack&(1<<k) or board&m:continue
                b=board|m;remove=0;count=0
                for mask in masks:
                    if b&mask==mask:remove|=mask;count+=1
                b&=~remove;r=rack&~(1<<k);r=r or 7;value=cleared+count;p=path+[(k,x,y)]
                if value>=goal:return p
                key=(b,r,value)
                if key not in candidates:candidates[key]=(b,r,value,p)
        beam=sorted(candidates.values(),key=lambda a:(a[2]*100-a[0].bit_count(),-len(a[3])),reverse=True)[:160]
    raise AssertionError('No legal Blockudoku solution within budget')

def block(g,won,c):
    if not won:return 0,0
    if 'plan' not in c:c['plan']=block_plan(g)
    k,x,y=c['plan'][0];direction=cursor(g,x,y)
    if direction:return 0,direction
    if g.selected!=k:return 0,KEY_B
    c['plan'].pop(0);return 0,KEY_A

def triple(g,won,c):
    if not won:return 0,0
    targets=((0,1),(1,0),(1,1),(3,1),(2,0),(2,1),(0,2),(2,2),(1,2));i=c.get('i',0);x,y=targets[i];direction=cursor(g,x,y)
    if direction:return 0,direction
    c['i']=i+1;return 0,KEY_A

def lights(g,won,c):
    if not won:return 0,KEY_A
    if 'plan' not in c:
        solutions=[]
        def toggle(m,p):
            for x,y in ((p%5,p//5),(p%5-1,p//5),(p%5+1,p//5),(p%5,p//5-1),(p%5,p//5+1)):
                if 0<=x<5 and 0<=y<5:m^=1<<(y*5+x)
            return m
        for first in range(32):
            m=g.mask;path=[]
            for x in range(5):
                if first&(1<<x):path.append(x);m=toggle(m,x)
            for y in range(1,5):
                for x in range(5):
                    if m&(1<<((y-1)*5+x)):p=y*5+x;path.append(p);m=toggle(m,p)
            if m==0:solutions.append(path)
        c['plan']=min(solutions,key=len)
    p=c['plan'][0];direction=cursor(g,p%5,p//5)
    if direction:return 0,direction
    c['plan'].pop(0);return 0,KEY_A

def sudoku(g,won,c):
    if not won:return 0,KEY_B
    if 'solution' not in c:
        b=g.board[:]
        def dfs():
            if 0 not in b:return True
            p=b.index(0);x=p%4;y=p//4;used={b[y*4+i] for i in range(4)}|{b[i*4+x] for i in range(4)}|{b[(y//2*2+dy)*4+x//2*2+dx] for dy in range(2) for dx in range(2)}
            for v in range(1,5):
                if v not in used:
                    b[p]=v
                    if dfs():return True
            b[p]=0;return False
        assert dfs();c['solution']=b
    for p,v in enumerate(c['solution']):
        if g.board[p]!=v:
            direction=cursor(g,p%4,p//4);return 0,direction or KEY_A
    return 0,KEY_B

def slide(g,won,c):
    if not won:return 0,0
    if 'plan' not in c:
        initial=tuple(g.board);goal=tuple(range(1,9))+(0,);queue=deque([initial]);parent={initial:None}
        while queue:
            b=queue.popleft()
            if b==goal:break
            p=b.index(0)
            for dx,dy,k in ((-1,0,KEY_LEFT),(1,0,KEY_RIGHT),(0,-1,KEY_UP),(0,1,KEY_DOWN)):
                x=p%3+dx;y=p//3+dy
                if 0<=x<3 and 0<=y<3:
                    n=y*3+x;a=list(b);a[p],a[n]=a[n],a[p];a=tuple(a)
                    if a not in parent:parent[a]=(b,k);queue.append(a)
        path=[];b=goal
        while parent[b]:b,k=parent[b];path.append(k)
        c['plan']=path[::-1]
    return 0,c['plan'].pop(0)

POLICIES={46:suika,47:block,48:triple,49:lights,50:sudoku,56:slide}
