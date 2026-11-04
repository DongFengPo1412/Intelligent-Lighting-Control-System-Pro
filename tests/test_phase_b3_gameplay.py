"""Frozen real-input wins/losses, differential checkpoints and lifecycle tests."""
import json
import math
from pathlib import Path
import unittest
from arcade_runner import ArcadeSession
from arcade.base_cartridge import *

DATA=json.loads((Path(__file__).parent/'fixtures/phase_b3_input_paths.json').read_text(encoding='utf-8'))
RULES=json.loads((Path(__file__).parent/'fixtures/phase_b3_rules.json').read_text(encoding='utf-8'))
DT=16667/1_000_000


class B3Tests(unittest.TestCase):
    def test_exact_100_manifest_and_production_sources(self):
        root=Path(__file__).resolve().parents[1]
        manifest=json.loads((root/'games_100_manifest.json').read_text(encoding='utf-8'))
        self.assertEqual([int(g['id']) for g in manifest],list(range(1,101)))
        self.assertEqual(set(ArcadeSession().cartridges),set(range(1,101)))
        for g in manifest:
            self.assertEqual(g['status'],'integrated_software')
            self.assertTrue((root/g['firmware_source']).is_file())
            self.assertTrue((root/g['simulator_source']).is_file())

    def test_bowling_standard_score_arithmetic(self):
        from arcade.b3_helpers import bowling_total
        for rolls,total in (([10]*12,300),([5,5]*10+[5],150),([0]*20,0),([10,7,3,9,0,10,0,8,8,2,0,6,10,10,10,8,1],167)):
            self.assertEqual(bowling_total(rolls),total)

    def test_visible_upgrade_choices_have_different_real_effects(self):
        case=next(c for c in DATA['cases'] if c['id']==99 and c['difficulty']==0 and c['outcome']=='win')
        for key in (KEY_A,KEY_B):
            g=ArcadeSession().cartridges[99];g.init();g.start();ready=False
            for n,down,pressed in case['inputs']:
                for _ in range(n):
                    if g.kills>=3:ready=True;break
                    g.update(DT,down,pressed)
                if ready:break
            self.assertTrue(ready);g.update(DT,0,key)
            self.assertEqual(g.upgrades,1)
            self.assertEqual((g.damage,g.rate_bonus),(2,0) if key==KEY_A else (1,1))

    def test_complete_input_only_wins_and_losses_with_key_state_checkpoints(self):
        ids=set()
        for case in DATA['cases']:
            with self.subTest(id=case['id'],level=case['difficulty'],outcome=case['outcome']):
                ids.add(case['id']);g=ArcadeSession().cartridges[case['id']];self.assertTrue(g.set_difficulty(case['difficulty']));g.init();g.start()
                g.pause();g.update(.04,KEY_RIGHT|KEY_A,KEY_RIGHT|KEY_A);self.assertEqual(g.state,STATE_PAUSED);g.resume()
                checkpoints={c[0]:c for c in case['checkpoints']};step=0
                for n,down,pressed in case['inputs']:
                    for _ in range(n):
                        step+=1;g.update(DT,down,pressed)
                        if step in checkpoints:
                            st=g.get_status();actual=[step,st['state'],st['score'],st['lives'],st['progress']]+[eval('g.'+key,{'g':g}) for key in RULES[str(g.game_id)]['keys']]
                            self.assertEqual(actual,checkpoints[step]);self.assertEqual(len(g.render()),768)
                self.assertEqual(g.state,STATE_VICTORY if case['outcome']=='win' else STATE_GAMEOVER)
                if case['outcome']=='win':self.assertGreater(g.score,0)
                for _ in range(60):g.update(DT,0,0)
                self.assertEqual(len(g.render()),768);g.reset();self.assertEqual(g.state,STATE_TITLE);g.start();self.assertEqual(g.state,STATE_PLAYING)
                g.update(float('nan'),0,0);g.update(-1,65535,65535);self.assertEqual(len(g.render()),768)
        self.assertEqual(ids,{int(k) for k in RULES})
        self.assertEqual(len(DATA['cases']),len(ids)*6)


if __name__=='__main__':unittest.main()
