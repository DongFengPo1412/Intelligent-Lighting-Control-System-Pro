"""Export real C++/Python frames and evidence-separated 100-game audit.
Requires --native-log from a passing host run; never certifies physical hardware.
All generated outputs must be outside the source repository.
"""
import argparse,ast,csv,hashlib,html,json,re,shutil
from pathlib import Path
from collections import Counter
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"pc-agent-vision"))
from arcade_runner import ArcadeSession
from arcade.base_cartridge import STATE_PLAYING
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];DT=16667/1000000

def read(path):
    b=path.read_bytes();return b.decode('utf-16') if b.startswith((b'\xff\xfe',b'\xfe\xff')) else b.decode('utf-8',errors='replace')
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-dir',required=True);p.add_argument('--cpp-captures',required=True);p.add_argument('--native-log',required=True);p.add_argument('--native-comparison',required=True);a=p.parse_args();out=Path(a.output_dir).resolve();cpp=Path(a.cpp_captures).resolve()
    if out==ROOT or ROOT in out.parents:raise ValueError('Use a task artifact directory outside repository')
    log=read(Path(a.native_log));assert 'C++ production constructors/NVS failures/replay/protocol/watchdog tests passed' in log and '51 rounds' in log and 'Phase C production directed' in log
    # Exploratory replay uses each backend's existing RNG. A mismatch is a review
    # finding, not a successful cross-language certificate or proof of a rule bug.
    comparison_path=Path(a.native_comparison).resolve()
    comparison={int(r['id']):r for r in csv.DictReader(comparison_path.open())}
    assert len(comparison)==100
    out.mkdir(parents=True,exist_ok=True);images=out/'frames';images.mkdir(exist_ok=True);raw=out/'rgb';raw.mkdir(exist_ok=True)
    roots=[json.loads((ROOT/'tests/fixtures'/name).read_text()) for name in ('phase_b3_input_paths.json','phase_b2_input_paths.json','phase_c_input_paths.json')]
    manifest=json.loads((ROOT/'games_100_manifest.json').read_text(encoding='utf-8'));registry=json.loads((ROOT/'pc-agent-vision/arcade/registered_games.json').read_text());assert len(manifest)==len(registry)==100
    prior={int(r['target_id']):r for r in csv.DictReader((ROOT/'game_acceptance.csv').open(encoding='utf-8-sig'))}
    native={(int(r['id']),r['phase']):r for r in csv.DictReader((cpp/'frames.csv').open())};frames=[];records=[]
    def plan(id):
        found=[c for root in roots for c in root['cases'] if c['id']==id and c['difficulty']==1]
        return next((c for c in found if c.get('outcome','win')=='win'),found[0] if found else None)
    b3wins={c['id'] for c in roots[0]['cases'] if c['outcome']=='win'};b2wins={c['id'] for c in roots[1]['cases'] if c.get('outcome','win')=='win'};newwins={c['id'] for c in roots[2]['cases'] if c['outcome']=='win'};losses={c['id'] for c in roots[2]['cases'] if c['outcome']=='loss'}
    # Explicit existing production test coverage, not inferred from registration.
    verified_wins=b3wins|b2wins|newwins|{17,55,85,92,95}
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',12);small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',10)
    observations=[]
    for entry in registry:
        id=entry['id'];meta=manifest[id-1];g=ArcadeSession().cartridges[id];g.set_difficulty(1)
        if id==100:g.set_replay_seed(0x100fa)
        g.init();shots={};rle=[];checks=[];input_step=0
        def advance(down,pressed):
            nonlocal input_step
            input_step+=1;g.update(DT,down,pressed)
            if rle and rle[-1][1:]==[down,pressed]:rle[-1][0]+=1
            else:rle.append([1,down,pressed])
            if input_step%60==0 or g.state>=3:
                status=g.get_status();checks.append([input_step,status["state"],status["score"],status["lives"],status["progress"]])
        def snap(phase,source):
            b=bytes(g.render());assert len(b)==768;shots[phase]=(b,dict(state=g.state,score=g.get_status()['score'],progress=g.get_status()['progress'],source=source))
        snap('title','Reset');g.start();snap('play','Start')
        for tick in range(12):
            g.update(DT,0,0)
            if tick%2==0:snap(f'anim{tick//2}','idle_real_updates')
        g.init();g.start();case=plan(id)
        if case:
            step=0
            for count,down,pressed in case['inputs']:
                for _ in range(count):
                    advance(down,pressed);step+=1
                    if step==max(1,case['steps']//2) and g.state==STATE_PLAYING:snap('play','legal_input_witness')
                    if g.state>=3:break
                if g.state>=3:break
        else:
            seed=0xc0ffee^id;key=0
            for step in range(18000):
                if g.state!=STATE_PLAYING:break
                if step%15==0:seed=(seed*1664525+1013904223)&0xffffffff;key=(1,2,4,8,16,32,18,36)[(seed>>16)%8]
                advance(key,key if step%15==0 else 0)
                if step==90 and g.state==STATE_PLAYING:snap('play','deterministic_exploratory_inputs')
        observations.append(dict(id=id,seed=0x100fa if id==100 else None,difficulty=1,steps=input_step,inputs=rle,checkpoints=checks,terminal=g.get_status(),source="legal_input_witness" if case else "exploratory_inputs"))
        if g.state>=3:
            for _ in range(60):g.update(DT,0,0)
            snap('result','legal_input_witness' if case else 'deterministic_exploratory_inputs')
        else:snap('unfinished','deterministic_exploratory_inputs')
        for phase,(b,st) in shots.items():
            (raw/f'py_{id:03}_{phase}.rgb').write_bytes(b);im=Image.frombytes('RGB',(16,16),b);im.save(images/f'py_{id:03}_{phase}.png');frames.append(dict(id=id,backend='Python',phase=phase,**st,nonzero=sum(v>0 for v in b),mean_channel=sum(b)/768,max_channel=max(b),sha256=hashlib.sha256(b).hexdigest()))
        for (gid,phase),st in native.items():
            if gid!=id:continue
            b=(cpp/st['file']).read_bytes();assert len(b)==768;(raw/f'cpp_{id:03}_{phase}.rgb').write_bytes(b);Image.frombytes('RGB',(16,16),b).save(images/f'cpp_{id:03}_{phase}.png');frames.append(dict(id=id,backend='C++',phase=phase,state=int(st['state']),score=int(st['score']),progress=int(st['progress']),source=st['source'],nonzero=sum(v>0 for v in b),mean_channel=sum(b)/768,max_channel=max(b),sha256=hashlib.sha256(b).hexdigest()))
        cppsource=(ROOT/meta['firmware_source']).read_text(encoding='utf-8');pysource=(ROOT/meta['simulator_source']).read_text(encoding='utf-8');specific=bool(re.search(r'SoundEvent\s*\(|Sounds\(\)\.Emit\s*\(',cppsource));cppresult=native.get((id,'result'));pyresult=shots.get('result');states_match=bool(cppresult and pyresult and int(cppresult['state'])==pyresult[1]['state']);three=all((id,s) in native and s in shots for s in ('title','play','result'))
        records.append(dict(id=f'{id:03}',name=meta['name'],REGISTERED='YES',HOST_BUILD='PASSED',CORE_RULES='INPUT_PATH_VERIFIED' if id in verified_wins else 'SOURCE_SCREENED_ONLY',FULL_ROUND='CPP_PY_WIN_PATH_PASSED' if id in verified_wins else 'CPP_PY_LOSS_ONLY' if id in losses else 'NOT_CERTIFIED',DIFFICULTY='THREE_TIERS_INPUT_VERIFIED' if id in b3wins|b2wins|{17,85,92,95} else 'SUPPORTED_NOT_FULLY_CERTIFIED' if g.difficulty_supported else 'NOT_SUPPORTED',VISUAL='ACTUAL_CPP_PY_THREE_STATES' if three else 'INCOMPLETE_STATE_CAPTURE',PYTHON_BACKEND=('NATIVE_DLL' if not g._fallback_mode else 'DEGRADED_PLACEHOLDER_UNCERTIFIED') if id==1 else 'PYTHON_CARTRIDGE',CONTROL_TYPE=g.control_type,CONTROL_MATCH='YES' if int(native[(id,'title')]['control_type'])==g.control_type else 'MISMATCH',MOBILE_INPUT='MAPPING_SOURCE_PRESENT; BROWSER_CHECK_SEPARATE; PHONE_NOT_TESTED',SFX='CARTRIDGE_EVENTS_PRESENT; LISTENING_PENDING' if specific else 'GENERIC_MANAGER_EVENTS_ONLY; REVIEW_PENDING',SCORING='CROSS_LANGUAGE_INPUT_CHECKPOINTS' if id in verified_wins|losses else 'NOT_CERTIFIED',HIGH_SCORE='RAM_CACHE_NVS_HOST_ADAPTER_PASSED; PHYSICAL_POWER_CYCLE_PENDING',HARDWARE='NOT_TESTED',PRODUCT_QUALITY='NOT_CERTIFIED',OBSERVED_TERMINAL_AGREEMENT=str(states_match),ADAPTATION=meta['core_mechanic'],firmware_sha256=hashlib.sha256(cppsource.encode()).hexdigest(),python_sha256=hashlib.sha256(pysource.encode()).hexdigest()))
    for record in records:
        observed=comparison[int(record['id'])]
        record['EXPLORATORY_CHECKPOINT_MISMATCHES']=int(observed['checkpoint_mismatches'])
        record['CROSS_LANGUAGE_REVIEW']=('UNSEEDED_RANDOMNESS_DIFFERS; NOT_CERTIFIED' if record['EXPLORATORY_CHECKPOINT_MISMATCHES'] else 'OBSERVED_PATH_AGREES; NOT_A_COMPLETE_RULE_PROOF')
    (out/'all_100_observation_paths.json').write_text(json.dumps(dict(dt_us=16667,cases=observations),separators=(',',':')),encoding='utf-8')
    with (out/'all_100_quality.csv').open('w',newline='',encoding='utf-8-sig') as f:w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
    (out/'frames.json').write_text(json.dumps(frames,ensure_ascii=False,indent=2),encoding='utf-8');(out/'all_100_quality.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    for page in range(2):
        atlas=Image.new('RGB',(800,1400),(12,18,27));draw=ImageDraw.Draw(atlas);draw.text((12,8),f'Phase C {page*50+1:03}-{page*50+50:03}: C++ top / Python bottom; title-play-result',font=font,fill='white')
        for n,r in enumerate(records[page*50:page*50+50]):
            id=int(r['id']);x=10+(n%5)*158;y=38+(n//5)*135;draw.text((x,y),f'{id:03} '+r['name'][:10],font=small,fill=(220,230,245))
            for row,backend in enumerate(('cpp','py')):
                for col,stage in enumerate(('title','play','result')):
                    f=images/f'{backend}_{id:03}_{stage}.png'
                    if f.exists():atlas.paste(Image.open(f).resize((48,48),Image.Resampling.NEAREST),(x+col*50,y+18+row*50))
                    else:draw.text((x+col*50,y+30+row*50),'pending',font=small,fill='orange')
        atlas.save(out/f'overview_{page+1}.png')
    cards=[]
    for r in records:
        id=int(r['id']);cells=[]
        for backend in ('cpp','py'):
            parts=''.join(f'<figure><img src="frames/{backend}_{id:03}_{stage}.png"><figcaption>{backend} {stage}</figcaption></figure>' for stage in ('title','play','result'))
            anim=[]
            for i in range(6):
                f=images/f'{backend}_{id:03}_anim{i}.png'
                if f.exists():anim.append(Image.open(f).resize((128,128),Image.Resampling.NEAREST))
            if anim:anim[0].save(images/f'{backend}_{id:03}_idle.gif',save_all=True,append_images=anim[1:],duration=33,loop=0)
            cells.append('<div class="row">'+parts+f'<figure><img src="frames/{backend}_{id:03}_idle.gif"><figcaption>6 idle-update samples</figcaption></figure></div>')
        cards.append(f'<section data-search="{html.escape(r["id"]+r["name"])}"><h2>{r["id"]} {html.escape(r["name"])}</h2><p>{html.escape(r["FULL_ROUND"])} / {html.escape(r["SFX"])}</p>'+''.join(cells)+'</section>')
    page='''<!doctype html><meta charset="utf-8"><title>Phase C: actual C++ / Python renderer gallery</title><style>body{background:#0c121b;color:#dce7f5;font:15px system-ui;margin:24px}input{padding:10px;position:sticky;top:0}section{border:1px solid #34475d;padding:16px;margin:16px 0}.row{display:flex;gap:18px;flex-wrap:wrap}figure{margin:8px}img{width:128px;height:128px;image-rendering:pixelated;background:black}figcaption{font-size:12px}h2{font-size:18px}</style><h1>100款真实渲染图集 · 软件截图，非实机LED验收</h1><p>每款：开始/游玩/真实结算；上C++下Python。idle GIF来自6次真实更新采样，不能证明显示帧率、输入延迟或动画品质。胜负、难度、听音、手机与产品验收分别记录。</p><input id="filter" placeholder="筛选编号或游戏名" oninput="document.querySelectorAll('section').forEach(x=>x.hidden=!x.dataset.search.toLowerCase().includes(this.value.toLowerCase()))">'''+''.join(cards)
    (out/'index.html').write_text(page,encoding='utf-8');summary=dict(registered=len(records),cpp_py_win_rounds=len(verified_wins),loss_only_ids=sorted(losses-verified_wins),remaining_win_uncertified=[r['id'] for r in records if r['FULL_ROUND']!='CPP_PY_WIN_PATH_PASSED'],three_state_count=sum(r['VISUAL']=='ACTUAL_CPP_PY_THREE_STATES' for r in records),control_mismatches=[r['id'] for r in records if r['CONTROL_MATCH']!='YES'],generic_sfx_only=[r['id'] for r in records if 'GENERIC_' in r['SFX']],terminal_divergences=[r['id'] for r in records if r['OBSERVED_TERMINAL_AGREEMENT']!='True'],blank_frames=[(f['id'],f['backend'],f['phase']) for f in frames if not f['nonzero']],boundary='Sources and host rendering/evidence only; no physical LED/phone/audio or final product certification')
    summary['exploratory_rng_review']=[r['id'] for r in records if r['EXPLORATORY_CHECKPOINT_MISMATCHES']]
    (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(json.dumps(summary));
if __name__=='__main__':main()
