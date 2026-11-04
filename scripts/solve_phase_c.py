"""Generate actual input witnesses; all output destinations must be explicit."""
import argparse,json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"pc-agent-vision"))
from arcade_runner import ArcadeSession
from arcade.base_cartridge import *
from b3_policies_6 import memory
from phase_c_policies import POLICIES
from phase_c_board_policies import POLICIES as BOARD_POLICIES
POLICIES.update(BOARD_POLICIES)
from phase_c_observation_policies import POLICIES as OBSERVATION_POLICIES
POLICIES.update(OBSERVATION_POLICIES)
DT=16667/1000000

def witness(id,level,won,seed=None):
    g=ArcadeSession().cartridges[id]
    if g.difficulty_supported:g.set_difficulty(level)
    if seed is not None:assert g.set_replay_seed(seed)
    g.init();g.start();ctx={};rle=[];checks=[]
    for step in range(1,18001):
        down,pressed=(memory(g,won,ctx) if id==100 else POLICIES[id](g,won,ctx));g.update(DT,down,pressed)
        if rle and rle[-1][1:]==[down,pressed]:rle[-1][0]+=1
        else:rle.append([1,down,pressed])
        if step%60==0 or g.state!=STATE_PLAYING:
            s=g.get_status();rules=json.loads((Path(__file__).resolve().parents[1]/'tests/fixtures/phase_b3_rules.json').read_text(encoding='utf-8'));keys=rules.get(str(id),{}).get('keys',[]);checks.append([step,s['state'],s['score'],s['lives'],s['progress']]+[eval('g.'+key,{'g':g}) for key in keys])
        if g.state!=STATE_PLAYING:break
    assert g.state in (STATE_VICTORY,STATE_GAMEOVER) if won is None else g.state==(STATE_VICTORY if won else STATE_GAMEOVER),(id,level,won,g.get_status())
    return dict(id=id,difficulty=level,seed=seed,outcome='win' if g.state==STATE_VICTORY else 'loss',steps=step,inputs=rle,checkpoints=checks)
def main():
    p=argparse.ArgumentParser();p.add_argument('--ids',nargs='+',type=int,required=True);p.add_argument('--output',required=True);p.add_argument('--observe-terminal',action='store_true',help='Observe actual terminal, without requiring a player win');a=p.parse_args();cases=[]
    for id in a.ids:
        if id==100:
            for d in range(3):
                for seed in (0,1,2,42,0xffffffff,0xabcdef,100,101,65536,12345678,31337,0x100fa):
                    c=witness(id,d,True,seed);cases.append(c);print(id,d,seed,c['outcome'],c['steps'],flush=True)
        else:
            for won in ((None,) if a.observe_terminal else (True,False) if id in (15,19,52) else (True,)):
                c=witness(id,1,won);cases.append(c);print(id,c['outcome'],c['steps'],flush=True)
    Path(a.output).write_text(json.dumps(dict(dt_us=16667,cases=cases),separators=(',',':'))+'\n',encoding='utf-8')
if __name__=='__main__':main()
