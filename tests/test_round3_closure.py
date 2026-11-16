"""Round 3 closure test suite: PC camera auth, F16 (#101 semantic), F17/F18 (#101 parity & mechanics), and F22."""

from __future__ import annotations

import inspect
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import aiohttp
from aiohttp.test_utils import TestClient, TestServer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pc-agent-vision"))

import arcade_catalog
import kurisu_agent
import web_server
from access_control import AccessPolicy
from arcade import game_101_microlight as g101
from arcade.b3_helpers import KEY_A, KEY_B, KEY_LEFT, KEY_RIGHT, KEY_UP
from arcade.game_101_microlight import Game101MicroLight
from memory_store import MemoryStore
from semantic_control import WIRE_SCHEMA, SemanticControl, exact_plan, from_wire
from simulator import SilentVoice, SimulatedController


class PcWebcamAuthAndSessionOwnershipTests(unittest.IsolatedAsyncioTestCase):
    async def test_hotspot_peer_cannot_start_or_stop_pc_camera_nor_hijack_remote(self):
        app = web_server.create_app(simulate=True, no_audio=True)

        async with TestServer(app) as server:
            async with TestClient(server) as client:
                pro = web_server.pro_api
                pro.controller.port = "COM9"
                pro.vision.stop()
                policy = app["access_policy"]

                # 1. Trusted hotspot peer WITHOUT admin token:
                #    - camera start (explicit "camera", empty, or unknown "pc") -> 401!
                #    - ordinary controls (/status, /music) -> non-401!
                with patch.object(policy, "local", return_value=False), \
                     patch.object(AccessPolicy, "is_trusted_peer", return_value=True):
                    for payload in [
                        {"enabled": True, "source": "camera"},
                        {"enabled": True},
                        {"enabled": True, "source": "pc"},
                    ]:
                        resp = await client.post("/api/pro/vision", json=payload)
                        self.assertEqual(resp.status, 401, f"Expected 401 for {payload}")
                        body = await resp.json()
                        self.assertEqual(body.get("error"), "pc_camera_requires_admin_auth")

                    self.assertEqual((await client.get("/api/pro/status")).status, 200)
                    self.assertNotEqual(
                        (await client.post("/api/pro/music", json={"stop": True})).status,
                        401,
                    )

                # 2. Local admin starts PC camera ("camera") -> 200 & issues vision token
                def fake_cam_start(mode="pet", camera=0):
                    pro.vision.started = True
                    pro.vision.source = "camera"
                    pro.vision.active_session_id = "pc_cam_1"
                    return True

                with patch.object(pro.vision, "start", side_effect=fake_cam_start):
                    start_cam = await client.post("/api/pro/vision", json={"enabled": True, "source": "camera"})
                    self.assertEqual(start_cam.status, 200)
                    cam_data = await start_cam.json()
                    self.assertEqual(cam_data.get("source"), "camera")
                    self.assertTrue(cam_data.get("vision_token"))
                    self.assertTrue(cam_data.get("session_id"))

                # 3. Separate unauthenticated hotspot peer (clean session) CANNOT read frame/feed or stop PC camera
                async with aiohttp.ClientSession() as attacker:
                    with patch.object(policy, "local", return_value=False), \
                         patch.object(AccessPolicy, "is_trusted_peer", return_value=True):
                        self.assertEqual((await attacker.get(server.make_url("/api/pro/camera/frame"))).status, 401)
                        self.assertEqual((await attacker.get(server.make_url("/api/pro/camera/feed"))).status, 401)
                        stop_steal = await attacker.post(server.make_url("/api/pro/vision"), json={"enabled": False})
                        self.assertEqual(stop_steal.status, 401)
                        stop_steal_body = await stop_steal.json()
                        self.assertIn(
                            stop_steal_body.get("error"),
                            ("pc_camera_requires_admin_auth", "vision_session_ownership_required"),
                        )

                # 4. Admin can stop PC camera cleanly
                def fake_cam_stop():
                    pro.vision.started = False
                    pro.vision.source = "none"
                    pro.vision.active_session_id = None

                with patch.object(pro.vision, "stop", side_effect=fake_cam_stop):
                    stop_admin = await client.post("/api/pro/vision", json={"enabled": False})
                    self.assertEqual(stop_admin.status, 200)

                # 5. Hotspot peer CAN start phone remote camera without admin token,
                #    cannot hijack it without owning token, and owner CAN stop it.
                async with aiohttp.ClientSession() as phone_client, aiohttp.ClientSession() as other_peer:
                    with patch.object(policy, "local", return_value=False), \
                         patch.object(AccessPolicy, "is_trusted_peer", return_value=True):
                        start_rem = await phone_client.post(
                            server.make_url("/api/pro/vision"),
                            json={"enabled": True, "source": "remote", "facing": "user"},
                        )
                        self.assertEqual(start_rem.status, 200)
                        rem_data = await start_rem.json()
                        rem_tok = rem_data["vision_token"]
                        rem_sess = rem_data["session_id"]
                        self.assertEqual(rem_data.get("source"), "remote")

                        # Another peer (no vision token, clean session) cannot stop phone remote session or read frames
                        other_stop = await other_peer.post(server.make_url("/api/pro/vision"), json={"enabled": False})
                        self.assertEqual(other_stop.status, 401)
                        self.assertEqual((await other_peer.get(server.make_url("/api/pro/camera/frame"))).status, 401)

                        # Owner with token + session can upload frame (gets 400 invalid jpeg rather than 401) & stop
                        up_bad = await phone_client.post(
                            server.make_url(f"/api/pro/camera/frame?session_id={rem_sess}"),
                            headers={"X-Vision-Token": rem_tok, "X-Vision-Session": rem_sess},
                            data=b"notajpeg",
                        )
                        self.assertNotEqual(up_bad.status, 401)

                        owner_stop = await phone_client.post(
                            server.make_url("/api/pro/vision"),
                            headers={"X-Vision-Token": rem_tok, "X-Vision-Session": rem_sess},
                            json={"enabled": False, "source": "remote"},
                        )
                        self.assertEqual(owner_stop.status, 200)


class F16Semantic101Tests(unittest.TestCase):
    def test_schema_prompt_and_exact_plan_support_101(self):
        self.assertEqual(WIRE_SCHEMA["properties"]["game_id"]["maximum"], 101)
        plan_src = inspect.getsource(SemanticControl.plan)
        self.assertIn("1..101", plan_src)
        self.assertIn("101", plan_src)
        self.assertIn("微光纪元", plan_src)

        for utterance in ["启动101号游戏", "玩微光纪元", "打开MicroLight", "启动第101款游戏"]:
            res = exact_plan(utterance)
            self.assertIsNotNone(res, f"exact_plan missed: {utterance}")
            self.assertEqual(res["actions"][0]["tool"], "start_game")
            self.assertEqual(res["actions"][0]["value"], 101)

        # Out of range 102 and negations/questions/chat must not trigger #101
        self.assertIsNone(exact_plan("启动102号游戏"))
        for non_trigger in ("别玩微光纪元", "不要打开101号游戏", "微光纪元是什么游戏", "今天天气怎么样"):
            r = exact_plan(non_trigger)
            self.assertTrue(r is None or r.get("actions") == [], f"Unexpected action for {non_trigger}: {r}")

    def test_mocked_llm_semantic_plan_accepts_101_and_rejects_102(self):
        sc = SemanticControl()

        class FakeResp:
            def __init__(self, obj):
                self._raw = json.dumps({"message": {"content": json.dumps(obj)}}).encode("utf-8")

            def read(self):
                return self._raw

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        def make_opener(obj):
            class FakeOpener:
                def open(self, req, timeout=30):
                    return FakeResp(obj)

            return FakeOpener()

        ok_wire = {
            "kind": "control",
            "effect": "保持现状",
            "timer_seconds": 0,
            "brightness": -1,
            "volume": -1,
            "game_id": 101,
            "stop_countdown": False,
            "query_status": False,
            "worldline": False,
        }
        with patch("urllib.request.build_opener", return_value=make_opener(ok_wire)):
            out_101 = sc.plan("打开那个探索新游戏吧")
        self.assertEqual(out_101["actions"][0]["tool"], "start_game")
        self.assertEqual(out_101["actions"][0]["value"], 101)

        bad_wire = dict(ok_wire, game_id=102)
        with patch("urllib.request.build_opener", return_value=make_opener(bad_wire)):
            with self.assertRaises(ValueError):
                sc.plan("打开那个新街机吧")

        # Validate from_wire boundaries directly
        self.assertEqual(from_wire(ok_wire)["actions"][0]["value"], 101)
        self.assertEqual(from_wire(dict(ok_wire, game_id=0))["actions"], [])
        for bad_id in (102, -1, True):
            with self.assertRaises(ValueError):
                from_wire(dict(ok_wire, game_id=bad_id))

    def test_agent_reports_failure_honestly_on_nack_for_101(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
            ctrl = SimulatedController()
            ctrl.port = "COM9"
            ctrl.command_result = lambda p: {"status": "error", "error": "hardware_nack"}
            voice = SilentVoice()
            store = MemoryStore(Path(td) / "mem.json")
            agent = kurisu_agent.KurisuAgent(controller=ctrl, voice=voice, memory=store)
            with patch("light_tools.get_light_controller", return_value=ctrl):
                reply = agent.chat("启动101号游戏")
            self.assertTrue(
                any(k in reply for k in ("没有确认", "失败", "未能", "未生效", "硬件", "nack", "异常")),
                f"Expected honest NACK failure reply, got: {reply}",
            )


class F17F18MicroLightTests(unittest.TestCase):
    def test_negative_biome_floor_division(self):
        g = Game101MicroLight()
        g.set_replay_seed(2026)
        g.init()
        expected = [
            (-80, 5), (-41, 5), (-40, 6), (-39, 6), (-1, 6),
            (0, 0), (39, 0), (40, 1), (41, 1), (80, 2),
        ]
        for wx, b in expected:
            self.assertEqual(g.get_biome(wx), b, f"Biome mismatch at wx={wx}")

    def test_jump_mine_no_conflict_build_combat_and_bounds(self):
        g = Game101MicroLight()
        g.set_replay_seed(9527)
        g.start()

        # 1. KEY_A must NOT jump; KEY_UP jumps & lands cleanly
        y0 = g.player_y
        self.assertTrue(g.grounded)
        g.update(1.0 / 30.0, 0, KEY_A)
        self.assertAlmostEqual(g.player_y, y0, delta=0.05)
        self.assertTrue(g.grounded)

        g.update(1.0 / 30.0, KEY_UP, KEY_UP)
        for _ in range(6):
            g.update(1.0 / 30.0, KEY_UP, 0)
        self.assertLess(g.player_y, y0 - 0.5)
        self.assertFalse(g.grounded)
        for _ in range(60):
            g.update(1.0 / 30.0, 0, 0)
        self.assertTrue(g.grounded)
        self.assertAlmostEqual(g.player_y, y0, delta=0.1)

        # 2. Mining mutates tile & grants drop
        tx, ty = g.target()
        g.put_tile(tx, ty, g101.TILE_WOOD)
        wood0 = g.inv["wood"]
        g.update(1.0 / 30.0, 0, KEY_A)
        self.assertEqual(g.tile(tx, ty), g101.TILE_AIR)
        self.assertEqual(g.inv["wood"], wood0 + 2)

        # 3. Building consumes resource & blocks movement
        g.build_index = g101.BUILD_WOOD_WALL
        wood_mid = g.inv["wood"]
        g.update(1.0 / 30.0, 0, KEY_B)
        self.assertEqual(g.tile(tx, ty), g101.TILE_WOOD_WALL)
        self.assertEqual(g.inv["wood"], wood_mid - 2)
        for _ in range(20):
            g.update(1.0 / 30.0, KEY_RIGHT, 0)
        self.assertLessEqual(g.player_x, tx - 0.99)

        # 4. Out-of-resource build rejected honestly
        g.inv["wood"] = 0
        g.inv["fiber"] = 0
        g.update(1.0 / 30.0, KEY_LEFT, KEY_LEFT)
        ltx, lty = g.target()
        self.assertFalse(g.build())
        self.assertEqual(g.tile(ltx, lty), g101.TILE_AIR)
        self.assertEqual(g.tile(tx, ty), g101.TILE_WOOD_WALL)

        # 5. Combat attack + knockback + kill drop
        self.assertTrue(g.spawn_enemy_at(g.player_x - 1.0, g.player_y + 1.0, "slime", 2))
        fiber0 = g.inv["fiber"]
        g.update(1.0 / 30.0, 0, KEY_B)
        self.assertEqual(len(g.enemies), 1)
        for _ in range(10):
            g.update(1.0 / 30.0, KEY_LEFT, 0)
        g.update(1.0 / 30.0, 0, KEY_B)
        self.assertEqual(len(g.enemies), 0)
        self.assertGreaterEqual(g.inv["fiber"], fiber0 + 1)

        # 6. 20-min exploration bounded edits & enemies
        long_g = Game101MicroLight()
        long_g.set_replay_seed(12345)
        long_g.start()
        for step in range(36000):
            d = KEY_RIGHT if (step % 40 < 20) else (KEY_RIGHT | KEY_UP)
            p = KEY_UP if (step % 30 == 0) else (KEY_A if step % 45 == 0 else 0)
            long_g.update(1.0 / 30.0, d, p)
            self.assertLessEqual(len(long_g.edits), g101.MAX_EDITS)
            self.assertLessEqual(len(long_g.enemies), g101.MAX_ENEMIES)

        # 7. Popcount win condition: biome 6 gives raw mask 65 >= 4, count=2 < 4
        wt = Game101MicroLight()
        wt.set_replay_seed(77)
        wt.start()
        for i in range(6000):
            if wt.get_biome(math.floor(wt.player_x)) == 6:
                break
            wt.update(0.05, KEY_LEFT, KEY_UP if i % 15 == 0 else 0)
        self.assertLess(wt.visited_biome_count(), 4)
        for _ in range(3000):
            wt.update(0.05, 0, 0)
        self.assertEqual(wt.state, g101.STATE_GAMEOVER)

        # Visiting 4 biomes wins on timeout
        wt2 = Game101MicroLight()
        wt2.set_replay_seed(77)
        wt2.start()
        wt2.hp = 99  # prevent night slimes killing idle character during timeout check
        wt2.biomes_visited = (1 << 0) | (1 << 1) | (1 << 2) | (1 << 3)
        for _ in range(3000):
            wt2.update(0.05, 0, 0)
        self.assertEqual(wt2.state, g101.STATE_VICTORY)

        # Death & restart resets cleanly
        wt2.start()
        self.assertEqual(wt2.state, g101.STATE_PLAYING)
        self.assertEqual(wt2.hp, 5)

    def test_cpp_python_parity_and_catalog_consistency(self):
        g = Game101MicroLight()
        g.set_replay_seed(2026)
        g.start()
        for f in range(180):
            d = 0
            p = 0
            if f < 40:
                d = KEY_RIGHT
            elif f < 80:
                d = KEY_LEFT
            elif f < 140:
                d = KEY_RIGHT
            if f in (10, 50, 90):
                p |= KEY_UP
            if f in (25, 120):
                p |= KEY_A
            if f == 135:
                p |= KEY_B
            g.update(1.0 / 30.0, d, p)

        fb = g.render()
        csum = 0
        for b in fb:
            csum = (csum * 131 + b) & 0xFFFFFFFF
        surfs = [g.surface_at(-80), g.surface_at(0), g.surface_at(45), g.surface_at(120)]
        # Exact cross-language comparison against compiled C++ output:
        # PARITY px=9.12676 py=10.0001 hp=5 biomes=1 wood=4 score=30 surf=8,11,10,13 fb_csum=1362504820
        self.assertEqual(surfs, [8, 11, 10, 13])
        self.assertAlmostEqual(g.player_x, 9.12676, delta=0.05)
        self.assertEqual(g.hp, 5)
        self.assertEqual(g.biomes_visited, 1)
        self.assertEqual(g.inv["wood"], 4)
        self.assertEqual(g.score, 30)
        self.assertEqual(csum, 1362504820)

        # Catalog & guide consistency
        entry = arcade_catalog.resolve_arcade_game(101)
        self.assertEqual(entry, (101, "微光纪元"))
        guides_text = (ROOT / "pc-agent-vision" / "web_app" / "arcade_game_guides.js").read_text(encoding="utf-8")
        self.assertIn("101:", guides_text)
        self.assertIn("方向键移动与跳跃", guides_text)


class F22DocsAlignmentTests(unittest.TestCase):
    def test_agents_and_baseline_aligned(self):
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("30 FPS", agents)
        self.assertIn("33ms", agents)
        baseline = (ROOT / "docs" / "PRO_FINAL_REQUIREMENTS_BASELINE.md").read_text(encoding="utf-8")
        self.assertIn("main", baseline)


if __name__ == "__main__":
    unittest.main()
