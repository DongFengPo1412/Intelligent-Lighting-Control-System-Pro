# -*- coding: utf-8 -*-
"""Unit tests for Mario 16x16 Game Engine (C++ core loaded via mario16.dll)."""

import os
import ctypes
import unittest
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DLL_PATH = ROOT / "pc-agent-vision" / "mario16.dll"

KEY_LEFT   = 1 << 0
KEY_RIGHT  = 1 << 1
KEY_UP     = 1 << 2
KEY_DOWN   = 1 << 3
KEY_A      = 1 << 4   # Jump
KEY_B      = 1 << 5   # Run
KEY_START  = 1 << 6   # Pause / Start
KEY_SELECT = 1 << 7


class TestMarioGame(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.has_dll = DLL_PATH.is_file()
        if cls.has_dll:
            cls.dll = ctypes.CDLL(str(DLL_PATH))
            cls.dll.mario_create.restype = ctypes.c_void_p
            cls.dll.mario_destroy.argtypes = [ctypes.c_void_p]
            cls.dll.mario_reset.argtypes = [ctypes.c_void_p]
            cls.dll.mario_update.argtypes = [ctypes.c_void_p, ctypes.c_float, ctypes.c_uint16, ctypes.c_uint16]
            cls.dll.mario_render.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
            cls.dll.mario_get_status.argtypes = [
                ctypes.c_void_p,
                ctypes.POINTER(ctypes.c_uint16),
                ctypes.POINTER(ctypes.c_uint8),
                ctypes.POINTER(ctypes.c_uint8),
                ctypes.POINTER(ctypes.c_uint8),
                ctypes.POINTER(ctypes.c_uint8),
            ]

    def _get_status(self, game):
        score = ctypes.c_uint16()
        lives = ctypes.c_uint8()
        coins = ctypes.c_uint8()
        state = ctypes.c_uint8()
        prog = ctypes.c_uint8()
        self.dll.mario_get_status(
            game,
            ctypes.byref(score),
            ctypes.byref(lives),
            ctypes.byref(coins),
            ctypes.byref(state),
            ctypes.byref(prog)
        )
        return dict(score=score.value, lives=lives.value, coins=coins.value, state=state.value, progress=prog.value)

    def test_01_dll_exists(self):
        self.assertTrue(self.has_dll, f"mario16.dll must exist at {DLL_PATH}")

    def test_02_initial_state_is_title(self):
        game = self.dll.mario_create()
        try:
            st = self._get_status(game)
            self.assertEqual(st["state"], 0)  # ST_TITLE
            self.assertEqual(st["lives"], 3)
            self.assertEqual(st["coins"], 0)
            self.assertEqual(st["score"], 0)
        finally:
            self.dll.mario_destroy(game)

    def test_03_render_produces_valid_pixel_buffer(self):
        game = self.dll.mario_create()
        try:
            buf = np.zeros((16, 16, 3), dtype=np.uint8)
            self.dll.mario_render(game, buf.ctypes.data_as(ctypes.c_char_p))
            # Title screen marquee renders text pixels with non-zero color
            self.assertGreater(int(buf.max()), 100)
            self.assertEqual(buf.shape, (16, 16, 3))
        finally:
            self.dll.mario_destroy(game)

    def test_04_start_and_transition_to_play(self):
        game = self.dll.mario_create()
        try:
            # Press A in TITLE to transition to READY (1)
            self.dll.mario_update(game, 0.02, KEY_A, KEY_A)
            st = self._get_status(game)
            self.assertEqual(st["state"], 1)  # ST_READY

            # Advance past ready delay (1.7 seconds @ 0.02s/frame = 86 frames)
            for _ in range(90):
                self.dll.mario_update(game, 0.02, 0, 0)

            st = self._get_status(game)
            self.assertEqual(st["state"], 2)  # ST_PLAY
        finally:
            self.dll.mario_destroy(game)

    def test_05_player_movement_advances_progress(self):
        game = self.dll.mario_create()
        try:
            # Start game
            self.dll.mario_update(game, 0.02, KEY_START, KEY_START)
            for _ in range(90):
                self.dll.mario_update(game, 0.02, 0, 0)
            st_start = self._get_status(game)
            self.assertEqual(st_start["state"], 2)

            # Hold RIGHT for 1.5 seconds (75 frames)
            for _ in range(75):
                self.dll.mario_update(game, 0.02, KEY_RIGHT, 0)

            st_moved = self._get_status(game)
            self.assertGreater(st_moved["progress"], st_start["progress"])
        finally:
            self.dll.mario_destroy(game)

    def test_06_pause_and_resume(self):
        game = self.dll.mario_create()
        try:
            # Start and enter PLAY
            self.dll.mario_update(game, 0.02, KEY_START, KEY_START)
            for _ in range(90):
                self.dll.mario_update(game, 0.02, 0, 0)
            self.assertEqual(self._get_status(game)["state"], 2)

            # Press START to pause
            self.dll.mario_update(game, 0.02, KEY_START, KEY_START)
            self.assertEqual(self._get_status(game)["state"], 3)  # ST_PAUSE

            # Press START again to resume
            self.dll.mario_update(game, 0.02, KEY_START, KEY_START)
            self.assertEqual(self._get_status(game)["state"], 2)  # ST_PLAY
        finally:
            self.dll.mario_destroy(game)

    def test_07_level_map_header_exists_and_valid(self):
        level_h = ROOT / "firmware-s3" / "main" / "display" / "mario_level.h"
        self.assertTrue(level_h.is_file(), "mario_level.h must exist in firmware-s3/main/display")
        content = level_h.read_text(encoding="utf-8")
        self.assertIn("#define LEVEL_W 96", content)
        self.assertIn("#define LEVEL_H 16", content)
        self.assertIn("LEVEL_MAP", content)
        self.assertIn("S", content)  # Spawn point
        self.assertIn("F", content)  # Flag pole


if __name__ == "__main__":
    unittest.main()
