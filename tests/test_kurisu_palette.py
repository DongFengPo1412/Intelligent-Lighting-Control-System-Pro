"""Check actual source-image pixels and the generated image transfer tables."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('kurisu_palette', ROOT / 'scripts/update_kurisu_sprites.py')
palette = importlib.util.module_from_spec(spec)
spec.loader.exec_module(palette)


class OriginalPaletteTests(unittest.TestCase):
    def test_colors_match_sampled_source_image(self):
        expected = {
            'BG_OFF': '000000', 'DARK_BLK': '000000', 'SOLE': '000000',
            'HR_D': '472D1E', 'HAIR': '8D4A3A', 'HR_M': '6A3621', 'HR_L': 'BA7766',
            'LASH': '341C4E', 'EYEW': 'FFFFFF', 'IRIS': '878DD7', 'EYEL': 'E1D5FD',
            'SKIN': 'FDF6F0', 'SHIRT_A': 'E0E8EE', 'SHIRT_W': 'FFFFFF',
            'TIE': 'C35449', 'COAT': 'AE7959', 'BOOT': '886754',
        }
        for name, color in expected.items():
            with self.subTest(part=name):
                self.assertEqual(bytes(getattr(palette, name)).hex().upper(), color)

    def test_checked_in_firmware_matches_generator(self):
        self.assertEqual(len(palette.grid), 16)
        self.assertTrue(all(len(row) == 16 for row in palette.grid))
        actual = (ROOT / 'firmware-s3/main/display/kurisu_sprites.h').read_text(encoding='utf-8')
        self.assertEqual(actual, palette.generate_header())

    def test_all_256_pixels_match_independent_png_sampling(self):
        rows = (ROOT / 'tests/fixtures/kurisu_design_hex.txt').read_text().splitlines()
        expected = [row.split() for row in rows]
        actual = [[bytes(pixel).hex().upper() for pixel in row] for row in palette.grid]
        self.assertEqual(actual, expected)

    def test_checked_in_transfer_matches_generator(self):
        actual = (ROOT / 'firmware-s3/main/display/srgb_transfer.h').read_text(encoding='utf-8')
        self.assertEqual(actual, palette.generate_transfer_header())

    def test_led_drive_targets_survive_output_scaling(self):
        for role, target in palette.LED_REFERENCE_PWM.items():
            actual = tuple(v * palette.LED_REFERENCE_BRIGHTNESS // 255 for v in palette.LED_PALETTE[role])
            self.assertEqual(actual, target, role)
        # Output data must not accidentally become source sRGB again.
        self.assertNotEqual(palette.LED_PALETTE['HAIR'], palette.HAIR)

    def test_visual_roles_retain_requested_contrast(self):
        p = palette.LED_REFERENCE_PWM
        self.assertGreater(p['HAIR'][0], 5 * max(p['HAIR'][1:]))
        self.assertGreater(p['HR_D'][0], p['HR_D'][1])
        self.assertGreater(p['HR_D'][1], p['HR_D'][2])
        self.assertLess(p['HR_M'][0], p['HAIR'][0])
        self.assertGreater(sum(p['HR_L']), sum(p['HR_M']))
        self.assertGreater(p['SKIN'][0], 2 * p['SKIN'][1])
        self.assertGreater(p['IRIS'][2], p['IRIS'][0])
        self.assertGreater(p['EYEL'][2], p['EYEL'][0])
        self.assertLess(sum(p['LASH']), sum(p['IRIS']))
        self.assertLess(sum(p['IRIS']), sum(p['EYEL']))
        self.assertGreater(p['COAT'][1] / p['COAT'][0], p['HAIR'][1] / p['HAIR'][0])
        self.assertEqual(p['PANTS'], p['COAT'])
        self.assertTrue(all(v > 0 for v in p['SOLE']))
        self.assertEqual(p['BG_OFF'], (0, 0, 0))
        self.assertEqual(p['TIE'][1:], (0, 0))
        self.assertGreater(p['TIE'][0], max(max(c) for role, c in p.items() if role != 'TIE'))

    def test_penultimate_row_uses_pants_matching_coat(self):
        self.assertEqual(palette.grid_roles[14][6:10], ['PANTS'] * 4)
        self.assertEqual(palette.grid_roles[15][6:10], ['SOLE'] * 4)
        self.assertEqual(palette.grid_roles[5][15], 'HR_D')

    def test_only_requested_cells_change_roles(self):
        display = palette.get_display_roles()
        changes = {(x, y) for y in range(16) for x in range(16)
                   if display[y][x] != palette.grid_roles[y][x]}
        skin = {(4, 8), (4, 9), (11, 8), (11, 9)}
        unlit = {(4, 13), (11, 13)}
        self.assertEqual(changes, skin | unlit)
        for x, y in skin:
            self.assertEqual(palette.grid_roles[y][x], 'EYEW')
            self.assertEqual(display[y][x], 'SKIN')
        for x, y in unlit:
            self.assertEqual(palette.grid_roles[y][x], 'SKIN')
            self.assertEqual(display[y][x], 'BG_OFF')

    def test_user_accepted_face_eyes_and_tie_are_preserved(self):
        accepted = {'SKIN': (12, 5, 4), 'LASH': (2, 0, 3),
                    'IRIS': (6, 2, 9), 'EYEL': (10, 5, 13), 'TIE': (20, 0, 0)}
        for role, color in accepted.items():
            self.assertEqual(palette.LED_REFERENCE_PWM[role], color, role)
        self.assertEqual(palette.LED_REFERENCE_PWM['HAIR'][1:], (0, 0))
        self.assertLess(palette.LED_REFERENCE_PWM['HAIR'][0], accepted['TIE'][0])

    def test_hair_accents_are_three_ordered_red_levels(self):
        p = palette.LED_REFERENCE_PWM
        self.assertLess(p['HR_M'][0], p['HAIR'][0])
        self.assertLess(p['HAIR'][0], p['HR_L'][0])
        self.assertLess(p['HAIR'][0], 7)
        for role in ('HAIR', 'HR_M', 'HR_L'):
            self.assertEqual(p[role][1:], (0, 0), role)

    def test_border_color_is_unique_for_calibration_mask(self):
        matches = [role for role, color in palette.LED_PALETTE.items()
                   if color == palette.LED_PALETTE['HR_D']]
        self.assertEqual(matches, ['HR_D'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
