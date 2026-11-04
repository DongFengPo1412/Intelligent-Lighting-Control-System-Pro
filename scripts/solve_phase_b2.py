"""Generate input-only full-round witnesses. Explicit --output; no device/audio.

Rush Hour uses BFS over legal car translations. Qix searches safe straight cuts
by replaying the actual simulator with a moving enemy. No winning state is set.
"""
import argparse
import copy
import json
import math
import sys
from pathlib import Path
from collections import deque
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'pc-agent-vision'))
from arcade_runner import ArcadeSession
from arcade.base_cartridge import *

DT=16667/1_000_000
DIRS=((KEY_LEFT,-1,0),(KEY_RIGHT,1,0),(KEY_UP,0,-1),(KEY_DOWN,0,1))


def tap(game,key,frames=7):
    game.update(DT,0,key)
    for _ in range(frames-1):game.update(DT,0,0)


def rush_solution(cars):
    initial=tuple(x+y*6 for x,y,_,_ in cars);todo=deque([initial]);parent={initial:None}
    while todo:
        state=todo.popleft()
        if state[0]%6==4:
            path=[]
            while parent[state] is not None:
                prev,move=parent[state];path.append(move);state=prev
            return path[::-1]
        for i,(_,_,n,v) in enumerate(cars):
            for d in (-1,1):
                x=state[i]%6+(0 if v else d);y=state[i]//6+(d if v else 0)
                occupied={(p%6+(0 if cars[j][3] else k),p//6+(k if cars[j][3] else 0)) for j,p in enumerate(state) if j!=i for k in range(cars[j][2])}
                if any(not(0<=x+(0 if v else k)<6 and 0<=y+(k if v else 0)<6) or (x+(0 if v else k),y+(k if v else 0)) in occupied for k in range(n)):continue
                nxt=list(state);nxt[i]=x+y*6;nxt=tuple(nxt)
                if nxt not in parent:parent[nxt]=(state,(i,d));todo.append(nxt)
    raise AssertionError('No Rush Hour solution')


def qix_cut(game):
    start=(game.x,game.y);parent={start:None};todo=deque([start]);best=None
    while todo:
        x,y=todo.popleft()
        for key,dx,dy in DIRS:
            nx,ny=x+dx,y+dy
            if 1<=nx<=14 and 1<=ny<=14 and game.grid[ny][nx]==1 and (nx,ny) not in parent:
                parent[nx,ny]=((x,y),key);todo.append((nx,ny))
    for (x,y) in parent:
        for key,dx,dy in DIRS:
            nx,ny=x+dx,y+dy;distance=1
            if not(1<=nx<=14 and 1<=ny<=14) or game.grid[ny][nx]!=0:continue
            while 1<=nx<=14 and 1<=ny<=14 and game.grid[ny][nx]==0:nx+=dx;ny+=dy;distance+=1
            if not(1<=nx<=14 and 1<=ny<=14) or game.grid[ny][nx]!=1:continue
            path=[];pos=(x,y)
            while parent[pos] is not None:pos,k=parent[pos];path.append(k)
            path=path[::-1]+[KEY_A]+[key]*distance
            trial=copy.deepcopy(game)
            for k in path:
                tap(trial,k)
                if trial.state!=STATE_PLAYING:break
            if trial.state==STATE_GAMEOVER or trial.claimed<=game.claimed:continue
            value=(trial.state==STATE_VICTORY,trial.claimed,-len(path))
            if best is None or value>best[0]:best=(value,path)
    assert best,'No surviving capture found'
    return best[1]


def witness(gid,level):
    g=ArcadeSession().cartridges[gid];g.set_difficulty(level);g.init();g.start();inputs=[]
    def frame(down=0,pressed=0):
        inputs.append([down,pressed]);g.update(DT,down,pressed)
    def press(key,frames=7):
        frame(0,key)
        for _ in range(frames-1):frame()
    if gid==35:
        for key,n in ((KEY_RIGHT,1),(KEY_DOWN,10),(KEY_UP,10),(KEY_RIGHT,9),(KEY_DOWN,10),(KEY_RIGHT,1),(KEY_DOWN,1)):
            for _ in range(n):press(key)
    elif gid==57:
        for car,d in rush_solution(g.cars):
            while g.selected!=car:press(KEY_A)
            press((KEY_UP if d<0 else KEY_DOWN) if g.cars[car][3] else (KEY_LEFT if d<0 else KEY_RIGHT))
    elif gid==58:
        for key,n in ((KEY_UP,2),(KEY_RIGHT,1),(KEY_UP,2),(KEY_LEFT,1),(KEY_UP,3),(KEY_RIGHT,1),(KEY_UP,3)):
            for _ in range(n):press(key)
        press(KEY_A)
        for _ in range(1000):
            if g.state!=STATE_PLAYING:break
            frame()
    elif gid==81:
        for _ in range(10):
            if g.state!=STATE_PLAYING:break
            for key in qix_cut(g):
                press(key)
                if g.state!=STATE_PLAYING:break
    elif gid==98:
        for _ in range(5000):
            if g.state!=STATE_PLAYING:break
            target_vx=max(-.8,min(.8,(8-g.x)*.6))
            angle=max(-.45,min(.45,(target_vx-g.vx)*.6))
            keys=KEY_RIGHT if g.angle<angle-.025 else KEY_LEFT if g.angle>angle+.025 else 0
            target_vy=max(.35,min(1.2,(13-g.y)*.45))
            if g.vy>target_vy:keys|=KEY_A
            frame(keys)
    elif gid==55:
        stages=[[(5,1),(5,5)],[(0,4),(4,4),(4,1)],[(1,0),(1,6),(5,6),(5,2)],[(0,1),(3,1),(3,5),(6,5),(6,0)]]
        for stage,mirrors in enumerate(stages):
            assert g.stage==stage
            for x,y in mirrors:
                while g.cursor_x!=x:press(KEY_RIGHT if g.cursor_x<x else KEY_LEFT)
                while g.cursor_y!=y:press(KEY_DOWN if g.cursor_y<y else KEY_UP)
                press(KEY_A)
            press(KEY_B)
            for _ in range(100):
                if g.stage!=stage or g.state!=STATE_PLAYING:break
                frame()
    assert g.state==STATE_VICTORY,(gid,level,g.get_status(),vars(g))
    rle=[]
    for down,pressed in inputs:
        if rle and rle[-1][1:]==[down,pressed]:rle[-1][0]+=1
        else:rle.append([1,down,pressed])
    return dict(id=gid,difficulty=level,steps=len(inputs),inputs=rle,score=g.score)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True);args=parser.parse_args()
    cases=[]
    for gid in (35,57,58,81,98):
        for level in range(3):
            row=witness(gid,level);cases.append(row);print(gid,level,row['steps'],row['score'],flush=True)
    cases.append(witness(55,1))
    Path(args.output).write_text(json.dumps(dict(dt_us=16667,cases=cases),indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
