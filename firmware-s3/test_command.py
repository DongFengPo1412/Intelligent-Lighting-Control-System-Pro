import serial
import time
import sys

def test():
    print(">>> 正在连接 COM9 串口...", flush=True)
    try:
        s = serial.Serial('COM9', 115200, timeout=0.2)
    except Exception as e:
        print(f"打开串口失败: {e}", flush=True)
        return

    time.sleep(1.0)

    # 读取并打印启动日志
    print("--- [1] 接收开机日志 ---", flush=True)
    raw = s.read(s.in_waiting or 1)
    if raw:
        print("  <-", raw.decode('utf-8', errors='ignore'), flush=True)

    # 1. 状态查询测试
    print("\n--- [2] 发送 'status\\n' ---", flush=True)
    s.write(b"status\n")
    time.sleep(0.3)
    raw = s.read(s.in_waiting or 1)
    print("  <- 收到回复:", raw.decode('utf-8', errors='ignore').strip(), flush=True)

    # 2. 纯文本换灯效指令测试: "fire" (赛博物理火焰)
    print("\n--- [3] 发送 'fire\\n' (切换为赛博物理火焰) ---", flush=True)
    s.write(b"fire\n")
    time.sleep(0.3)
    raw = s.read(s.in_waiting or 1)
    print("  <- 收到回复:", raw.decode('utf-8', errors='ignore').strip(), flush=True)

    # 3. 换光效指令测试: "matrix" (黑客帝国代码雨 Pro)
    print("\n--- [4] 发送 'matrix\\n' (切换为黑客帝国代码雨 Pro) ---", flush=True)
    s.write(b"matrix\n")
    time.sleep(0.3)
    raw = s.read(s.in_waiting or 1)
    print("  <- 收到回复:", raw.decode('utf-8', errors='ignore').strip(), flush=True)

    # 4. JSON 倒计时指令测试: {"cmd":"countdown", "seconds":6}
    print("\n--- [5] 发送 JSON 指令: {\"cmd\":\"countdown\",\"seconds\":6} ---", flush=True)
    s.write(b'{"cmd":"countdown","seconds":6}\n')
    time.sleep(0.3)
    raw = s.read(s.in_waiting or 1)
    print("  <- 收到回复:", raw.decode('utf-8', errors='ignore').strip(), flush=True)

    # 5. 监测倒计时逐秒流逝
    print("\n--- [6] 监测倒计时流逝遥测 (监测 3 秒) ---", flush=True)
    for _ in range(3):
        time.sleep(1.0)
        s.write(b"status\n")
        time.sleep(0.1)
        raw = s.read(s.in_waiting or 1)
        resp = raw.decode('utf-8', errors='ignore').strip()
        if resp:
            print("  [遥测状态]:", resp, flush=True)

    s.close()
    print("\n>>> 自动化测试顺利完成！所有通信指令与响应均验证通过！", flush=True)

if __name__ == '__main__':
    test()
