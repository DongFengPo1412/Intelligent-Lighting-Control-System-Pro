# -*- coding: utf-8 -*-
"""
arcade_runner.py —— 统一 16x16 街机卡带运行时中枢
确立 ESP32-S3 为正式硬件模式下的唯一权威来源 (Single Source of Truth)；
Python 模拟器仅在显式请求或离线仿真时运行，明确标记来源。
"""

import asyncio
import json
import time
import threading
import inspect
from functools import wraps
from arcade.fixed_step import FixedStepClock
from collections import deque
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
from arcade.game_002_doodle_jump import Game002DoodleJump
from arcade.game_003_celeste_dash import Game003CelesteDash
from arcade.game_004_gravity_flip import Game004GravityFlip
from arcade.game_005_lode_runner import Game005LodeRunner
from arcade.game_006_bubble_bobble import Game006BubbleBobble
from arcade.game_009_flappy_bird import Game009FlappyBird
from arcade.game_010_stack import Game010Stack
from arcade.game_014_orbit_hop import Game014OrbitHop
from arcade.game_015_simon_memory import Game015SimonMemory
from arcade.game_016_whack_a_mole import Game016WhackAMole
from arcade.game_017_rhythm_lanes import Game017RhythmLanes
from arcade.game_018_red_green_light import Game018RedGreenLight
from arcade.game_019_shell_game import Game019ShellGame
from arcade.game_020_pong import Game020Pong
from arcade.game_021_breakout import Game021Breakout
from arcade.game_022_pinball import Game022Pinball
from arcade.game_026_space_invaders import Game026SpaceInvaders
from arcade.game_027_asteroids import Game027Asteroids
from arcade.game_028_missile_command import Game028MissileCommand
from arcade.game_029_centipede import Game029Centipede
from arcade.game_030_duck_hunt import Game030DuckHunt
from arcade.game_031_robotron import Game031Robotron
from arcade.game_033_snake import Game033Snake
from arcade.game_034_pacman import Game034Pacman
from arcade.game_038_bomberman import Game038Bomberman
from arcade.game_040_mirror_maze import Game040MirrorMaze
from arcade.game_041_tetris import Game041Tetris
from arcade.game_042_puyo_puyo import Game042PuyoPuyo
from arcade.game_043_merge_2048 import Game043Merge2048
from arcade.game_044_bejeweled import Game044Bejeweled
from arcade.game_045_samegame import Game045SameGame
from arcade.game_051_flow_free import Game051FlowFree
from arcade.game_052_pipe_connect import Game052PipeConnect
from arcade.game_053_tower_of_hanoi import Game053TowerOfHanoi
from arcade.game_054_sokoban import Game054Sokoban
from arcade.game_055_mirror_laser import Game055MirrorLaser
from arcade.game_062_reversi import Game062Reversi
from arcade.game_063_gomoku import Game063Gomoku
from arcade.game_064_checkers import Game064Checkers
from arcade.game_065_dots_and_boxes import Game065DotsAndBoxes
from arcade.game_066_battleship import Game066Battleship
from arcade.game_067_quoridor import Game067Quoridor
from arcade.game_072_hex_board import Game072HexBoard
from arcade.game_073_ludo_race import Game073LudoRace
from arcade.game_074_highway_racer import Game074HighwayRacer
from arcade.game_075_slalom_ski import Game075SlalomSki
from arcade.game_076_mini_golf import Game076MiniGolf
from arcade.game_083_tower_defense import Game083TowerDefense
from arcade.game_084_node_conquest import Game084NodeConquest
from arcade.game_085_lemmings_rescue import Game085LemmingsRescue
from arcade.game_086_tiny_farm import Game086TinyFarm
from arcade.game_087_traffic_control import Game087TrafficControl
from arcade.game_088_atc_landing import Game088AtcLanding
from arcade.game_092_fruit_slice import Game092FruitSlice
from arcade.game_093_black_hole import Game093BlackHole
from arcade.game_094_grapple_swing import Game094GrappleSwing
from arcade.game_095_super_hexagon import Game095SuperHexagon
from arcade.game_097_frogger import Game097Frogger

from arcade.game_035_boulder_dash import Game035BoulderDash
from arcade.game_057_rush_hour import Game057RushHour
from arcade.game_058_program_robot import Game058ProgramRobot
from arcade.game_081_qix import Game081Qix
from arcade.game_098_lunar_lander import Game098LunarLander

from arcade.game_007_downwell import Game007Downwell

from arcade.game_008_jump_king import Game008JumpKing

from arcade.game_011_dino_runner import Game011DinoRunner

from arcade.game_012_knife_hit import Game012KnifeHit

from arcade.game_013_pendulum_toss import Game013PendulumToss

from arcade.game_023_air_hockey import Game023AirHockey

from arcade.game_024_peggle import Game024Peggle

from arcade.game_025_marble_maze import Game025MarbleMaze

from arcade.game_032_defender import Game032Defender

from arcade.game_036_dig_dug import Game036DigDug

from arcade.game_037_qbert import Game037Qbert

from arcade.game_039_fog_maze import Game039FogMaze

from arcade.game_046_suika import Game046Suika

from arcade.game_047_blockudoku import Game047Blockudoku

from arcade.game_048_triple_town import Game048TripleTown

from arcade.game_049_lights_out import Game049LightsOut

from arcade.game_050_mini_sudoku import Game050MiniSudoku

from arcade.game_056_sliding_puzzle import Game056SlidingPuzzle

from arcade.game_059_cut_rope import Game059CutRope

from arcade.game_060_portal_puzzle import Game060PortalPuzzle

from arcade.game_061_connect_four import Game061ConnectFour

from arcade.game_068_mastermind import Game068Mastermind

from arcade.game_069_nim import Game069Nim

from arcade.game_070_flood_it import Game070FloodIt

from arcade.game_071_peg_solitaire import Game071PegSolitaire

from arcade.game_077_bowling import Game077Bowling

from arcade.game_078_baseball import Game078Baseball

from arcade.game_079_penalty import Game079Penalty

from arcade.game_080_tron import Game080Tron

from arcade.game_082_artillery import Game082Artillery

from arcade.game_089_firefighter import Game089Firefighter

from arcade.game_090_conveyor import Game090Conveyor

from arcade.game_091_wire_maze import Game091WireMaze

from arcade.game_096_ice_maze import Game096IceMaze

from arcade.game_099_auto_survivor import Game099AutoSurvivor

from arcade.game_100_memory_match import Game100MemoryMatch

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


def synchronized(method):
    @wraps(method)
    def call(self,*args,**kwargs):
        with self._lock:
            return method(self,*args,**kwargs)
    return call


class ArcadeSession:
    """街机调度会话：硬件优先，ESP32 唯一权威"""

    def __init__(self, controller=None, broadcast_fn=None):
        self._lock = threading.RLock()
        self._clock=FixedStepClock()
        self.sound_enabled=True;self.sound_volume=25
        self.sound_events=deque(maxlen=16)
        self.controller = controller
        self.broadcast_fn = broadcast_fn
        self.cartridges: Dict[int, BaseCartridge] = {
            1: Game001Mario(),
            2: Game002DoodleJump(),
            3: Game003CelesteDash(),
            4: Game004GravityFlip(),
            5: Game005LodeRunner(),
            6: Game006BubbleBobble(),
            9: Game009FlappyBird(),
            10: Game010Stack(),
            14: Game014OrbitHop(),
            15: Game015SimonMemory(),
            16: Game016WhackAMole(),
            17: Game017RhythmLanes(),
            18: Game018RedGreenLight(),
            19: Game019ShellGame(),
            20: Game020Pong(),
            21: Game021Breakout(),
            22: Game022Pinball(),
            26: Game026SpaceInvaders(),
            27: Game027Asteroids(),
            28: Game028MissileCommand(),
            29: Game029Centipede(),
            30: Game030DuckHunt(),
            31: Game031Robotron(),
            33: Game033Snake(),
            34: Game034Pacman(),
            38: Game038Bomberman(),
            40: Game040MirrorMaze(),
            41: Game041Tetris(),
            42: Game042PuyoPuyo(),
            43: Game043Merge2048(),
            44: Game044Bejeweled(),
            45: Game045SameGame(),
            51: Game051FlowFree(),
            52: Game052PipeConnect(),
            53: Game053TowerOfHanoi(),
            54: Game054Sokoban(),
            55: Game055MirrorLaser(),
            62: Game062Reversi(),
            63: Game063Gomoku(),
            64: Game064Checkers(),
            65: Game065DotsAndBoxes(),
            66: Game066Battleship(),
            67: Game067Quoridor(),
            72: Game072HexBoard(),
            73: Game073LudoRace(),
            74: Game074HighwayRacer(),
            75: Game075SlalomSki(),
            76: Game076MiniGolf(),
            83: Game083TowerDefense(),
            84: Game084NodeConquest(),
            85: Game085LemmingsRescue(),
            86: Game086TinyFarm(),
            87: Game087TrafficControl(),
            88: Game088AtcLanding(),
            92: Game092FruitSlice(),
            93: Game093BlackHole(),
            94: Game094GrappleSwing(),
            95: Game095SuperHexagon(),
            97: Game097Frogger(),
        }
        self.cartridges[35]=Game035BoulderDash()
        self.cartridges[57]=Game057RushHour()
        self.cartridges[58]=Game058ProgramRobot()
        self.cartridges[81]=Game081Qix()
        self.cartridges[98]=Game098LunarLander()
        self.cartridges[7]=Game007Downwell()
        self.cartridges[8]=Game008JumpKing()
        self.cartridges[11]=Game011DinoRunner()
        self.cartridges[12]=Game012KnifeHit()
        self.cartridges[13]=Game013PendulumToss()
        self.cartridges[23]=Game023AirHockey()
        self.cartridges[24]=Game024Peggle()
        self.cartridges[25]=Game025MarbleMaze()
        self.cartridges[32]=Game032Defender()
        self.cartridges[36]=Game036DigDug()
        self.cartridges[37]=Game037Qbert()
        self.cartridges[39]=Game039FogMaze()
        self.cartridges[46]=Game046Suika()
        self.cartridges[47]=Game047Blockudoku()
        self.cartridges[48]=Game048TripleTown()
        self.cartridges[49]=Game049LightsOut()
        self.cartridges[50]=Game050MiniSudoku()
        self.cartridges[56]=Game056SlidingPuzzle()
        self.cartridges[59]=Game059CutRope()
        self.cartridges[60]=Game060PortalPuzzle()
        self.cartridges[61]=Game061ConnectFour()
        self.cartridges[68]=Game068Mastermind()
        self.cartridges[69]=Game069Nim()
        self.cartridges[70]=Game070FloodIt()
        self.cartridges[71]=Game071PegSolitaire()
        self.cartridges[77]=Game077Bowling()
        self.cartridges[78]=Game078Baseball()
        self.cartridges[79]=Game079Penalty()
        self.cartridges[80]=Game080Tron()
        self.cartridges[82]=Game082Artillery()
        self.cartridges[89]=Game089Firefighter()
        self.cartridges[90]=Game090Conveyor()
        self.cartridges[91]=Game091WireMaze()
        self.cartridges[96]=Game096IceMaze()
        self.cartridges[99]=Game099AutoSurvivor()
        self.cartridges[100]=Game100MemoryMatch()
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

    @synchronized
    def legacy_control(self,game_id,action,key=None,down=True):
        """Compatibility routes share the formal cartridge; never launch another engine."""
        if game_id not in (1,33,41):return {'status':'error','error':'invalid_game_id'}
        if action=='start':
            selected=self.select_game(game_id)
            if selected.get('status')!='ok':return selected
            return self.start()
        # Input must never silently select or restart a different cartridge.
        status=self.read_status()
        if status.get('status')!='ok':return status
        if status.get('game_status',{}).get('game_id')!=game_id:
            return {'status':'error','error':'cartridge_not_selected'}
        if action=='pulse':
            if key not in KEY_MAP:return {'status':'error','error':'invalid_key'}
            return self.input_state(self.keys_down,KEY_MAP[key])
        if action=='key':
            if not isinstance(key,str) or key not in KEY_MAP or type(down) is not bool:
                return {'status':'error','error':'invalid_key'}
            return self.key(key,down)
        methods={'stop':self.stop,'exit':self.stop,'pause':self.pause,'resume':self.resume,'reset':self.reset,'status':self.read_status}
        return methods[action]() if action in methods else {'status':'error','error':'unknown_action'}

    @synchronized
    def select_game(self, game_id: int, force_simulation: bool = False) -> Dict[str, Any]:
        """选择卡带：向 ESP32 下发正式指令或在显式离线模拟时切换本地卡带"""
        valid_ids = self.cartridges
        if type(game_id) is not int or game_id not in valid_ids:
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
            self._clock.reset()
            self.current_cartridge._sound_sink=lambda kind,detail:self.sound_events.append((kind,detail)) if self.sound_enabled and self.sound_volume else None
            self.current_cartridge.init()
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

    @synchronized
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

    @synchronized
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

    @synchronized
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

    @synchronized
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

    @synchronized
    def stop(self) -> Dict[str, Any]:
        self.is_running = False
        self.keys_down = 0
        self.keys_pressed = 0
        if self.task and not self.task.done():
            self.task.get_loop().call_soon_threadsafe(self.task.cancel)

        if not self.simulated_mode:
            if not self.is_hardware_available():
                return {"status": "error", "error": "device_offline", "message": "ESP32 硬件灯板未连接或网络离线", "simulated": False}
            res = self._send_esp32_command({"cmd": "arcade", "action": "exit"})
            if res.get("status") != "ok":
                return {"status":"error","error":res.get("error","stop_failed"),"simulated":False}
            self._update_status_from_hardware(res.get("arcade", {}))
            return {"status":"ok","source":"esp32_hardware","simulated":False,"game_status":self.status}

        if self.current_cartridge:
            self.current_cartridge.pause()
        self.status["state"] = STATE_TITLE
        self.status["state_name"] = "TITLE"
        return {"status": "ok", "source": "simulator", "simulated": True}

    @synchronized
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

    @synchronized
    def input_state(self, down, pressed):
        if any(type(v) is not int or not 0 <= v <= 255 for v in (down,pressed)):
            return {"status":"error","error":"invalid_input"}
        self.keys_down, self.keys_pressed = down, pressed
        if self.simulated_mode:
            if not self.current_cartridge:
                return {"status":"error","error":"no_cartridge_selected"}
            self.current_cartridge.update(0.,down,pressed)
            self.keys_pressed=0
            self._refresh_simulator_status()
            return {"status":"ok","source":"simulator","simulated":True,"game_status":self.status}
        if not self.is_hardware_available():
            self.keys_down=self.keys_pressed=0
            return {"status":"error","error":"device_offline","simulated":False}
        reply=self._send_esp32_command({"cmd":"arcade","action":"input","down":down,"pressed":pressed})
        self.keys_pressed=0
        if reply.get("status") != "ok":
            self.keys_down=0
            return {"status":"error","error":reply.get("error","input_failed"),"simulated":False}
        self._update_status_from_hardware(reply["arcade"])
        return {"status":"ok","source":"esp32_hardware","simulated":False,"game_status":self.status}

    def read_status(self):
        with self._lock:
            if self.simulated_mode:
                self._refresh_simulator_status()
                return {"status":"ok","game_status":dict(self.status),"source":"simulator","simulated":True}
            previous=self.status
        reply=self._send_esp32_command({"cmd":"arcade","action":"status"})
        with self._lock:
            if self.simulated_mode or self.status is not previous:
                return {"status":"error","error":"stale_reply","simulated":False}
            if reply.get("status") != "ok":
                return {"status":"error","error":reply.get("error","device_offline"),"simulated":False}
            self._update_status_from_hardware(reply['arcade'])
            return {"status":"ok","game_status":dict(self.status),"source":"esp32_hardware","simulated":False}

    @synchronized
    def configure(self,enabled,volume,difficulty=None):
        if type(enabled) is not bool or type(volume) is not int or not 0<=volume<=100 or (difficulty is not None and (type(difficulty) is not int or difficulty not in (0,1,2))):
            return {"status":"error","error":"invalid_arcade_config"}
        if not self.simulated_mode:
            command={"cmd":"arcade","action":"config","sound_enabled":enabled,"sound_volume":volume}
            if difficulty is not None:command['difficulty']=difficulty
            reply=self._send_esp32_command(command)
            if reply.get('status')!='ok':return {"status":"error","error":reply.get('error','config_rejected'),"simulated":False}
            self._update_status_from_hardware(reply['arcade'])
        else:
            game=self.current_cartridge
            if game is None:return {"status":"error","error":"no_cartridge_selected"}
            if difficulty is not None:
                if not game.difficulty_supported:return {"status":"error","error":"difficulty_unsupported"}
                if difficulty!=game.difficulty:
                    if game.get_status()['state'] in (STATE_PLAYING,STATE_PAUSED):return {"status":"error","error":"difficulty_requires_restart"}
                    game.set_difficulty(difficulty);game.reset();self._clock.reset()
            self.sound_enabled=enabled;self.sound_volume=volume
            if not enabled:self.sound_events.clear()
            self._refresh_simulator_status()
        return {"status":"ok","simulated":self.simulated_mode,"source":"simulator" if self.simulated_mode else "esp32_hardware","game_status":dict(self.status)}

    @synchronized
    def players(self, count):
        if type(count) is not int or count not in (1,2) or self.status['game_id'] != 20:
            return {"status":"error","error":"invalid_player_mode"}
        self.keys_down=self.keys_pressed=0
        if self.simulated_mode:
            self.current_cartridge.set_player_count(count)
            self._refresh_simulator_status()
            return {"status":"ok","game_status":self.status,"simulated":True,"source":"simulator"}
        reply=self._send_esp32_command({"cmd":"arcade","action":"players","count":count})
        if reply.get('status')!='ok':
            return {"status":"error","error":reply.get('error','players_failed'),"simulated":False}
        self._update_status_from_hardware(reply['arcade'])
        return {"status":"ok","game_status":self.status,"simulated":False,"source":"esp32_hardware"}

    @synchronized
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
        with self._lock:
            if self.simulated_mode:
                return self._get_frame()
            controller=self.controller
            gid=self.status['game_id']
            if not self.is_hardware_available():
                return {"status":"error","error":"device_offline","running":False,"source":"hardware_offline","hex":"","simulated":False}
        # Disposable remote readback owns neither the game state lock nor the
        # gateway's control lane while waiting for a packet.
        res=self._send_esp32_command({"cmd":"frame"})
        with self._lock:
            if self.simulated_mode or self.controller is not controller or self.status['game_id']!=gid:
                return {"status":"error","error":"stale_frame","running":False,"source":"hardware_offline","hex":"","simulated":False}
            pixels=res.get('pixels')
            if res.get('status')!='ok' or not isinstance(pixels,str) or len(pixels)!=1536 or any(c not in '0123456789abcdefABCDEF' for c in pixels):
                return {"status":"error","error":res.get('error','invalid_frame'),"running":False,"source":"hardware_offline","hex":"","simulated":False}
            self.current_hex=pixels
            return {"running":self.is_running,"status":dict(self.status),"hex":pixels,
                "source":"hardware_pwm","frame_id":res.get('frame_id',0),"simulated":False}

    def _get_frame(self) -> Dict[str, Any]:
        """获取当前帧缓冲与 HUD 状态"""
        # Render a simulator ONLY when explicitly selected.
        if self.simulated_mode and self.current_cartridge:
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
                reply=self.controller.command_result(payload)
                if not isinstance(reply,dict):
                    return {"status":"error","error":"invalid_hardware_reply"}
                if reply.get("status") == "ok" and payload.get("cmd") == "arcade":
                    st=reply.get("arcade")
                    if not isinstance(st,dict) or type(st.get("game_id")) is not int or type(st.get("state")) is not int:
                        return {"status":"error","error":"invalid_arcade_reply"}
                return reply
            elif hasattr(self.controller, "send_json"):
                ok = self.controller.send_json(payload)
                return {"status":"error","error":"ack_state_unavailable" if ok else "send_failed"}
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
            "player_count": arc_data.get("player_count", 0),
            "difficulty_supported": arc_data.get("difficulty_supported",False),
            "difficulty": arc_data.get("difficulty",1),
            "sound_enabled": arc_data.get("sound_enabled",False),
            "sound_volume": arc_data.get("sound_volume",0),
            **{f"sound_{key}":arc_data.get(f"sound_{key}",0) for key in ("played","dropped","preempted","busy","short_writes","late","faults","duplicates")},
            "timing_dropped_ms": arc_data.get("timing_dropped_ms",0),
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
            "player_count": st.get("player_count", 0),
            "high_score": st.get("high_score", 0),
            "lives": st.get("lives", 1),
            "state": st_code,
            "state_name": STATE_NAMES.get(st_code, "UNKNOWN"),
            "progress": st.get("progress", 0),
            "source": "simulator",
            "simulated": True,
            "difficulty_supported": self.current_cartridge.difficulty_supported,
            "difficulty": self.current_cartridge.difficulty,
            "sound_enabled": self.sound_enabled,
            "sound_volume": self.sound_volume,
            "timing_dropped_ms": self._clock.dropped_us//1000,
        }

    def _game_name_for_id(self, gid: int) -> str:
        names = {1: "超级马里奥", 33: "经典贪吃蛇", 41: "俄罗斯方块"}
        return names.get(gid, f"游戏 #{gid:03d}")

    @synchronized
    def _simulator_step(self,dt):
        if not self.simulated_mode or not self.current_cartridge:
            return None
        def step(fixed_dt):
            self.current_cartridge.update(fixed_dt,self.keys_down,self.keys_pressed)
            self.keys_pressed=0
        self._clock.advance(dt,step)
        self.current_hex=self.current_cartridge.render().hex()
        self._refresh_simulator_status()
        return {"type":"arcade_frame","hex":self.current_hex,"status":dict(self.status),"simulated":True}

    async def run_loop(self):
        """Explicit simulator only; serialize physics with input/switch/snapshot calls."""
        self.is_running=True
        last_time=time.monotonic()
        while self.is_running:
            now=time.monotonic();dt=now-last_time;last_time=now
            frame=await asyncio.to_thread(self._simulator_step,dt)
            if frame and self.broadcast_fn:
                result=self.broadcast_fn(frame)
                if inspect.isawaitable(result):
                    await result
            await asyncio.sleep(.033)


_session: Optional[ArcadeSession] = None


def get_arcade_session(controller=None, broadcast_fn=None) -> ArcadeSession:
    global _session
    if _session is None:
        _session = ArcadeSession(controller, broadcast_fn)
    elif controller and _session.controller != controller:
        _session.controller = controller
    return _session
