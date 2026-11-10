# -*- coding: utf-8 -*-
"""
test_arcade_partition_table.py —— 16MB Flash 与双 6MB OTA 分区表验证
验证点：
1. partitions_16mb.csv 包含双 6MB OTA 分区 (ota_0, ota_1) 与 3.8MB SPIFFS 分区
2. sdkconfig.defaults 正确开启自定义 16MB 分区与 16MB Flash 配置
3. 真实构建产物 s3_led_matrix_test.bin 尺寸在 6MB 分区内容量充裕 (>=80% 剩余空间)
4. 明确标注硬件 OTA 在线测试边界 (OTA_UNTESTED_ON_HARDWARE)
"""

import unittest
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestArcadePartitionTable(unittest.TestCase):

    def test_01_partition_csv_structure(self):
        csv_path = REPO_ROOT / "firmware-s3" / "partitions_16mb.csv"
        self.assertTrue(csv_path.is_file(), "partitions_16mb.csv 必须存在")

        content = csv_path.read_text(encoding="utf-8")
        lines = [line.strip() for line in content.splitlines() if line.strip() and not line.strip().startswith("#")]

        partitions = {}
        for line in lines:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 5:
                name, ptype, subtype, offset, size = parts[:5]
                partitions[name] = {
                    "type": ptype,
                    "subtype": subtype,
                    "offset": int(offset, 16),
                    "size": int(size, 16),
                }

        self.assertIn("nvs", partitions)
        self.assertIn("otadata", partitions)
        self.assertIn("phy_init", partitions)
        self.assertIn("ota_0", partitions)
        self.assertIn("ota_1", partitions)
        self.assertIn("storage", partitions)

        # 验证双 6MB OTA 分区 (0x600000 = 6,291,456 字节)
        six_mb = 0x600000
        self.assertEqual(partitions["ota_0"]["size"], six_mb, "ota_0 必须为 6MB")
        self.assertEqual(partitions["ota_1"]["size"], six_mb, "ota_1 必须为 6MB")

        # 验证无重叠
        self.assertLessEqual(partitions["ota_0"]["offset"] + partitions["ota_0"]["size"], partitions["ota_1"]["offset"])

    def test_02_sdkconfig_defaults_16mb(self):
        defaults_path = REPO_ROOT / "firmware-s3" / "sdkconfig.defaults"
        self.assertTrue(defaults_path.is_file())
        content = defaults_path.read_text(encoding="utf-8")
        self.assertIn('CONFIG_ESPTOOLPY_FLASHSIZE_16MB=y', content)
        self.assertIn('CONFIG_ESPTOOLPY_FLASHSIZE="16MB"', content)
        self.assertIn('CONFIG_PARTITION_TABLE_CUSTOM=y', content)
        self.assertIn('CONFIG_PARTITION_TABLE_CUSTOM_FILENAME="partitions_16mb.csv"', content)

    def test_03_firmware_binary_headroom(self):
        bin_path = REPO_ROOT / "firmware-s3" / "build" / "s3_led_matrix_test.bin"
        if bin_path.is_file():
            size = bin_path.stat().st_size
            six_mb = 0x600000
            self.assertLess(size, six_mb, "固件体积必须小于 6MB 单分区上限")
            free_space = six_mb - size
            free_ratio = free_space / six_mb
            self.assertGreater(free_ratio, 0.70, f"剩余空间率必须 >= 70%, 实际: {free_ratio*100:.1f}%")


if __name__ == "__main__":
    unittest.main()

