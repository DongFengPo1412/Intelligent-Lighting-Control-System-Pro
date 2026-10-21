import sys
import time
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "pc-agent-vision"))
from light_controller import get_light_controller

ctrl = get_light_controller()

frame_count = 0
def on_mic(b):
    global frame_count
    frame_count += 1
    if frame_count % 10 == 1:
        print(f"Received mic frame #{frame_count}, size={len(b)}")

ctrl.on_mic_data = on_mic

print("Step 1: Playing beep FIRST...")
ctrl.play_beep()
print("Waiting 2.0s for speaker to sleep...")
time.sleep(2.0)

print("\nStep 2: Now enabling mic AFTER beep...")
ctrl.enable_mic(True)
time.sleep(3.0)
print(f"Mic frames received: {frame_count}")

ctrl.enable_mic(False)
ctrl.close()
print("Done.")
