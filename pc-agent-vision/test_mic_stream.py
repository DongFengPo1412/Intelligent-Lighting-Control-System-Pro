import time
from light_controller import get_light_controller

ctrl = get_light_controller()
count = 0
total_bytes = 0

def on_mic(b):
    global count, total_bytes
    count += 1
    total_bytes += len(b)

ctrl.on_mic_data = on_mic
print("Enabling mic streaming on ESP32-S3...")
ctrl.enable_mic(True)

# 监听 2 秒
time.sleep(2.0)

print("Disabling mic streaming...")
ctrl.enable_mic(False)
time.sleep(0.5)

print(f"Result: Successfully received {count} mic frames ({total_bytes} bytes) from INMP441!")
ctrl.close()
