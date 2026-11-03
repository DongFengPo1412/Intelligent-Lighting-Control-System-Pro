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
from .game_045_side_pocket import Game045SidePocket
from .game_046_city_connection import Game046CityConnection
from .game_047_double_dragon import Game047DoubleDragon
from .game_048_elevator_action import Game048ElevatorAction
from .game_049_balloon_fight import Game049BalloonFight
from .game_050_kung_fu_master import Game050KungFuMaster
from .game_051_shinobi import Game051Shinobi
from .game_052_gunsmoke import Game052GunSmoke
from .game_053_wrestling import Game053Wrestling
from .game_054_antarctic import Game054Antarctic
from .game_055_ninjagaiden import Game055NinjaGaiden
from .game_056_1942 import Game056_1942
from .game_057_wonderboy import Game057WonderBoy
from .game_058_paperboy import Game058Paperboy
from .game_059_trackfield import Game059TrackField
from .game_060_marblemadness import Game060MarbleMadness
from .game_061_battlecity import Game061BattleCity
from .game_062_shadowwarriors import Game062ShadowWarriors
from .game_063_rampart import Game063Rampart
from .game_064_inthehunt import Game064InTheHunt
from .game_065_punchout import Game065PunchOut
from .game_066_twinbee import Game066TwinBee
from .game_067_snowbros import Game067SnowBros
from .game_068_metalgear import Game068MetalGear
from .game_069_qbert import Game069Qbert
from .game_070_lunarpool import Game070LunarPool
from .game_071_ghostsngoblins import Game071GhostsNGoblins
from .game_072_bombjack import Game072BombJack
from .game_073_gradius import Game073Gradius
from .game_074_donkeykong3 import Game074DonkeyKong3
from .game_075_outrun import Game075OutRun
from .game_076_spelunker import Game076Spelunker
from .game_077_windjammers import Game077Windjammers
from .game_078_karatechamp import Game078KarateChamp
from .game_079_subroc3d import Game079SubRoc3D
from .game_080_cadillacs import Game080Cadillacs
from .game_081_rampage import Game081Rampage
from .game_082_chasehq import Game082ChaseHQ
from .game_083_puyopuyo import Game083PuyoPuyo
from .game_084_warriorsoffate import Game084WarriorsOfFate
from .game_085_renegade import Game085Renegade
from .game_086_kikikaikai import Game086KiKiKaiKai
from .game_087_streetsofrage import Game087StreetsOfRage
from .game_088_bumpnjump import Game088BumpNJump
from .game_089_snowbros2 import Game089SnowBros2
from .game_090_sunsetriders import Game090SunsetRiders
from .game_091_ninjabaseball import Game091NinjaBaseball
from .game_092_sengokublade import Game092SengokuBlade
from .game_093_pengo import Game093Pengo
from .game_094_crashboys import Game094CrashBoys
from .game_095_burgertime import Game095BurgerTime
from .game_096_pooyan import Game096Pooyan
from .game_097_tapper import Game097Tapper
from .game_098_mappy import Game098Mappy
from .game_099_joust import Game099Joust
from .game_100_timepilot import Game100TimePilot
from .game_101_spyhunter import Game101SpyHunter
from .game_102_columns import Game102Columns
from .game_103_dkjr import Game103DKJr
from .game_104_digdug2 import Game104DigDug2
from .game_105_arkanoid import Game105Arkanoid
from .game_106_crazyclimber import Game106CrazyClimber
from .game_107_xevious import Game107Xevious
from .game_108_pinball import Game108Pinball
from .game_109_spaceharrier import Game109SpaceHarrier
from .game_110_devilworld import Game110DevilWorld
from .game_111_leaguebowling import Game111LeagueBowling
from .game_112_defender import Game112Defender
from .game_113_asteroids import Game113Asteroids
from .game_114_berzerk import Game114Berzerk
from .game_115_tempest import Game115Tempest
from .game_116_lunarlander import Game116LunarLander
from .game_117_superoffroad import Game117SuperOffRoad
from .game_118_yiearkungfu import Game118YieArKungFu
from .game_119_pitfall2 import Game119Pitfall2
from .game_120_goldminer import Game120GoldMiner
from .game_121_spacetaxi import Game121SpaceTaxi
from .game_122_bosconian import Game122Bosconian
from .game_123_targ import Game123Targ

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
ArcadeRegistry.register(Game045SidePocket)
ArcadeRegistry.register(Game046CityConnection)
ArcadeRegistry.register(Game047DoubleDragon)
ArcadeRegistry.register(Game048ElevatorAction)
ArcadeRegistry.register(Game049BalloonFight)
ArcadeRegistry.register(Game050KungFuMaster)
ArcadeRegistry.register(Game051Shinobi)
ArcadeRegistry.register(Game052GunSmoke)
ArcadeRegistry.register(Game053Wrestling)
ArcadeRegistry.register(Game054Antarctic)
ArcadeRegistry.register(Game055NinjaGaiden)
ArcadeRegistry.register(Game056_1942)
ArcadeRegistry.register(Game057WonderBoy)
ArcadeRegistry.register(Game058Paperboy)
ArcadeRegistry.register(Game059TrackField)
ArcadeRegistry.register(Game060MarbleMadness)
ArcadeRegistry.register(Game061BattleCity)
ArcadeRegistry.register(Game062ShadowWarriors)
ArcadeRegistry.register(Game063Rampart)
ArcadeRegistry.register(Game064InTheHunt)
ArcadeRegistry.register(Game065PunchOut)
ArcadeRegistry.register(Game066TwinBee)
ArcadeRegistry.register(Game067SnowBros)
ArcadeRegistry.register(Game068MetalGear)
ArcadeRegistry.register(Game069Qbert)
ArcadeRegistry.register(Game070LunarPool)
ArcadeRegistry.register(Game071GhostsNGoblins)
ArcadeRegistry.register(Game072BombJack)
ArcadeRegistry.register(Game073Gradius)
ArcadeRegistry.register(Game074DonkeyKong3)
ArcadeRegistry.register(Game075OutRun)
ArcadeRegistry.register(Game076Spelunker)
ArcadeRegistry.register(Game077Windjammers)
ArcadeRegistry.register(Game078KarateChamp)
ArcadeRegistry.register(Game079SubRoc3D)
ArcadeRegistry.register(Game080Cadillacs)
ArcadeRegistry.register(Game081Rampage)
ArcadeRegistry.register(Game082ChaseHQ)
ArcadeRegistry.register(Game083PuyoPuyo)
ArcadeRegistry.register(Game084WarriorsOfFate)
ArcadeRegistry.register(Game085Renegade)
ArcadeRegistry.register(Game086KiKiKaiKai)
ArcadeRegistry.register(Game087StreetsOfRage)
ArcadeRegistry.register(Game088BumpNJump)
ArcadeRegistry.register(Game089SnowBros2)
ArcadeRegistry.register(Game090SunsetRiders)
ArcadeRegistry.register(Game091NinjaBaseball)
ArcadeRegistry.register(Game092SengokuBlade)
ArcadeRegistry.register(Game093Pengo)
ArcadeRegistry.register(Game094CrashBoys)
ArcadeRegistry.register(Game095BurgerTime)
ArcadeRegistry.register(Game096Pooyan)
ArcadeRegistry.register(Game097Tapper)
ArcadeRegistry.register(Game098Mappy)
ArcadeRegistry.register(Game099Joust)
ArcadeRegistry.register(Game100TimePilot)
ArcadeRegistry.register(Game101SpyHunter)
ArcadeRegistry.register(Game102Columns)
ArcadeRegistry.register(Game103DKJr)
ArcadeRegistry.register(Game104DigDug2)
ArcadeRegistry.register(Game105Arkanoid)
ArcadeRegistry.register(Game106CrazyClimber)
ArcadeRegistry.register(Game107Xevious)
ArcadeRegistry.register(Game108Pinball)
ArcadeRegistry.register(Game109SpaceHarrier)
ArcadeRegistry.register(Game110DevilWorld)
ArcadeRegistry.register(Game111LeagueBowling)
ArcadeRegistry.register(Game112Defender)
ArcadeRegistry.register(Game113Asteroids)
ArcadeRegistry.register(Game114Berzerk)
ArcadeRegistry.register(Game115Tempest)
ArcadeRegistry.register(Game116LunarLander)
ArcadeRegistry.register(Game117SuperOffRoad)
ArcadeRegistry.register(Game118YieArKungFu)
ArcadeRegistry.register(Game119Pitfall2)
ArcadeRegistry.register(Game120GoldMiner)
ArcadeRegistry.register(Game121SpaceTaxi)
ArcadeRegistry.register(Game122Bosconian)
ArcadeRegistry.register(Game123Targ)
