"""Complete deterministic rounds via inputs, plus independent mechanism failures.
No terrain, enemies or progress counters are rewritten by the winning policies.
"""
import math
import unittest
from arcade_runner import ArcadeSession
from arcade.fixed_step import FixedStepClock
from arcade.base_cartridge import *

DT=16667/1_000_000
LANES=(KEY_LEFT,KEY_DOWN,KEY_UP,KEY_RIGHT)

def rhythm_policy(g):
    pressed=0
    for note in g.notes:
        if note.active and abs(note.y-13)<.16:pressed|=LANES[note.lane]
    return 0,pressed

def hex_policy(g):
    threats=[w for w in g.walls if w.radius>=1.9]
    if not threats:return 0,0
    wall=min(threats,key=lambda w:w.radius)
    choices=[]
    for sector in range(6):
        if not wall.solid_mask&(1<<sector):
            target=(sector+.5)*math.pi/3
            delta=(target-g.player_angle+math.pi)%(2*math.pi)-math.pi
            choices.append(delta)
    delta=min(choices,key=abs)
    return (KEY_RIGHT if delta>.07 else KEY_LEFT if delta<-.07 else 0),0

def lemming_policy(g,flags):
    stage=g.stage
    if stage==1:target=(6,4);skill=2;mark='dig1'
    elif stage==2:target=(7,11);skill=1;mark='build2'
    elif 'dig3' not in flags:target=(6,4);skill=2;mark='dig3'
    else:target=(7,9);skill=1;mark='build3'
    if mark in flags:return 0,0
    x,y=target
    if g.cursor_x!=x:return 0,KEY_RIGHT if g.cursor_x<x else KEY_LEFT
    if g.cursor_y!=y:return 0,KEY_DOWN if g.cursor_y<y else KEY_UP
    if g.selected_skill!=skill:return 0,KEY_B
    if any(lm.alive and lm.state==0 and lm.x==x and lm.y==y for lm in g.lemmings):
        flags.add(mark);return 0,KEY_A
    return 0,0

def fruit_policy(g):
    # Evaluate the actual finite slash segment, including every active bomb.
    r=(1.9,1.65,1.4)[g.difficulty]
    if g.slash_timer<=DT:
        best=None
        for dx,dy,mask in [(1,0,KEY_RIGHT),(-1,0,KEY_LEFT),(0,1,KEY_DOWN),(0,-1,KEY_UP),
                (1,1,KEY_RIGHT|KEY_DOWN),(1,-1,KEY_RIGHT|KEY_UP),(-1,1,KEY_LEFT|KEY_DOWN),(-1,-1,KEY_LEFT|KEY_UP)]:
            x=max(1.5,min(14.5,g.blade_x+dx*14*DT));y=max(1.5,min(14.5,g.blade_y+dy*14*DT))
            norm=math.hypot(dx,dy);ux,uy=dx/norm,dy/norm
            hits=0;safe=True
            for item in g.items:
                if not item.active:continue
                cx,cy=item.x+1,item.y+1
                projection=max(-5,min(5,(cx-x)*ux+(cy-y)*uy))
                dist=math.hypot(cx-(x+projection*ux),cy-(y+projection*uy))
                if item.is_bomb and dist<=r+.1:safe=False
                if not item.is_bomb and 1<=cy<=15 and dist<=r-.1:hits+=1
            if safe and hits and (best is None or hits>best[0]):best=(hits,mask)
        if best:return best[1],KEY_A
    fruits=[i for i in g.items if i.active and not i.is_bomb and i.y<14.5]
    if not fruits:return 0,0
    target=min(fruits,key=lambda i:abs(i.x+1-g.blade_x)+abs(i.y+1-g.blade_y))
    mask=KEY_LEFT if target.x+1<g.blade_x-.4 else KEY_RIGHT if target.x+1>g.blade_x+.4 else 0
    if g.blade_y>8.5:mask|=KEY_UP
    elif g.blade_y<7.5:mask|=KEY_DOWN
    return mask,0


class PhaseBTests(unittest.TestCase):
    def test_complete_round_and_restart_at_each_difficulty(self):
        for gid,policy in [(17,rhythm_policy),(85,lemming_policy),(92,fruit_policy),(95,hex_policy)]:
            for difficulty in range(3):
                with self.subTest(gid=gid,difficulty=difficulty):
                    g=ArcadeSession().cartridges[gid];self.assertTrue(g.set_difficulty(difficulty));g.init();g.start()
                    if gid==17:
                        frame=g.render()
                        self.assertEqual(sum(frame[3*x:3*x+3]==bytearray((80,230,140)) for x in range(16)),(10,8,5)[difficulty])
                    flags=set();events=[];g._sound_sink=lambda k,d:events.append((k,d))
                    for tick in range(16000):
                        if g.state!=STATE_PLAYING:break
                        down,pressed=policy(g,flags) if gid==85 else policy(g)
                        g.update(DT,down,pressed)
                        if tick%61==0:self.assertEqual(len(g.render()),768)
                    self.assertEqual(g.state,STATE_VICTORY,f'{gid} level {difficulty}, score={g.score}, flags={flags}')
                    self.assertGreater(g.score,0)
                    if gid==17:self.assertTrue(any(e[0]=='beat' for e in events));self.assertEqual(g.notes_cleared,64)
                    if gid==85:self.assertEqual(g.stage,3);self.assertGreaterEqual(g.saved_count,(2,3,4)[difficulty])
                    if gid==92:self.assertGreaterEqual(g.fruits_sliced,40);self.assertFalse(g.exploded)
                    if gid==95:self.assertTrue(g.survival_timer>=45 or g.walls_passed>=30)
                    g.reset();self.assertEqual(g.state,STATE_TITLE);self.assertEqual(g.difficulty,difficulty)
                    g.start();g.pause();g.update(DT,KEY_A,KEY_A);self.assertEqual(g.state,STATE_PAUSED)
                    g.resume();self.assertEqual(g.state,STATE_PLAYING)

    def test_no_input_eventually_loses_every_selected_game(self):
        for gid in (17,85,92,95):
            g=ArcadeSession().cartridges[gid];g.init();g.start()
            for _ in range(12000):
                if g.state!=STATE_PLAYING:break
                g.update(DT,0,0)
            self.assertEqual(g.state,STATE_GAMEOVER,str(gid))

    def test_clock_preserves_elapsed_time_and_caps_stalls(self):
        c=FixedStepClock();called=[]
        for _ in range(45000):c.advance(.04,lambda dt:called.append(dt))
        self.assertEqual(c.steps,1_800_000_000//16667);self.assertEqual(c.dropped_us,0)
        before=c.steps;c.advance(2,lambda dt:called.append(dt));self.assertEqual(c.steps-before,4)
        self.assertGreater(c.dropped_us,1_900_000)
        c.advance(-1,lambda _:self.fail('backward time advanced'))

    def test_settings_are_authoritative_and_failed_change_has_no_side_effects(self):
        s=ArcadeSession();s.select_game(17,True)
        reply=s.configure(False,15,0);self.assertEqual(reply['game_status']['difficulty'],0)
        s.start();self.assertEqual(s.configure(True,90,2)['status'],'error');self.assertFalse(s.sound_enabled)
        s.reset();self.assertEqual(s.configure(True,25,2)['game_status']['difficulty'],2)
        s.select_game(20,True);self.assertEqual(s.configure(True,25,2)['error'],'difficulty_unsupported')
        for enabled,volume,level in [('true',25,None),(True,True,None),(True,101,None),(True,25,3)]:
            self.assertEqual(s.configure(enabled,volume,level)['status'],'error')

    def test_actual_simulator_clock_path_all_59_and_hitch(self):
        session=ArcadeSession()
        for gid in session.cartridges:
            with self.subTest(gid=gid):
                session.select_game(gid,True);session.start()
                for i in range(100):
                    session._simulator_step((.033,.047,.065,.018)[i%4])
                self.assertEqual(len(session.current_hex),1536)
                before=session._clock.steps
                session._simulator_step(2.)
                self.assertEqual(session._clock.steps-before,4)

if __name__=='__main__':unittest.main()
