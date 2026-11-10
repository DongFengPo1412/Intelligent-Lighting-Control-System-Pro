from .b3_helpers import *
import secrets


class Game101MicroLight(BatchCartridge):
    game_id = 101
    name = '微光纪元'
    english_name = 'MicroLight'
    core_mechanic = 'Side-scrolling 16x16 survival, building, mining, and exploring 7 biomes under a dynamic day-night cycle.'
    control_type = 3

    def set_replay_seed(self, seed):
        if type(seed) is not int or not 0 <= seed <= 0xffffffff:
            return False
        self._replay_seed = seed
        return True

    def use_random_seeds(self):
        self._replay_seed = None

    def get_biome(self, world_x):
        block_biome = (world_x if world_x >= 0 else (world_x - 39)) // 40
        return block_biome % 7

    def setup(self):
        seed = getattr(self, '_replay_seed', None)
        if seed is None:
            seed = secrets.randbits(32)
            if seed == getattr(self, '_last_seed', None):
                seed = (seed + 1) & 0xffffffff
        self._last_seed = seed

        self.player_x = 4.0
        self.player_y = 8.0
        self.vy = 0.0
        self.grounded = True
        self.hp = 5
        self.max_hp = 5
        self.aim_dx = 1
        self.aim_dy = 0
        self.wood = 0
        self.stone = 0
        self.crystal = 0
        self.biomes_visited = 1 << self.get_biome(int(self.player_x))
        self.day_clock = 30.0
        self.hurt_cd = 0.0

    def tick(self, dt, down, pressed):
        self.day_clock = (self.day_clock + dt) % 180.0
        if self.hurt_cd > 0:
            self.hurt_cd = max(0.0, self.hurt_cd - dt)

        speed = 5.0
        if (down & KEY_LEFT) or (pressed & KEY_LEFT):
            self.player_x -= speed * dt
            self.aim_dx = -1
            self.aim_dy = 0
        elif (down & KEY_RIGHT) or (pressed & KEY_RIGHT):
            self.player_x += speed * dt
            self.aim_dx = 1
            self.aim_dy = 0

        if pressed & KEY_UP:
            self.aim_dx = 0
            self.aim_dy = -1
        elif pressed & KEY_DOWN:
            self.aim_dx = 0
            self.aim_dy = 1

        if (pressed & KEY_UP) or ((pressed & KEY_A) and not self.grounded):
            if self.grounded:
                self.vy = -7.5
                self.grounded = False
                self.emit_sound('jump')

        self.vy += 16.0 * dt
        self.player_y += self.vy * dt

        if self.player_y >= 9.0:
            self.player_y = 9.0
            self.vy = 0.0
            self.grounded = True

        if (pressed & KEY_A) and self.grounded:
            self.award(15)
            self.wood += 1
            self.stone += 1
            self.emit_sound('action')

        if pressed & KEY_B:
            self.award(30)
            self.crystal += 1
            self.emit_sound('hit')

        cur_biome = self.get_biome(int(self.player_x))
        if not (self.biomes_visited & (1 << cur_biome)):
            self.biomes_visited |= (1 << cur_biome)
            self.award(100)
            self.emit_sound('item')

        if cur_biome == 6 and self.player_y >= 9.0:
            if self.hurt_cd <= 0:
                self.hp -= 1
                self.hurt_cd = 1.0
                self.emit_sound('collision')

        if self.biomes_visited == 0x7F:
            self.award(500)
            self.finish(True)
        elif self.hp <= 0:
            self.finish(False)
        elif self.elapsed > (180.0, 120.0, 90.0)[self.difficulty]:
            self.finish(bin(self.biomes_visited).count('1') >= 4)

    def progress(self):
        return bin(self.biomes_visited).count('1') * 100 // 7

    def draw(self, fb):
        phase = self.day_clock / 180.0
        if phase < 0.40:
            sky = (60, 160, 230)
        elif phase < 0.55:
            t = (phase - 0.40) / 0.15
            sky = (int(60 + t * 140), int(160 - t * 70), int(230 - t * 170))
        elif phase < 0.85:
            sky = (12, 20, 40)
        else:
            t = (phase - 0.85) / 0.15
            sky = (int(12 + t * 48), int(20 + t * 140), int(40 + t * 190))

        for y in range(16):
            for x in range(16):
                self.px(fb, x, y, sky)

        if 0.55 <= phase < 0.85:
            self.px(fb, 2, 2, (220, 230, 255))
            self.px(fb, 7, 3, (200, 210, 240))
            self.px(fb, 12, 1, (240, 240, 255))
            self.px(fb, 4, 5, (180, 200, 220))

        center_x = int(self.player_x)
        offset = center_x - 7
        for sx in range(16):
            wx = offset + sx
            biome = self.get_biome(wx)
            colors = [
                (65, 153, 72), (32, 110, 45), (35, 112, 211),
                (225, 184, 94), (210, 238, 245), (80, 112, 75), (83, 69, 82)
            ]
            surf_c = colors[biome]
            if biome == 1 and (wx % 6 == 0):
                self.px(fb, sx, 9, (143, 91, 47))
                self.px(fb, sx, 8, (42, 130, 54))
            elif biome == 6 and (wx % 4 == 0):
                surf_c = (249, 88, 25)

            self.px(fb, sx, 10, surf_c)
            for y in range(11, 16):
                self.px(fb, sx, y, (116, 79, 49) if y == 11 else (93, 98, 112))

        pl_sx = 7
        pl_sy = int(round(self.player_y))
        if 2 <= pl_sy < 16:
            if self.hurt_cd > 0 and int(self.hurt_cd * 10) % 2:
                self.px(fb, pl_sx, pl_sy - 1, (255, 255, 255))
                self.px(fb, pl_sx, pl_sy, (255, 255, 255))
            else:
                self.px(fb, pl_sx, pl_sy - 1, (255, 230, 80))
                self.px(fb, pl_sx, pl_sy, (60, 190, 220))

        cx = pl_sx + self.aim_dx
        cy = pl_sy + self.aim_dy
        if 0 <= cx < 16 and 0 <= cy < 16:
            self.px(fb, cx, cy, (91, 240, 249))

        for h in range(self.max_hp):
            hx = 15 - h
            self.px(fb, hx, 0, (237, 55, 59) if h < self.hp else (70, 20, 25))
