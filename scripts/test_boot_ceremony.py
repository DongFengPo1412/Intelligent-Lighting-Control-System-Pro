import sys
import time
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision"))
from light_controller import get_light_controller

ctrl = get_light_controller()
print("Starting boot ceremony test...")
ctrl.run_boot_ceremony(async_mode=False)
print("Boot ceremony finished! Waiting 5s in listening mode...")
time.sleep(5.0)
ctrl.close()
print("Test completed.")
