# -*- coding: utf-8 -*-
"""
arcade_runner.py —— 统一 16x16 街机卡带运行时中枢
确立 ESP32-S3 为正式硬件模式下的唯一权威来源 (Single Source of Truth)；
Python 模拟器仅在显式请求或离线仿真时运行，明确标记来源。
"""

import asyncio
import json
import time
from typing import Dict, Any, Optional
from arcade.base_cartridge import (
    BaseCartridge,
    CTRL_TAP_SINGLE,
    CTRL_TWO_BUTTON,
    CTRL_DPAD_4WAY,
    CTRL_ARCADE_AB,
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAMEOVER,
    STATE_VICTORY,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_UP,
    KEY_DOWN,
    KEY_A,
    KEY_B,
    KEY_START,
    KEY_SELECT,
)
from arcade.game_001_mario import Game001Mario
from arcade.game_009_flappy_bird import Game009FlappyBird
from arcade.game_010_stack import Game010Stack
from arcade.game_020_pong import Game020Pong
from arcade.game_021_breakout import Game021Breakout
from arcade.game_026_space_invaders import Game026SpaceInvaders
from arcade.game_033_snake import Game033Snake
from arcade.game_034_pacman import Game034Pacman
from arcade.game_038_bomberman import Game038Bomberman
from arcade.game_041_tetris import Game041Tetris
from arcade.game_054_sokoban import Game054Sokoban
from arcade.game_074_highway_racer import Game074HighwayRacer
from arcade.game_097_frogger import Game097Frogger

KEY_MAP = {
    "left": KEY_LEFT,
    "right": KEY_RIGHT,
    "up": KEY_UP,
    "down": KEY_DOWN,
    "a": KEY_A,
    "b": KEY_B,
    "start": KEY_START,
    "select": KEY_SELECT,
}

STATE_NAMES = {
    STATE_TITLE: "TITLE",
    STATE_PLAYING: "PLAYING",
    STATE_PAUSED: "PAUSED",
    STATE_GAMEOVER: "GAMEOVER",
    STATE_VICTORY: "VICTORY",
}


class ArcadeSession:
    """街机调度会话：硬件优先，ESP32 唯一权威"""

    def __init__(self, controller=None, broadcast_fn=None):
        self.controller = controller
        self.broadcast_fn = broadcast_fn
        self.cartridges: Dict[int, BaseCartridge] = {
            1: Game001Mario(),
            9: Game009FlappyBird(),
            10: Game010Stack(),
            20: Game020Pong(),
            21: Game021Breakout(),
            26: Game026SpaceInvaders(),
            33: Game033Snake(),
            34: Game034Pacman(),
            38: Game038Bomberman(),
            41: Game041Tetris(),
            54: Game054Sokoban(),
            74: Game074HighwayRacer(),
            97: Game097Frogger(),
        }
        self.current_cartridge: Optional[BaseCartridge] = None
        self.is_running = False
        self.task: Optional[asyncio.Task] = None
        self.keys_down = 0
        self.keys_pressed = 0
        self.current_hex = ""
        self.simulated_mode = False
        self.status = {
            "game_id": 0,
            "game_name": "None",
            "control_type": CTRL_ARCADE_AB,
            "score": 0,
            "high_score": 0,
            "lives": 1,
            "state": STATE_TITLE,
            "state_name": "TITLE",
            "progress": 0,
            "source": "uninitialized",
            "simulated": False,
        }

    def is_hardware_available(self) -> bool:
        if not self.controller:
            return False
        if getattr(self.controller, "port", None) == "SIMULATION":
            return False
        if hasattr(self.controller, "control_connected"):
            return bool(self.controller.control_connected)
        return True

    def select_game(self, game_id: int, force_simulation: bool = False) -> Dict[str, Any]:
        """选择卡带：向 ESP32 下发正式指令或在显式离线模拟时切换本地卡带"""
        valid_ids = [1, 9, 10, 20, 21, 26, 33, 34, 38, 41, 54, 74, 97]
        if game_id not in valid_ids:
            return {"status": "error", "error": "invalid_game_id", "message": f"不支持的街机编号: {game_id}"}

        # 切换游戏时，彻底清除旧游戏的长按与瞬按键状态
        self.keys_down = 0
        self.keys_pressed = 0

        # 如果显式指定了离线仿真，或者明确处于 SIMULATION 纯模拟环境
        is_sim_env = getattr(self.controller, "port", None) == "SIMULATION" or force_simulation

        if is_sim_env:
            # 显式模拟模式 (明确标记 simulated: True)
            self.simulated_mode = True
            self.current_cartridge = self.cartridges[game_id]
            self.current_cartridge.reset()
            self._refresh_simulator_status()
            self.is_running = True
            return {"status": "ok", "source": "simulator", "simulated": True, "game_status": self.status}

        # 硬件模式：检查硬件是否就绪，离线时坚决诚实报错，严禁冒充成功
        if not self.is_hardware_available():
            self.is_running = False
            return {
                "status": "error",
                "error": "device_offline",
                "message": "ESP32 硬件灯板未连接或网络离线，请先检查 Wi-Fi 连接",
                "simulated": False,
            }

        # 硬件在线，下发硬件指令
        self.simulated_mode = False
        res = self._send_esp32_command({"cmd": "arcade", "action": "select", "game_id": game_id})
        if res.get("status") == "ok":
            arc_data = res.get("arcade", {})
            self._update_status_from_hardware(arc_data, game_id)
            self.is_running = True
            return {"status": "ok", "source": "esp32_hardware", "simulated": False, "game_status": self.status}
        return {
            "status": "error",
            "error": res.get("error", "select_failed"),
            "message": "ESP32 街机选卡失败",
            "hardware_reply": res,
            "simulated": False,
        }

    def start(self, force_simulation: bool = False) -> Dict[str, Any]:
        if not self.simulated_mode:
            if not self.is_hardware_available():
                return {"status": "error", "error": "device_offline", "message": "ESP32 硬件灯板未连接或网络离线", "simulated": False}
            res = self._send_esp32_command({"cmd": "arcade", "action": "start"})
            if res.get("status") == "ok":
                self._update_status_from_hardware(res.get("arcade", {}))
                return {"status": "ok", "source": "esp32_hardware", "simulated": False, "game_status": self.status}
            return {"status": "error", "error": res.get("error", "send_failed"), "simulated": False}

        if self.current_cartridge:
            self.current_cartridge.start()
            self._refresh_simulator_status()
            return {"status": "ok", "source": "simulator", "simulated": True, "game_status": self.status}
        return {"status": "error", "error": "no_cartridge_selected"}

    def pause(self) -> Dict[str, Any]:
        if not self.simulated_mode:
            if not self.is_hardware_available():
                return {"status": "error", "error": "device_offline", "message": "ESP32 硬件灯板未连接或网络离线", "simulated": False}
            res = self._send_esp32_command({"cmd": "arcade", "action": "pause"})
            if res.get("status") == "ok":
                self._update_status_from_hardware(res.get("arcade", {}))
                return {"status": "ok", "source": "esp32_hardware", "simulated": False, "game_status": self.status}
            return {"status": "error", "error": res.get("error", "send_failed"), "simulated": False}

        if self.current_cartridge:
            self.current_cartridge.pause()
            self._refresh_simulator_status()
            return {"status": "ok", "source": "simulator", "simulated": True, "game_status": self.status}
        return {"status": "error", "error": "no_cartridge_selected"}

    def resume(self) -> Dict[str, Any]:
        if not self.simulated_mode:
            if not self.is_hardware_available():
                return {"status": "error", "error": "device_offline", "message": "ESP32 硬件灯板未连接或网络离线", "simulated": False}
            res = self._send_esp32_command({"cmd": "arcade", "action": "resume"})
            if res.get("status") == "ok":
                self._update_status_from_hardware(res.get("arcade", {}))
                return {"status": "ok", "source": "esp32_hardware", "simulated": False, "game_status": self.status}
            return {"status": "error", "error": res.get("error", "send_failed"), "simulated": False}

        if self.current_cartridge:
            self.current_cartridge.resume()
            self._refresh_simulator_status()
            return {"status": "ok", "source": "simulator", "simulated": True, "game_status": self.status}
        return {"status": "error", "error": "no_cartridge_selected"}

    def reset(self) -> Dict[str, Any]:
        self.keys_down = 0
        self.keys_pressed = 0
        if not self.simulated_mode:
            if not self.is_hardware_available():
                return {"status": "error", "error": "device_offline", "message": "ESP32 硬件灯板未连接或网络离线", "simulated": False}
            res = self._send_esp32_command({"cmd": "arcade", "action": "reset"})
            if res.get("status") == "ok":
                self._update_status_from_hardware(res.get("arcade", {}))
                return {"status": "ok", "source": "esp32_hardware", "simulated": False, "game_status": self.status}
            return {"status": "error", "error": res.get("error", "send_failed"), "simulated": False}

        if self.current_cartridge:
            self.current_cartridge.reset()
            self._refresh_simulator_status()
            return {"status": "ok", "source": "simulator", "simulated": True, "game_status": self.status}
        return {"status": "error", "error": "no_cartridge_selected"}

    def stop(self) -> Dict[str, Any]:
        self.is_running = False
        self.keys_down = 0
        self.keys_pressed = 0
        if self.task and not self.task.done():
            self.task.cancel()

        if not self.simulated_mode:
            if not self.is_hardware_available():
                return {"status": "error", "error": "device_offline", "message": "ESP32 硬件灯板未连接或网络离线", "simulated": False}
            res = self._send_esp32_command({"cmd": "arcade", "action": "exit"})
            self.status["state"] = STATE_TITLE
            self.status["state_name"] = "TITLE"
            return {"status": "ok", "source": "esp32_hardware", "simulated": False}

        if self.current_cartridge:
            self.current_cartridge.pause()
        self.status["state"] = STATE_TITLE
        self.status["state_name"] = "TITLE"
        return {"status": "ok", "source": "simulator", "simulated": True}

    def key(self, key_name: str, is_down: bool) -> Dict[str, Any]:
        mask = KEY_MAP.get(key_name.lower(), 0)
        if not mask:
            return {"status": "error", "error": "invalid_key", "key": key_name}

        if is_down:
            if not (self.keys_down & mask):
                self.keys_pressed |= mask
            self.keys_down |= mask
        else:
            self.keys_down &= ~mask

        if not self.simulated_mode:
            if not self.is_hardware_available():
                return {"status": "error", "error": "device_offline", "message": "ESP32 硬件灯板未连接或网络离线", "simulated": False}
            cmd = {
                "cmd": "arcade",
                "action": "input",
                "down": self.keys_down,
                "pressed": self.keys_pressed,
            }
            # 瞬按标记下发后清零
            self.keys_pressed = 0
            res = self._send_esp32_command(cmd)
            if res.get("status") == "ok":
                self._update_status_from_hardware(res.get("arcade", {}))
                return {"status": "ok", "source": "esp32_hardware", "simulated": False, "game_status": self.status}
            return {"status": "error", "error": res.get("error", "send_failed"), "simulated": False}

        # 模拟模式按键
        if self.current_cartridge:
            self.current_cartridge.update(0.016, self.keys_down, self.keys_pressed)
            self.keys_pressed = 0
            self._refresh_simulator_status()
            return {"status": "ok", "source": "simulator", "simulated": True, "game_status": self.status}
        return {"status": "error", "error": "no_cartridge_selected"}

    def heartbeat(self) -> Dict[str, Any]:
        """心跳保活与状态回传"""
        if not self.simulated_mode:
            if not self.is_hardware_available():
                return {"status": "error", "error": "device_offline", "message": "ESP32 硬件灯板未连接或网络离线", "simulated": False}
            res = self._send_esp32_command({"cmd": "arcade", "action": "heartbeat"})
            if res.get("status") == "ok":
                self._update_status_from_hardware(res.get("arcade", {}))
                return {"status": "ok", "source": "esp32_hardware", "simulated": False, "game_status": self.status}
            return {"status": "error", "error": res.get("error", "device_offline"), "simulated": False}

        # 模拟模式心跳
        return {"status": "ok", "source": "simulator", "simulated": True, "game_status": self.status}

    def get_frame(self) -> Dict[str, Any]:
        """获取当前帧缓冲与 HUD 状态"""
        if not self.simulated_mode:
            if not self.is_hardware_available():
                return {
                    "running": False,
                    "status": self.status,
                    "hex": "",
                    "source": "hardware_offline",
                    "frame_id": 0,
                    "simulated": False,
                    "error": "device_offline",
                }
            # 从真实硬件快照帧缓冲 (hardware_pwm)
            res = self._send_esp32_command({"cmd": "frame"})
            if res.get("status") == "ok" and "pixels" in res:
                self.current_hex = res.get("pixels", "")
                return {
                    "running": self.is_running,
                    "status": self.status,
                    "hex": self.current_hex,
                    "source": "hardware_pwm",
                    "frame_id": res.get("frame_id", 0),
                    "simulated": False,
                }

        # 离线模拟器渲染
        if self.current_cartridge:
            fb = self.current_cartridge.render()
            self.current_hex = fb.hex()
            self._refresh_simulator_status()
            return {
                "running": self.is_running,
                "status": self.status,
                "hex": self.current_hex,
                "source": "simulator",
                "simulated": True,
            }

        return {
            "running": False,
            "status": self.status,
            "hex": "",
            "source": "none",
            "frame_id": 0,
            "simulated": False,
        }

    def _send_esp32_command(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.controller:
            return {"status": "error", "error": "no_controller"}
        try:
            if hasattr(self.controller, "command_result"):
                return self.controller.command_result(payload)
            elif hasattr(self.controller, "send_json"):
                ok = self.controller.send_json(payload)
                return {"status": "ok" if ok else "error"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
        return {"status": "error", "error": "unsupported_transport"}

    def _update_status_from_hardware(self, arc_data: Dict[str, Any], default_gid: int = 0) -> None:
        if not arc_data:
            return
        gid = arc_data.get("game_id", default_gid or self.status["game_id"])
        st_code = arc_data.get("state", STATE_TITLE)
        self.status = {
            "game_id": gid,
            "game_name": arc_data.get("name", self._game_name_for_id(gid)),
            "control_type": arc_data.get("control_type", CTRL_ARCADE_AB),
            "score": arc_data.get("score", 0),
            "high_score": arc_data.get("high_score", 0),
            "lives": arc_data.get("lives", 1),
            "state": st_code,
            "state_name": STATE_NAMES.get(st_code, "UNKNOWN"),
            "progress": arc_data.get("progress", 0),
            "source": "esp32_hardware",
            "simulated": False,
        }

    def _refresh_simulator_status(self) -> None:
        if not self.current_cartridge:
            return
        st = self.current_cartridge.get_status()
        gid = self.current_cartridge.game_id
        st_code = st.get("state", STATE_TITLE)
        self.status = {
            "game_id": gid,
            "game_name": self.current_cartridge.name,
            "control_type": self.current_cartridge.control_type,
            "score": st.get("score", 0),
            "high_score": st.get("high_score", 0),
            "lives": st.get("lives", 1),
            "state": st_code,
            "state_name": STATE_NAMES.get(st_code, "UNKNOWN"),
            "progress": st.get("progress", 0),
            "source": "simulator",
            "simulated": True,
        }

    def _game_name_for_id(self, gid: int) -> str:
        names = {1: "超级马里奥", 33: "经典贪吃蛇", 41: "俄罗斯方块"}
        return names.get(gid, f"游戏 #{gid:03d}")

    async def run_loop(self):
        """仅在显式模拟模式下驱动 Python 卡带"""
        self.is_running = True
        last_time = time.monotonic()
        while self.is_running:
            if not self.simulated_mode:
                # 硬件模式下不运行 Python 物理模拟循环，避免产生两套独立游戏状态！
                await asyncio.sleep(0.1)
                continue

            now = time.monotonic()
            dt = now - last_time
            last_time = now

            if self.current_cartridge:
                self.current_cartridge.update(dt, self.keys_down, self.keys_pressed)
                self.keys_pressed = 0
                fb = self.current_cartridge.render()
                self.current_hex = fb.hex()
                self._refresh_simulator_status()

                if self.broadcast_fn:
                    try:
                        self.broadcast_fn({
                            "type": "arcade_frame",
                            "hex": self.current_hex,
                            "status": self.status,
                            "simulated": True,
                        })
                    except Exception:
                        pass
            await asyncio.sleep(0.033)


_session: Optional[ArcadeSession] = None


def get_arcade_session(controller=None, broadcast_fn=None) -> ArcadeSession:
    global _session
    if _session is None:
        _session = ArcadeSession(controller, broadcast_fn)
    elif controller and _session.controller != controller:
        _session.controller = controller
    return _session
