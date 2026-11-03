# -*- coding: utf-8 -*-
import sys
import unittest
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "pc-agent-vision"))

loader = unittest.TestLoader()
suite = loader.discover(start_dir=str(ROOT / "tests"), pattern="test_arcade_*.py")

# Also add test_mario_game.py
mario_suite = loader.discover(start_dir=str(ROOT / "tests"), pattern="test_mario_game.py")
suite.addTests(mario_suite)

print(f"Total test cases discovered: {suite.countTestCases()}")

t0 = time.time()
runner = unittest.TextTestRunner(verbosity=1)
result = runner.run(suite)
dt = time.time() - t0

print(f"\nExecution finished in {dt:.3f}s")
print(f"Tests run: {result.testsRun}, Failures: {len(result.failures)}, Errors: {len(result.errors)}")
if result.wasSuccessful():
    print("ALL TESTS PASSED! (100% pass rate)")
else:
    print("SOME TESTS FAILED!")
    sys.exit(1)

