import os
import sys
import unittest

def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.join(root, "pc-agent-vision"))
    sys.path.insert(0, root)

    loader = unittest.defaultTestLoader
    suite = loader.discover(os.path.join(root, "tests"), pattern="test_arcade_*.py")
    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)

if __name__ == "__main__":
    main()
