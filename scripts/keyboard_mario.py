#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
keyboard_serial.py —— 用电脑键盘 + USB 串口玩 16x16 马里奥（手机不在手边时调试用）

    pip install pyserial
    python tools/keyboard_serial.py --list
    python tools/keyboard_serial.py --port COM5
    python tools/keyboard_serial.py            # 自动找串口
    python tools/keyboard_serial.py --json     # 改发 JSON，测试固件的 JSON 解析

按键：
    A / D 或 ← / →        左右移动
    空格 / J              跳跃（A 键）
    左Shift / K           加速跑（B 键）
    Enter                 开始 / 暂停
    R                     重开
    T                     灯板测试
    Esc                   退出

也可以和项目里现成的 light_controller 一起用（和 finger_tip_stream.py 一致的发送方式）：
    python tools/keyboard_serial.py --controller
"""

import argparse
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

KEY_CODES = {
    "a": "L",  # 左
    "d": "R",  # 右
    "w": "U",  # 上（跳）
    "s": "D",  # 下（快速下落）
    " ": "A",  # 跳
    "j": "A",
    "k": "B",  # 跑
}

CODE_NAMES = {
    "L": "left", "R": "right", "U": "up", "D": "down",
    "A": "a", "B": "b", "S": "start", "X": "select",
}


def parse_args():
    p = argparse.ArgumentParser(description="键盘 -> 串口 -> 16x16 马里奥")
    p.add_argument("--port", help="串口，例如 COM5 或 /dev/ttyUSB0")
    p.add_argument("--baud", type=int, default=115200)
    p.add_argument("--json", action="store_true", help="用 JSON 命令而不是短命令")
    p.add_argument("--controller", action="store_true", help="改用 light_controller 发送")
    p.add_argument("--list", action="store_true", help="列出可用串口")
    return p.parse_args()


def list_ports():
    try:
        from serial.tools import list_ports as lp
    except ImportError:
        print("需要 pyserial：pip install pyserial")
        return
    ports = list(lp.comports())
    for p in ports:
        print("  %-12s %s" % (p.device, p.description))
    if not ports:
        print("  没有找到串口")


class SerialLink:
    def __init__(self, port, baud):
        import serial

        self.ser = serial.Serial(port, baud, timeout=0)
        time.sleep(0.3)
        self.ser.reset_input_buffer()

    def send_line(self, line):
        self.ser.write((line + "\n").encode("ascii"))

    def send_key(self, code, down):
        self.send_line("%s%d" % (code, 1 if down else 0))

    def drain(self):
        if not self.ser.in_waiting:
            return
        data = self.ser.read(self.ser.in_waiting)
        sys.stdout.write(data.decode("utf-8", "ignore"))
        sys.stdout.flush()

    def close(self):
        self.ser.close()


class ControllerLink:
    """复用项目里 finger_tip_stream.py 用的 light_controller（可选）。"""

    def __init__(self):
        from pathlib import Path
        for parent in Path(__file__).resolve().parents:
            candidate = parent / "pc-agent-vision"
            if (candidate / "light_controller.py").is_file():
                if str(candidate) not in sys.path:
                    sys.path.insert(0, str(candidate))
                break
        from light_controller import get_light_controller

        self.ctl = get_light_controller()
        if not getattr(self.ctl, "is_connected", False):
            raise RuntimeError("light_controller 未连接串口")

    def send_line(self, line):
        self.ctl.send_json({"cmd": "raw", "line": line})

    def send_key(self, code, down):
        self.ctl.send_json({"cmd": "key", "k": CODE_NAMES[code], "v": 1 if down else 0})

    def drain(self):
        return

    def close(self):
        return


class Hold:
    """把“按住的键”维持住：键盘没有 keyup，用 150ms 内没有重复就视为松开。"""

    def __init__(self, link, timeout=0.15):
        self.link = link
        self.timeout = timeout
        self.down = {}

    def press(self, code):
        if code not in self.down:
            self.link.send_key(code, True)
            print("  [key] %s down" % CODE_NAMES.get(code, code))
        self.down[code] = time.time()

    def poll(self):
        now = time.time()
        for code, stamp in list(self.down.items()):
            if now - stamp > self.timeout:
                self.link.send_key(code, False)
                del self.down[code]

    def release_all(self):
        for code in list(self.down):
            self.link.send_key(code, False)
        self.down.clear()


def read_chars():
    """读取当前可用的输入字符（Windows 用 msvcrt，Linux/macOS 用 termios）。"""
    if sys.platform.startswith("win"):
        import msvcrt

        out = []
        while msvcrt.kbhit():
            ch = msvcrt.getwch()
            if ch in ("\x00", "\xe0"):
                out.append(msvcrt.getwch())
            else:
                out.append(ch)
        return out

    import select

    if not hasattr(read_chars, "_fd"):
        import termios
        import tty

        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        tty.setcbreak(fd)
        read_chars._fd = fd
        read_chars._old = old
    out = []
    while select.select([sys.stdin], [], [], 0)[0]:
        ch = sys.stdin.read(1)
        if not ch:
            break
        out.append(ch)
    return out


def main():
    args = parse_args()
    if args.list:
        list_ports()
        return 0

    try:
        if args.controller:
            link = ControllerLink()
            print("[kbd] 已通过 light_controller 连接")
        else:
            port = args.port
            if not port:
                from serial.tools import list_ports as lp

                cands = [p.device for p in lp.comports()]
                if not cands:
                    print("没找到串口，请用 --port 指定（--list 可查看）")
                    return 1
                port = cands[0]
                print("[kbd] 自动选择串口:", port)
            link = SerialLink(port, args.baud)
    except ImportError as e:
        print("缺少依赖：%s" % e)
        print("请先运行： pip install pyserial")
        return 1
    except Exception as e:
        print("连接失败：%s" % e)
        return 1

    print("[kbd] 已连接。A/D 或 ←/→ 移动，空格跳，Shift 跑，Enter 暂停，R 重开，Esc 退出。")
    hold = Hold(link)

    try:
        while True:
            link.drain()
            for ch in read_chars():
                if ch == "\x1b":
                    return 0
                if ch in ("\r", "\n"):
                    hold.press("S")
                    continue
                low = ch.lower()
                if low == "r":
                    link.send_line('{"cmd":"reset"}' if args.json else "#R")
                    print("  [cmd] 重开")
                    continue
                if low == "t":
                    link.send_line('{"cmd":"test"}' if args.json else "#T")
                    print("  [cmd] 灯板测试")
                    continue
                code = KEY_CODES.get(low)
                if code:
                    hold.press(code)
            hold.poll()
            time.sleep(0.01)
    except KeyboardInterrupt:
        return 0
    finally:
        try:
            hold.release_all()
            link.close()
        except Exception:
            pass
        print("\n[kbd] 已退出")


if __name__ == "__main__":
    sys.exit(main())
