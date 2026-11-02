# -*- coding: utf-8 -*-
"""
test_arcade_017_piano_tiles.py —— 别踩白块儿 2014 完整单元测试
验证四轨下落、底线精准打击、连击加分、踩白即死、漏击判负与全曲通关判定
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_017_piano_tiles import Game017PianoTiles, PianoNote
from arcade.base_cartridge import (
    KEY_LEFT,
    KEY_DOWN,
    KEY_UP,
    KEY_RIGHT,
    STATE_PLAYING,
    STATE_GAMEOVER,
    STATE_VICTORY,
    CTRL_MULTI_TRACK,
)
from arcade.arcade_registry import ArcadeRegistry

class TestGame017PianoTiles(unittest.TestCase):
    def setUp(self):
        self.game = Game017PianoTiles()
        self.game.reset()

    def test_metadata_and_registry(self):
        """测试卡带元数据与注册中心集成"""
        self.assertEqual(self.game.game_id, 17)
        self.assertEqual(self.game.name, "别踩白块儿")
        self.assertEqual(self.game.english_name, "Piano Tiles 2014")
        self.assertEqual(self.game.release_year, 2014)
        self.assertEqual(self.game.control_type, CTRL_MULTI_TRACK)

        cart = ArcadeRegistry.get_cartridge(17)
        self.assertIsNotNone(cart)
        self.assertEqual(cart.name, "别踩白块儿")

    def test_four_track_initialization(self):
        """测试四轨道初始音符生成与基本参数"""
        self.assertGreaterEqual(len(self.game.notes), 1)
        note = self.game.notes[0]
        self.assertIn(note.track, (0, 1, 2, 3))
        self.assertEqual(note.height, 3.0)

    def test_accurate_hit_on_hit_line(self):
        """测试底线精准击碎音符、连击累加与闪光触发"""
        # 手动放置一颗音符在 Track 0, y=12.0 (底线判定区)
        self.game.notes = [PianoNote(0, 12.0)]
        self.assertEqual(self.game.combo, 0)
        self.assertEqual(self.game.total_hits, 0)

        # 按 Track 0 (KEY_LEFT)
        self.game.update(0.02, 0, KEY_LEFT)

        self.assertEqual(self.game.combo, 1)
        self.assertEqual(self.game.total_hits, 1)
        self.assertGreater(self.game.score, 0)
        self.assertGreater(self.game.hit_flash_timer[0], 0.0) # 闪光激活

    def test_stepping_on_white_empty_track(self):
        """测试踩到空白轨道立即判定猝死"""
        # 仅在 Track 0 有音符，玩家按下 Track 2 (KEY_UP)
        self.game.notes = [PianoNote(0, 12.0)]
        self.assertEqual(self.game.state, STATE_PLAYING)

        self.game.update(0.02, 0, KEY_UP)
        self.assertEqual(self.game.state, STATE_GAMEOVER)

    def test_too_early_hit_triggers_gameover(self):
        """测试音符过高时提前乱按视为踩白猝死"""
        # 音符还在顶部 y=1.0 处，尚未进入底线判定区
        self.game.notes = [PianoNote(0, 1.0)]
        self.game.update(0.02, 0, KEY_LEFT)
        self.assertEqual(self.game.state, STATE_GAMEOVER)

    def test_miss_note_dropped_below_bottom(self):
        """测试音符漏击跌穿底线触发 Game Over"""
        self.game.notes = [PianoNote(1, 15.1)]
        # 自由下落一小步使其 y > 15.2
        self.game.update(0.02, 0, 0)
        self.assertEqual(self.game.state, STATE_GAMEOVER)

    def test_speed_scaling_with_hits(self):
        """测试连击击中后下落节奏自适应提速"""
        initial_speed = self.game.fall_speed
        self.game.notes = [PianoNote(0, 12.0)]
        self.game.update(0.02, 0, KEY_LEFT)
        self.assertGreater(self.game.fall_speed, initial_speed)

    def test_four_track_key_mapping(self):
        """测试四轨按键映射: Track 0=LEFT, Track 1=DOWN, Track 2=UP, Track 3=RIGHT"""
        # 测试 Track 3 (KEY_RIGHT)
        self.game.notes = [PianoNote(3, 12.0)]
        self.game.update(0.02, 0, KEY_RIGHT)
        self.assertEqual(self.game.total_hits, 1)

    def test_victory_on_target_hits(self):
        """测试击满目标音符数 (40块) 达成乐章通关"""
        self.game.total_hits = 39
        self.game.notes = [PianoNote(2, 12.0)]

        # 击碎最后第 40 块
        self.game.update(0.02, 0, KEY_UP)
        self.assertEqual(self.game.total_hits, 40)
        self.assertEqual(self.game.state, STATE_VICTORY)

    def test_render_buffer_dimensions(self):
        """测试渲染输出符合 16x16 RGB 规范 (768 字节)"""
        buf = self.game.render()
        self.assertEqual(len(buf), 16 * 16 * 3)

if __name__ == "__main__":
    unittest.main()
