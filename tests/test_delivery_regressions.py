"""Delivery contracts with fake transports/models; no device or audio access."""
import io
import json
import os
from pathlib import Path
import sys
import threading
import types
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'pc-agent-vision'))

from semantic_control import SemanticControl
from wifi_gateway import WiFiGateway


class DeliveryTests(unittest.TestCase):
    def test_full_canvas_transport_has_fragment_reassembly_enabled(self):
        gateway = WiFiGateway.__new__(WiFiGateway)
        gateway._send_lock = threading.RLock()
        gateway._pending_lock = threading.Lock()
        gateway._pending = {}
        gateway.is_running = True
        gateway.port = 8888
        gateway.get_target_ips = lambda: ['FAKE_TARGET']
        packets = []

        def send(data, address):
            packets.append(data)
            envelope = json.loads(data)
            pending = gateway._pending[envelope['request_id']]
            pending['result'] = {'status': 'ok'}
            pending['event'].set()

        gateway.sock = types.SimpleNamespace(sendto=send)
        command = json.dumps({'cmd': 'canvas', 'hex': 'ff0000' * 256}, separators=(',', ':'))
        self.assertTrue(gateway.send_command(command, timeout=0, retries=0))
        self.assertEqual(len(packets), 1)
        self.assertEqual(json.loads(json.loads(packets[0])['command'])['hex'], 'ff0000' * 256)
        self.assertGreater(len(packets[0]) + 28, 1500)
        defaults = (ROOT / 'firmware-s3/sdkconfig.defaults').read_text(encoding='utf-8')
        self.assertIn('CONFIG_LWIP_IP4_REASSEMBLY=y', defaults.splitlines())

    def test_warmup_loads_model_then_primes_planner_before_listening(self):
        planner = SemanticControl()
        opener = types.SimpleNamespace(open=lambda *a, **kw: io.BytesIO(b'{"done":true}'))
        with patch('semantic_control.urllib.request.build_opener', return_value=opener), \
                patch.object(planner, 'plan', return_value={'kind': 'chat'}) as plan:
            self.assertTrue(planner.warmup()['done'])
        plan.assert_called_once_with('你好，很高兴见到你', timeout=120)

    def test_failed_model_load_does_not_prime_planner(self):
        planner = SemanticControl()
        opener = types.SimpleNamespace(open=lambda *a, **kw: io.BytesIO(b'{"done":false}'))
        with patch('semantic_control.urllib.request.build_opener', return_value=opener), \
                patch.object(planner, 'plan') as plan:
            with self.assertRaises(RuntimeError):
                planner.warmup()
        plan.assert_not_called()

    def test_generated_wake_keywords_use_task_cache(self):
        import wake_detector
        output = Path(os.environ['KURISU_TEST_TMP']) / ('wake-' + uuid.uuid4().hex)
        captured = {}
        fake_sherpa = types.SimpleNamespace(KeywordSpotter=lambda **kw: captured.update(kw))
        with patch.dict(os.environ, {'KURISU_CACHE_DIR': str(output)}), \
                patch.dict(sys.modules, {'sherpa_onnx': fake_sherpa}):
            wake_detector.WakeDetector()
        keywords = Path(captured['keywords_file'])
        self.assertTrue(keywords.is_relative_to(output))
        self.assertFalse(keywords.is_relative_to(ROOT))
        self.assertIn('@助手', keywords.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
