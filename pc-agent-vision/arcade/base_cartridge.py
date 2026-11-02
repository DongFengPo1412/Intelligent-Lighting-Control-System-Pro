# -*- coding: utf-8 -*-
"""
base_cartridge.py —— 街机游戏卡带 Python 抽象基类
与 ESP32-S3 C++ arcade::Cartridge 规范 1:1 对齐
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple

# 按键掩码 (KeyBits)
KEY_LEFT   = 1 << 0
KEY_RIGHT  = 1 << 1
KEY_UP     = 1 << 2
KEY_DOWN   = 1 << 3
KEY_A      = 1 << 4   # 动作 A (跳跃 / 射击)
KEY_B      = 1 << 5   # 动作 B (冲刺 / 炸弹)
KEY_START  = 1 << 6   # 开始 / 暂停
KEY_SELECT = 1 << 7   # 退出 / 菜单

# 虚拟手柄类型 (通知前端呈现对应 UI)
CTRL_TAP_SINGLE   = 0  # 全屏单键轻点 (如: 飞翔小鸟, 堆叠大师)
CTRL_TWO_BUTTON   = 1  # 左右双键 (如: 涂鸦跳跃, 赛车避障)
CTRL_DPAD_4WAY    = 2  # 四向十字键 (如: 贪吃蛇, 推箱子)
CTRL_ARCADE_AB    = 3  # 十字键 + A/B 键 (如: 超级马里奥, 太空射击)
CTRL_MULTI_TRACK  = 4  # 四轨律动键 (如: 别踩白块儿)
CTRL_VERSUS_DUAL  = 5  # 双人同屏对战 (如: 乒乓对决)

# 状态枚举
STATE_TITLE    = 0
STATE_PLAYING  = 1
STATE_PAUSED   = 2
STATE_GAMEOVER = 3
STATE_VICTORY  = 4

class BaseCartridge(ABC):
    """所有街机卡带必须继承的标准基类"""

    @property
    @abstractmethod
    def game_id(self) -> int:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def english_name(self) -> str:
        pass

    @property
    @abstractmethod
    def release_year(self) -> int:
        pass

    @property
    @abstractmethod
    def control_type(self) -> int:
        pass

    @property
    @abstractmethod
    def core_mechanic(self) -> str:
        """核心独占玩法力学动词描述"""
        pass

    @abstractmethod
    def init(self) -> None:
        pass

    @abstractmethod
    def reset(self) -> None:
        pass

    @abstractmethod
    def update(self, dt: float, keys_down: int, keys_pressed: int) -> None:
        pass

    @abstractmethod
    def render(self) -> bytearray:
        """返回 16x16x3 = 768 字节的 RGB888 字节流"""
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """返回包含 score, lives, state, progress 等字段的状态字典"""
        pass
