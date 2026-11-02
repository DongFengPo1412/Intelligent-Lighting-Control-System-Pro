import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision")))

from arcade.game_041_crush_roller import (
    Game041CrushRoller,
    STATE_START,
    STATE_PLAYING,
    STATE_DEAD,
    STATE_VICTORY,
)
from arcade.base_cartridge import (
    CTRL_DPAD_4WAY,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
)
from arcade.arcade_registry import ArcadeRegistry


class TestGame041CrushRoller(unittest.TestCase):
    def setUp(self):
        self.game = Game041CrushRoller()
        self.game.reset()

    def test_registry_metadata(self):
        """测试卡带注册与元数据正确性"""
        instance = ArcadeRegistry.get_cartridge(41)
        self.assertIsNotNone(instance)
        self.assertEqual(instance.name, "涂鸦滚刷")
        self.assertEqual(instance.english_name, "Crush Roller 1981")
        self.assertEqual(instance.control_type, CTRL_DPAD_4WAY)
        self.assertEqual(instance.release_year, 1981)

    def test_maze_initialization_and_paintable_tiles(self):
        """测试街道迷宫、障碍建筑与待涂覆瓦片统计"""
        # 验证起点 (1, 1) 已被涂覆为 2
        self.assertEqual(self.game.maze[1][1], 2)
        # 验证邻近街道 (2, 1) 为未涂覆路面 1
        self.assertEqual(self.game.maze[1][2], 1)
        # 验证建筑阻挡区 (2, 2) 为实体墙体 0
        self.assertEqual(self.game.maze[2][2], 0)

        self.assertGreater(self.game.unpainted_tiles, 0)
        self.assertEqual(self.game.total_paint_tiles, self.game.unpainted_tiles + 1)

    def test_paintbrush_movement_and_wall_blocking(self):
        """测试油漆刷四向转向与建筑墙体阻挡"""
        self.game.player_x = 1.0
        self.game.player_y = 1.0
        self.game.player_dir = 1 # 向右

        # 向右移动
        self.game.update(0.1, KEY_RIGHT, 0)
        self.assertGreater(self.game.player_x, 1.0)

        # 尝试向下撞入建筑实心墙 (2, 2)
        self.game.update(0.1, KEY_DOWN, 0)
        self.assertEqual(self.game.player_y, 1.0) # 受到墙体阻隔无法向下拐入

    def test_surface_painting_coverage_mechanics(self):
        """测试滚刷走过未上漆街道即刻涂抹金漆并增加分数"""
        self.game.player_x = 1.0
        self.game.player_y = 1.0
        self.game.player_dir = 1 # 向右移动
        initial_unpainted = self.game.unpainted_tiles

        # 推进至 (2, 1)
        for _ in range(6):
            self.game.update(0.05, KEY_RIGHT, 0)

        self.assertEqual(self.game.maze[1][2], 2) # (2, 1) 成功着色
        self.assertEqual(self.game.unpainted_tiles, initial_unpainted - 1)
        self.assertGreater(self.game.score, 0)

    def test_steamroller_activation_by_player(self):
        """测试玩家触发重型压路机机关启动向前冲撞"""
        roller = self.game.rollers[0]
        self.assertEqual(roller["dir"], 0) # 初始静止

        # 玩家走向压路机槽位 (5.0, 5.0)
        self.game.player_x = 5.0
        self.game.player_y = 5.0
        self.game.player_dir = 1 # 向右启动

        self.game.update(0.05, 0, 0)
        # 压路机被激活向前疾驰
        self.assertNotEqual(roller["dir"], 0)

    def test_steamroller_crushes_chasing_monsters(self):
        """测试压路机直接碾碎追击怪物并给予 400 分大奖"""
        roller = self.game.rollers[0]
        roller["x"] = 5.0
        roller["y"] = 5.0
        roller["dir"] = 2 # 向右冲刺 (dir_idx = 1)
        roller["active"] = True

        monster = self.game.monsters[0]
        monster["x"] = 5.5
        monster["y"] = 5.0
        monster["active"] = True

        initial_score = self.game.score
        self.game.update(0.05, 0, 0)

        # 怪物被碾碎
        self.assertFalse(monster["active"])
        self.assertGreater(monster["respawn_timer"], 0.0)
        self.assertEqual(self.game.score, initial_score + 400)

    def test_monster_touches_player_death(self):
        """测试无压路机掩护下怪物触碰玩家导致扣命"""
        self.assertEqual(self.game.lives, 3)
        # 移至远离压路机槽位的普通街道 (1.0, 5.0)
        self.game.player_x = 1.0
        self.game.player_y = 5.0
        self.game.monsters[0]["x"] = 1.2
        self.game.monsters[0]["y"] = 5.0
        self.game.monsters[0]["active"] = True

        self.game.update(0.05, 0, 0)
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.state, STATE_DEAD)

    def test_all_tiles_painted_triggers_victory(self):
        """测试 100% 地面涂覆完成触发通关胜利"""
        # 将未涂瓦片设为 1
        self.game.unpainted_tiles = 1
        # 涂抹最后一格
        self.game.maze[5][5] = 1
        self.game.paint_tile(5, 5)

        self.assertEqual(self.game.unpainted_tiles, 0)
        self.assertEqual(self.game.state, STATE_VICTORY)
        self.assertGreater(self.game.score, 1000)

    def test_render_framebuffer_integrity(self):
        """测试 16x16 帧缓冲区建筑深蓝、沥青灰、金黄已涂表面着色"""
        # 移开玩家画刷以露出起点金漆地面
        self.game.player_x = 2.0
        self.game.player_y = 1.0
        fb = self.game.render()
        self.assertEqual(len(fb), 16 * 16 * 3)

        # 检查内部实心建筑砖墙 (x=2, y=2 深蓝 [30, 55, 153])
        wall_idx = (2 * 16 + 2) * 3
        self.assertEqual(fb[wall_idx], 30)
        self.assertEqual(fb[wall_idx + 1], 55)
        self.assertEqual(fb[wall_idx + 2], 153)

        # 检查起点涂抹金漆 (x=1, y=1 金黄 [241, 196, 15])
        start_idx = (1 * 16 + 1) * 3
        self.assertEqual(fb[start_idx], 241)
        self.assertEqual(fb[start_idx + 1], 196)
        self.assertEqual(fb[start_idx + 2], 15)


if __name__ == "__main__":
    unittest.main()
