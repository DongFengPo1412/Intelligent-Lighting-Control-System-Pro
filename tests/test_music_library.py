"""Catalog, queue and spoken requests with generated files and fake devices."""

import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest.mock import patch

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pc-agent-vision"))
from music_library import MusicLibrary, LibraryPlayback
from music_commands import MusicCommands, parse_music_request
from music_engine import MusicPlayer, decode_audio


class Device:
    port = "TEST"

    def __init__(self):
        self.mode = 17
        self.playback_started_at = None
        self.playback_cancel = threading.Event()
        self.played = []
        self.peaks, self.energies = [], []

    def set_mode(self, mode):
        self.mode = mode
        return True

    def frame(self):
        return {"mode": self.mode}

    def send_json(self, command):
        return True

    def play_audio_pcm(self, pcm):
        self.playback_cancel.clear()
        self.playback_started_at = time.monotonic()
        self.played.append(len(pcm))
        self.peaks.append(
            float(np.max(np.abs(np.frombuffer(pcm, dtype="<i2").astype(float)))) / 32768
        )
        return not self.playback_cancel.wait(len(pcm) / 32000)

    def music_features(self, *args, **kwargs):
        self.energies.append(args[0])
        return True

    def send_raw(self, line):
        return True


class LibraryContracts(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(dir=os.environ["KURISU_TEST_TMP"]))
        self.music = self.root / "songs"
        self.music.mkdir()
        for name in (
            "周杰伦 - 晴天.wav",
            "周杰伦 - 稻香.wav",
            "甲 - 同名.wav",
            "乙 - 同名.wav",
        ):
            sf.write(self.music / name, np.sin(np.arange(2400) * 0.2) * 0.1, 16000)
        self.settings = self.root / "settings" / "music-library.json"
        with patch.dict(os.environ, {"KURISU_MUSIC_DIR": ""}):
            self.library = MusicLibrary(self.settings)
        self.library.configure(str(self.music))
        self.device = Device()
        self.player = MusicPlayer(self.device)
        self.queue = LibraryPlayback(self.library, self.player)
        self.commands = MusicCommands(self.library, self.queue)

    def tearDown(self):
        self.queue.stop()

    def wait_idle(self, timeout=3):
        until = time.monotonic() + timeout
        while time.monotonic() < until:
            if not self.player.running and self.device.mode == 17:
                return
            time.sleep(0.01)
        self.fail("queue did not finish")

    def test_scan_search_config_persistence_and_read_only_sources(self):
        before = {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in self.music.iterdir()
        }
        self.assertEqual(self.library.status()["count"], 4)
        result = self.library.search("周杰伦 的 晴天")
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["title"], "晴天")
        self.assertNotIn("path", result["items"][0])
        self.assertEqual(
            self.library.search("周杰伦", offset=1, limit=1)["items"][0]["title"],
            "稻香",
        )
        with patch.dict(os.environ, {"KURISU_MUSIC_DIR": ""}):
            restored = MusicLibrary(self.settings)
        self.assertEqual(restored.root, str(self.music))
        restored.scan()
        self.assertEqual(
            restored.search("晴天")["items"][0]["id"], result["items"][0]["id"]
        )
        self.assertEqual(
            before,
            {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.music.iterdir()
            },
        )

    def test_invalid_paths_and_ids_cannot_read_other_files(self):
        with self.assertRaises(ValueError):
            self.library.configure("relative")
        with self.assertRaises(ValueError):
            self.library.configure(str(self.root / "absent"))
        with self.assertRaises(ValueError):
            self.library.path("../../outside.wav")
        self.assertEqual(self.library.status()["count"], 4)

    def test_unique_voice_request_plays_without_speaking_over_song(self):
        result = self.commands.handle("请帮我播放一首周杰伦唱的《晴天》")
        self.assertFalse(result["speak"])
        self.assertIn("晴天", result["reply"])
        self.assertTrue(self.player.running)
        self.assertEqual(self.device.mode, 30)
        self.assertEqual(self.queue.current["title"], "晴天")

    def test_music_headroom_does_not_attenuate_the_analysis_source(self):
        track = self.library.tracks[0]
        self.queue.play(track["id"], single=True)
        self.wait_idle()
        self.assertLess(self.device.peaks[0], 0.026)
        self.assertGreater(max(self.device.energies), 0.25)

    def test_duplicate_title_clarifies_and_spoken_choice_selects_exact_id(self):
        result = self.commands.handle("播放同名")
        self.assertIn("2 首", result["reply"])
        self.assertFalse(self.player.running)
        selected = self.queue.candidates[1]["id"]
        result = self.commands.handle("播放第2首")
        self.assertFalse(result["speak"])
        self.assertEqual(self.queue.current["id"], selected)

    def test_negations_questions_and_light_modes_do_not_play(self):
        for text in (
            "不要播放晴天",
            "你听过晴天吗",
            "播放晴天会怎么样",
            "我很喜欢周杰伦",
            "播放音乐光环",
        ):
            self.assertIsNone(self.commands.handle(text), text)
        self.assertFalse(self.player.running)
        self.assertEqual(parse_music_request("现在放的什么歌？")["action"], "status")

    def test_real_asr_homophones_resolve_against_the_catalog(self):
        sf.write(self.music / "周杰伦 - 七里香.wav", np.zeros(2400), 16000)
        self.library.scan()
        result = self.commands.handle("播放周介伦，其理乡。")
        self.assertIn("七里香", result["reply"])
        self.assertFalse(result["speak"])
        self.assertEqual(self.queue.current["title"], "七里香")

    def test_homophone_collisions_still_require_clarification(self):
        sf.write(self.music / "甲 - 心雨.wav", np.zeros(2400), 16000)
        sf.write(self.music / "乙 - 新语.wav", np.zeros(2400), 16000)
        self.library.scan()
        result = self.commands.handle("播放欣雨")
        self.assertIn("2 首", result["reply"])
        self.assertFalse(self.player.running)

    def test_second_real_asr_error_has_one_strong_catalog_candidate(self):
        sf.write(self.music / "周杰伦 - 七里香.wav", np.zeros(2400), 16000)
        self.library.scan()
        result = self.commands.handle("播放逐渐人的七笔箱。")
        self.assertIn("七里香", result["reply"])
        self.assertFalse(result["speak"])

    def test_natural_end_advances_once_and_restores_pet(self):
        songs = self.library.all_matches("周杰伦")
        self.queue.play(songs[0]["id"], scope="周杰伦")
        self.wait_idle()
        self.assertEqual(len(self.device.played), 2)
        self.assertEqual(self.queue.cursor, 1)
        self.assertIsNone(self.queue.error)

    def test_stop_invalidates_pending_auto_next(self):
        self.queue.play(self.library.tracks[0]["id"])
        self.queue.stop()
        time.sleep(0.25)
        self.assertEqual(len(self.device.played), 1)
        self.assertFalse(self.player.running)
        self.assertEqual(self.device.mode, 17)

    def test_switching_does_not_let_old_song_start_an_extra_song(self):
        songs = self.library.all_matches("周杰伦")
        self.queue.play(songs[0]["id"], scope="周杰伦")
        self.queue.step(1)
        self.wait_idle()
        self.assertEqual(len(self.device.played), 2)
        self.assertEqual(self.queue.current["id"], songs[1]["id"])

    def test_repeat_one_and_shuffle_keep_current_and_have_no_duplicate_ids(self):
        self.queue.set_options(repeat="one")
        self.queue.play(self.library.tracks[0]["id"])
        until = time.monotonic() + 2
        while len(self.device.played) < 2 and time.monotonic() < until:
            time.sleep(0.01)
        self.assertGreaterEqual(len(self.device.played), 2)
        self.queue.set_options(order="shuffle")
        self.assertEqual(len(set(self.queue.queue)), 4)
        self.assertEqual(self.queue.queue[self.queue.cursor], self.queue.current["id"])
        with self.assertRaises(ValueError):
            self.queue.set_options(repeat="invalid")

    def test_missing_or_removed_track_never_reports_playing(self):
        self.assertIn("没有找到", self.commands.handle("播放不存在的歌")["reply"])
        track = self.library.tracks[0]
        # Move our generated fixture inside its own task cache; retain it.
        self.library.path(track["id"]).rename(self.root / "retained-moved-fixture.wav")
        with self.assertRaises(OSError):
            self.queue.play(track["id"])
        self.assertFalse(self.player.running)

    def test_local_files_do_not_have_the_upload_byte_limit(self):
        track = self.library.tracks[0]
        path = self.library.path(track["id"])
        with path.open("ab") as out:
            out.truncate(21 * 1024 * 1024)
        self.assertEqual(len(decode_audio(path)), 4800)


class MusicLibraryApi(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from aiohttp.test_utils import TestClient, TestServer

        self.root = Path(tempfile.mkdtemp(dir=os.environ["KURISU_TEST_TMP"]))
        self.songs = self.root / "songs"
        self.songs.mkdir()
        sf.write(self.songs / "演唱者 - 测试.wav", np.zeros(3200), 16000)
        self.env = patch.dict(
            os.environ,
            {
                "KURISU_DATA_DIR": str(self.root / "data"),
                "KURISU_MUSIC_DIR": "",
                "KURISU_RENDERER_WASM": "",
            },
        )
        self.env.start()
        import web_server

        self.web_server = web_server
        self.client = TestClient(TestServer(web_server.create_app(simulate=True)))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()
        self.env.stop()

    async def test_web_catalog_play_status_and_text_voice_route_share_the_queue(self):
        r = await self.client.post(
            "/api/pro/library", json={"action": "configure", "root": str(self.songs)}
        )
        self.assertEqual(r.status, 200)
        self.assertEqual((await r.json())["count"], 1)
        catalog = await (await self.client.get("/api/pro/library?q=测试")).json()
        r = await self.client.post(
            "/api/pro/music", json={"track_id": catalog["items"][0]["id"]}
        )
        self.assertEqual(r.status, 200)
        self.assertEqual((await r.json())["current"]["title"], "测试")
        await self.client.post("/api/pro/music", json={"stop": True})
        # Same callback path as recognized speech, with silent fake TTS/devices.
        r = await self.client.post("/api/chat", json={"message": "播放测试"})
        self.assertIn("开始播放", (await r.json())["reply"])
        state = await (await self.client.get("/api/pro/status")).json()
        self.assertEqual(state["music"]["current"]["title"], "测试")
        self.assertTrue(state["simulated"])

    async def test_malformed_commands_and_root_are_rejected(self):
        for url, payload in (
            ("/api/pro/library", {"action": "configure", "root": "relative"}),
            ("/api/pro/music", {"track_id": "../../file"}),
            ("/api/pro/music", {"action": "options", "repeat": "bad"}),
        ):
            r = await self.client.post(url, json=payload)
            self.assertEqual(r.status, 400, await r.text())


if __name__ == "__main__":
    unittest.main()
