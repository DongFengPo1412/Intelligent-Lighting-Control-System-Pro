"""Same integer time contract as arcade_clock.h; no real sleeping in tests."""
import math

class FixedStepClock:
    STEP_US=16667
    MAX_STEPS=4
    def __init__(self):
        self.remainder=0
        self.dropped_us=0
        self.steps=0
    def reset(self):self.remainder=0
    def advance(self,elapsed,update):
        if not math.isfinite(elapsed) or elapsed<0:
            self.reset();return 0
        self.remainder+=round(elapsed*1_000_000)
        count=0
        while self.remainder>=self.STEP_US and count<self.MAX_STEPS:
            update(self.STEP_US/1_000_000)
            self.remainder-=self.STEP_US;count+=1;self.steps+=1
        drop=self.remainder-self.remainder%self.STEP_US
        self.dropped_us+=drop;self.remainder-=drop
        return count
