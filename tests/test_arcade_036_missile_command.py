import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_036_missile_command import (
    Game036MissileCommand,
    STATE_START,
    STATE_PLAYING,
    STATE_WAVE_CLEAR,
    STATE_GAMEOVER,
    CITY_X,
    BASE_X,
)
from arcade.base_cartridge import (
    CTRL_ARCADE_AB,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_A,
    KEY_B,
)
from arcade.arcade_registry import ArcadeRegistry


class TestGame036MissileCommand(unittest.TestCase):
    def setUp(self):
        self.game = Game036MissileCommand()
        self.game.reset()

    def test_registry_metadata(self):
        """测试卡带注册与元数据正确性"""
        instance = ArcadeRegistry.get_cartridge(36)
        self.assertIsNotNone(instance)
        self.assertEqual(instance.name, "导弹防线")
        self.assertEqual(instance.english_name, "Missile Command 1980")
        self.assertEqual(instance.control_type, CTRL_ARCADE_AB)
        self.assertEqual(instance.release_year, 1980)

    def test_world_assets_and_wave_init(self):
        """测试初始地表防线、6座城市、3大基站与弹药配给"""
        self.assertEqual(self.game.get_surviving_cities(), 6)
        self.assertEqual(self.game.ammo, 15)
        self.assertEqual(self.game.wave, 1)
        self.assertEqual(self.game.state, STATE_PLAYING)

    def test_crosshair_four_way_aiming(self):
        """测试四向瞄准准星移动与边界"""
        self.game.crosshair_x = 7.5
        self.game.crosshair_y = 7.5

        # 向上移动
        self.game.update(0.1, KEY_UP, 0)
        self.assertLess(self.game.crosshair_y, 7.5)

        # 尝试越出天际线
        for _ in range(20):
            self.game.update(0.1, KEY_UP, 0)
        self.assertGreaterEqual(self.game.crosshair_y, 1.0)

    def test_fire_interceptor_from_nearest_silo(self):
        """测试从最近的发射井发射反导拦截火箭并消耗备弹"""
        self.assertEqual(self.game.ammo, 15)
        self.game.crosshair_x = 1.0 # 接近 Base 0 (x=0)
        self.game.crosshair_y = 5.0

        # 按键 A 发射
        self.game.update(0.05, KEY_A, 0)
        self.assertEqual(self.game.ammo, 14)
        self.assertEqual(len(self.game.interceptors), 1)

        ic = self.game.interceptors[0]
        self.assertLess(ic["x"], 1.0) # 从左侧基站 (x=0) 腾空发射向右上方
        self.assertLess(ic["y"], 15.0) # 高速升空
        self.assertLess(ic["vy"], 0.0)

    def test_interceptor_detonation_spawns_fireball(self):
        """测试拦截弹抵达目标点后凌空殉爆生成扩散火球"""
        self.game.crosshair_x = 7.0
        self.game.crosshair_y = 6.0
        self.game.fire_interceptor()
        self.assertEqual(len(self.game.interceptors), 1)

        # 步进时间直到抵达引爆
        for _ in range(15):
            self.game.update(0.05, 0, 0)

        self.assertEqual(len(self.game.explosions), 1)
        ex = self.game.explosions[0]
        self.assertTrue(ex["active"])
        self.assertGreater(ex["radius"], 0.0)

    def test_fireball_aoe_destroys_enemy_missiles(self):
        """测试火球爆风范围破片同时摧毁来袭敌弹"""
        # 手动生成一枚敌方弹道导弹
        self.game.enemy_missiles.append({
            "active": True,
            "x": 6.0,
            "y": 6.0,
            "target_x": 6.0,
            "target_y": 15.0,
            "vx": 0.0,
            "vy": 2.0,
        })

        # 在附近引爆火球
        self.game.explosions.append({
            "active": True,
            "x": 6.2,
            "y": 5.9,
            "radius": 1.5,
            "max_radius": 2.0,
            "timer": 0.5,
        })

        initial_score = self.game.score
        self.game.update(0.05, 0, 0)

        # 敌弹应被炸毁
        self.assertEqual(len(self.game.enemy_missiles), 0)
        self.assertEqual(self.game.score, initial_score + 100)

    def test_enemy_missile_destroys_city(self):
        """测试敌方导弹击中地表摧毁城市"""
        self.assertEqual(self.game.get_surviving_cities(), 6)

        # 敌弹命中城市 0 (CITY_X[0] = 2)
        self.game.enemy_missiles.append({
            "active": True,
            "x": 2.0,
            "y": 14.8,
            "target_x": 2.0,
            "target_y": 15.0,
            "vx": 0.0,
            "vy": 5.0,
        })

        self.game.update(0.05, 0, 0)
        self.assertFalse(self.game.cities_alive[0])
        self.assertEqual(self.game.get_surviving_cities(), 5)

    def test_all_cities_destroyed_triggers_gameover(self):
        """测试所有 6 座城市全部沦陷导致游戏结束"""
        for i in range(6):
            self.game.cities_alive[i] = False

        # 触发一次敌弹落地检查
        self.game.enemy_missiles.append({
            "active": True,
            "x": 7.0,
            "y": 14.9,
            "target_x": 7.0,
            "target_y": 15.0,
            "vx": 0.0,
            "vy": 5.0,
        })

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_GAMEOVER)

    def test_wave_clear_awards_city_and_ammo_bonus(self):
        """测试波次全歼后结算城市存活与剩余备弹奖励"""
        self.game.enemy_spawn_remaining = 0
        self.game.enemy_missiles.clear()
        self.game.ammo = 10

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.state, STATE_WAVE_CLEAR)
        # 6 城市 * 100 + 10 弹药 * 5 = 650
        self.assertEqual(self.game.score, 650)

    def test_render_framebuffer_integrity(self):
        """测试 16x16 帧缓冲区防线、基站与准星着色"""
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        # 检查发射基站着色 (底排中心 x=7, y=15 蓝色 [52, 152, 219])
        base_idx = (15 * 16 + 7) * 3
        self.assertEqual(fb[base_idx], 52)
        self.assertEqual(fb[base_idx + 1], 152)
        self.assertEqual(fb[base_idx + 2], 219)


if __name__ == "__main__":
    unittest.main()
