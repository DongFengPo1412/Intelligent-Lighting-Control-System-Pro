"""Input-only complete rounds plus independent failure/mechanism assertions."""
import json
import math
from pathlib import Path
import unittest
from arcade_runner import ArcadeSession
from arcade.base_cartridge import *

DT=16667/1_000_000
CASES=json.loads((Path(__file__).parent/'fixtures/phase_b2_input_paths.json').read_text(encoding='utf-8'))['cases']


class PhaseB2Tests(unittest.TestCase):
    def game(self,gid,level=1):
        g=ArcadeSession().cartridges[gid];g.set_difficulty(level);g.init();g.start();return g

    def test_frozen_input_only_complete_rounds_and_lifecycle(self):
        for case in CASES:
            with self.subTest(gid=case['id'],difficulty=case['difficulty']):
                g=self.game(case['id'],case['difficulty']);events=[];g._sound_sink=lambda k,d:events.append((k,d))
                g.pause();before=bytes(g.render());g.update(.04,KEY_A|KEY_RIGHT,KEY_A|KEY_RIGHT)
                self.assertEqual(g.state,STATE_PAUSED);self.assertEqual(bytes(g.render()),before);g.resume()
                for count,down,pressed in case['inputs']:
                    for _ in range(count):g.update(DT,down,pressed)
                    self.assertEqual(len(g.render()),768)
                self.assertEqual(g.state,STATE_VICTORY)
                self.assertGreater(g.score,0);self.assertTrue(events)
                if case['id']==81:
                    self.assertEqual(g.grid[g.ey][g.ex],0)
                    self.assertFalse(any(2 in row for row in g.grid))
                if case['id']==55:self.assertEqual(g.stage,3);self.assertGreater(g.lives,0)
                if case['id']==58:self.assertEqual(g.get_status()['progress'],100);self.assertEqual(g.get_status()['lives'],3)
                for _ in range(60):g.update(DT,0,0)
                self.assertEqual(len(g.render()),768)
                g.reset();self.assertEqual(g.state,STATE_TITLE);g.start();self.assertEqual(g.state,STATE_PLAYING)

    def test_no_input_failure_and_frame_bounds_at_every_difficulty(self):
        for gid in (35,57,58,81,98):
            for level in range(3):
                with self.subTest(gid=gid,difficulty=level):
                    g=self.game(gid,level)
                    for _ in range(8000):
                        if g.state!=STATE_PLAYING:break
                        g.update(DT,0,0)
                    self.assertEqual(g.state,STATE_GAMEOVER)
                    g.reset();g.start();g.update(float('nan'),0,0);g.update(-1,65535,65535)
                    self.assertEqual(len(g.render()),768)

    def test_boulders_fall_crush_and_horizontal_push(self):
        g=self.game(35);g.update(DT,0,KEY_RIGHT);self.assertEqual(g.gems,1);self.assertEqual(g.score,100)
        # Controlled collision fixture, separate from the full-round witnesses.
        g.grid[4][5]=3;g.grid[4][6]=0;g.x=4;g.y=4
        g.update(DT,0,KEY_RIGHT);self.assertEqual((g.x,g.grid[4][6]),(5,3))
        g.x=3;g.y=5;g.grid[3][3]=3;g.grid[4][3]=g.grid[5][3]=0
        for _ in range(12):g.update(.05,0,0)
        self.assertEqual(g.state,STATE_GAMEOVER)

    def test_rush_hour_axis_collision_and_actual_move_budget(self):
        g=self.game(57,2);before=[c[:] for c in g.cars]
        g.update(DT,0,KEY_UP);self.assertEqual(g.cars,before)
        g.update(DT,0,KEY_RIGHT);self.assertEqual(g.cars,before) # red blocked by vertical truck
        for _ in range(4):g.update(DT,0,KEY_A)
        for i in range(16):g.update(DT,0,KEY_RIGHT if i%2==0 else KEY_LEFT)
        self.assertEqual(g.moves,16);self.assertEqual(g.state,STATE_GAMEOVER)

    def test_program_relative_turns_capacity_gate_and_three_failed_runs(self):
        for level,limit in enumerate((20,17,14)):
            g=self.game(58,level)
            for _ in range(30):g.update(DT,0,KEY_UP)
            self.assertEqual(len(g.program),limit)
            self.assertTrue(g.wall(3,2));g.reset();g.start()
            for _ in range(4):g.update(DT,0,KEY_UP)
            for run in range(3):
                g.update(DT,0,KEY_A)
                for _ in range(100):
                    g.update(DT,0,0)
                    if not g.running:break
                self.assertEqual(g.attempts,2-run)
            self.assertEqual(g.state,STATE_GAMEOVER)

    def test_robot_all_four_heading_markers_are_visually_distinct(self):
        g=self.game(58);markers=[]
        for heading in range(4):
            g.heading=heading;frame=g.render()
            marker=tuple(tuple(frame[((g.y*2+y)*16+g.x*2+x)*3:((g.y*2+y)*16+g.x*2+x)*3+3]) for y in range(2) for x in range(2))
            self.assertEqual(marker.count((60,180,255)),2);markers.append(marker)
        self.assertEqual(len(set(markers)),4)

    def test_qix_trail_self_collision_and_enemy_collision(self):
        g=self.game(81)
        for key in (KEY_A,KEY_RIGHT,KEY_RIGHT,KEY_DOWN,KEY_LEFT,KEY_UP):g.update(DT,0,key)
        self.assertEqual(g.state,STATE_GAMEOVER)
        g=self.game(81);g.grid[g.ey+g.vy][g.ex+g.vx]=2
        for _ in range(10):g.update(DT,0,0)
        self.assertEqual(g.state,STATE_GAMEOVER)

    def test_lander_inertia_thrust_fuel_and_unsafe_contact(self):
        g=self.game(98);g.update(.05,0,0);self.assertGreater(g.vy,0)
        fuel=g.fuel
        for _ in range(10):g.update(.05,KEY_A|KEY_RIGHT,0)
        self.assertLess(g.fuel,fuel);self.assertGreater(g.angle,0);self.assertGreater(g.vx,0)
        g.x=8;g.y=12.99;g.vy=3;g.update(DT,0,0)
        self.assertEqual(g.state,STATE_GAMEOVER)

    def test_laser_bomb_failure_through_real_mirror_input(self):
        g=self.game(55)
        for lives in (2,1,0):
            g.update(DT,0,KEY_A)
            for _ in range(60):g.update(DT,0,0)
            self.assertEqual(g.lives,lives+1) # previewing a wrong route is safe
            g.update(DT,0,KEY_B)
            for _ in range(35):g.update(DT,0,0)
            self.assertEqual(g.lives,lives)
        self.assertEqual(g.state,STATE_GAMEOVER)


if __name__=='__main__':unittest.main()
