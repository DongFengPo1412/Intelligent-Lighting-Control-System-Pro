"""Bounded drawing/math primitives. Individual cartridges own all game rules."""
import math
from .batch_cartridge import BatchCartridge
from .base_cartridge import *

def clamp(v,lo,hi):return max(lo,min(hi,v))
def wrap(v):return v%(2*math.pi)
def angle_distance(a,b):return abs((a-b+math.pi)%(2*math.pi)-math.pi)
def rng(seed):return (seed*1664525+1013904223)&0xffffffff
def line(fb,x0,y0,x1,y1,color):
    x0,y0,x1,y1=map(int,(x0,y0,x1,y1));dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;error=dx+dy
    while True:
        BatchCartridge.px(fb,x0,y0,color)
        if (x0,y0)==(x1,y1):break
        e=2*error
        if e>=dy:error+=dy;x0+=sx
        if e<=dx:error+=dx;y0+=sy
def disc(fb,x,y,radius,color):
    for yy in range(16):
        for xx in range(16):
            if (xx-x)**2+(yy-y)**2<=radius**2:BatchCartridge.px(fb,xx,yy,color)
