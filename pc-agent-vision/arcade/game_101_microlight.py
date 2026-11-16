from collections import OrderedDict
import math
import secrets
from .b3_helpers import *

# Tile IDs synchronized 1:1 with firmware-s3/main/display/arcade/game_101_microlight.h
TILE_AIR = 0
TILE_GRASS = 1
TILE_DIRT = 2
TILE_STONE = 3
TILE_WOOD = 4
TILE_LEAF = 5
TILE_SAND = 6
TILE_SNOW = 7
TILE_ICE = 8
TILE_WATER = 9
TILE_MUD = 10
TILE_BASALT = 11
TILE_LAVA = 12
TILE_CACTUS = 13
TILE_COPPER = 14
TILE_CRYSTAL = 15
TILE_COAL = 16
TILE_FLOWER = 17
TILE_TORCH = 18
TILE_WOOD_WALL = 19
TILE_STONE_WALL = 20
TILE_BRIDGE = 21
TILE_LADDER = 22
TILE_PLATFORM = 23
TILE_CAMPFIRE = 24
TILE_BEACON = 25
TILE_CHEST = 26
TILE_RUIN = 27
TILE_MUSHROOM = 28
TILE_BEDROCK = 29

BUILD_TORCH = 0
BUILD_WOOD_WALL = 1
BUILD_STONE_WALL = 2
BUILD_BRIDGE = 3
BUILD_CAMPFIRE = 4
BUILD_BEACON = 5

MAX_EDITS = 256
MAX_ENEMIES = 4
BIOME_WIDTH = 40

# (solid, hardness, light, rgb, drops)
TILES = {
    TILE_AIR: (False, 0, 0, (0, 0, 0), ()),
    TILE_GRASS: (True, 2, 0, (65, 153, 72), (("dirt", 1),)),
    TILE_DIRT: (True, 2, 0, (116, 79, 49), (("dirt", 1),)),
    TILE_STONE: (True, 3, 0, (93, 98, 112), (("stone", 1),)),
    TILE_WOOD: (True, 2, 0, (143, 91, 47), (("wood", 2),)),
    TILE_LEAF: (False, 1, 0, (42, 130, 54), (("fiber", 1),)),
    TILE_SAND: (True, 1, 0, (225, 184, 94), (("sand", 1),)),
    TILE_SNOW: (True, 1, 0, (209, 238, 245), (("snow", 1),)),
    TILE_ICE: (True, 2, 0, (105, 199, 229), (("ice", 1),)),
    TILE_WATER: (False, 0, 0, (35, 112, 211), ()),
    TILE_MUD: (True, 2, 0, (83, 103, 61), (("dirt", 1),)),
    TILE_BASALT: (True, 4, 0, (83, 69, 82), (("stone", 1),)),
    TILE_LAVA: (False, 0, 4, (249, 88, 25), ()),
    TILE_CACTUS: (True, 2, 0, (53, 141, 83), (("wood", 1), ("fiber", 1))),
    TILE_COPPER: (True, 3, 0, (203, 113, 55), (("ore", 1),)),
    TILE_CRYSTAL: (True, 4, 2, (169, 88, 240), (("crystal", 1),)),
    TILE_COAL: (True, 3, 0, (55, 64, 79), (("coal", 1),)),
    TILE_FLOWER: (False, 1, 0, (237, 129, 167), (("fiber", 1),)),
    TILE_TORCH: (False, 1, 4, (255, 191, 83), (("wood", 1),)),
    TILE_WOOD_WALL: (True, 2, 0, (159, 110, 63), (("wood", 1),)),
    TILE_STONE_WALL: (True, 3, 0, (149, 159, 168), (("stone", 1),)),
    TILE_BRIDGE: (True, 2, 0, (175, 127, 72), (("wood", 1),)),
    TILE_LADDER: (False, 2, 0, (230, 165, 75), (("wood", 1),)),
    TILE_PLATFORM: (True, 2, 0, (168, 118, 67), (("wood", 1),)),
    TILE_CAMPFIRE: (False, 1, 5, (255, 126, 48), (("wood", 1),)),
    TILE_BEACON: (True, 4, 8, (91, 240, 249), (("crystal", 1),)),
    TILE_CHEST: (True, 2, 1, (249, 198, 53), ()),
    TILE_RUIN: (True, 3, 0, (115, 122, 157), (("stone", 1),)),
    TILE_MUSHROOM: (False, 1, 1, (218, 102, 194), (("berry", 1),)),
    TILE_BEDROCK: (True, 255, 0, (43, 48, 67), ()),
}

BUILD_RECIPES = (
    ("火把", TILE_TORCH, {"wood": 1, "fiber": 1}),
    ("木墙", TILE_WOOD_WALL, {"wood": 2}),
    ("石墙", TILE_STONE_WALL, {"stone": 2}),
    ("木桥", TILE_BRIDGE, {"wood": 2}),
    ("篝火", TILE_CAMPFIRE, {"wood": 2, "coal": 1}),
    ("星核灯塔", TILE_BEACON, {"ore": 2, "crystal": 2}),
)

_MASK64 = (1 << 64) - 1


def _hash_step(h, val):
    z = ((int(val) & _MASK64) + 0x9E3779B97F4A7C15) & _MASK64
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & _MASK64
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & _MASK64
    h = (h ^ z ^ (z >> 31)) & _MASK64
    return (h * 0x00E7037ED1A0B428) & _MASK64


def _micro_rnd(a, b, c):
    h = 0xA0761D6478BD642F
    h = _hash_step(h, a)
    h = _hash_step(h, b)
    h = _hash_step(h, c)
    return (h >> 11) / (1 << 53)


def _smoothstep(t):
    return t * t * (3.0 - 2.0 * t)


def _value_noise(x, y, seed):
    xi = math.floor(x)
    yi = math.floor(y)
    a = _smoothstep(x - xi)
    b = _smoothstep(y - yi)
    t00 = _micro_rnd(xi, yi, seed)
    t10 = _micro_rnd(xi + 1, yi, seed)
    t01 = _micro_rnd(xi, yi + 1, seed)
    t11 = _micro_rnd(xi + 1, yi + 1, seed)
    return (t00 * (1.0 - a) + t10 * a) * (1.0 - b) + (t01 * (1.0 - a) + t11 * a) * b


class Game101MicroLight(BatchCartridge):
    game_id = 101
    name = "微光纪元"
    english_name = "MicroLight"
    core_mechanic = "Side-scrolling 16x16 sandbox survival, mining, building, combat, and 7 biomes under a dynamic day-night cycle."
    control_type = 3

    def set_replay_seed(self, seed):
        if type(seed) is not int or not 0 <= seed <= 0xFFFFFFFF:
            return False
        self._replay_seed = seed
        return True

    def use_random_seeds(self):
        self._replay_seed = None

    @staticmethod
    def get_biome(world_x):
        return (int(world_x) // BIOME_WIDTH) % 7

    def surface_at(self, world_x):
        world_x = int(world_x)
        if -4 <= world_x <= 4:
            return 11
        biome = self.get_biome(world_x)
        levels = (11, 10, 13, 11, 9, 12, 9)
        level = float(levels[biome])
        s = int(self.world_seed)
        slope = (_value_noise(world_x / 27.0, 0.0, s + 10) - 0.5) * 3.0
        detail = (_value_noise(world_x / 8.0, 0.0, s + 11) - 0.5) * 1.8
        if biome == 3:
            detail += (_value_noise(world_x / 14.0, 1.0, s + 13) - 0.5) * 2.5
        elif biome == 6:
            detail += (_value_noise(world_x / 11.0, 1.0, s + 17) - 0.5) * 3.0
        pos_in_biome = world_x % BIOME_WIDTH
        if pos_in_biome < 6:
            prev_b = self.get_biome(world_x - 8)
            a = _smoothstep(pos_in_biome / 6.0)
            level = float(levels[prev_b]) * (1.0 - a) + level * a
        elif pos_in_biome > BIOME_WIDTH - 6:
            next_b = self.get_biome(world_x + 8)
            a = _smoothstep((pos_in_biome - (BIOME_WIDTH - 6)) / 6.0)
            level = level * (1.0 - a) + float(levels[next_b]) * a
        return max(7, min(15, round(level + slope + detail)))

    def _raw_tile(self, wx, wy):
        wx, wy = int(wx), int(wy)
        if wy >= 26:
            return TILE_BEDROCK
        surface = self.surface_at(wx)
        biome = self.get_biome(wx)
        s = int(self.world_seed)

        if wy < surface:
            if biome == 2 and wy >= 11:
                return TILE_WATER
            if biome == 5 and wy >= 11 and ((wx // 5) % 3 != 0):
                return TILE_WATER
            if biome == 6 and wy >= 11 and _micro_rnd(wx // 4, s, 451) < 0.22:
                return TILE_LAVA
            if -4 <= wx <= 4:
                if wy == surface - 1:
                    if wx == 2:
                        return TILE_WOOD
                    if wx == 3:
                        return TILE_COPPER
                    if wx == -2:
                        return TILE_FLOWER
                return TILE_AIR
            if wy == surface - 1 and _micro_rnd(wx, s, 901) < 0.02 and abs(wx) > 10:
                return TILE_CHEST
            if biome == 3 and wy in (surface - 1, surface - 2) and _micro_rnd(wx, s, 222) < 0.08:
                return TILE_CACTUS
            if biome in (0, 1, 5):
                chance = 0.22 if biome == 1 else (0.10 if biome == 5 else 0.08)
                if (_micro_rnd(wx, s, 123) < chance and _micro_rnd(wx - 1, s, 123) >= chance and abs(wx) > 4):
                    if wy in (surface - 1, surface - 2):
                        return TILE_WOOD
                for dx in (-1, 0, 1):
                    bx = wx + dx
                    if (_micro_rnd(bx, s, 123) < chance and _micro_rnd(bx - 1, s, 123) >= chance and abs(bx) > 4):
                        top = self.surface_at(bx) - 3
                        if wy == top or (dx == 0 and wy == top - 1):
                            return TILE_LEAF
            if wy == surface - 1 and _micro_rnd(wx, s, 314) < 0.14:
                if biome == 5:
                    return TILE_MUSHROOM
                if biome in (0, 1):
                    return TILE_FLOWER
            return TILE_AIR

        if wy == surface:
            return (TILE_GRASS, TILE_GRASS, TILE_SAND, TILE_SAND, TILE_SNOW, TILE_MUD, TILE_BASALT)[biome]

        depth = wy - surface
        if depth <= 2:
            if biome in (2, 3):
                return TILE_SAND
            if biome == 4:
                return TILE_ICE
            if biome == 6:
                return TILE_BASALT
            return TILE_DIRT

        cave = _value_noise(wx / 9.0, wy / 7.0, s + 52) * 0.67 + _value_noise(wx / 3.0, wy / 4.0, s + 53) * 0.33
        if cave > 0.66:
            return TILE_AIR
        ore = _value_noise(wx / 3.7, wy / 3.5, s + 38)
        if depth >= 5 and ore > 0.77:
            return TILE_CRYSTAL
        if ore > 0.66:
            return TILE_COPPER
        if ore < 0.24:
            return TILE_COAL
        return TILE_BASALT if (biome == 6 or wy > 20) else TILE_STONE

    def tile(self, wx, wy):
        key = (int(wx), int(wy))
        if key in self.edits:
            return self.edits[key]
        return self._raw_tile(key[0], key[1])

    def put_tile(self, wx, wy, tid):
        if tid not in TILES:
            return False
        key = (int(wx), int(wy))
        self.edits[key] = int(tid)
        self.edits.move_to_end(key)
        while len(self.edits) > MAX_EDITS:
            self.edits.popitem(last=False)
        return True

    def solid(self, wx, wy):
        return TILES[self.tile(wx, wy)][0]

    def visited_biome_count(self):
        return bin(self.biomes_visited & 0x7F).count("1")

    def target(self):
        px_i = math.floor(self.player_x + 0.5)
        py_i = math.floor(self.player_y + 0.45)
        if self.aim_dx != 0:
            return px_i + self.aim_dx, py_i + 1
        if self.aim_dy < 0:
            return px_i, py_i - 1
        return px_i, py_i + 2

    def collides(self, x, y):
        if y < -40.0:
            return True
        x0 = math.floor(x + 1e-4)
        x1 = math.floor(x + 1.0 - 1e-4)
        y0 = math.floor(y + 1e-4)
        y1 = math.floor(y + 2.0 - 1e-4)
        for tx in range(x0, x1 + 1):
            for ty in range(y0, y1 + 1):
                if self.solid(tx, ty):
                    return True
        return False

    def _move_axis(self, delta, horizontal):
        if delta == 0.0:
            return False
        tx = self.player_x + delta if horizontal else self.player_x
        ty = self.player_y if horizontal else self.player_y + delta
        if not self.collides(tx, ty):
            if horizontal:
                self.player_x = tx
            else:
                self.player_y = ty
            return False
        lo, hi = 0.0, 1.0
        for _ in range(12):
            mid = (lo + hi) * 0.5
            nx = self.player_x + delta * mid if horizontal else self.player_x
            ny = self.player_y if horizontal else self.player_y + delta * mid
            if self.collides(nx, ny):
                hi = mid
            else:
                lo = mid
        if horizontal:
            self.player_x += delta * lo
            self.vx = 0.0
        else:
            self.player_y += delta * lo
            self.vy = 0.0
        return True

    def in_fluid(self):
        for tx in (math.floor(self.player_x + 0.1), math.floor(self.player_x + 0.9)):
            for ty in (math.floor(self.player_y + 0.5), math.floor(self.player_y + 1.5)):
                tid = self.tile(tx, ty)
                if tid in (TILE_WATER, TILE_LAVA):
                    return tid
        return TILE_AIR

    def touching_cactus(self):
        for tx in (math.floor(self.player_x - 0.1), math.floor(self.player_x + 1.1)):
            for ty in (math.floor(self.player_y + 0.2), math.floor(self.player_y + 1.8)):
                if self.tile(tx, ty) == TILE_CACTUS:
                    return True
        return False

    def apply_damage(self, amt):
        if self.hurt_cd > 0 or self.state != STATE_PLAYING:
            return
        self.hp = max(0, self.hp - amt)
        self.hurt_cd = 1.0
        self.hit_flash = 0.3
        self.emit_sound("collision")

    def is_night(self):
        phase = (self.day_clock % 180.0) / 180.0
        return phase > 0.60 or phase < 0.09

    def ambient_light(self):
        phase = (self.day_clock % 180.0) / 180.0
        return max(0.15, min(1.0, (0.58 - abs(phase - 0.45)) * 3.1))

    def setup(self):
        seed = getattr(self, "_replay_seed", None)
        if seed is None:
            seed = secrets.randbits(32)
            if seed == getattr(self, "_last_seed", None):
                seed = (seed + 1) & 0xFFFFFFFF
        self._last_seed = seed
        self.world_seed = seed if seed else 9527
        self._prng = self.world_seed

        self.edits = OrderedDict()
        self.enemies = []
        self.inv = {
            "wood": 5, "stone": 3, "dirt": 0, "sand": 0,
            "snow": 0, "ice": 0, "ore": 0, "coal": 0,
            "crystal": 0, "fiber": 3, "berry": 3, "relic": 0,
        }
        self.player_x = 0.0
        self.player_y = float(self.surface_at(0) - 2)
        self.vx = 0.0
        self.vy = 0.0
        self.grounded = True
        self.coyote = 0.12
        self.jump_buffer = 0.0
        self.hp = 5
        self.max_hp = 5
        self.facing = 1
        self.aim_dx = 1
        self.aim_dy = 0
        self.pick_tier = 1
        self.sword_tier = 0
        self.build_index = BUILD_TORCH
        self.biomes_visited = 1 << self.get_biome(0)
        self.beacons_placed = 0
        self.day_clock = 32.0
        self.hurt_cd = 0.0
        self.hit_flash = 0.0
        self.mine_cd = 0.0
        self.build_cd = 0.0
        self.attack_cd = 0.0
        self.attack_fx = 0.0
        self.spawn_timer = 4.0
        self._mine_key = None
        self._mine_hits = 0

    def mine(self):
        if self.mine_cd > 0:
            return False
        self.mine_cd = 0.12
        tx, ty = self.target()
        tid = self.tile(tx, ty)
        if tid in (TILE_AIR, TILE_WATER, TILE_LAVA, TILE_BEDROCK):
            return False
        if tid == TILE_CHEST:
            self.put_tile(tx, ty, TILE_AIR)
            self.inv["relic"] += 1
            self.inv["ore"] += 2
            self.inv["crystal"] += 1
            self.inv["berry"] += 2
            self.award(80)
            self.emit_sound("score")
            return True
        key = (tx, ty, tid)
        if key != self._mine_key:
            self._mine_key = key
            self._mine_hits = 0
        self._mine_hits += 1 + self.pick_tier
        hardness = TILES[tid][1]
        if self._mine_hits < hardness:
            self.emit_sound("action")
            return False
        for res, qty in TILES[tid][4]:
            self.inv[res] = self.inv.get(res, 0) + qty
        self.put_tile(tx, ty, TILE_AIR)
        self._mine_key = None
        self._mine_hits = 0
        self.award(15 * hardness)
        self.emit_sound("action")
        return True

    def can_afford(self, slot):
        cost = BUILD_RECIPES[slot][2]
        return all(self.inv.get(k, 0) >= v for k, v in cost.items())

    def build(self):
        if self.build_cd > 0:
            return False
        self.build_cd = 0.15
        tx, ty = self.target()
        existing = self.tile(tx, ty)
        slot = BUILD_BRIDGE if existing == TILE_WATER else self.build_index
        _, place_tid, cost = BUILD_RECIPES[slot]
        if not self.can_afford(slot):
            return False
        if slot == BUILD_BRIDGE:
            if existing not in (TILE_WATER, TILE_AIR):
                return False
        elif existing != TILE_AIR:
            return False
        if (TILES[place_tid][0] and self.player_x < tx + 1 and self.player_x + 1.0 > tx
                and self.player_y < ty + 1 and self.player_y + 2.0 > ty):
            return False
        has_support = (self.solid(tx, ty + 1) or self.solid(tx - 1, ty)
                       or self.solid(tx + 1, ty) or self.tile(tx, ty + 1) == TILE_WATER)
        if not has_support:
            return False
        for k, v in cost.items():
            self.inv[k] -= v
        self.put_tile(tx, ty, place_tid)
        if place_tid == TILE_BEACON:
            self.beacons_placed += 1
        self.award(30)
        self.emit_sound("score")
        return True

    def attack(self):
        if self.attack_cd > 0:
            return False
        tx, ty = self.target()
        for e in self.enemies[:]:
            near_target = abs(e["x"] - tx) <= 1.65 and abs(e["y"] - ty) <= 1.85
            near_player = abs(e["x"] - self.player_x) <= 1.55 and abs(e["y"] - (self.player_y + 1.0)) <= 1.55
            if near_target or near_player:
                self.attack_cd = 0.25
                self.attack_fx = 0.16
                e["hp"] -= 1 + self.sword_tier
                e["x"] += 1.2 if e["x"] >= self.player_x else -1.2
                if e["hp"] <= 0:
                    self.enemies.remove(e)
                    self.inv["fiber"] += 1
                    self._prng = rng(self._prng)
                    if (self._prng & 3) == 0:
                        self.inv["ore"] += 1
                    self.award(40)
                else:
                    self.award(15)
                self.emit_sound("hit")
                return True
        return False

    def spawn_enemy_at(self, x, y, kind="slime", hp=2):
        if len(self.enemies) >= MAX_ENEMIES:
            return False
        self.enemies.append({"x": float(x), "y": float(y), "kind": kind, "hp": int(hp), "attack_timer": 0.3})
        return True

    def _spawn_ambient_enemy(self):
        if len(self.enemies) >= MAX_ENEMIES:
            return
        px_i = math.floor(self.player_x)
        underground = self.player_y > self.surface_at(px_i) + 2
        if not underground and not self.is_night():
            return
        self._prng = rng(self._prng)
        side = 1 if (self._prng & 1) else -1
        self._prng = rng(self._prng)
        dist = 8 + (self._prng % 4)
        sx = px_i + side * dist
        if underground:
            self._prng = rng(self._prng)
            sy = math.floor(self.player_y) + (self._prng % 5) - 2
            if not self.solid(sx, sy):
                self.spawn_enemy_at(sx, sy, "wisp", 2)
        else:
            sy = self.surface_at(sx) - 1
            if not self.solid(sx, sy):
                b = self.get_biome(sx)
                kind = {3: "scorpion", 4: "icebug", 5: "wisp"}.get(b, "slime")
                self.spawn_enemy_at(sx, sy, kind, 3 if kind == "scorpion" else 2)

    def _update_enemies(self, dt):
        for e in self.enemies[:]:
            if abs(e["x"] - self.player_x) > 18.0:
                self.enemies.remove(e)
                continue
            e["attack_timer"] = max(0.0, e["attack_timer"] - dt)
            direction = 1.0 if self.player_x > e["x"] else -1.0
            speed = 1.0 if e["kind"] == "slime" else 1.45
            e["x"] += direction * speed * dt
            if e["kind"] == "wisp":
                dy = max(-1.0, min(1.0, (self.player_y + 1.0) - e["y"]))
                e["y"] += dy * dt * 0.65
            else:
                e["y"] = float(self.surface_at(math.floor(e["x"])) - 1)
            if abs(e["x"] - self.player_x) < 1.05 and abs(e["y"] - (self.player_y + 1.0)) < 1.3 and e["attack_timer"] <= 0:
                self.apply_damage(1)
                e["attack_timer"] = 1.4

    def tick(self, dt, down, pressed):
        self.day_clock = (self.day_clock + dt) % 180.0
        self.hurt_cd = max(0.0, self.hurt_cd - dt)
        self.hit_flash = max(0.0, self.hit_flash - dt)
        self.mine_cd = max(0.0, self.mine_cd - dt)
        self.build_cd = max(0.0, self.build_cd - dt)
        self.attack_cd = max(0.0, self.attack_cd - dt)
        self.attack_fx = max(0.0, self.attack_fx - dt)
        self.jump_buffer = max(0.0, self.jump_buffer - dt)
        self.coyote = 0.12 if self.grounded else max(0.0, self.coyote - dt)

        fluid = self.in_fluid()
        move_dir = (1 if ((down | pressed) & KEY_RIGHT) else 0) - (1 if ((down | pressed) & KEY_LEFT) else 0)
        if move_dir != 0:
            self.facing = move_dir

        if (down & KEY_UP) or ((pressed & KEY_UP) and not self.grounded):
            self.aim_dx, self.aim_dy = 0, -1
        elif down & KEY_DOWN:
            self.aim_dx, self.aim_dy = 0, 1
        else:
            self.aim_dx, self.aim_dy = self.facing, 0

        max_speed = 3.25 if fluid == TILE_WATER else 5.3
        on_ice = self.grounded and self.tile(math.floor(self.player_x + 0.5), math.floor(self.player_y + 2.05)) == TILE_ICE
        if move_dir != 0:
            self.vx = move_dir * max_speed
        elif on_ice:
            self.vx *= max(0.0, 1.0 - 2.5 * dt)
        else:
            self.vx = 0.0
        self._move_axis(self.vx * dt, True)

        if pressed & KEY_UP:
            self.jump_buffer = 0.15
        if self.jump_buffer > 0 and (self.grounded or self.coyote > 0) and fluid != TILE_WATER:
            self.vy = -10.1
            self.jump_buffer = 0.0
            self.coyote = 0.0
            self.grounded = False
            self.emit_sound("jump")
        elif fluid == TILE_WATER and ((down & KEY_UP) or (pressed & KEY_UP)):
            self.vy = min(self.vy, -3.4)

        if fluid == TILE_WATER:
            self.vy = min(3.2, self.vy + 6.5 * dt)
            if down & KEY_DOWN:
                self.vy = 3.3
        else:
            self.vy = min(12.0, self.vy + 21.0 * dt)

        hit_y = self._move_axis(self.vy * dt, False)
        self.grounded = (hit_y and self.vy == 0.0 and self.collides(self.player_x, self.player_y + 0.04)) or (
            self.collides(self.player_x, self.player_y + 0.04) and self.vy >= 0
        )
        if self.grounded:
            self.vy = max(0.0, self.vy)

        if fluid == TILE_LAVA or self.touching_cactus():
            self.apply_damage(1)
        if self.player_y > 60.0:
            self.hp = 0

        if pressed & KEY_A:
            self.mine()
        if pressed & KEY_B:
            if not self.attack():
                self.build()

        if self.hp > 0 and self.hp < self.max_hp and self.inv["berry"] >= 2 and (down & KEY_DOWN) and (pressed & KEY_A):
            self.inv["berry"] -= 2
            self.hp = min(self.max_hp, self.hp + 1)
            self.emit_sound("score")

        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            self.spawn_timer = 4.5 if self.is_night() else 9.5
            self._spawn_ambient_enemy()
        self._update_enemies(dt)

        cur_biome = self.get_biome(math.floor(self.player_x))
        if not (self.biomes_visited & (1 << cur_biome)):
            self.biomes_visited |= 1 << cur_biome
            self.award(100)
            self.emit_sound("item")

        if self.biomes_visited == 0x7F or self.beacons_placed >= 1:
            self.award(500)
            self.finish(True)
        elif self.hp <= 0:
            self.finish(False)
        elif self.elapsed > (180.0, 120.0, 90.0)[self.difficulty]:
            self.finish(self.visited_biome_count() >= 4)

    def progress(self):
        return self.visited_biome_count() * 100 // 7

    @property
    def status(self):
        return dict(
            game_id=self.game_id, name=self.name, state=self.state, score=self.score,
            high_score=self.high_score, lives=self.hp, progress=min(100, max(0, self.progress())),
            control_type=self.control_type, difficulty=self.difficulty,
            difficulty_supported=self.difficulty_supported,
        )

    def draw(self, fb):
        phase = (self.day_clock % 180.0) / 180.0
        ambient = self.ambient_light()
        cam_x = round(self.player_x) - 7
        cam_y = round(self.player_y) - 7

        lights = [(self.player_x + 0.5, self.player_y + 1.0, 3.1)]
        for sy in range(16):
            for sx in range(16):
                tid = self.tile(cam_x + sx, cam_y + sy)
                lrad = TILES[tid][2]
                if lrad > 0:
                    lights.append((cam_x + sx + 0.5, cam_y + sy + 0.5, float(lrad)))

        day_skies = (
            (70, 167, 235), (50, 132, 204), (64, 168, 235),
            (118, 179, 223), (112, 182, 211), (55, 133, 139), (138, 97, 112),
        )
        for sy in range(16):
            wy = cam_y + sy
            for sx in range(16):
                wx = cam_x + sx
                biome = self.get_biome(wx)
                surf = self.surface_at(wx)
                tid = self.tile(wx, wy)
                if tid == TILE_AIR:
                    if wy < surf:
                        ds = day_skies[biome]
                        sr = 12.0 * (1.0 - ambient) + ds[0] * ambient
                        sg = 20.0 * (1.0 - ambient) + ds[1] * ambient
                        sb = 42.0 * (1.0 - ambient) + ds[2] * ambient
                        if 0.48 < phase < 0.66:
                            dusk = 0.34 * max(0.0, 1.0 - abs(phase - 0.58) / 0.11)
                            sr = sr * (1.0 - dusk) + 200.0 * dusk
                            sg = sg * (1.0 - dusk) + 108.0 * dusk
                            sb = sb * (1.0 - dusk) + 65.0 * dusk
                        if ambient < 0.52 and _micro_rnd(wx, wy, int(self.world_seed) + 109) > 0.976:
                            sr, sg, sb = 167, 198, 230
                        self.px(fb, sx, sy, (int(sr), int(sg), int(sb)))
                    else:
                        self.px(fb, sx, sy, (12, 14, 27))
                else:
                    rgb = TILES[tid][3]
                    illum = max(0.14, ambient) if wy <= surf + 1 else 0.18
                    for lx, ly, lrad in lights:
                        dist = math.hypot(wx + 0.5 - lx, wy + 0.5 - ly)
                        illum = max(illum, 0.22 + 0.85 * max(0.0, 1.0 - dist / lrad))
                    illum = min(1.12, illum)
                    self.px(fb, sx, sy, tuple(min(255, int(c * illum)) for c in rgb))

        enemy_rgb = {"slime": (220, 64, 83), "scorpion": (238, 120, 42), "icebug": (115, 218, 253), "wisp": (186, 97, 246)}
        for e in self.enemies:
            ex = round(e["x"]) - cam_x
            ey = round(e["y"]) - cam_y
            self.px(fb, ex, ey, enemy_rgb.get(e["kind"], (220, 64, 83)))

        tx, ty = self.target()
        ax, ay = tx - cam_x, ty - cam_y
        if self.attack_fx > 0:
            self.px(fb, ax, ay, (255, 239, 142))
        elif int(self.day_clock * 3.0) % 2 == 0:
            self.px(fb, ax, ay, (91, 240, 249))

        pl_sx = round(self.player_x) - cam_x
        pl_sy = round(self.player_y) - cam_y
        if self.hurt_cd > 0 and int(self.hurt_cd * 10) % 2 == 1:
            self.px(fb, pl_sx, pl_sy, (255, 255, 255))
            self.px(fb, pl_sx, pl_sy + 1, (255, 255, 255))
        else:
            self.px(fb, pl_sx, pl_sy, (255, 222, 96))
            self.px(fb, pl_sx, pl_sy + 1, (94, 215, 245))

        cap_hp = min(7, self.max_hp)
        for h in range(cap_hp):
            hx = 16 - cap_hp + h
            self.px(fb, hx, 0, (251, 42, 70) if h < self.hp else (69, 24, 43))
