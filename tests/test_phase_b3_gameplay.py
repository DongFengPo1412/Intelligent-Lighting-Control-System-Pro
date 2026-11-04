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
