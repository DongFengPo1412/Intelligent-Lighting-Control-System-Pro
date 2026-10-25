"""Offline contracts: no board, serial discovery, camera, model or speaker access."""

import io
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / "pc-agent-vision"))
from memory_store import MemoryStore
from mcp_server import McpSession
from network_audio import packet, receive
from music_engine import MusicFeatures
from visual_features import GazeCalibration
from conversation_session import ConversationSession
from multimodal_hub import ControlArbiter
from simulator import SimulatedController, SilentVoice
from xiaozhi_bridge import XiaoZhiConnection, OpusCodec


@contextmanager
def task_directory():
    # Retain generated fixtures in the task cache for inspection/recovery.
    yield tempfile.mkdtemp(dir=os.environ["KURISU_TEST_TMP"])


class RuntimeContracts(unittest.TestCase):
    def test_memory_survives_restart_and_can_be_forgotten(self):
        with task_directory() as d:
            p = Path(d) / "memory.sqlite3"
            m = MemoryStore(p)
            key = m.remember("主人喜欢蓝色海洋灯光")
            m.append_turn("user", "你好")
            m.close()
            m = MemoryStore(p)
            self.assertEqual(m.search("蓝色海洋")[0]["id"], key)
            self.assertEqual(m.recent_turns(), [{"role": "user", "content": "你好"}])
            self.assertTrue(m.forget(key))
            self.assertEqual(m.search("蓝色海洋"), [])
            m.close()

    def test_mcp_initialization_validation_and_failure(self):
        calls = []
        tools = [
            {
                "name": "lamp",
                "parameters": {
                    "type": "object",
                    "properties": {"mode": {"type": "integer", "minimum": 0, "maximum": 31}},
                    "required": ["mode"],
                    "additionalProperties": False,
                },
            }
        ]
        s = McpSession(tools, lambda n, a: calls.append((n, a)) or {"status": "error"})

        def request(method, params={}):
            return s.dispatch(dict(jsonrpc="2.0", id=7, method=method, params=params))

        self.assertIn("error", request("tools/list"))
        self.assertIn("result", request("initialize", {"protocolVersion": "2025-06-18"}))
        self.assertEqual(request("tools/list")["result"]["tools"][0]["name"], "lamp")
        self.assertIn("error", request("tools/call", {"name": "lamp", "arguments": {"mode": True}}))
        self.assertFalse(calls)
        self.assertTrue(
            request("tools/call", {"name": "lamp", "arguments": {"mode": 26}})["result"]["isError"]
        )
        self.assertIsNone(s.dispatch(dict(jsonrpc="2.0", method="notifications/initialized")))

    def test_network_pcm_handles_fragmentation_and_rejects_bad_samples(self):
        class Fragmented:
            def __init__(self, data):
                self.data = io.BytesIO(data)

            def recv(self, n):
                return self.data.read(min(n, 2))

        payload = b"\0\0\xff\x7f"
        self.assertEqual(receive(Fragmented(packet(2, payload))), (2, payload))
        with self.assertRaises(ValueError):
            receive(Fragmented(packet(2, b"x")))
        with self.assertRaises(ConnectionError):
            receive(Fragmented(packet(2, payload)[:-1]))

    def test_continuous_turn_and_explicit_end(self):
        s = ConversationSession()
        self.assertTrue(s.after_reply())
        self.assertTrue(s.should_end("结束对话。"))
        self.assertFalse(s.should_end("不要结束对话"))
        self.assertFalse(ConversationSession(False).after_reply())

    def test_explicit_input_temporarily_blocks_automatic_modes(self):
        clock = [0]
        a = ControlArbiter(lambda: clock[0])
        a.claim_user(10)
        self.assertFalse(a.allows_automatic())
        clock[0] = 11
        self.assertTrue(a.allows_automatic())

    def test_gaze_calibration_requires_noncollinear_points(self):
        g = GazeCalibration()
        error = g.fit(
            [
                [0, 0, 0.1, 0.2],
                [1, 0, 0.9, 0.2],
                [0, 1, 0.1, 0.8],
                [1, 1, 0.9, 0.8],
                [0.5, 0.5, 0.5, 0.5],
            ]
        )
        self.assertLess(error, 1e-8)
        for x in g.predict(0.5, 0.5):
            self.assertAlmostEqual(x, 0.5)
        with self.assertRaises(ValueError):
            g.fit([[0, 0, 0, 0]] * 5)

    def test_mir_distinguishes_transient_and_steady_signal(self):
        import numpy as np

        m = MusicFeatures()
        wave = np.sin(np.arange(1024) * 2 * np.pi * 440 / 16000) * 0.2
        first = m.analyze(wave, 0)
        steady = m.analyze(wave, 0.1)
        self.assertTrue(first["onset"])
        self.assertFalse(steady["onset"])
        self.assertEqual(len(first["bands"]), 16)
        self.assertTrue(all(0 <= v <= 15 for v in first["bands"]))

    def test_memory_reindexes_when_embedding_provider_changes(self):
        with task_directory() as d:
            p = Path(d) / "m.db"
            m = MemoryStore(p)
            key = m.remember("散步")
            m.close()

            class Semantic:
                name = "test-semantic"

                def __call__(self, text):
                    return [1.0, 0.0] if text in ("散步", "漫步") else [0.0, 1.0]

            m = MemoryStore(p, embed=Semantic())
            self.assertEqual(m.search("漫步")[0]["id"], key)
            m.close()

    def test_reference_echo_filter_converges_on_synthetic_linear_echo(self):
        import numpy as np
        from echo_cancellation import EchoCanceller

        x = np.random.default_rng(17).normal(0, 0.08, 4800)
        reference = (x * 32767).astype("<i2").tobytes()
        mic = (x * 0.45 * 32767).astype("<i2").tobytes()
        e = EchoCanceller(taps=16, delay_samples=0)
        e.feed_reference(reference)
        residual = np.frombuffer(e.process(mic), dtype="<i2").astype(float)
        self.assertLess(
            np.mean(residual[-1000:] ** 2),
            np.mean(np.frombuffer(mic, dtype="<i2").astype(float)[-1000:] ** 2) * 0.02,
        )

    def test_extended_controls_reject_nonfinite_and_malformed_inputs(self):
        c = SimulatedController()
        calls = []
        c.send_json = lambda p: calls.append(p) or True
        for value in (float("nan"), float("inf"), -0.1, 1.1, True):
            with self.assertRaises(ValueError):
                c.track(value, 0.5)
        with self.assertRaises(ValueError):
            c.difficulty(0.5, "yes")
        with self.assertRaises(ValueError):
            c.canvas("00" * 767)
        self.assertFalse(calls)

    def test_simulated_gamma_uses_the_firmware_integer_transfer(self):
        with patch.dict(os.environ, {"KURISU_RENDERER_WASM": ""}):
            c = SimulatedController()
            c.canvas("808080" * 256)
            c.set_mode(29)
            self.assertEqual(c.frame()["pixels"][:6], "0a0a0a")
            self.assertTrue(c.send_json({"cmd": "gamma", "enable": True}))
            self.assertEqual(c.frame()["pixels"][:6], "040404")
            self.assertFalse(c.send_json({"cmd": "gamma", "enable": 1}))

    def test_vision_arbitration_and_calibrated_game_input(self):
        from multimodal_hub import MultimodalHub

        c = SimulatedController()
        calls = []
        c.snake_move = lambda x, y: calls.append((x, y)) or True
        h = MultimodalHub(c)
        c.mode = 19
        h.mode = "gaze_game"
        h.process({"present": True, "gaze_x": 0.1, "gaze_y": 0.5, "calibrated": False}, 100)
        h.process({"present": True, "gaze_x": 0.1, "gaze_y": 0.5, "calibrated": False}, 101)
        self.assertFalse(calls)
        h.process({"present": True, "gaze_x": 0.1, "gaze_y": 0.5, "calibrated": True}, 102)
        h.process({"present": True, "gaze_x": 0.1, "gaze_y": 0.5, "calibrated": True}, 103)
        self.assertEqual(calls, [(-1, 0)])

    def test_opus_round_trip_is_real_codec_without_playback(self):
        import numpy as np

        codec = OpusCodec(60)
        wave = (np.sin(np.arange(9600) * 0.17) * 5000).astype("<i2").tobytes()
        packets = list(codec.encode(wave))
        decoded = b"".join(codec.decode(p) for p in packets)
        self.assertEqual(len(packets), 10)
        self.assertGreater(len(decoded) // 2, 9000)
        self.assertGreater(
            np.sqrt(np.mean(np.frombuffer(decoded, dtype="<i2").astype(float) ** 2)), 1000
        )

    @unittest.skipUnless(
        os.environ.get("KURISU_TEST_RENDERER_WASM"), "Offline C++ renderer was not built"
    )
    def test_real_cpp_renderer_feeds_modes_canvas_and_games(self):
        with patch.dict(
            os.environ, {"KURISU_RENDERER_WASM": os.environ.get("KURISU_TEST_RENDERER_WASM", "")}
        ):
            c = SimulatedController()
            try:
                for mode in (1, 4, 10, 17, 19, 21, 23, 24, 26, 27, 28, 29, 30, 31):
                    self.assertTrue(c.set_mode(mode))
                    frame = c.frame()
                    self.assertEqual(len(frame["pixels"]), 1536)
                    self.assertEqual(frame["frame_source"], "simulation_cpp_pwm")
                c.canvas("ff0000" * 256)
                c.set_mode(29)
                self.assertEqual(c.frame()["pixels"], "140000" * 256)
            finally:
                c.close()

    def test_manual_mode_disables_visual_takeover_until_reenabled(self):
        from multimodal_hub import MultimodalHub

        c = SimulatedController()
        h = MultimodalHub(c)
        h.mode = "fingertip"
        c.set_mode(1)
        h.arbiter.until = 0
        h.process({"present": True, "hand": {"x": 0.5, "y": 0.5}}, 100)
        self.assertEqual(c.mode, 1)
        self.assertFalse(h.automatic_enabled)


class XiaoZhiContracts(unittest.IsolatedAsyncioTestCase):
    def connection(self):
        import types

        class Socket:
            def __init__(self):
                self.messages = []
                self.audio = []

            async def send_json(self, v):
                self.messages.append(v)

            async def send_bytes(self, v):
                self.audio.append(v)

        class Codec:
            def __init__(self, ms):
                pass

            def decode(self, data):
                return b"\x00\x10" * 960

            def encode(self, data):
                yield b"opus-test-packet"

        self.ws = Socket()
        self.calls = []
        agent = types.SimpleNamespace(
            chat=lambda text, **kwargs: self.calls.append((text, kwargs)) or "回答"
        )
        voice = types.SimpleNamespace(synthesize_to_pcm=lambda text: bytes(1920))
        return XiaoZhiConnection(
            self.ws, agent, voice, lambda pcm: "蓝灯", [], lambda *a: None, Codec
        )

    async def hello(self, c):
        await c.text(
            dict(
                type="hello",
                version=1,
                transport="websocket",
                audio_params=dict(format="opus", sample_rate=16000, channels=1, frame_duration=60),
            )
        )

    async def test_requires_handshake_and_rejects_other_binary_versions(self):
        c = self.connection()
        with self.assertRaises(ValueError):
            await c.text({"type": "listen", "state": "start"})
        with self.assertRaises(ValueError):
            await c.text(dict(type="hello", version=3, audio_params={}))
        await self.hello(c)
        self.assertEqual(self.ws.messages[0]["audio_params"]["format"], "opus")
        await c.close()

    async def test_manual_audio_to_agent_to_opus_and_abort(self):
        c = self.connection()
        await self.hello(c)
        await c.text(dict(type="listen", state="start", mode="manual"))
        for _ in range(4):
            await c.binary(b"encoded")
        await c.text(dict(type="listen", state="stop"))
        await c.reply_task
        self.assertEqual(self.calls[0][0], "蓝灯")
        self.assertFalse(self.calls[0][1]["speak"])
        self.assertEqual(self.ws.audio, [b"opus-test-packet"])
        self.assertEqual(self.ws.messages[-1]["state"], "stop")
        await c.text({"type": "abort"})
        self.assertTrue(c.cancel.is_set())
        await c.close()

    async def test_bidirectional_mcp_device_request_correlation(self):
        import asyncio

        c = self.connection()
        await self.hello(c)
        task = asyncio.create_task(c.request_device("tools/list"))
        await asyncio.sleep(0)
        rid = self.ws.messages[-1]["payload"]["id"]
        await c.text(dict(type="mcp", payload=dict(jsonrpc="2.0", id=rid, result={"tools": []})))
        self.assertEqual(await task, {"tools": []})
        self.assertFalse(c.pending)
        await c.close()


class WebContracts(unittest.IsolatedAsyncioTestCase):
    async def test_unified_entry_delivers_all_local_assets_and_legacy_alias(self):
        from html.parser import HTMLParser

        class Assets(HTMLParser):
            paths = []

            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag in ('script', 'img', 'link'):
                    path = attrs.get('src') or attrs.get('href')
                    if path:
                        self.paths.append(path)

        response = await self.client.get('/')
        self.assertEqual(response.status, 200)
        html = await response.text()
        parser = Assets()
        parser.feed(html)
        for path in set(parser.paths):
            self.assertFalse(path.startswith(('http:', 'https:')), path)
            asset = await self.client.get('/' + path)
            self.assertEqual(asset.status, 200, path)
        for page in ('overview', 'lights', 'music', 'interaction', 'settings'):
            self.assertIn('id="page-' + page + '"', html)
        alias = await (await self.client.get('/pro.html')).text()
        self.assertIn('pro.js', alias)
        self.assertNotIn('id="musicFile"', alias)

    async def test_music_visual_selection_reaches_player(self):
        import web_server
        with patch.object(web_server.pro_api.music,'play') as play:
            response=await self.client.post('/api/pro/music-upload?visual=spectrum',data=b'fixture')
            self.assertEqual(response.status,200)
            play.assert_called_once_with(b'fixture',False)
        with patch.object(web_server.pro_api.music,'play') as play:
            response=await self.client.post('/api/pro/music-upload',data=b'fixture')
            self.assertEqual(response.status,200)
            play.assert_called_once_with(b'fixture',True)

    async def test_bad_visual_is_rejected_before_decoding_or_downloading(self):
        response=await self.client.post('/api/pro/music-upload?visual=bad',data=b'fixture')
        self.assertEqual(response.status,400)
        self.assertIn('visual',(await response.json())['error'])
        response=await self.client.post('/api/pro/music',json=dict(url='http://invalid.invalid/song.wav',visual='bad'))
        self.assertEqual(response.status,400)

    async def asyncSetUp(self):
        self.tmp = tempfile.mkdtemp(dir=os.environ["KURISU_TEST_TMP"])
        self.env = patch.dict(os.environ, {"KURISU_DATA_DIR": self.tmp, "KURISU_SIMULATE": "1"})
        self.env.start()
        from aiohttp.test_utils import TestClient, TestServer
        import web_server

        self.client = TestClient(TestServer(web_server.create_app(simulate=True)))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()
        self.env.stop()

    async def test_canvas_and_frame_are_connected_in_simulation(self):
        r = await self.client.post("/api/pro/canvas", json={"hex": "ff0000" * 256})
        self.assertEqual(r.status, 200)
        r = await self.client.get("/api/pro/frame")
        data = await r.json()
        self.assertEqual(data["frame_source"], "simulation_pwm")
        self.assertEqual(len(data["pixels"]), 1536)
        self.assertEqual(data["pixels"][:6], "140000")

    async def test_http_mcp_session_routes_to_controller(self):
        r = await self.client.post(
            "/mcp", json=dict(jsonrpc="2.0", id=1, method="initialize", params={})
        )
        self.assertEqual(r.status, 200)
        sid = r.headers["Mcp-Session-Id"]
        r = await self.client.post(
            "/mcp",
            headers={"Mcp-Session-Id": sid},
            json=dict(
                jsonrpc="2.0",
                id=2,
                method="tools/call",
                params={"name": "set_light_mode", "arguments": {"mode": 26}},
            ),
        )
        self.assertFalse((await r.json())["result"]["isError"])
        self.assertEqual((await (await self.client.get("/api/pro/frame")).json())["mode"], 26)

    async def test_memory_and_invalid_canvas_http(self):
        r = await self.client.post("/api/pro/memory", json={"text": "喜欢紫色"})
        self.assertEqual(r.status, 200)
        r = await self.client.get("/api/pro/memory")
        self.assertEqual((await r.json())[0]["text"], "喜欢紫色")
        r = await self.client.post("/api/pro/canvas", json={"hex": "bad"})
        self.assertEqual(r.status, 400)

    async def test_simulation_never_opens_sensor_or_uses_xiaozhi_when_disabled(self):
        r = await self.client.post("/api/pro/vision", json={"enabled": True})
        self.assertEqual(r.status, 400)
        r = await self.client.get("/xiaozhi/v1/")
        self.assertEqual(r.status, 503)
        r = await self.client.get("/pro.html")
        self.assertEqual(r.status, 200)
        r = await self.client.post("/api/pro/difficulty", json={"level": True, "adaptive": True})
        self.assertEqual(r.status, 400)


if __name__ == "__main__":
    unittest.main()
