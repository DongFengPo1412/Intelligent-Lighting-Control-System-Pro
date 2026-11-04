"""Phase C real-input regression: no terminal/score setters or puzzle-state backdoors."""
import collections,json,unittest
from pathlib import Path
from arcade_runner import ArcadeSession
from arcade.base_cartridge import *
ROOT=Path(__file__).resolve().parents[1]
DT=16667/1000000
DATA=json.loads((ROOT/'tests/fixtures/phase_c_input_paths.json').read_text(encoding='utf-8'))
RULES=json.loads((ROOT/'tests/fixtures/phase_b3_rules.json').read_text(encoding='utf-8'))
class PhaseCTests(unittest.TestCase):
    def test_mario_ready_pause_and_public_state_follow_engine(self):
        g=ArcadeSession().cartridges[1];g.init();g.start()
        self.assertEqual(g.state,g.get_status()['state']);self.assertEqual(g.state,STATE_PLAYING)
        g.pause();self.assertEqual(g.state,STATE_PAUSED);before=bytes(g.render())
        for _ in range(150):g.update(DT,KEY_RIGHT,KEY_RIGHT)
        self.assertEqual(bytes(g.render()),before);g.resume();self.assertEqual(g.state,STATE_PLAYING)
        if g._fallback_mode:self.skipTest('Native Mario DLL not available; fallback is not physics certification')
        for _ in range(18000):
            g.update(DT,KEY_RIGHT,0)
            self.assertEqual(g.state,g.get_status()['state']);self.assertEqual(g.score,g.get_status()['score'])
            if g.state==STATE_GAMEOVER:break
        self.assertEqual(g.state,STATE_GAMEOVER);self.assertEqual(g.get_status()['lives'],0)

    def test_all_authored_pacman_pellets_are_reachable(self):
        from collections import deque
        g=ArcadeSession().cartridges[34];g.init();g.start();start=(round(g.pac_x),round(g.pac_y));queue=deque([start]);seen={start}
        while queue:
            x,y=queue.popleft()
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                xx=x+dx;yy=y+dy
                if yy==7:xx%=16
                if 0<=xx<16 and 0<=yy<16 and not g._is_wall(xx,yy) and (xx,yy) not in seen:seen.add((xx,yy));queue.append((xx,yy))
        pellets={(x,y) for y in range(16) for x in range(16) if g.grid[y][x] in (1,2)}
        self.assertEqual(len(pellets),119);self.assertFalse(pellets-seen)

    def test_tron_turn_reverse_hold_and_collision_events(self):
        g=ArcadeSession().cartridges[80];g.init();g.start();events=[];g._sound_sink=lambda k,d:events.append((k,d))
        g.update(DT,KEY_RIGHT,KEY_RIGHT)
        for _ in range(3):g.update(DT,KEY_RIGHT,0)
        g.update(DT,KEY_LEFT,KEY_LEFT)
        self.assertEqual([e for e in events if e[0]=='action'],[('action',1)])
        for _ in range(240):
            g.update(DT,KEY_RIGHT,0)
            if g.state==STATE_GAMEOVER:break
        self.assertEqual(g.state,STATE_GAMEOVER);self.assertEqual(sum(k=='collision' for k,d in events),1)

    def test_memory_fresh_decks_and_replay_seed_validation(self):
        g=ArcadeSession().cartridges[100];decks=set()
        for _ in range(20):
            g.reset();self.assertEqual(collections.Counter(g.cards),collections.Counter({i:2 for i in range(8)}));decks.add(tuple(g.cards))
        self.assertGreater(len(decks),15)
        for seed in (0,1,42,0xffffffff):
            self.assertTrue(g.set_replay_seed(seed));g.reset();deck=tuple(g.cards);g.start();self.assertEqual(tuple(g.cards),deck)
        for seed in (-1,0x100000000,True,'1',None):self.assertFalse(g.set_replay_seed(seed))
        g.use_random_seeds();g.reset();self.assertFalse(getattr(g,'_replay_seed',None))

    def test_nim_opponent_turn_is_visible_and_does_not_accept_double_take(self):
        g=ArcadeSession().cartridges[69];g.init();g.start();g.update(DT,0,KEY_A);piles=g.piles[:]
        self.assertGreater(g.thinking,0)
        for _ in range(10):g.update(DT,0,KEY_A)
        self.assertEqual(g.piles,piles)
        for _ in range(15):g.update(DT,0,0)
        self.assertLess(sum(g.piles),sum(piles))

    def test_three_fire_missions_use_water_and_refill(self):
        data=json.loads((ROOT/'tests/fixtures/phase_b3_input_paths.json').read_text())
        case=next(c for c in data['cases'] if c['id']==89 and c['difficulty']==2 and c['outcome']=='win')
        g=ArcadeSession().cartridges[89];g.set_difficulty(2);g.init();g.start();waves=set();spent=0;refills=0
        for n,down,pressed in case['inputs']:
            for _ in range(n):
                water=g.water;g.update(DT,down,pressed);waves.add(g.wave);spent+=g.water<water;refills+=g.water>water
        self.assertEqual(g.state,STATE_VICTORY);self.assertEqual(waves,{0,1,2,3});self.assertGreaterEqual(spent,9);self.assertGreaterEqual(refills,1)

    def test_additional_input_only_rounds_and_seed_variations(self):
        for case in DATA['cases']:
            with self.subTest(id=case['id'],seed=case.get('seed'),outcome=case['outcome']):
                g=ArcadeSession().cartridges[case['id']]
                if g.difficulty_supported:self.assertTrue(g.set_difficulty(case['difficulty']))
                if case.get('seed') is not None:self.assertTrue(g.set_replay_seed(case['seed']))
                g.init();g.start();checks={p[0]:p for p in case['checkpoints']};step=0;keys=RULES.get(str(g.game_id),{}).get('keys',[])
                for n,down,pressed in case['inputs']:
                    for _ in range(n):
                        step+=1;g.update(DT,down,pressed)
                        if step in checks:
                            s=g.get_status();self.assertEqual([step,s['state'],s['score'],s['lives'],s['progress']]+[eval('g.'+key,{'g':g}) for key in keys],checks[step]);self.assertEqual(len(g.render()),768)
                self.assertEqual(g.state,STATE_VICTORY if case['outcome']=='win' else STATE_GAMEOVER)
                if g.game_id==54:self.assertEqual(g.get_status()['score'],g.score)
                g.pause();g.reset();g.start();self.assertEqual(g.state,STATE_PLAYING)
if __name__=='__main__':unittest.main()
