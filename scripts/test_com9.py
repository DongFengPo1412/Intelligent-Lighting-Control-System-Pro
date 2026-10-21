import serial
import time

try:
    s = serial.Serial('COM9', 115200, timeout=1.0)
    print("Port COM9 opened successfully!")
    s.write(b'{"cmd":"status"}\n')
    time.sleep(0.3)
    resp = s.read(s.in_waiting or 100)
    print("Response:", resp.decode('utf-8', errors='ignore'))
    s.close()
except Exception as e:
    print("Failed:", e)
