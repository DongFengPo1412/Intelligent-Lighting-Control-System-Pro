"""Opt-in physical test: Wi-Fi commands, countdown retry safety and COM9 microphone.

Run with the web server stopped. This changes modes briefly, plays one beep,
samples the onboard mic, then restores the Kurisu pet and disables mic streaming.
"""
import array
import json
from pathlib import Path
import sys
import time
import threading
import uuid

import serial

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'pc-agent-vision'))
from wifi_gateway import WiFiGateway


def run():
    ser = serial.Serial('COM9', 115200, timeout=.1)
    chunks = []
    reading = threading.Event()
    reading.set()
    def read_serial():
        while reading.is_set():
            try:
                data = ser.read(ser.in_waiting or 1)
                if data:
                    chunks.append(data)
            except serial.SerialException:
                break
    reader = threading.Thread(target=read_serial, daemon=True)
    reader.start()
    gw = WiFiGateway()
    results = []
    def check(name, condition, detail=None):
        results.append({'test': name, 'passed': bool(condition), 'detail': detail})
        print(json.dumps(results[-1], ensure_ascii=False), flush=True)
        if not condition:
            raise AssertionError(name)
    def command(text, expected=True, **kwargs):
        ok = gw.send_command(text, **kwargs)
        check(text, ok == expected, dict(gw.last_result))
        return dict(gw.last_result)
    try:
        deadline = time.monotonic() + 30
        while not gw.is_online() and time.monotonic() < deadline:
            gw.send_command('{"cmd":"status"}', timeout=.3, retries=0)
            time.sleep(.1)
        check('Wi-Fi discovery', gw.is_online(), gw.get_status())
        command('{"cmd":"status"}')
        if '--silent' in sys.argv:
            command('{"cmd":"volume","val":0}')
        for mode in sorted(set(range(26)) - {18, 25}):
            state = command(json.dumps({'cmd': 'mode', 'val': mode}))
            check(f'board mode {mode}', state['mode'] == mode)
            time.sleep(.25)
        for text in ('not_a_command', '{"cmd":"mode","val":18}',
                     '{"cmd":"countdown","seconds":-1}', '{"cmd":"brightness","val":999}',
                     '{"cmd":"board_led","mode":"invalid"}',
                     '{"cmd":"game","name":"tetris","action":"invalid"}'):
            command(text, expected=False)
        rid = uuid.uuid4().hex
        command('{"cmd":"countdown","seconds":6}', request_id=rid)
        time.sleep(2.1)
        command('{"cmd":"countdown","seconds":6}', request_id=rid)
        status = command('{"cmd":"status"}')
        check('duplicate does not restart timer', 0 < status['countdown_remaining'] <= 4, status)
        command('{"cmd":"mode","val":1}', expected=False, request_id=rid)
        check('conflicting ID rejected', gw.last_result.get('error') == 'request_id_conflict')
        time.sleep(4.2)
        status = command('{"cmd":"status"}')
        check('countdown reaches zero', status['countdown_remaining'] == 0, status)
        # The existing display intentionally plays a 1.5 s completion animation.
        deadline = time.monotonic() + 2.5
        while status['countdown_active'] and time.monotonic() < deadline:
            time.sleep(.3)
            status = command('{"cmd":"status"}')
        check('countdown completes', not status['countdown_active'], status)
        command('{"cmd":"beep"}')
        first_chunk = len(chunks)
        command('{"cmd":"mic","enable":true}')
        time.sleep(2)
        command('{"cmd":"mic","enable":false}')
        raw = bytearray(b''.join(chunks[first_chunk:]))
        packets = 0
        samples = array.array('h')
        while True:
            pos = raw.find(b'\x55\xaa')
            if pos < 0 or len(raw) < pos + 4:
                break
            size = int.from_bytes(raw[pos+2:pos+4], 'big')
            if not 0 < size <= 2048 or size % 2:
                del raw[:pos+2]
                continue
            if len(raw) < pos+4+size:
                break
            samples.frombytes(bytes(raw[pos+4:pos+4+size]))
            packets += 1
            del raw[:pos+4+size]
        check('onboard microphone PCM frames', packets >= 30,
              {'packets': packets, 'samples': len(samples), 'peak': max(map(abs, samples), default=0)})
        return results
    finally:
        gw.send_command('{"cmd":"stop_countdown"}')
        gw.send_command('{"cmd":"mode","val":17}')
        gw.send_command('{"cmd":"board_led","mode":"listening"}')
        gw.send_command('{"cmd":"mic","enable":false}')
        if '--silent' in sys.argv:
            gw.send_command('{"cmd":"volume","val":70}')
        gw.close()
        reading.clear()
        reader.join(1)
        ser.close()
        text = b''.join(chunks).decode('utf-8', errors='replace')
        serial_log = Path(__file__).resolve().parents[1] / 'firmware-s3' / 'build' / 'hardware_test_serial.log'
        serial_log.write_bytes(b''.join(chunks))
        check('no panic or brownout', not any(word in text.lower() for word in
              ('guru meditation', 'stack canary', 'stack overflow', 'brownout detector', 'rebooting...', 'corrupted')))


if __name__ == '__main__':
    result = run()
    print(f'PASS: {len(result)} physical checks', flush=True)
