"""Input-only B3 witnesses and cross-language checkpoints. No hardware/audio.

Every solver must pass production rules; copying a simulator for planning never
changes the real instance. --output must be explicitly selected by the caller.
"""
import argparse
import copy
import json
import math
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'pc-agent-vision'))
from arcade_runner import ArcadeSession
from arcade.base_cartridge import *

ROOT=Path(__file__).resolve().parents[1]
DT=16667/1_000_000
POLICIES={}


def pendulum_landing(g):
    speed=(1.3,1.7,2.1)[g.difficulty];phase=g.phase+speed*DT
    a=.9*math.sin(phase);omega=.9*speed*math.cos(phase)
    x=8+5*math.sin(a);y=1+5*math.cos(a);vx=5*math.cos(a)*omega;vy=-5*math.sin(a)*omega
    t=(-vy+math.sqrt(vy*vy+10*(13-y)))/5
    return x+vx*t


def policy(g,won,context):
    gid=g.game_id
    if gid in POLICIES:return POLICIES[gid](g,won,context)
    if not won:
        if gid==8:
            context['n']=context.get('n',0)+1
            return ((KEY_A|KEY_RIGHT) if context['n']<=18 else 0),0
        if gid==12 and not g.flying:
            trial=copy.deepcopy(g);trial.update(DT,0,KEY_A)
            for _ in range(20):trial.update(DT,0,0)
            return 0,KEY_A if trial.state==STATE_GAMEOVER else 0
        if gid==13 and not g.flying:
            return 0,KEY_A if abs(pendulum_landing(g)-(4,11,7)[g.hits%3])>5 else 0
        return 0,0
    if gid==7:
        if g.y>=22.9 and g.grounded:context['reloaded']=True
        target=10.5 if g.kills>=2 and not context.get('reloaded') else 8.
        down=KEY_RIGHT if g.x<target-.06 else KEY_LEFT if g.x>target+.06 else 0
        enemy=next((ey for active,ey in zip(g.enemy,(10,22,34)) if active and ey>g.y),None)
        shoot=enemy is not None and abs(g.x-8)<.5 and enemy-g.y<7 and g.ammo and not any(y<enemy+1 for x,y in g.bullets)
        return down,KEY_A if shoot else 0
    if gid==8:
        plan=context.get('plan',[])
        if not plan:
            assert g.grounded,(g.x,g.y)
            best=None
            for frames in range(35,73):
                for direction in (KEY_LEFT,KEY_RIGHT):
                    trial=copy.deepcopy(g)
                    for _ in range(frames):trial.update(DT,KEY_A|direction,0)
                    trial.update(DT,0,0)
                    for n in range(300):
                        trial.update(DT,0,0)
                        if trial.state!=STATE_PLAYING or trial.grounded:break
                    if trial.state!=STATE_GAMEOVER and trial.y<g.y-5:
                        value=(trial.y,abs(trial.x-7.5))
                        if best is None or value<best[0]:best=(value,frames,direction,n)
            assert best,('no jump',g.x,g.y,g.difficulty)
            _,frames,direction,n=best
            plan=[(KEY_A|direction,0)]*frames+[(0,0)]*(n+2)
            context['plan']=plan
        return plan.pop(0)
    if gid==11:
        near=min((x for x in g.ob if x>=2.1),default=100)
        return 0,KEY_A if g.y>=11.999 and near-3<5 else 0
    if gid==12:
        if g.flying:return 0,0
        trial=copy.deepcopy(g);trial.update(DT,0,KEY_A)
        for _ in range(20):
            if not trial.flying:break
            trial.update(DT,0,0)
        return 0,KEY_A if trial.state!=STATE_GAMEOVER and trial.hits>g.hits else 0
    if gid==13:
        target=(4,11,7)[g.hits%3];width=(2.5,2.,1.5)[g.difficulty]
        return 0,KEY_A if not g.flying and abs(pendulum_landing(g)-target)<width-.4 else 0
    if gid==23:
        target=max(2,min(14,g.x+g.vx*max(0,(12-g.y)/g.vy))) if g.vy>0 else 8
        down=KEY_LEFT if g.paddle_x>target+.04 else KEY_RIGHT if g.paddle_x<target-.04 else 0
        return down|KEY_A,0
    return POLICIES[gid](g,won,context)


def witness(gid,level,won,rules):
    g=ArcadeSession().cartridges[gid];assert g.set_difficulty(level)
    if gid==100:assert g.set_replay_seed(0x100fa)
    g.init();g.start()
    rle=[];checks=[];context={};expected=STATE_VICTORY if won else STATE_GAMEOVER
    keys=rules[str(gid)]['keys']
    for step in range(1,20001):
        down,pressed=policy(g,won,context);g.update(DT,down,pressed)
        if rle and rle[-1][1:]==[down,pressed]:rle[-1][0]+=1
        else:rle.append([1,down,pressed])
        if step%60==0 or g.state!=STATE_PLAYING:
            status=g.get_status()
            values=[eval('g.'+key,{'g':g}) for key in keys]
            checks.append([step,status['state'],status['score'],status['lives'],status['progress'],*values])
        if g.state!=STATE_PLAYING:break
    assert g.state==expected,(gid,level,won,g.get_status(),{k:v for k,v in vars(g).items() if not isinstance(v,list)})
    return dict(id=gid,difficulty=level,**({'seed':0x100fa} if gid==100 else {}),outcome='win' if won else 'loss',steps=step,inputs=rle,checkpoints=checks)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--ids',type=int,nargs='+',required=True);p.add_argument('--output',required=True);p.add_argument('--rules',required=True);a=p.parse_args()
    rules=json.loads(Path(a.rules).read_text(encoding='utf-8'));cases=[]
    for gid in a.ids:
        for level in range(3):
            for won in (True,False):
                case=witness(gid,level,won,rules);cases.append(case);print(gid,level,case['outcome'],case['steps'],flush=True)
    Path(a.output).write_text(json.dumps(dict(dt_us=16667,cases=cases),separators=(',',':'))+'\n',encoding='utf-8')


import importlib
for _group in range(2,7):
    if Path(__file__).with_name(f'b3_policies_{_group}.py').is_file():
        POLICIES.update(importlib.import_module(f'b3_policies_{_group}').POLICIES)
if __name__=='__main__':main()
