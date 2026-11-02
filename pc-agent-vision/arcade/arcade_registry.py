# -*- coding: utf-8 -*-
"""
arcade_registry.py —— 街机游戏卡带中央注册中心与版本管理
维护所有已实现卡带的索引、状态、元数据，并支持实例化与动态加载
"""

from typing import Dict, List, Optional, Type, Any
from .base_cartridge import BaseCartridge
from .game_004_doodle_jump import Game004DoodleJump
from .game_005_flappy_bird import Game005FlappyBird
from .game_006_stack import Game006Stack
from .game_007_pong import Game007Pong
from .game_008_breakout import Game008Breakout
from .game_009_space_invaders import Game009SpaceInvaders
from .game_010_pacman import Game010Pacman
from .game_011_frogger import Game011Frogger
from .game_012_highway_racer import Game012HighwayRacer
from .game_013_bomberman import Game013Bomberman
from .game_014_sokoban import Game014Sokoban
from .game_015_tron import Game015Tron
from .game_016_neon_2048 import Game016Neon2048
from .game_017_piano_tiles import Game017PianoTiles
from .game_018_minesweeper import Game018Minesweeper
from .game_019_puzzle_bobble import Game019PuzzleBobble
from .game_020_artillery import Game020Artillery
from .game_021_dig_dug import Game021DigDug
from .game_022_galaga import Game022Galaga
from .game_023_donkey_kong import Game023DonkeyKong
from .game_024_lode_runner import Game024LodeRunner
from .game_025_bubble_bobble import Game025BubbleBobble
from .game_026_whack_a_mole import Game026WhackAMole
from .game_027_magic_tower import Game027MagicTower
from .game_028_danmaku import Game028Danmaku
from .game_029_slither_arena import Game029SlitherArena
from .game_030_submarine import Game030Submarine
from .game_031_rally_x import Game031RallyX
from .game_032_crossy_road import Game032CrossyRoad
from .game_033_clay_shooting import Game033ClayShooting
from .game_034_pipe_dream import Game034PipeDream
from .game_035_othello import Game035Othello
from .game_036_missile_command import Game036MissileCommand
from .game_037_sprint_racer import Game037SprintRacer
from .game_038_ice_climber import Game038IceClimber
from .game_039_legend_of_kage import Game039LegendOfKage
from .game_040_dodgeball import Game040Dodgeball
from .game_041_crush_roller import Game041CrushRoller
from .game_042_mario_bros import Game042MarioBros
from .game_043_centipede import Game043Centipede
from .game_044_excitebike import Game044Excitebike

class ArcadeRegistry:
    """街机游戏注册与元数据管理器"""
    _cartridges: Dict[int, Type[BaseCartridge]] = {}
    _catalog: List[Dict[str, Any]] = []

    @classmethod
    def register(cls, cartridge_cls: Type[BaseCartridge]):
        # 实例化探针获取元数据
        dummy = cartridge_cls()
        gid = dummy.game_id
        cls._cartridges[gid] = cartridge_cls
        entry = {
            "id": gid,
            "name": dummy.name,
            "english_name": dummy.english_name,
            "year": dummy.release_year,
            "control_type": dummy.control_type,
            "core_mechanic": dummy.core_mechanic,
            "status": "implemented",
        }
        # 保持有序
        cls._catalog = [item for item in cls._catalog if item["id"] != gid]
        cls._catalog.append(entry)
        cls._catalog.sort(key=lambda x: x["id"])

    @classmethod
    def get_cartridge(cls, game_id: int) -> Optional[BaseCartridge]:
        cart_cls = cls._cartridges.get(game_id)
        if cart_cls:
            return cart_cls()
        return None

    @classmethod
    def list_catalog(cls) -> List[Dict[str, Any]]:
        return list(cls._catalog)

# 注册现存已实现的独立街机游戏
ArcadeRegistry.register(Game004DoodleJump)
ArcadeRegistry.register(Game005FlappyBird)
ArcadeRegistry.register(Game006Stack)
ArcadeRegistry.register(Game007Pong)
ArcadeRegistry.register(Game008Breakout)
ArcadeRegistry.register(Game009SpaceInvaders)
ArcadeRegistry.register(Game010Pacman)
ArcadeRegistry.register(Game011Frogger)
ArcadeRegistry.register(Game012HighwayRacer)
ArcadeRegistry.register(Game013Bomberman)
ArcadeRegistry.register(Game014Sokoban)
ArcadeRegistry.register(Game015Tron)
ArcadeRegistry.register(Game016Neon2048)
ArcadeRegistry.register(Game017PianoTiles)
ArcadeRegistry.register(Game018Minesweeper)
ArcadeRegistry.register(Game019PuzzleBobble)
ArcadeRegistry.register(Game020Artillery)
ArcadeRegistry.register(Game021DigDug)
ArcadeRegistry.register(Game022Galaga)
ArcadeRegistry.register(Game023DonkeyKong)
ArcadeRegistry.register(Game024LodeRunner)
ArcadeRegistry.register(Game025BubbleBobble)
ArcadeRegistry.register(Game026WhackAMole)
ArcadeRegistry.register(Game027MagicTower)
ArcadeRegistry.register(Game028Danmaku)
ArcadeRegistry.register(Game029SlitherArena)
ArcadeRegistry.register(Game030Submarine)
ArcadeRegistry.register(Game031RallyX)
ArcadeRegistry.register(Game032CrossyRoad)
ArcadeRegistry.register(Game033ClayShooting)
ArcadeRegistry.register(Game034PipeDream)
ArcadeRegistry.register(Game035Othello)
ArcadeRegistry.register(Game036MissileCommand)
ArcadeRegistry.register(Game037SprintRacer)
ArcadeRegistry.register(Game038IceClimber)
ArcadeRegistry.register(Game039LegendOfKage)
ArcadeRegistry.register(Game040Dodgeball)
ArcadeRegistry.register(Game041CrushRoller)
ArcadeRegistry.register(Game042MarioBros)
ArcadeRegistry.register(Game043Centipede)
ArcadeRegistry.register(Game044Excitebike)
