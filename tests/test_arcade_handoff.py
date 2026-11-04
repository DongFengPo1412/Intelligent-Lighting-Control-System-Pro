"""Inherited cartridges: actual simulation, protocol consistency, and solved rounds.

Host tests are not physical LED, phone, power or audio acceptance.
"""
import json
from pathlib import Path
import random
import re
import threading
import unittest
from collections import deque

from arcade_runner import ArcadeSession
from arcade.base_cartridge import KEY_UP,KEY_DOWN,KEY_LEFT,KEY_RIGHT,KEY_A,KEY_B,STATE_PAUSED,STATE_PLAYING,STATE_VICTORY

ROOT=Path(__file__).resolve().parents[1]
REGISTRY=json.loads((ROOT/'pc-agent-vision/arcade/registered_games.json').read_text())


class HandoffTests(unittest.TestCase):
    def test_canonical_target_ids_match_every_transport_and_build_registry(self):
        ids={e['id'] for e in REGISTRY}
        self.assertEqual(len(ids),len(REGISTRY))
        self.assertEqual(ids,set(ArcadeSession().cartridges))
        manager=(ROOT/'firmware-s3/main/display/arcade/arcade_manager.cpp').read_text(encoding='utf-8')
        self.assertEqual(ids,{int(i) for i in re.findall(r'case (\d+):',manager)})
        js=(ROOT/'pc-agent-vision/web_app/arcade_transport.js').read_text(encoding='utf-8')
        self.assertEqual(ids,set(json.loads(re.search(r'const IDS = new Set\((\[[^\n]+\])\)',js)[1])))
        java=(ROOT/'android-app/src/org/fglab/kurisu/DeviceUdpClient.java').read_text()
        self.assertEqual(ids,{int(i) for i in re.findall(r'id==(\d+)',java)})
        cmake=(ROOT/'firmware-s3/main/CMakeLists.txt').read_text()
        self.assertEqual({e['module'] for e in REGISTRY},set(re.findall(r'arcade/(game_\w+)\.cpp',cmake)))

    def test_each_registered_game_executes_inputs_pauses_resets_and_renders_bounded_frames(self):
        session=ArcadeSession()
        for gid,cart in session.cartridges.items():
            with self.subTest(game_id=gid):
                self.assertEqual(session.select_game(gid,True)['status'],'ok')
                cart.init();cart.start()
                self.assertEqual(cart.game_id,gid)
                self.assertEqual(cart.get_status()['state'],STATE_PLAYING)
                rng=random.Random(gid)
                for step in range(1800):
                    key=1<<rng.randrange(6)
                    cart.update(.016,key if step%7 else 0,key if step%9==0 else 0)
                    if step%31==0:
                        frame=cart.render()
                        self.assertEqual(len(frame),768)
                        self.assertTrue(all(0<=v<=255 for v in frame))
                cart.reset();cart.start();cart.pause()
                self.assertEqual(cart.get_status()['state'],STATE_PAUSED)
                paused=bytes(cart.render());cart.update(.04,KEY_A,KEY_A)
                self.assertEqual(cart.get_status()['state'],STATE_PAUSED)
                cart.resume();self.assertEqual(cart.get_status()['state'],STATE_PLAYING)
                self.assertTrue(paused)

    def test_pong_explicit_mode_preserves_lifecycle_score_and_independent_players(self):
        session=ArcadeSession();session.select_game(20,True)
        self.assertEqual(session.players(2)['game_status']['player_count'],2)
        session.start();g=session.current_cartridge
        p1,p2=g.p1_y,g.p2_y
        g.update(.04,KEY_UP|KEY_B,KEY_UP|KEY_B)
        self.assertLess(g.p1_y,p1);self.assertGreater(g.p2_y,p2)
        g.p1_score=2;g.p2_score=3;session.pause()
        self.assertEqual(session.players(1)['game_status']['state'],STATE_PAUSED)
        self.assertEqual((g.p1_score,g.p2_score),(2,3))
        session.resume();session.reset();session.start()
        self.assertEqual(session.read_status()['game_status']['player_count'],1)
        for invalid in (True,0,3,'2'):
            self.assertEqual(session.players(invalid)['status'],'error')
        session.players(2);session.select_game(20,True)
        self.assertEqual(session.read_status()['game_status']['player_count'],1)

    def test_remote_frame_wait_does_not_own_game_lock(self):
        entered=threading.Event();release=threading.Event()
        class Controller:
            port='FAKE';control_connected=True
            def command_result(self,payload):
                if payload['cmd']=='frame':
                    entered.set();release.wait(2)
                    return {'status':'error','error':'lost_frame'}
                return {'status':'ok','arcade':{'game_id':20,'state':1}}
        s=ArcadeSession(Controller());s.status['game_id']=20
        result=[];reader=threading.Thread(target=lambda:result.append(s.get_frame()))
        reader.start()
        try:
            self.assertTrue(entered.wait(1))
            self.assertEqual(s.input_state(18,16)['status'],'ok')
            self.assertTrue(reader.is_alive())
        finally:
            release.set();reader.join(2)
        self.assertEqual(result[0]['error'],'lost_frame')

    def test_hanoi_all_authored_stages_solve_through_real_input(self):
        g=ArcadeSession().cartridges[53];g.init();g.start()
        def press(key):g.update(.016,key,key)
        def cursor(target):
            while g.cursor_peg!=target:press(KEY_RIGHT if g.cursor_peg<target else KEY_LEFT)
        def solve(n,src,dst,aux):
            if not n:return
            solve(n-1,src,aux,dst)
            cursor(src);press(KEY_A);cursor(dst);press(KEY_A)
            solve(n-1,aux,dst,src)
        for n in (4,5):
            self.assertEqual(g.num_disks,n)
            solve(n,0,2,1)
        self.assertEqual(g.state,STATE_VICTORY)
        self.assertGreater(g.score,0)

    def test_mirror_maze_all_authored_levels_have_executable_solution(self):
        g=ArcadeSession().cartridges[40];g.init();g.start()
        for level in range(g.TOTAL_LEVELS):
            self.assertEqual(g.level,level)
            start=(g.ax,g.ay,g.bx,g.by);goal=(g.goal_ax,g.goal_ay,g.goal_bx,g.goal_by)
            queue=deque([start]);parent={start:None}
            while queue and goal not in parent:
                pos=queue.popleft()
                for dx,dy,key in ((-1,0,KEY_LEFT),(1,0,KEY_RIGHT),(0,-1,KEY_UP),(0,1,KEY_DOWN)):
                    ax,ay,bx,by=pos
                    if 0<=ax+dx<16 and 0<=ay+dy<16 and g.map[ay+dy][ax+dx]!=1:ax+=dx;ay+=dy
                    if 0<=bx-dx<16 and 0<=by+dy<16 and g.map[by+dy][bx-dx]!=1:bx-=dx;by+=dy
                    nxt=(ax,ay,bx,by)
                    if g.map[ay][ax]==2 or g.map[by][bx]==2 or nxt in parent:continue
                    parent[nxt]=(pos,key);queue.append(nxt)
            self.assertIn(goal,parent,f'unsolvable authored mirror level {level}')
            steps=[];current=goal
            while parent[current] is not None:
                current,key=parent[current];steps.append(key)
            for key in reversed(steps):g.update(.016,key,key)
        self.assertEqual(g.state,STATE_VICTORY)


if __name__=='__main__':unittest.main()
