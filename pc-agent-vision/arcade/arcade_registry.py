# -*- coding: utf-8 -*-
"""
arcade_registry.py —— 街机游戏卡带中央注册中心与版本管理
维护所有已实现卡带的索引、状态、元数据，并支持实例化与动态加载
"""

from typing import Dict, List, Optional, Type, Any
from .base_cartridge import BaseCartridge
from .game_004_doodle_jump import Game004DoodleJump

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
