# -*- coding: utf-8 -*-
"""
test_arcade_009_space_invaders.py —— 太空侵略者 1978 完整单元测试
验证外星编队行军、下压转向、掩体损毁、防空拦截、炸弹投掷与胜败判定
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_009_space_invaders import Game009SpaceInvaders
from arcade.base_cartridge import (
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
    STATE_PLAYING,
    STATE_GAMEOVER,
    STATE_VICTORY,
    CTRL_ARCADE_AB,
)
from arcade.arcade_registry import ArcadeRegistry

class TestGame009SpaceInvaders(unittest.TestCase):
    def setUp(self):
        self.game = Game009SpaceInvaders()
        self.game.reset()

    def test_metadata_and_registry(self):
        """测试卡带元数据与注册中心集成"""
        self.assertEqual(self.game.game_id, 9)
        self.assertEqual(self.game.name, "太空侵略者")
        self.assertEqual(self.game.english_name, "Space Invaders 1978")
        self.assertEqual(self.game.release_year, 1978)
        self.assertEqual(self.game.control_type, CTRL_ARCADE_AB)

        cart = ArcadeRegistry.get_cartridge(9)
        self.assertIsNotNone(cart)
        self.assertEqual(cart.name, "太空侵略者")

    def test_fleet_initialization(self):
        """测试外星舰队初始状态：3排4列共12只，分值递减"""
        self.assertEqual(len(self.game.fleet), 3)
        self.assertEqual(len(self.game.fleet[0]), 4)
        self.assertEqual(self.game.remaining_aliens, 12)

        # Row 0: 30分
        self.assertEqual(self.game.fleet[0][0].score_val, 30)
        # Row 1: 20分
        self.assertEqual(self.game.fleet[1][0].score_val, 20)
        # Row 2: 10分
        self.assertEqual(self.game.fleet[2][0].score_val, 10)

    def test_player_cannon_movement(self):
        """测试玩家炮台在 [1.0, 14.0] 区间内平滑移动与边界限制"""
        self.assertEqual(self.game.player_x, 7.0)

        # 左移
        self.game.update(0.1, KEY_LEFT, 0)
        self.assertLess(self.game.player_x, 7.0)

        # 极限左移
        for _ in range(30):
            self.game.update(0.1, KEY_LEFT, 0)
        self.assertEqual(self.game.player_x, 1.0)

        # 极限右移
        for _ in range(40):
            self.game.update(0.1, KEY_RIGHT, 0)
        self.assertEqual(self.game.player_x, 14.0)

    def test_player_bullet_firing_and_single_shot_limit(self):
        """测试单发激光炮开火与同屏单发防抖限制"""
        self.assertFalse(self.game.player_bullet.active)
        # 移至掩体间隙净空区 x=5.0
        self.game.player_x = 5.0

        # 开火
        self.game.update(0.02, 0, KEY_A)
        self.assertTrue(self.game.player_bullet.active)
        self.assertEqual(self.game.player_bullet.x, self.game.player_x)
        self.assertLess(self.game.player_bullet.vy, 0)

        bullet_y = self.game.player_bullet.y
        # 再次按键，原子弹仍在飞，不能生成第二颗
        self.game.update(0.02, 0, KEY_B)
        self.assertLess(self.game.player_bullet.y, bullet_y)

    def test_bullet_kills_alien_and_accelerates_march(self):
        """测试击杀敌机后分值累加、总数递减与行军间隔压缩"""
        initial_interval = self.game.march_interval
        # 人工放置子弹在外星人 (r=2, c=0) 头部
        target_ax = self.game.fleet_x + 0 * 2
        target_ay = self.game.fleet_y + 2 * 2

        self.game.player_bullet.active = True
        self.game.player_bullet.x = float(target_ax)
        self.game.player_bullet.y = float(target_ay) + 0.3
        self.game.player_bullet.vy = -18.0

        self.game.update(0.02, 0, 0)

        self.assertFalse(self.game.fleet[2][0].alive)
        self.assertEqual(self.game.remaining_aliens, 11)
        self.assertEqual(self.game.score, 10) # Row 2 价值 10 分
        self.assertFalse(self.game.player_bullet.active) # 子弹命中消解
        self.assertLess(self.game.march_interval, initial_interval) # 行军节奏加快

    def test_bunker_blocks_and_takes_damage(self):
        """测试掩体阻挡子弹并逐步受损损毁"""
        # Bunker 0 位于 x=2..3, y=11..12
        self.assertEqual(self.game.bunkers[0][1][0].hp, 2) # y=12, x=2

        # 玩家向上开火打在掩体底部 (x=2, y=12.2)
        self.game.player_bullet.active = True
        self.game.player_bullet.x = 2.0
        self.game.player_bullet.y = 12.3
        self.game.player_bullet.vy = -10.0

        self.game.update(0.02, 0, 0)
        self.assertFalse(self.game.player_bullet.active)
        self.assertEqual(self.game.bunkers[0][1][0].hp, 1) # 耐久减1

        # 再次射击该位置
        self.game.player_bullet.active = True
        self.game.player_bullet.x = 2.0
        self.game.player_bullet.y = 12.3
        self.game.player_bullet.vy = -10.0
        self.game.update(0.02, 0, 0)
        self.assertEqual(self.game.bunkers[0][1][0].hp, 0) # 耐久耗尽彻底打穿

    def test_fleet_marching_and_wall_turn_drop(self):
        """测试外星编队触壁反弹并逐行下压"""
        self.game.fleet_x = 8
        self.game.fleet_y = 1
        self.game.fleet_dir = 1
        # max_c 是 3, fleet_x + 3*2 = 8 + 6 = 14
        # 下一步向右: next_edge = 8 + 6 + 1 = 15 < 16, 还能走一步
        self.game.march_timer = self.game.march_interval
        self.game.update(0.01, 0, 0)
        self.assertEqual(self.game.fleet_x, 9)
        self.assertEqual(self.game.fleet_dir, 1)
        self.assertEqual(self.game.fleet_y, 1)

        # 再走一步: next_edge = 9 + 6 + 1 = 16 >= 16，此时必须触壁下压并反向
        self.game.march_timer = self.game.march_interval
        self.game.update(0.01, 0, 0)
        self.assertEqual(self.game.fleet_y, 2) # 下压一行
        self.assertEqual(self.game.fleet_dir, -1) # 转向向左

    def test_alien_invasion_base_defeat(self):
        """测试侵略者触及底线防线直接导致游戏失败"""
        self.game.fleet_y = 8
        # max_r=2, fleet_y + 2*2 = 8 + 4 = 12
        # 下压一行到达 9: 9 + 4 = 13 >= 13, 触发 GameOver
        self.game.fleet_x = 9
        self.game.fleet_dir = 1
        self.game.march_timer = self.game.march_interval
        self.game.update(0.01, 0, 0) # 触壁下压
        self.assertEqual(self.game.fleet_y, 9)
        self.assertEqual(self.game.state, STATE_GAMEOVER)

    def test_alien_bomb_damages_player(self):
        """测试敌机炸弹命中玩家炮台削减生命"""
        self.assertEqual(self.game.lives, 3)

        # 生成一枚炸弹正对玩家头顶
        self.game.alien_bombs[0].active = True
        self.game.alien_bombs[0].x = self.game.player_x
        self.game.alien_bombs[0].y = 12.8
        self.game.alien_bombs[0].vy = 10.0

        self.game.update(0.03, 0, 0)
        self.assertEqual(self.game.lives, 2)
        self.assertFalse(self.game.alien_bombs[0].active)

    def test_victory_on_all_aliens_destroyed(self):
        """测试清剿全部侵略者取得最终胜利"""
        # 预设只剩最后 1 只
        self.game.remaining_aliens = 1
        for r in range(3):
            for c in range(4):
                self.game.fleet[r][c].alive = False
        self.game.fleet[0][0].alive = True

        # 子弹直击最后一只
        self.game.player_bullet.active = True
        self.game.player_bullet.x = float(self.game.fleet_x)
        self.game.player_bullet.y = float(self.game.fleet_y) + 0.3
        self.game.player_bullet.vy = -18.0

        self.game.update(0.02, 0, 0)
        self.assertEqual(self.game.remaining_aliens, 0)
        self.assertEqual(self.game.state, STATE_VICTORY)

    def test_render_buffer_dimensions(self):
        """测试渲染输出符合 16x16 RGB 规范 (768 字节)"""
        buf = self.game.render()
        self.assertEqual(len(buf), 16 * 16 * 3)

if __name__ == "__main__":
    unittest.main()
