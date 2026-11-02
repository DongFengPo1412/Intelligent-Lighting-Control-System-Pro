#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_level.py —— 生成 16x16 灯板马里奥的关卡头文件 firmware/mario16/mario_level.h

关卡用 16 行 x 96 列的字符画描述，1 个字符 = 1 颗灯：
    '.' 空气      '#' 地面/泥土      '=' 砖块平台
    'p' 水管      'o' 金币           'g' 板栗仔（记录左上角，实体 2x2）
    'S' 出生点    'F' 旗杆

想改关卡时有两种办法：
  1) 直接手改 mario_level.h 里的字符画（每行必须正好 LEVEL_W 个字符）；
  2) 改本脚本里的 build() 再运行：  python tools/build_level.py
"""

from pathlib import Path

W, H = 96, 16
GROUND_TOP = 14          # 地面占第 14、15 行

FIRST_PIT = (22, 23)
SECOND_PIT = (58, 59)
THIRD_PIT = (68, 69)
PITS = [FIRST_PIT, SECOND_PIT, THIRD_PIT]

PIPES = [(50, 51), (55, 56)]     # 水管左列区间，占第 12、13 行
PLATFORM1 = (11, 34, 38)         # (行, 起列, 止列)
PLATFORM2 = (11, 72, 76)

COINS = [
    # 开场空中三枚
    (10, 18), (10, 19), (10, 20),
    # 第一个坑上方
    (10, 22), (10, 23),
    # 第一段砖台上方
    (9, 35), (9, 36), (9, 37),
    # 两根水管之间
    (10, 52), (10, 53), (10, 54),
    # 第三个坑上方
    (10, 68), (10, 69),
    # 第二段砖台上方
    (9, 74), (9, 75),
]

GOOMBAS = [
    (12, 27),    # 地面
    (12, 44),    # 地面
    (12, 63),    # 地面
    (9, 73),     # 站在 PLATFORM2 上（平台顶是第 11 行，2 格高的板栗仔占 9、10 行）
]

STAIRS = [
    # (行, 起列, 止列)
    (13, 82, 84),
    (12, 85, 87),
    (11, 88, 90),
]

FLAG_COL = 93
FLAG_ROWS = range(6, 14)

SPAWN = (11, 2)


def build():
    g = [["." for _ in range(W)] for _ in range(H)]

    # 地面（挖掉三个坑）
    for x in range(W):
        if any(a <= x <= b for a, b in PITS):
            continue
        for y in range(GROUND_TOP, H):
            g[y][x] = "#"

    # 砖台
    for row, x0, x1 in (PLATFORM1, PLATFORM2):
        for x in range(x0, x1 + 1):
            g[row][x] = "="

    # 水管
    for x0, x1 in PIPES:
        for x in range(x0, x1 + 1):
            for y in (12, 13):
                g[y][x] = "p"

    # 台阶（只铺到地面上沿，不要把地面换成砖色）
    for row, x0, x1 in STAIRS:
        for x in range(x0, x1 + 1):
            for y in range(row, GROUND_TOP):
                g[y][x] = "="

    # 金币
    for y, x in COINS:
        g[y][x] = "o"

    # 板栗仔标记（左上角）
    for y, x in GOOMBAS:
        g[y][x] = "g"

    # 旗杆
    for y in FLAG_ROWS:
        g[y][FLAG_COL] = "F"

    # 出生点
    sy, sx = SPAWN
    g[sy][sx] = "S"

    return ["".join(row) for row in g]


def validate(rows):
    assert len(rows) == H, "关卡必须是 16 行"
    for i, r in enumerate(rows):
        assert len(r) == W, "第 %d 行长度是 %d，应为 %d" % (i, len(r), W)

    flat = "".join(rows)
    assert flat.count("S") == 1, "出生点必须且只能有 1 个"
    assert flat.count("F") == len(FLAG_ROWS), "旗杆高度不对"
    assert flat.count("o") == len(COINS), "金币数量不对"
    assert flat.count("g") == len(GOOMBAS), "板栗仔数量不对"

    sy, sx = SPAWN
    # 出生点下方必须有地面，且 2x3 的身体空间是空的
    for y in range(sy, sy + 3):
        for x in range(sx, sx + 2):
            assert rows[y][x] in ".S", "出生点被挡住: (%d,%d)" % (x, y)
    for x in range(sx, sx + 2):
        assert rows[GROUND_TOP][x] == "#", "出生点脚下没有地面"

    # 坑的宽度提示：2 格以内普通跳跃可过，3 格需要助跑
    for a, b in PITS:
        assert b - a + 1 <= 3
    return True


def emit_header(rows):
    lines = [
        "// 本文件由 tools/build_level.py 自动生成，请勿手工修改；改关卡请改脚本或直接改字符串。",
        "#pragma once",
        "",
        "#define LEVEL_W %d" % W,
        "#define LEVEL_H %d" % H,
        "",
        "// 图例: '.' 空气  '#' 地面  '=' 砖台  'p' 水管  'o' 金币  'g' 板栗仔  'S' 出生点  'F' 旗杆",
        "static const char LEVEL_MAP[] =",
    ]
    for r in rows:
        lines.append('    "%s\\n"' % r)
    lines.append("    ;")
    lines.append("")
    return "\n".join(lines)


def main():
    rows = build()
    validate(rows)
    header = emit_header(rows)
    root = Path(__file__).resolve().parents[1]
    targets = [
        root / "firmware-s3" / "main" / "display" / "mario_level.h",
        root / "firmware-s3" / "examples" / "mario16_arduino" / "mario_level.h",
    ]
    for out in targets:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(header, encoding="utf-8")
        print("已写出 %s" % out)
    for i, r in enumerate(rows):
        print("%2d %s" % (i, r))


if __name__ == "__main__":
    main()
