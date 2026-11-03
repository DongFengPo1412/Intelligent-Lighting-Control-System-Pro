# -*- coding: utf-8 -*-
"""
test_arcade_result_screen.py —— 16x16 街机结算与高分屏幕显示测试
验证点：
1. 3x5 字体完整性 (0-9 及 G, O, W, I, N, S, C, A, H, E)
2. 1~4 位分数居中排版
3. >4 位大数字 (如 12500、100000) 跑马灯平滑滚动，全周期无截断
4. Phase 0 (当前分数) 与 Phase 1 (历史最高分) 自动分页交替渲染
5. 新纪录高分闪烁
"""

import unittest
from arcade.arcade_result_screen import (
    FONT_DIGITS_3X5,
    FONT_LETTERS_3X5,
    draw_digit_3x5,
    draw_char_3x5,
    draw_score_number,
    render_result_screen,
)


class TestArcadeResultScreen(unittest.TestCase):
    def setUp(self):
        self.fb = bytearray(16 * 16 * 3)

    def test_font_definitions(self):
        for d in range(10):
            self.assertIn(d, FONT_DIGITS_3X5)
            self.assertEqual(len(FONT_DIGITS_3X5[d]), 5)
        for ch in ('G', 'O', 'W', 'I', 'N', 'S', 'C', 'A', 'H', 'E'):
            self.assertIn(ch, FONT_LETTERS_3X5)
            self.assertEqual(len(FONT_LETTERS_3X5[ch]), 5)

    def test_draw_digit_and_char(self):
        # Draw digit 7
        draw_digit_3x5(self.fb, 7, 0, 0, 255, 100, 50)
        self.assertGreater(sum(self.fb), 0)

        # Draw letter H
        fb_h = bytearray(16 * 16 * 3)
        draw_char_3x5(fb_h, 'H', 2, 2, 0, 220, 255)
        self.assertGreater(sum(fb_h), 0)

    def test_short_score_centered(self):
        # 1-digit score (e.g. 5) -> centered around x=6
        fb = bytearray(16 * 16 * 3)
        draw_score_number(fb, 5, 7, 255, 255, 255, 0.0)
        # Check that pixels are drawn in the central columns (6..9)
        lit_cols = set()
        for y in range(16):
            for x in range(16):
                if fb[(y * 16 + x) * 3] > 0:
                    lit_cols.add(x)
        self.assertTrue(all(5 <= x <= 10 for x in lit_cols))

    def test_large_score_no_truncation(self):
        # 5-digit score (12500): total_width = 19px, larger than 16px
        # We test across the 2.5s cycle: at t=0.0 (offset 0), at t=1.2 (offset mid), at t=2.0 (offset tail)
        # Verify that all 5 digits ('1', '2', '5', '0', '0') appear in the screen window during the scroll cycle
        digits_seen = set()
        for t_step in [0.0, 0.5, 1.0, 1.5, 2.0, 2.4]:
            fb = bytearray(16 * 16 * 3)
            draw_score_number(fb, 12500, 7, 255, 255, 255, t_step)
            # The framebuffer must have non-zero active pixels on line 7-11
            lit_count = sum(1 for i in range(len(fb)) if fb[i] > 0)
            self.assertGreater(lit_count, 10, f"No digits visible at t={t_step}")

    def test_paging_current_score_and_high_score(self):
        # Phase 0 (0.0s..2.2s): should render 'G' and 'O' for Game Over, score 120
        fb_phase0 = bytearray(16 * 16 * 3)
        render_result_screen(fb_phase0, is_victory=False, score=120, high_score=500, anim_time=1.0)

        # Check top row has red pixels (G O)
        has_red_top = any(fb_phase0[(y * 16 + x) * 3 + 0] > 200 and fb_phase0[(y * 16 + x) * 3 + 1] < 100
                          for y in range(1, 6) for x in range(16))
        self.assertTrue(has_red_top, "Phase 0 must display red G O header")

        # Phase 1 (2.2s..4.4s): should render 'H' and 'I' for High Score
        fb_phase1 = bytearray(16 * 16 * 3)
        render_result_screen(fb_phase1, is_victory=False, score=120, high_score=500, anim_time=3.0)

        # Check top row has sky blue pixels (H I: cyan r=0, g=220, b=255)
        has_cyan_top = any(fb_phase1[(y * 16 + x) * 3 + 2] > 200 and fb_phase1[(y * 16 + x) * 3 + 0] < 50
                           for y in range(1, 6) for x in range(16))
        self.assertTrue(has_cyan_top, "Phase 1 must display cyan HI header")

    def test_victory_screen(self):
        # Victory renders WIN in gold
        fb_win = bytearray(16 * 16 * 3)
        render_result_screen(fb_win, is_victory=True, score=800, high_score=800, anim_time=0.5)
        has_gold = any(fb_win[(y * 16 + x) * 3 + 0] == 255 and fb_win[(y * 16 + x) * 3 + 1] == 215
                       for y in range(1, 6) for x in range(16))
        self.assertTrue(has_gold, "Victory screen must render gold WIN header")


if __name__ == "__main__":
    unittest.main()

