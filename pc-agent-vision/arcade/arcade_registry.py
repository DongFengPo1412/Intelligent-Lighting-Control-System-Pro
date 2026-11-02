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
