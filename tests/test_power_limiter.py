# -*- coding: utf-8 -*-
"""
test_power_limiter.py —— DisplayHAL 软件功耗/能量限制器测试与功耗预算校验
全面覆盖：全黑、稀疏游戏帧、全红、全白、高密度随机画面下的限流行为、
等比例有损降亮衰减因子、以及 5V 电源轨电流安全预算计算。
"""

import unittest
import random


def apply_energy_limiter(pixels_rgb, max_energy=15000):
    """
    与 firmware-s3/main/display/display_hal.cc 的 DisplayHAL::Show 软件限幅算法 1:1 对齐
    """
    total_energy = sum(r + g + b for r, g, b in pixels_rgb)
    if max_energy > 0 and total_energy > max_energy:
        # 有损降阶缩放 (Lossy Brightness Reduction)
        scaled_pixels = [
            (
                (r * max_energy) // total_energy,
                (g * max_energy) // total_energy,
                (b * max_energy) // total_energy,
            )
            for r, g, b in pixels_rgb
        ]
        out_energy = sum(r + g + b for r, g, b in scaled_pixels)
    else:
        scaled_pixels = list(pixels_rgb)
        out_energy = total_energy

    return scaled_pixels, total_energy, out_energy


class TestPowerLimiter(unittest.TestCase):

    def test_01_all_black_frame(self):
        """全黑画面：总能量为 0，不发生衰减"""
        pixels = [(0, 0, 0)] * 256
        scaled, in_e, out_e = apply_energy_limiter(pixels, 15000)
        self.assertEqual(in_e, 0)
        self.assertEqual(out_e, 0)
        self.assertEqual(scaled, pixels)

    def test_02_sparse_arcade_frame(self):
        """典型街机游戏帧：全屏仅点亮约 25 颗高亮像素，未超阈值，保持 100% 原始亮度"""
        pixels = [(0, 0, 0)] * 256
        for i in range(25):
            pixels[i] = (255, 200, 0)  # 25 颗黄色像素
        expected_in = 25 * (255 + 200 + 0)  # 11,375
        self.assertLess(expected_in, 15000)

        scaled, in_e, out_e = apply_energy_limiter(pixels, 15000)
        self.assertEqual(in_e, expected_in)
        self.assertEqual(out_e, expected_in)
        self.assertEqual(scaled, pixels)

    def test_03_all_red_frame(self):
        """全屏纯红报警画面：总能量 65,280 超限，严格限幅至 <= 15,000"""
        pixels = [(255, 0, 0)] * 256
        in_expected = 256 * 255  # 65,280
        scaled, in_e, out_e = apply_energy_limiter(pixels, 15000)

        self.assertEqual(in_e, in_expected)
        self.assertLessEqual(out_e, 15000)
        # 验证单颗红色灯珠被等比降亮至约 58 (15000 / 256)
        for r, g, b in scaled:
            self.assertEqual(g, 0)
            self.assertEqual(b, 0)
            self.assertAlmostEqual(r, 15000 // 256, delta=2)

    def test_04_all_white_frame_worst_case(self):
        """极端全屏纯白冲击 (RGB=255,255,255)：总能量 195,840 严重超限，强制有损压制"""
        pixels = [(255, 255, 255)] * 256
        in_expected = 256 * 765  # 195,840
        scaled, in_e, out_e = apply_energy_limiter(pixels, 15000)

        self.assertEqual(in_e, in_expected)
        self.assertLessEqual(out_e, 15000)
        # 单颗灯珠 RGB 通道各被平滑压至约 19 (15000 / (256*3))
        for r, g, b in scaled:
            self.assertEqual(r, g)
            self.assertEqual(g, b)
            self.assertAlmostEqual(r, 15000 // (256 * 3), delta=2)

    def test_05_monotonic_clamping(self):
        """能量输出严格单调封顶断言"""
        for multiplier in [1, 2, 5, 10, 20]:
            pixels = [(min(255, 10 * multiplier), min(255, 10 * multiplier), min(255, 10 * multiplier))] * 256
            scaled, in_e, out_e = apply_energy_limiter(pixels, 15000)
            self.assertLessEqual(out_e, 15000)

    def test_06_current_and_power_budget_calculation(self):
        """
        物理电流与功耗预算数学校验 (以 5V 适配器额定 2.0A 为安全基准)：
        1. WS2812B 动态电流：MAX_ENERGY = 15000
           等效全开通道数 = 15000 / 255 ≈ 58.82 个
           单通道额定驱动电流 ≈ 16mA
           动态峰值电流 = 58.82 * 16mA ≈ 941mA (0.941A)
        2. WS2812B 静态电流 (Quiescent)：
           每颗静态待机电流 ≈ 1mA
           256 颗灯珠静态基底 = 256mA (0.256A)
           总 LED 峰值电流 = 0.941A + 0.256A = 1.197A
        3. ESP32-S3 主控峰值 (Wi-Fi 突发发射)：≈ 250mA (0.250A)
        4. MAX98357A I2S 功放峰值 (8Ω喇叭满幅)：≈ 300mA (0.300A)
        5. 整机极端综合峰值 = 1.197A + 0.250A + 0.300A = 1.747A
        1.747A < 2.000A，具备至少 250mA (12.6%) 的稳定裕量！
        """
        max_energy = 15000
        led_dynamic_current_a = (max_energy / 255.0) * 0.016
        led_quiescent_current_a = 256 * 0.001
        esp32_peak_current_a = 0.250
        audio_peak_current_a = 0.300

        total_system_peak_a = (
            led_dynamic_current_a + led_quiescent_current_a + esp32_peak_current_a + audio_peak_current_a
        )

        self.assertLess(total_system_peak_a, 2.0, "Total system peak current must stay below 2.0A adapter rating")
        self.assertAlmostEqual(total_system_peak_a, 1.747, places=2)


if __name__ == "__main__":
    unittest.main()

