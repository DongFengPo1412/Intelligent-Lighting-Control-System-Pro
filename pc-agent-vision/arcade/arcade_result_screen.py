# -*- coding: utf-8 -*-
"""
arcade_result_screen.py —— 统一 16x16 街机结算与成绩展示层 (Python 模拟端)
与 C++ arcade::ArcadeResultScreen 1:1 对齐
"""

import math

# 3x5 点阵字体数据 (数字 0-9)
FONT_DIGITS_3X5 = {
    0: (0b111, 0b101, 0b101, 0b101, 0b111),
    1: (0b010, 0b110, 0b010, 0b010, 0b111),
    2: (0b111, 0b001, 0b111, 0b100, 0b111),
    3: (0b111, 0b001, 0b111, 0b001, 0b111),
    4: (0b101, 0b101, 0b111, 0b001, 0b001),
    5: (0b111, 0b100, 0b111, 0b001, 0b111),
    6: (0b111, 0b100, 0b111, 0b101, 0b111),
    7: (0b111, 0b001, 0b010, 0b010, 0b010),
    8: (0b111, 0b101, 0b111, 0b101, 0b111),
    9: (0b111, 0b101, 0b111, 0b001, 0b111),
}

# 3x5 字母
FONT_LETTERS_3X5 = {
    'G': (0b111, 0b100, 0b101, 0b101, 0b111),
    'O': (0b111, 0b101, 0b101, 0b101, 0b111),
    'W': (0b101, 0b101, 0b101, 0b111, 0b101),
    'I': (0b111, 0b010, 0b010, 0b010, 0b111),
    'N': (0b101, 0b111, 0b111, 0b101, 0b101),
    'S': (0b111, 0b100, 0b111, 0b001, 0b111),
    'C': (0b111, 0b100, 0b100, 0b100, 0b111),
    'A': (0b010, 0b101, 0b111, 0b101, 0b101),
}


def set_pixel(fb: bytearray, x: int, y: int, r: int, g: int, b: int) -> None:
    if 0 <= x < 16 and 0 <= y < 16:
        idx = (y * 16 + x) * 3
        fb[idx + 0] = r
        fb[idx + 1] = g
        fb[idx + 2] = b


def draw_digit_3x5(fb: bytearray, digit: int, x: int, y: int, r: int, g: int, b: int) -> None:
    if digit not in FONT_DIGITS_3X5:
        return
    rows = FONT_DIGITS_3X5[digit]
    for row_idx, bits in enumerate(rows):
        for col_idx in range(3):
            if bits & (0b100 >> col_idx):
                set_pixel(fb, x + col_idx, y + row_idx, r, g, b)


def draw_char_3x5(fb: bytearray, ch: str, x: int, y: int, r: int, g: int, b: int) -> None:
    if ch not in FONT_LETTERS_3X5:
        return
    rows = FONT_LETTERS_3X5[ch]
    for row_idx, bits in enumerate(rows):
        for col_idx in range(3):
            if bits & (0b100 >> col_idx):
                set_pixel(fb, x + col_idx, y + row_idx, r, g, b)


def draw_score_number(fb: bytearray, score: int, y: int, r: int, g: int, b: int) -> None:
    s = str(score)
    length = len(s)
    if length <= 3:
        total_w = length * 3 + (length - 1)
        start_x = (16 - total_w) // 2
        for i, ch in enumerate(s):
            draw_digit_3x5(fb, int(ch), start_x + i * 4, y, r, g, b)
    else:
        start_x = 0
        for i, ch in enumerate(s[:4]):
            draw_digit_3x5(fb, int(ch), start_x + i * 4, y, r, g, b)


def render_result_screen(fb: bytearray, is_victory: bool, score: int, high_score: int, anim_time: float = 0.0) -> None:
    for i in range(len(fb)):
        fb[i] = 0

    if is_victory:
        # WIN
        draw_char_3x5(fb, 'W', 2, 1, 255, 215, 0)
        draw_char_3x5(fb, 'I', 6, 1, 255, 215, 0)
        draw_char_3x5(fb, 'N', 10, 1, 255, 215, 0)
    else:
        # G O
        draw_char_3x5(fb, 'G', 4, 1, 255, 30, 30)
        draw_char_3x5(fb, 'O', 9, 1, 255, 30, 30)

    # Score
    draw_score_number(fb, score, 8, 255, 190, 20)

    # Blinking restart prompt
    pulse = (math.sin(anim_time * 6.28 * 1.5) + 1.0) * 0.5
    b_val = int(pulse * 180 + 60)
    set_pixel(fb, 7, 14, 0, b_val, int(b_val * 0.8))
    set_pixel(fb, 8, 14, 0, b_val, int(b_val * 0.8))
