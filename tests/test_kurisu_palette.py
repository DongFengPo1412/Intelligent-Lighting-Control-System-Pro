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


if __name__ == '__main__':
    unittest.main(verbosity=2)
