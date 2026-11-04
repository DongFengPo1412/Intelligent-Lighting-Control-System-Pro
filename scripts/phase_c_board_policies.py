"""Board searches over legal placements, pushes and public opponent positions."""
import copy,heapq,itertools
from collections import deque
from arcade.base_cartridge import *
from phase_c_policies import cursor

def samegame(g,won,c):
    if not won:return 0,0
    if 'plan' not in c:
        beam=[(copy.deepcopy(g),[])];found=None
        for depth in range(50):
            candidates={}
            for t,path in beam:
                seen=set()
                for y in range(10):
                    for x in range(10):
                        if (x,y) in seen:continue
                        group=t.flood_component(x,y);seen.update(group)
                        if len(group)<2:continue
                        n=copy.deepcopy(t);n.eliminate_at(x,y);p=path+[(x,y)]
                        if n.state==STATE_VICTORY:found=p;break
                        if n.state!=STATE_PLAYING:continue
                        key=tuple(tuple(row) for row in n.grid)
                        if key not in candidates:candidates[key]=(n,p)
                    if found:break
                if found:break
            if found:break
            beam=sorted(candidates.values(),key=lambda a:(a[0].count_remaining(),-a[0].score))[:180]
            if not beam:break
        assert found,'SameGame beam did not certify a win';c['plan']=found
    x,y=c['plan'][0];key=cursor(g.cx,g.cy,x,y)
    if key:return 0,key
    c['plan'].pop(0);return 0,KEY_A

def sokoban(g,won,c):
    if not won:return 0,0
    if 'plan' not in c:
        goals=frozenset((x,y) for y in range(16) for x in range(16) if g.map[y][x]==2);floor={(x,y) for y in range(16) for x in range(16) if g.map[y][x]!=1};dirs=((1,0,KEY_RIGHT),(-1,0,KEY_LEFT),(0,1,KEY_DOWN),(0,-1,KEY_UP))
        initial=(tuple(sorted((b.x,b.y) for b in g.boxes)),(g.player_x,g.player_y));serial=itertools.count();queue=[(0,next(serial),initial,[])];visited={};found=None
        def reach(player,boxes):
            q=deque([player]);parent={player:None}
            while q:
                x,y=q.popleft()
                for dx,dy,k in dirs:
                    n=x+dx,y+dy
                    if n in floor and n not in boxes and n not in parent:parent[n]=((x,y),k);q.append(n)
            return parent
        while queue:
            _,_,(boxes,player),path=heapq.heappop(queue);boxset=set(boxes)
            if boxset==goals:found=path;break
            parents=reach(player,boxset);key=(boxes,min(parents))
            if key in visited and visited[key]<=len(path):continue
            visited[key]=len(path)
            assert len(visited)<250000,'Sokoban search budget exceeded'
            for x,y in boxes:
                for dx,dy,k in dirs:
                    stand=(x-dx,y-dy);dest=(x+dx,y+dy)
                    if stand not in parents or dest not in floor or dest in boxset:continue
                    # Static corner pruning: each wall pair traps a non-goal box.
                    if dest not in goals and any((dest[0]+ax,dest[1]+ay) not in floor and (dest[0]+bx,dest[1]+by) not in floor for ax,ay,bx,by in ((1,0,0,1),(1,0,0,-1),(-1,0,0,1),(-1,0,0,-1))):continue
                    walk=[];p=stand
                    while parents[p]:p,keymove=parents[p];walk.append(keymove)
                    moved=tuple(sorted(boxset-{(x,y)}|{dest}));newpath=path+walk[::-1]+[k];heuristic=sum(min(abs(a-u)+abs(b-v) for u,v in goals) for a,b in moved)
                    heapq.heappush(queue,(len(newpath)+heuristic*3,next(serial),(moved,(x,y)),newpath))
        assert found,'Sokoban authored puzzle unsolved';c['plan']=found
    return 0,c['plan'].pop(0)

def reversi(g,won,c):
    if not g.player_turn:return 0,0
    if c.get('turn')!=tuple(tuple(r) for r in g.board):
        options=[]
        for y in range(8):
            for x in range(8):
                flips=g.total_flips(x,y,1)
                if not flips:continue
                t=copy.deepcopy(g);t.place_disc(x,y,1);t._make_ai_move()
                corners=sum(1 if t.board[yy][xx]==1 else -1 if t.board[yy][xx]==2 else 0 for xx,yy in ((0,0),(7,0),(0,7),(7,7)))
                own=sum(v==1 for row in t.board for v in row);enemy=sum(v==2 for row in t.board for v in row);mobility=sum(t.total_flips(xx,yy,2)>0 for yy in range(8) for xx in range(8))
                value=corners*100+(own-enemy)*(.2 if own+enemy<50 else 4)-mobility*3
                options.append((value,x,y))
        assert options
        _,x,y=(max(options) if won else min(options));c.update(turn=tuple(tuple(r) for r in g.board),target=(x,y))
    x,y=c['target'];return 0,cursor(g.cursor_x,g.cursor_y,x,y) or KEY_A

def quoridor(g,won,c):
    if not g.player_turn:c.pop('target',None);return 0,0
    if 'target' not in c:
        pd=g.shortest_path_len(g.player_c,g.player_r,0);ad=g.shortest_path_len(g.ai_c,g.ai_r,6);options=[]
        for d in range(4):
            p=g.compute_pawn_step(g.player_c,g.player_r,g.ai_c,g.ai_r,d)
            if p:options.append((g.shortest_path_len(*p,0),d))
        _,d=(min(options) if won else max(options));target=('move',d)
        if won and g.player_walls and ad<=pd+1:
            def distance(sc,sr,goal,wc,wr,h):
                q=deque([(sc,sr,0)]);seen={(sc,sr)}
                while q:
                    x,y,n=q.popleft()
                    if y==goal:return n
                    for dx,dy in ((0,1),(0,-1),(1,0),(-1,0)):
                        xx=x+dx;yy=y+dy
                        extra=(h and x==xx and min(y,yy)==wr and wc<=x<=wc+1)or(not h and y==yy and min(x,xx)==wc and wr<=y<=wr+1)
                        if 0<=xx<7 and 0<=yy<7 and (xx,yy) not in seen and not extra and not g.is_edge_blocked(x,y,xx,yy):seen.add((xx,yy));q.append((xx,yy,n+1))
                return 999
            best=(0,None)
            for h in (True,False):
                for wr in range(6):
                    for wc in range(6):
                        if not g.can_place_wall(wc,wr,h):continue
                        gain=distance(g.ai_c,g.ai_r,6,wc,wr,h)-ad-(distance(g.player_c,g.player_r,0,wc,wr,h)-pd)
                        if gain>best[0]:best=(gain,(wc,wr,h))
            if best[0]>=2:target=('wall',*best[1])
        c['target']=target
    target=c['target']
    if target[0]=='move':
        if g.mode!=0:return 0,KEY_B
        return 0,(KEY_UP,KEY_DOWN,KEY_LEFT,KEY_RIGHT)[target[1]]|KEY_A
    _,x,y,h=target;mode=1 if h else 2
    if g.mode!=mode:return 0,KEY_B
    return 0,cursor(g.wall_c,g.wall_r,x,y) or KEY_A

POLICIES={45:samegame,54:sokoban,62:reversi,67:quoridor}
