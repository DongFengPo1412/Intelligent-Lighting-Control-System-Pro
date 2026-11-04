"""Lifecycle/drawing helpers only; each batch game owns its independent rules."""
import math
from .base_cartridge import *
from .arcade_result_screen import ArcadeResultScreen


class BatchCartridge(BaseCartridge):
    difficulty_supported = True
    release_year = 2026
    control_type = CTRL_ARCADE_AB

    def init(self):
        self._high_score = getattr(self, '_high_score', 0)
        self.reset()

    def reset(self):
        self._state = STATE_TITLE
        self._score = 0
        self.elapsed = self.timer = self.repeat = 0.
        self.setup()

    def start(self):
        if self.state in (STATE_TITLE, STATE_GAMEOVER, STATE_VICTORY):
            self.reset()
            self._state = STATE_PLAYING

    def pause(self):
        if self.state == STATE_PLAYING: self._state = STATE_PAUSED

    def resume(self):
        if self.state == STATE_PAUSED: self._state = STATE_PLAYING

    def finish(self, won):
        self._state = STATE_VICTORY if won else STATE_GAMEOVER
        self.timer = 0.

    def award(self, score):
        self._score += score
        self._high_score = max(self._high_score, self.score)

    def update(self, dt, down, pressed):
        if not math.isfinite(dt): return
        dt = max(0., min(.05, dt))
        down &= 255; pressed &= 255
        if self.state == STATE_PAUSED: return
        if self.state == STATE_TITLE:
            if pressed & 127: self.start()
            return
        if self.state in (STATE_VICTORY, STATE_GAMEOVER):
            self.timer += dt
            if self.timer > .5 and pressed & 127: self.start()
            return
        if pressed & KEY_START: self.pause(); return
        self.elapsed += dt
        self.repeat = max(0., self.repeat-dt)
        self.tick(dt, down, pressed)

    def direction(self, down, pressed):
        keys = pressed & 15
        if not keys and self.repeat <= 0: keys = down & 15
        if keys: self.repeat = .12
        for bit, dx, dy in ((KEY_LEFT,-1,0),(KEY_RIGHT,1,0),(KEY_UP,0,-1),(KEY_DOWN,0,1)):
            if keys & bit: return dx,dy
        return 0,0

    @staticmethod
    def px(fb,x,y,color):
        if 0<=x<16 and 0<=y<16: fb[(y*16+x)*3:(y*16+x)*3+3] = bytes(color)

    def cell(self,fb,x,y,color,scale=2,offset=2):
        for dy in range(scale):
            for dx in range(scale): self.px(fb,offset+x*scale+dx,offset+y*scale+dy,color)

    def render(self):
        if self.state in (STATE_VICTORY, STATE_GAMEOVER) and self.timer>.8:
            return ArcadeResultScreen.render(self.state==STATE_VICTORY,self.score,self._high_score,self.timer)
        fb=bytearray(768); self.draw(fb)
        if self.state==STATE_PAUSED:
            for y in range(5,10):
                self.px(fb,6,y,(255,255,255)); self.px(fb,9,y,(255,255,255))
        return fb

    def get_status(self):
        return dict(game_id=self.game_id,score=self.score,high_score=self._high_score,
                    lives=0 if self.state==STATE_GAMEOVER else 1,state=self.state,
                    progress=max(0,min(100,self.progress())))
