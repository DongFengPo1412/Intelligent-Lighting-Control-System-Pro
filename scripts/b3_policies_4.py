"""Input-only planning for rope, portals and classic board puzzles."""
import math,copy,itertools
from collections import deque
from arcade.base_cartridge import *
DT=16667/1000000

def rope(g,won,c):
    if not won:return 0,0
    if g.cut:return 0,0
    a=math.sin((g.elapsed+DT)*(1.2,1.5,1.8)[g.difficulty])*1.1;r=math.cos((g.elapsed+DT)*(1.2,1.5,1.8)[g.difficulty])*1.1*(1.2,1.5,1.8)[g.difficulty];x=8+5*math.sin(a);y=2+5*math.cos(a);vx=5*math.cos(a)*r;vy=-5*math.sin(a)*r
    for _ in range(300):
        vy+=5*DT;x+=vx*DT;y+=vy*DT
        if y>=13:break
    return 0,KEY_A if abs(x-12)<(.9,.8,.65)[g.difficulty] else 0

def portal(g,won,c):
    if not won:return 0,0
    from collections import deque
    initial=(g.x,g.y,g.gate);goal=g.EXITS[g.stage];queue=deque([initial]);parent={initial:None};end=None
    while queue:
        x,y,gate=queue.popleft()
        if (x,y)==goal and gate:end=(x,y,gate);break
        choices=[]
        for dx,dy,key in ((1,0,KEY_RIGHT),(-1,0,KEY_LEFT),(0,1,KEY_DOWN),(0,-1,KEY_UP)):
            nx=x+dx;ny=y+dy
            if not(1<=nx<=6 and 1<=ny<=6) or nx==4 or (ny==3 and nx>=5 and not gate) or (nx,ny)==g.BLOCKS[g.stage]:continue
            choices.append(((nx,ny,gate or (nx,ny)==g.SWITCHES[g.stage]),key))
        a,b=g.PORTALS[g.stage]
        if (x,y) in (a,b):
            nx,ny=b if (x,y)==a else a;choices.append(((nx,ny,gate or (nx,ny)==g.SWITCHES[g.stage]),KEY_A))
        for node,key in choices:
            if node not in parent:parent[node]=((x,y,gate),key);queue.append(node)
    assert end,('portal room unsolvable',g.stage)
    path=[]
    while parent[end]:end,key=parent[end];path.append(key)
    return 0,path[-1]

def connect(g,won,c):
    if not won:return 0,KEY_A
    if 'plan' not in c:
        seen=set()
        def dfs(t,depth):
            key=(tuple(t.board),depth)
            if depth==0 or key in seen:return None
            seen.add(key)
            order=(3,2,4,1,5,0,6)
            for col in order:
                n=copy.deepcopy(t);p=n.drop(col,1)
                if p<0:continue
                if n.won(1):return [col]
                if all(n.board):continue
                n.drop(n.choose(),2)
                if n.won(2) or all(n.board):continue
                path=dfs(n,depth-1)
                if path is not None:return [col]+path
            return None
        c['plan']=dfs(g,10);assert c['plan'],'connect path'
    target=c['plan'][0]
    if g.column!=target:return 0,KEY_RIGHT if g.column<target else KEY_LEFT
    c['plan'].pop(0);return 0,KEY_A

def feedback(a,b):
    exact=sum(x==y for x,y in zip(a,b));return exact,sum(min(a.count(i),b.count(i)) for i in range(6))-exact

def mastermind(g,won,c):
    if not won:return 0,KEY_A
    if c.get('tries')!=g.tries:
        if 'candidates' not in c:c['candidates']=list(itertools.product(range(6),repeat=4));target=(0,0,1,1)
        else:
            c['candidates']=[v for v in c['candidates'] if feedback(list(v),c['target'])==(g.exact,g.near)]
            assert c['candidates'];target=c['candidates'][0]
            if len(c['candidates'])>1:
                best=(10000,None)
                for v in c['candidates'][:200]:
                    groups={}
                    for a in c['candidates']:
                        f=feedback(list(a),list(v));groups[f]=groups.get(f,0)+1
                    value=max(groups.values())
                    if value<best[0]:best=(value,v)
                target=best[1]
        c.update(tries=g.tries,target=list(target))
    for i,v in enumerate(c['target']):
        if g.guess[i]!=v:
            if g.slot!=i:return 0,KEY_RIGHT if g.slot<i else KEY_LEFT
            return 0,KEY_DOWN
    return 0,KEY_A

def nim(g,won,c):
    if not won:return 0,0
    if g.thinking>0:return 0,0
    xor=g.piles[0]^g.piles[1]^g.piles[2]
    targets=[(i,v-(v^xor)) for i,v in enumerate(g.piles) if (v^xor)<v]
    i,n=targets[0] if targets else next((i,1) for i,v in enumerate(g.piles) if v)
    if g.pile!=i:return 0,KEY_RIGHT if g.pile<i else KEY_LEFT
    if g.take!=n:return 0,KEY_DOWN if g.take<n else KEY_UP
    return 0,KEY_A

def flood(g,won,c):
    if not won:return 0,0
    if 'plan' not in c:
        full=(1<<36)-1;initial=(g.flooded,g.color);queue=deque([initial]);parents={initial:None};goal=None
        while queue:
            mask,col=queue.popleft()
            if mask==full:goal=(mask,col);break
            for color in range(4):
                if color==col:continue
                m=mask;old=-1
                while old!=m:
                    old=m
                    for p,v in enumerate(g.board):
                        if v==color and any(0<=n<36 and m&(1<<n) for n in (p-1 if p%6 else -1,p+1 if p%6<5 else -1,p-6,p+6)):m|=1<<p
                key=(m,color)
                if key not in parents:parents[key]=((mask,col),color);queue.append(key)
        assert goal;path=[]
        while parents[goal]:goal,color=parents[goal];path.append(color)
        c['plan']=path[::-1]
    target=c['plan'][0]
    if g.selected!=target:return 0,KEY_RIGHT
    c['plan'].pop(0);return 0,KEY_A
POLICIES={59:rope,60:portal,61:connect,68:mastermind,69:nim,70:flood}
