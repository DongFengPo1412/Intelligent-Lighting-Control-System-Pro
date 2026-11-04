"""Actual public-board controllers for remaining terminal captures; no hidden ship map reads."""
from collections import deque
from arcade.base_cartridge import *
from phase_c_policies import cursor

def lode(g,won,c):
    goals={(p.x,p.y) for p in g.guards if p.active and not p.trapped};initial=(g.player_x,g.player_y);q=deque([initial]);parent={initial:None};end=None
    while q:
        x,y=q.popleft()
        if (x,y) in goals:end=(x,y);break
        if g._can_fall(x,y):choices=[((x,y+1),0)]
        else:
            choices=[((x-1,y),KEY_LEFT),((x+1,y),KEY_RIGHT)]
            if g.grid[y][x]==3:choices.append(((x,y-1),KEY_UP))
            if g.grid[y][x] in (3,4) or (y<15 and g.grid[y+1][x]==3):choices.append(((x,y+1),KEY_DOWN))
        for p,k in choices:
            if 0<=p[0]<16 and 0<=p[1]<16 and g._can_walk(*p) and p not in parent:parent[p]=((x,y),k);q.append(p)
    if end is None:return KEY_LEFT,0
    path=[]
    while parent[end]:end,k=parent[end];path.append(k)
    return 0,path[-1] if path else 0

def checkers(g,won,c):
    if not g.player_turn:c.pop('target',None);return 0,0
    target=c.get('target')
    if target and ((g.selected_x,g.selected_y)==(target[2],target[3]) or g.in_chain_jump):c.pop('target',None);target=None
    if target is None:
        choices=[]
        for sy in range(8):
            for sx in range(8):
                if not g.is_player_piece(g.board[sy][sx]):continue
                if g.in_chain_jump and (sx,sy)!=(g.selected_x,g.selected_y):continue
                for dy in (-2,-1,1,2):
                    for dx in (-2,-1,1,2):
                        tx=sx+dx;ty=sy+dy
                        if abs(dx)!=abs(dy) or not g.is_valid_move(sx,sy,tx,ty,g.in_chain_jump):continue
                        value=(100 if abs(dx)==2 else 0)+(30 if ty==0 else 0)-(35 if g._would_be_capturable_at(tx,ty,sx,sy) else 0)-ty
                        choices.append((value,(sx,sy,tx,ty)))
        if not choices:return 0,KEY_B
        target=max(choices)[1];c['target']=target
    sx,sy,tx,ty=target
    if (g.selected_x,g.selected_y)!=(sx,sy):return 0,cursor(g.cursor_x,g.cursor_y,sx,sy) or KEY_A
    key=cursor(g.cursor_x,g.cursor_y,tx,ty)
    if not key:c.pop('target',None)
    return 0,key or KEY_A

def battleship(g,won,c):
    if not g.player_turn:return 0,0
    options=[]
    for y in range(8):
        for x in range(8):
            if g.player_shots[y][x]!=0:continue
            value=0
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                nx=x+dx;ny=y+dy
                if 0<=nx<8 and 0<=ny<8 and g.player_shots[ny][nx]==2:value+=10
                nx=x+2*dx;ny=y+2*dy
                if 0<=nx<8 and 0<=ny<8 and g.player_shots[ny][nx]==2:value+=3
            options.append((value, (x+y)%2==0,-(y*8+x),x,y))
    _,_,_,x,y=max(options);return 0,cursor(g.cursor_x,g.cursor_y,x,y) or KEY_A
POLICIES={5:lode,64:checkers,66:battleship}
