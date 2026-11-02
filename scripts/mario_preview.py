#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
preview.py —— 把 mario_level.h 里的字符画关卡渲染成 PNG 预览图。

    python tools/preview.py

产物在 docs/ 下。渲染规则与固件 mario_game.cpp 里的配色基本一致，
方便在没有灯板的时候先看看关卡好不好看、好不好过。
"""

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
HEADER = ROOT / "firmware-s3" / "main" / "display" / "mario_level.h"
OUT_DIR = ROOT / "docs" / "images" / "mario16"

SCALE = 24
GRID = True

SKY = (0, 6, 18)
SKY_TOP = (0, 3, 10)
GRASS = (0, 95, 20)
DIRT = (60, 36, 9)
BRICK = (150, 85, 15)
BRICK2 = (175, 108, 30)
PIPE = (0, 195, 55)
PIPE_DARK = (0, 85, 28)
COIN = (255, 190, 10)
CAP = (235, 20, 20)
SKIN = (255, 190, 130)
OVERALL = (30, 60, 235)
GOOMBA = (160, 95, 30)
GOOMBA_FOOT = (80, 45, 10)
FLAG_POLE = (200, 200, 200)
FLAG = (0, 220, 90)


def parse_level():
    text = HEADER.read_text(encoding="utf-8")
    rows = re.findall(r'"([^"\\]*)\\n"', text)
    assert rows, "没找到关卡字符串"
    width = len(rows[0])
    for i, r in enumerate(rows):
        assert len(r) == width, "第 %d 行长度 %d != %d" % (i, len(r), width)
    return [list(r) for r in rows]


def font(size):
    for name in ("msyh.ttc", "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def render(level, cam, player=None, enemies=(), coin_phase=0):
    h = len(level)
    w = len(level[0])
    img = Image.new("RGB", (16, 16), SKY)
    px = img.load()

    # 天空渐变
    for y in range(16):
        t = y / 15.0
        px[0, y] = (
            int(SKY_TOP[0] + (SKY[0] - SKY_TOP[0]) * t),
            int(SKY_TOP[1] + (SKY[1] - SKY_TOP[1]) * t),
            int(SKY_TOP[2] + (SKY[2] - SKY_TOP[2]) * t),
        )
    for y in range(16):
        for x in range(16):
            px[x, y] = px[0, y]

    # 地形
    for sy in range(h):
        for sx in range(16):
            wx = cam + sx
            if wx < 0 or wx >= w:
                continue
            ch = level[sy][wx]
            if ch == "#":
                px[sx, sy] = GRASS if sy == 14 else DIRT
            elif ch == "=":
                px[sx, sy] = BRICK if (sx + sy) % 3 else BRICK2
            elif ch == "p":
                left_pipe = wx > 0 and level[sy][wx - 1] == "p"
                px[sx, sy] = PIPE if left_pipe else PIPE_DARK
            elif ch == "o":
                c = COIN if (coin_phase + sx) % 6 < 4 else (255, 140, 0)
                px[sx, sy] = c
            elif ch == "F":
                px[sx, sy] = FLAG_POLE

    # 旗面（和固件一致：杆顶右上方 2x2 绿旗）
    for sy in range(h):
        for sx in range(16):
            wx = cam + sx
            if 0 <= wx < w and level[sy][wx] == "F" and sy == 6:
                for dx in (1, 2):
                    for dy in (0, 1):
                        if 0 <= sx + dx < 16:
                            px[sx + dx, sy + dy] = FLAG
                break

    # 板栗仔
    for (ex, ey, alive) in enemies:
        for dy in range(2):
            for dx in range(2):
                x = int(ex) - cam + dx
                y = int(ey) + dy
                if 0 <= x < 16 and 0 <= y < 16:
                    px[x, y] = GOOMBA if dy == 0 else GOOMBA_FOOT

    # 马里奥 2x3
    if player is not None:
        mx, my = player
        sprite = ((CAP, CAP), (SKIN, CAP), (OVERALL, OVERALL))
        for dy, row in enumerate(sprite):
            for dx, c in enumerate(row):
                x = int(mx) - cam + dx
                y = int(my) + dy
                if 0 <= x < 16 and 0 <= y < 16:
                    px[x, y] = c

    out = Image.new("RGB", (16 * SCALE, 16 * SCALE), (0, 0, 0))
    big = img.resize((16 * SCALE, 16 * SCALE), Image.NEAREST)
    out.paste(big, (0, 0))

    if GRID:
        d = ImageDraw.Draw(out)
        for i in range(17):
            d.line([(i * SCALE, 0), (i * SCALE, 16 * SCALE)], fill=(12, 12, 12))
            d.line([(0, i * SCALE), (16 * SCALE, i * SCALE)], fill=(12, 12, 12))
    return out


def main():
    OUT_DIR.mkdir(exist_ok=True)
    level = parse_level()
    f = font(20)
    f2 = font(14)

    scenes = [
        ("preview_start.png", 0, (2, 11), [], "起点：金币、第一个坑"),
        ("preview_platform.png", 24, (32, 7), [(27, 12, True)], "砖台与板栗仔（跳跃中）"),
        ("preview_pipes.png", 50, (52, 7), [(62, 12, True)], "两根水管、第二个坑"),
        ("preview_goal.png", 80, (85, 9), [], "台阶与终点旗杆"),
    ]

    for name, cam, player, enemies, caption in scenes:
        img = render(level, cam, player, enemies, coin_phase=2)
        canvas = Image.new("RGB", (img.width, img.height + 46), (16, 16, 16))
        canvas.paste(img, (0, 0))
        d = ImageDraw.Draw(canvas)
        d.text((8, img.height + 6), caption, fill=(230, 230, 230), font=f)
        d.text((8, img.height + 27), "16x16 WS2812  |  camera x=%d" % cam, fill=(120, 120, 120), font=f2)
        canvas.save(OUT_DIR / name)
        print("wrote", OUT_DIR / name)


if __name__ == "__main__":
    main()
