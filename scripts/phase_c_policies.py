"""Legal input-only Phase C planners. Private state is read only for public-board search.
No assignment to runtime score/terminal/progress; copied simulations plan legal moves.
"""
from collections import deque
from functools import lru_cache
import copy,itertools
from arcade.base_cartridge import *

def cursor(x,y,tx,ty):return KEY_LEFT if x>tx else KEY_RIGHT if x<tx else KEY_UP if y>ty else KEY_DOWN if y<ty else 0

def simon(g,won,c):
    if g.phase==0 and g.lit_pad>=0:c.setdefault('shown',{})[g.show_idx]=g.lit_pad
    if g.phase!=2:c['wait']=0;return 0,0
    c['wait']=c.get('wait',0)+1
    if c['wait']<3:return 0,0
    expected=c['shown'][g.input_idx];return 0,(KEY_LEFT,KEY_DOWN,KEY_UP,KEY_RIGHT)[expected if won else (expected+1)%4]

def cups(g,won,c):
    if g.phase==0:c.update(slot=g.pearl_slot,done=0)
    if g.phase in (1,2):
        if g.swaps_done>c.get('done',0):
            a,b=c['pair'];slot=c['slot'];c['slot']=b if slot==a else a if slot==b else slot
        c['done']=g.swaps_done;c['pair']=(g.swap_a,g.swap_b)
    if g.phase!=2:return 0,0
    target=c['slot'] if won else (c['slot']+1)%g.num_cups
    return 0,KEY_LEFT if g.cursor_slot>target else KEY_RIGHT if g.cursor_slot<target else KEY_A

def hanoi(g,won,c):
    if not won:return 0,0
    if c.get('n')!=g.num_disks:
        path=[]
        def rec(n,a,b,aux):
            if n:rec(n-1,a,aux,b);path.append((a,b));rec(n-1,aux,b,a)
        rec(g.num_disks,0,2,1);c.update(n=g.num_disks,plan=path,holding=False)
    a,b=c['plan'][0];target=b if c['holding'] else a
    if g.cursor_peg!=target:return 0,KEY_RIGHT if g.cursor_peg<target else KEY_LEFT
    if c['holding']:c['plan'].pop(0)
    c['holding']=not c['holding'];return 0,KEY_A

def mirror(g,won,c):
    if not won:return 0,0
    if c.get('level')!=g.level:
        initial=(g.ax,g.ay,g.bx,g.by);goal=(g.goal_ax,g.goal_ay,g.goal_bx,g.goal_by);q=deque([initial]);parent={initial:None}
        while q:
            p=q.popleft()
            if p==goal:break
            for dx,dy,k in ((1,0,KEY_RIGHT),(-1,0,KEY_LEFT),(0,1,KEY_DOWN),(0,-1,KEY_UP)):
                ax,ay,bx,by=p
                if 0<=ax+dx<16 and 0<=ay+dy<16 and g.map[ay+dy][ax+dx]!=1:ax+=dx;ay+=dy
                if 0<=bx-dx<16 and 0<=by+dy<16 and g.map[by+dy][bx-dx]!=1:bx-=dx;by+=dy
                n=(ax,ay,bx,by)
                if g.map[ay][ax]==2 or g.map[by][bx]==2 or n in parent:continue
                parent[n]=(p,k);q.append(n)
        assert goal in parent;path=[]
        while parent[goal]:goal,k=parent[goal];path.append(k)
        c.update(level=g.level,plan=path[::-1])
    return 0,c['plan'].pop(0)

def flow(g,won,c):
    if not won:return 0,0
    if c.get('stage')!=g.stage:
        endpoints=g.endpoints;allends={p for pair in endpoints for p in pair};size=6
        def connected(a,b,blocked):
            q=deque([a]);seen={a}
            while q:
                p=q.popleft()
                if p==b:return True
                for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                    n=p[0]+dx,p[1]+dy
                    if 0<=n[0]<size and 0<=n[1]<size and n not in blocked and n not in seen:seen.add(n);q.append(n)
            return False
        def solve(color,occupied):
            if color==len(endpoints):return []
            start,end=endpoints[color];blocked=occupied|(allends-{start,end})
            def paths(p,path,seen):
                if p==end:
                    occ=occupied|set(path)
                    if all(connected(a,b,occ|(allends-{a,b})) for a,b in endpoints[color+1:]):
                        rest=solve(color+1,occ)
                        if rest is not None:return [path]+rest
                    return None
                options=sorted(((p[0]+dx,p[1]+dy) for dx,dy in ((1,0),(-1,0),(0,1),(0,-1))),key=lambda q:abs(q[0]-end[0])+abs(q[1]-end[1]))
                for n in options:
                    if 0<=n[0]<6 and 0<=n[1]<6 and n not in blocked and n not in seen:
                        result=paths(n,path+[n],seen|{n})
                        if result is not None:return result
                return None
            return paths(start,[start],{start})
        paths=solve(0,set());assert paths,'Flow Free authored stage unsolved';actions=[];x=g.cursor_x;y=g.cursor_y
        for path in paths:
            tx,ty=path[0]
            while (x,y)!=(tx,ty):k=cursor(x,y,tx,ty);actions.append(k);x+=(k==KEY_RIGHT)-(k==KEY_LEFT);y+=(k==KEY_DOWN)-(k==KEY_UP)
            actions.append(KEY_A)
            for tx,ty in path[1:]:actions.append(cursor(x,y,tx,ty));x=tx;y=ty
        c.update(stage=g.stage,plan=actions)
    return 0,c['plan'].pop(0)

def pipes(g,won,c):
    if not won:return 0,KEY_B
    if c.get('stage')!=g.stage:
        domains=[]
        for y in range(5):
            for x in range(5):
                mask=g.masks[y][x];values={mask};m=mask
                if not g.fixed[y][x]:
                    for _ in range(3):m=g.rotate_mask_cw(m);values.add(m)
                values={v for v in values if not((y==0 and v&1)or(x==4 and v&2)or(y==4 and v&4)or(x==0 and v&8))};domains.append(values)
        dirs=((0,-1,1,4),(1,0,2,8),(0,1,4,1),(-1,0,8,2))
        def solve(ds):
            ds=[set(v) for v in ds];changed=True
            while changed:
                changed=False
                for p,vs in enumerate(ds):
                    for dx,dy,bit,opp in dirs:
                        x=p%5+dx;y=p//5+dy
                        if not(0<=x<5 and 0<=y<5):continue
                        valid={a for a in vs if any(bool(a&bit)==bool(b&opp) for b in ds[y*5+x])}
                        if not valid:return None
                        if valid!=vs:ds[p]=vs=valid;changed=True
            undecided=[p for p,v in enumerate(ds) if len(v)>1]
            if not undecided:
                values=[next(iter(v)) for v in ds];seen={0};q=deque([0])
                while q:
                    p=q.popleft()
                    for dx,dy,bit,opp in dirs:
                        x=p%5+dx;y=p//5+dy
                        if values[p]&bit and 0<=x<5 and 0<=y<5 and y*5+x not in seen:seen.add(y*5+x);q.append(y*5+x)
                return values if 24 in seen else None
            p=min(undecided,key=lambda p:len(ds[p]))
            for v in sorted(ds[p]):
                child=[set(d) for d in ds];child[p]={v};result=solve(child)
                if result is not None:return result
            return None
        target=solve(domains)
        if target is None:
            # Dry, disconnected components need not be leak-free. Only the actual source component flows.
            original=[v for row in g.masks for v in row]
            def active(assigned):
                demands={}
                for p,v in assigned.items():
                    for dx,dy,bit,opp in dirs:
                        if not v&bit:continue
                        x=p%5+dx;y=p//5+dy
                        if not(0<=x<5 and 0<=y<5):return None
                        n=y*5+x
                        if n in assigned:
                            if not assigned[n]&opp:return None
                        else:demands[n]=demands.get(n,0)|opp
                if not demands:return [assigned.get(i,original[i]) for i in range(25)] if 24 in assigned else None
                choices=[]
                for n,bits in demands.items():
                    vs=[]
                    for v in domains[n]:
                        if v&bits!=bits:continue
                        valid=True
                        for dx,dy,bit,opp in dirs:
                            x=n%5+dx;y=n//5+dy
                            if 0<=x<5 and 0<=y<5 and y*5+x in assigned and bool(v&bit)!=bool(assigned[y*5+x]&opp):valid=False;break
                        if valid:vs.append(v)
                    if not vs:return None
                    choices.append((len(vs),n,vs))
                _,n,vs=min(choices)
                for v in vs:
                    result=active(assigned|{n:v})
                    if result is not None:return result
                return None
            target=active({0:original[0]})
        assert target,('Pipe source component unsolved',g.stage);c.update(stage=g.stage,target=target)
    if g.flow_active:return 0,KEY_B
    for p,v in enumerate(c['target']):
        if g.masks[p//5][p%5]!=v:return 0,cursor(g.cursor_x,g.cursor_y,p%5,p//5) or KEY_A
    return 0,KEY_B

POLICIES={15:simon,19:cups,40:mirror,51:flow,52:pipes,53:hanoi}
