"""T03 dynamic bilingual alignment, chunking, fail-silent, and T02 address-priority tests."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pc-agent-vision"))

from bilingual_guard import (
    chunk_sentences_safe,
    clean_production_prose,
    split_bilingual_text,
    translate_zh_to_ja,
    validate_bilingual_alignment,
)
from kurisu_agent import KurisuAgent
from memory_store import MemoryStore, parse_preference_action
from semantic_control import describe_action
from simulator import SimulatedController, SilentVoice


def _temp_dir() -> tempfile.TemporaryDirectory:
    base = os.environ.get("KURISU_TEST_TMP")
    if base:
        Path(base).mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=base)
    return tempfile.TemporaryDirectory()


class T02AddressPriorityTests(unittest.TestCase):
    """Verify real name vs preferred form of address priority across storage, search, restart, and prompt."""

    def test_separate_and_compound_name_vs_nickname_priority(self):
        with _temp_dir() as tmp:
            db_path = Path(tmp) / "addr.sqlite3"
            store = MemoryStore(db_path)
            try:
                store.remember_preference("我的名字是林达。")
                store.remember_preference("以后请叫我冈伦。")

                profile = store.user_address_profile()
                self.assertEqual(profile["real_name"], "林达")
                self.assertEqual(profile["preferred_address"], "冈伦")

                # Address queries MUST rank preferred_address ("冈伦") strictly first
                for q in ("我现在让你叫我什么？", "你怎么称呼我？", "你管我叫什么？"):
                    hits = store.search(q)
                    self.assertGreaterEqual(len(hits), 1, q)
                    self.assertIn("冈伦", hits[0]["text"], q)

                # Real-name queries MUST rank real_name ("林达") strictly first
                for q in ("我的本名叫什么？", "我的名字叫什么？"):
                    hits = store.search(q)
                    self.assertGreaterEqual(len(hits), 1, q)
                    self.assertIn("林达", hits[0]["text"], q)
            finally:
                store.close()

            # Cross-restart verification on fresh connection
            reopened = MemoryStore(db_path)
            try:
                self.assertEqual(
                    reopened.user_address_profile(),
                    {"preferred_address": "冈伦", "real_name": "林达"},
                )
                # Revoking nickname falls back cleanly without deleting real name
                reopened.remember_preference("不用再叫我冈伦了。")
                self.assertEqual(
                    reopened.user_address_profile(),
                    {"preferred_address": None, "real_name": "林达"},
                )
            finally:
                reopened.close()

    def test_compound_sentence_and_non_self_guard(self):
        self.assertIsNone(parse_preference_action("我叫你助手"))
        with _temp_dir() as tmp:
            store = MemoryStore(Path(tmp) / "compound.sqlite3")
            try:
                store.remember_preference("我的本名是林达，但希望被称作冈伦。")
                self.assertEqual(
                    store.user_address_profile(),
                    {"preferred_address": "冈伦", "real_name": "林达"},
                )
            finally:
                store.close()

    def test_converse_injects_explicit_address_priority_block(self):
        with _temp_dir() as tmp:
            store = MemoryStore(Path(tmp) / "agent_addr.sqlite3")
            try:
                store.remember_preference("我的名字是林达。")
                store.remember_preference("以后请叫我冈伦。")
                captured_payloads = []

                class FakeResp:
                    def __enter__(self):
                        return self

                    def __exit__(self, *args):
                        pass

                    def read(self):
                        return json.dumps(
                            {"message": {"content": "既然你指定了，我现在当然叫你冈伦。"}}
                        ).encode("utf-8")

                def fake_open(req, timeout=40):
                    captured_payloads.append(json.loads(req.data.decode("utf-8")))
                    return FakeResp()

                voice = SilentVoice()
                voice._translate_zh_to_ja_kurisu = (
                    lambda zh: "指定されたんだから、今はオカリンって呼ぶわ。"
                )
                agent = KurisuAgent(
                    controller=SimulatedController(),
                    voice=voice,
                    memory=store,
                )
                agent.semantic.plan = lambda text, ctx=(): {"kind": "chat", "actions": []}

                with patch(
                    "urllib.request.build_opener",
                    return_value=types.SimpleNamespace(open=fake_open),
                ):
                    reply = agent.chat("我现在让你叫我什么？", speak=False)

                self.assertIn("冈伦", reply)
                self.assertIn("オカリン", reply)
                sys_prompt = captured_payloads[0]["messages"][0]["content"]
                self.assertIn("当前生效的用户指定称呼：「冈伦」", sys_prompt)
                self.assertIn("严禁误答为用户的本名「林达」", sys_prompt)
            finally:
                store.close()


class T03BilingualThirtyCasesTests(unittest.TestCase):
    """30-case offline contract suite: 10 general chat + 10 numbers/commands/negation + 10 long/names/failures."""

    # =========================================================================
    # Group A: 10 General Chat & Output Sanitization Cases (C01 - C10)
    # =========================================================================

    def test_c01_general_scientific_greeting_alignment(self):
        zh = "早上好，我刚泡好黑咖啡准备整理实验数据。"
        ja = "おはよう、ちょうどブラックコーヒーを淹れて実験データを整理するところよ。"
        ok, reason = validate_bilingual_alignment(zh, ja)
        self.assertTrue(ok, reason)

    def test_c02_rejects_unprompted_assistant_catchphrase_in_ja(self):
        zh = "今天下午我们可以一起核对神经脉冲实验的记录。"
        ja = "今日の午後は神経パルスの記録を確認しましょう。助手じゃないって言ってるでしょ！"
        ok, reason = validate_bilingual_alignment(zh, ja)
        self.assertFalse(ok)
        self.assertIn("助手", reason)

    def test_c03_rejects_unprompted_baka_in_ja(self):
        zh = "这个问题可以从相对论和因果律两个角度来分析。"
        ja = "この問題は相対性理論と因果律の二つの視点から分析できるわ、このバカ！"
        ok, reason = validate_bilingual_alignment(zh, ja)
        self.assertFalse(ok)
        self.assertIn("バカ", reason)

    def test_c04_rejects_hallucinated_characters_mayuri_or_okabe(self):
        zh = "我最喜欢的周边是金属乌帕，那只是因为它的工业设计很精致。"
        ja = "私が一番好きなグッズはメタルうーぱよ、真由理には内緒にしてね。"
        ok, reason = validate_bilingual_alignment(zh, ja)
        self.assertFalse(ok)
        self.assertIn("真由理", reason)

    def test_c05_strips_pseudo_tool_calls_from_prose(self):
        dirty = "哼，心情还行吧。（set_kurisu_pet()）[set_light_mode(15)] <tool_call>{\"name\":\"x\"}</tool_call>"
        cleaned = clean_production_prose(dirty, lang="zh")
        self.assertEqual(cleaned, "哼，心情还行吧。")

    def test_c06_strips_stage_directions_while_preserving_canonical_parens(self):
        dirty_zh = "（嘴角微微上扬）电话微波炉（暂定）本质上是时间机器原型。（推眼镜）"
        self.assertEqual(
            clean_production_prose(dirty_zh, lang="zh"),
            "电话微波炉（暂定）本质上是时间机器原型。",
        )
        dirty_ja = "（顔を赤らめて）電話レンジ（仮）はタイムマシンの試作機よ。（笑）"
        self.assertEqual(
            clean_production_prose(dirty_ja, lang="ja"),
            "電話レンジ（仮）はタイムマシンの試作機よ。",
        )

    def test_c07_strips_kaomoji_and_ascii_slang_noise(self):
        dirty = "刚才那个实验结果真是太漂亮了！キタ━━━(゜∀゜)━━━!! (>﹏<) orz"
        cleaned = clean_production_prose(dirty, lang="zh")
        self.assertEqual(cleaned, "刚才那个实验结果真是太漂亮了！")

    def test_c08_strips_dual_speaker_self_roleplay_lines(self):
        dirty = "早上好，我已经喝过咖啡了。\n用户：你今天有什么实验安排？\n---\n备注：无关内容"
        cleaned = clean_production_prose(dirty, lang="zh")
        self.assertEqual(cleaned, "早上好，我已经喝过咖啡了。")

    def test_c09_rejects_male_first_person_pronoun_in_kurisu_ja(self):
        zh = "我今年18岁，在脑科学研究所负责记忆编码课题。"
        ja = "僕は18歳で、脳科学研究所で記憶符号化の研究をしているよ。"
        ok, reason = validate_bilingual_alignment(zh, ja)
        self.assertFalse(ok)
        self.assertIn("第一人称", reason)

    def test_c10_rejects_mixed_chinese_particles_and_wrong_kurisu_kanji(self):
        zh = "我的全名是牧濑红莉栖。"
        ja = "我的全名は牧瀬紅里菜です。"
        ok, _ = validate_bilingual_alignment(zh, ja)
        self.assertFalse(ok)

    # =========================================================================
    # Group B: 10 Numbers, Commands, Colors & Negations Cases (N01 - N10)
    # =========================================================================

    def test_n01_countdown_seconds_alignment(self):
        zh = "已开始60秒沙漏倒计时。"
        self.assertTrue(validate_bilingual_alignment(zh, "60秒のカウントダウンを始めたわ。")[0])
        self.assertTrue(validate_bilingual_alignment(zh, "1分のカウントダウンを始めたわ。")[0])
        self.assertFalse(validate_bilingual_alignment(zh, "30秒のカウントダウンを始めたわ。")[0])

    def test_n02_duration_minutes_alignment(self):
        zh = "实验预热还需要2分钟。"
        self.assertTrue(validate_bilingual_alignment(zh, "実験の予熱にはあと2分必要よ。")[0])
        self.assertTrue(validate_bilingual_alignment(zh, "実験の予熱にはあと120秒必要よ。")[0])
        self.assertFalse(validate_bilingual_alignment(zh, "実験の予熱にはあと5分必要よ。")[0])

    def test_n03_worldline_decimal_precision_alignment(self):
        zh = "命运石之门的世界线变动率是1.048596%。"
        self.assertTrue(
            validate_bilingual_alignment(zh, "シュタインズ・ゲートの世界線変動率は1.048596%よ。")[0]
        )
        self.assertFalse(
            validate_bilingual_alignment(zh, "シュタインズ・ゲートの世界線変動率は1.04859%よ。")[0]
        )

    def test_n04_multiple_integers_alignment(self):
        zh = "我17岁发表了论文，现在18岁。"
        self.assertTrue(
            validate_bilingual_alignment(zh, "私は17歳で論文を発表して、今は18歳よ。")[0]
        )
        self.assertFalse(
            validate_bilingual_alignment(zh, "私は論文を発表して、今は18歳よ。")[0]
        )

    def test_n05_color_preference_fidelity(self):
        zh = "你现在最喜欢的颜色是墨绿色，不再是深蓝色了。"
        self.assertTrue(
            validate_bilingual_alignment(
                zh, "あなたが今一番好きな色はダークグリーンで、もうダークブルーじゃないわ。"
            )[0]
        )
        self.assertFalse(
            validate_bilingual_alignment(
                zh, "あなたが今一番好きな色はピンクで、もう黄色じゃないわ。"
            )[0]
        )

    def test_n06_all_deterministic_control_descriptions_pass_alignment(self):
        actions = [
            {"tool": "set_light_mode", "value": 1},
            {"tool": "set_light_mode", "value": 2},
            {"tool": "set_light_mode", "value": 7},
            {"tool": "set_light_mode", "value": 23},
            {"tool": "start_countdown", "value": 90},
            {"tool": "stop_countdown", "value": None},
            {"tool": "trigger_steins_gate_worldline", "value": None},
            {"tool": "set_brightness", "value": 35},
            {"tool": "set_volume", "value": 75},
        ]
        for act in actions:
            zh, ja = describe_action(act)
            ok, reason = validate_bilingual_alignment(zh, ja)
            self.assertTrue(ok, f"{act}: {reason}")

    def test_n07_rejects_unrequested_hardware_control_promise_in_ja(self):
        zh = "蓝色确实会让人觉得安静放松。"
        ja = "青は落ち着く色ね、青いライトに切り替えたわ。"
        ok, reason = validate_bilingual_alignment(zh, ja)
        self.assertFalse(ok)
        self.assertIn("硬件执行承诺", reason)

    def test_n08_explicit_assistant_negation_alignment(self):
        zh = "都说了我不是助手，把实验步骤拿给我看看吧。"
        self.assertTrue(
            validate_bilingual_alignment(
                zh, "助手じゃないって言ってるでしょ、実験の手順を見せてみなさい。"
            )[0]
        )
        self.assertFalse(
            validate_bilingual_alignment(
                zh, "私はあなたの助手よ、実験の手順を見せてみなさい。"
            )[0]
        )

    def test_n09_weather_inability_negation_alignment(self):
        zh = "我没有接入实时天气数据，不清楚今天外面是不是晴天。"
        self.assertTrue(
            validate_bilingual_alignment(
                zh, "リアルタイムの天気データには接続していないから、外が晴れかどうかはわからないわ。"
            )[0]
        )
        self.assertFalse(
            validate_bilingual_alignment(zh, "今日の外は快晴で日差しが気持ちいいわよ。")[0]
        )

    def test_n10_revoked_preference_negation_alignment(self):
        zh = "我记得你已经不再喜欢银白色了。"
        self.assertTrue(
            validate_bilingual_alignment(zh, "もうシルバーホワイトは好きじゃないって覚えているわ。")[0]
        )
        self.assertFalse(
            validate_bilingual_alignment(zh, "今でもシルバーホワイトが大好きなのよね。")[0]
        )

    # =========================================================================
    # Group C: 10 Long Chunking, Mixed Names, & Failure/Cache Isolation (F01 - F10)
    # =========================================================================

    def test_f01_long_text_sentence_chunking_utf8_and_number_safety(self):
        long_zh = (
            "电话微波炉（暂定）在特定条件下能够产生微型克尔黑洞，将36字节以内的电子邮件发送到过去。"
            "当世界线变动率跨过1.048596%的临界点时，因果律收束会发生改变，所以我们必须严谨记录每一次实验观测数据！"
        )
        chunks = chunk_sentences_safe(long_zh, max_chars=70)
        self.assertGreaterEqual(len(chunks), 2)
        for ch in chunks:
            self.assertLessEqual(len(ch), 70)
            self.assertEqual(ch.encode("utf-8").decode("utf-8"), ch)
        rejoined = "".join(chunks)
        self.assertIn("1.048596%", rejoined)
        self.assertIn("36字节", rejoined)

    def test_f02_unpunctuated_multiline_zh_ja_split_preserves_line_boundary(self):
        raw = "今天下午一起整理脑科学数据吧\n今日の午後は一緒に脳科学のデータを整理しましょう"
        zh, ja = split_bilingual_text(raw)
        self.assertEqual(zh, "今天下午一起整理脑科学数据吧")
        self.assertEqual(ja, "今日の午後は一緒に脳科学のデータを整理しましょう")

    def test_f03_mixed_proper_nouns_linda_okarin_nakabachi_fidelity(self):
        zh = "虽然你的本名是林达，但我会按约定叫你冈伦。"
        self.assertTrue(
            validate_bilingual_alignment(
                zh, "あなたの本名はリンダだけど、約束通りオカリンって呼ぶわ。"
            )[0]
        )
        # Missing リンダ or オカリン must fail
        self.assertFalse(
            validate_bilingual_alignment(zh, "約束通りオカリンって呼ぶわ。")[0]
        )
        self.assertFalse(
            validate_bilingual_alignment(zh, "あなたの本名はリンダよ。")[0]
        )

    def test_f04_translate_zh_to_ja_recovers_on_single_corrective_retry(self):
        responses = [
            # Attempt 1: drifts by inserting unprompted バカ
            {"message": {"content": "実験データを一緒に確認しましょう、このバカ！"}},
            # Attempt 2: faithful aligned Japanese
            {"message": {"content": "実験データを一緒に確認しましょう。"}},
        ]
        idx = [0]

        class Resp:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def read(self):
                item = responses[idx[0]]
                idx[0] += 1
                return json.dumps(item).encode("utf-8")

        with patch(
            "urllib.request.build_opener",
            return_value=types.SimpleNamespace(open=lambda *a, **k: Resp()),
        ):
            ja, err = translate_zh_to_ja("我们一起核对实验数据吧。", api_base="http://127.0.0.1:11434/v1")
        self.assertIsNone(err)
        self.assertEqual(ja, "実験データを一緒に確認しましょう。")
        self.assertEqual(idx[0], 2)

    def test_f05_translation_network_failure_is_fail_silent_with_error_flag(self):
        with _temp_dir() as tmp:
            store = MemoryStore(Path(tmp) / "f05.sqlite3")
            try:
                spoken = []
                voice = SilentVoice(api_base="http://127.0.0.1:11434/v1", enable_translation=True)
                voice.speak = lambda text, **kw: spoken.append(text)
                agent = KurisuAgent(controller=SimulatedController(), voice=voice, memory=store)
                agent.semantic.plan = lambda text, ctx=(): {"kind": "chat", "actions": []}

                call_n = [0]

                class ConverseResp:
                    def __enter__(self):
                        return self

                    def __exit__(self, *args):
                        pass

                    def read(self):
                        return json.dumps({"message": {"content": "当然可以，把实验方案发给我看看。"}}).encode("utf-8")

                def fake_open(req, timeout=40):
                    call_n[0] += 1
                    if call_n[0] == 1:
                        return ConverseResp()
                    raise TimeoutError("translation endpoint timed out")

                with patch.dict(os.environ, {"KURISU_SIMULATE": "0"}):
                    with patch(
                        "urllib.request.build_opener",
                        return_value=types.SimpleNamespace(open=fake_open),
                    ):
                        reply = agent.chat("能帮我看一下实验方案吗？", speak=True)

                self.assertEqual(reply, "当然可以，把实验方案发给我看看。")
                self.assertNotIn("\n", reply)
                self.assertEqual(spoken, [])
                self.assertIn("动态中译日请求失败", agent.last_translation_error)
            finally:
                store.close()

    def test_f06_translation_unaligned_after_retry_is_fail_silent(self):
        bad_resp = {"message": {"content": "今日の午後は真由理と買い物に行くわ、バカ！"}}

        class Resp:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def read(self):
                return json.dumps(bad_resp).encode("utf-8")

        with patch(
            "urllib.request.build_opener",
            return_value=types.SimpleNamespace(open=lambda *a, **k: Resp()),
        ):
            ja, err = translate_zh_to_ja("实验需要60秒预热。", api_base="http://127.0.0.1:11434/v1")
        self.assertEqual(ja, "")
        self.assertIn("未通过等义校验", err)

    def test_f07_empty_model_response_reports_error_without_tts(self):
        with _temp_dir() as tmp:
            store = MemoryStore(Path(tmp) / "f07.sqlite3")
            try:
                spoken = []
                voice = SilentVoice()
                voice.speak = lambda text, **kw: spoken.append(text)
                agent = KurisuAgent(controller=SimulatedController(), voice=voice, memory=store)
                agent.semantic.plan = lambda text, ctx=(): {"kind": "chat", "actions": []}

                class EmptyResp:
                    def __enter__(self):
                        return self

                    def __exit__(self, *args):
                        pass

                    def read(self):
                        return json.dumps({"message": {"content": "   "}}).encode("utf-8")

                with patch(
                    "urllib.request.build_opener",
                    return_value=types.SimpleNamespace(open=lambda *a, **k: EmptyResp()),
                ):
                    reply = agent.chat("你好", speak=True)

                self.assertIn("本地模型暂时无法回复", reply)
                self.assertIn("Empty model response", agent.last_model_error)
            finally:
                store.close()

    def _build_stub_voice_engine(self, data_root: Path, tts_fn):
        """Construct VoiceEngine without loading CUDA/GPT-SoVITS weights or playing sound."""
        import threading
        from voice_engine import VoiceEngine

        eng = VoiceEngine.__new__(VoiceEngine)
        eng._lock = threading.RLock()
        eng.current_volume = 75
        eng.api_base = "http://127.0.0.1:11434/v1"
        eng.model = "kurisu"
        eng.backend = "ollama"
        eng.last_translation_error = None
        eng.last_tts_error = None
        eng.ref_audio_path = str(ROOT / "pc-agent-vision" / "ref_audio" / "prompt_shy.wav")
        eng.prompt_text = "だから、そういうこと言うなって言ってるでしょ"
        eng.prompt_lang = "ja"
        data_root.mkdir(parents=True, exist_ok=True)
        played = []
        eng.played_pcm = played
        eng.fake_ctrl = types.SimpleNamespace(
            audio_connected=True,
            audio_transport="usb",
            set_board_led=lambda *a, **kw: True,
            play_audio_pcm=lambda pcm: played.append(pcm) or True,
        )
        eng.tts = types.SimpleNamespace(run=tts_fn) if tts_fn is not None else None
        return eng

    def test_f08_tts_unavailable_fails_silently_without_sapi_and_sets_error(self):
        with _temp_dir() as tmp:
            data_root = Path(tmp) / "data"
            eng = self._build_stub_voice_engine(data_root, tts_fn=None)
            with patch.dict(os.environ, {"KURISU_DATA_DIR": str(data_root), "KURISU_CACHE_DIR": str(data_root / "cache")}), patch(
                "light_controller.get_light_controller", return_value=eng.fake_ctrl
            ):
                eng.speak("你好。\nこんにちは。", block=True, to_board=True)
            self.assertEqual(eng.played_pcm, [])
            self.assertIn("角色TTS模型未加载", eng.last_tts_error)

            # Also verify source code contains zero SAPI/pyttsx3 fallbacks and accurate comments
            ve_src = (ROOT / "pc-agent-vision" / "voice_engine.py").read_text(encoding="utf-8")
            for forbidden_sapi in ("pyttsx3", "win32com", "SpVoice", "System.Speech", "edge_tts"):
                self.assertNotIn(forbidden_sapi, ve_src)
            self.assertNotIn("零重采样损耗", ve_src)
            self.assertNotIn("正统傲娇日文台词收束", ve_src)
            self.assertIn("self.current_volume = 75", ve_src)
            self.assertIn("prompt_shy.wav", ve_src)

    def test_f09_partial_chunk_tts_failure_neither_caches_nor_plays_partial_audio(self):
        with _temp_dir() as tmp:
            data_root = Path(tmp) / "data"
            voice_cache = data_root / "cache" / "voice"
            calls = []

            def flaky_tts(req):
                calls.append((req["text_lang"], req["text"]))
                if req["text_lang"] == "ja":
                    raise RuntimeError("CUDA OOM on Japanese segment")
                t = np.arange(3200) / 32000.0
                yield 32000, (np.sin(2 * np.pi * 260 * t) * 0.3).astype(np.float32)

            eng = self._build_stub_voice_engine(data_root, tts_fn=flaky_tts)
            with patch.dict(os.environ, {"KURISU_DATA_DIR": str(data_root), "KURISU_CACHE_DIR": str(data_root / "cache")}), patch(
                "light_controller.get_light_controller", return_value=eng.fake_ctrl
            ):
                eng.speak("已开始60秒沙漏倒计时。\n60秒のカウントダウンを始めたわ。", block=True, to_board=True)

            self.assertEqual(len(calls), 2)
            self.assertEqual(calls[0][0], "zh")
            self.assertEqual(calls[1][0], "ja")
            self.assertEqual(eng.played_pcm, [])
            self.assertEqual(list(voice_cache.glob("*.wav")) if voice_cache.exists() else [], [])
            self.assertIn("日文语音分块合成失败", eng.last_tts_error)

    def test_f10_failed_turn_never_replays_previous_turn_cached_audio(self):
        with _temp_dir() as tmp:
            data_root = Path(tmp) / "data"
            voice_cache = data_root / "cache" / "voice"
            should_fail = [False]

            def toggle_tts(req):
                if should_fail[0]:
                    raise RuntimeError("TTS synth failed on turn 2")
                t = np.arange(3200) / 32000.0
                yield 32000, (np.sin(2 * np.pi * 260 * t) * 0.3).astype(np.float32)

            eng = self._build_stub_voice_engine(data_root, tts_fn=toggle_tts)
            with patch.dict(os.environ, {"KURISU_DATA_DIR": str(data_root), "KURISU_CACHE_DIR": str(data_root / "cache")}), patch(
                "light_controller.get_light_controller", return_value=eng.fake_ctrl
            ):
                eng.speak("已切换为蓝灯。\n青いライトに切り替えたわ。", block=True, to_board=True)
                self.assertEqual(len(eng.played_pcm), 1)
                self.assertEqual(len(list(voice_cache.glob("*.wav"))), 1)

                # Turn 2 with different text fails synthesis -> must NOT replay Turn 1's cached WAV/PCM
                eng.played_pcm.clear()
                should_fail[0] = True
                eng.speak("已切换为红灯。\n赤いライトに切り替えたわ。", block=True, to_board=True)
                self.assertEqual(eng.played_pcm, [])
                self.assertIsNotNone(eng.last_tts_error)
                self.assertEqual(len(list(voice_cache.glob("*.wav"))), 1)


class T03WebStatusErrorContractTests(unittest.IsolatedAsyncioTestCase):
    """Verify Web /api/chat and /api/status surface translation_error and tts_error cleanly."""

    async def asyncSetUp(self):
        base = os.environ.get("KURISU_TEST_TMP")
        if base:
            Path(base).mkdir(parents=True, exist_ok=True)
        self.tmp_obj = _temp_dir()
        self.env = patch.dict(
            os.environ,
            {"KURISU_DATA_DIR": self.tmp_obj.name, "KURISU_SIMULATE": "1"},
        )
        self.env.start()
        from aiohttp.test_utils import TestClient, TestServer
        import web_server

        self.web_server = web_server
        self.client = TestClient(TestServer(web_server.create_app(simulate=True)))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()
        self.env.stop()
        self.tmp_obj.cleanup()

    async def test_web_chat_and_status_expose_translation_and_tts_errors(self):
        def fake_chat(msg):
            self.web_server.agent.last_translation_error = "日语翻译未通过等义校验，未使用固定台词替代"
            self.web_server.agent.last_tts_error = "GPT-SoVITS 语音合成未就绪，已静音跳过播报"
            return "这是中文回复。"

        with patch.object(self.web_server.agent, "chat", side_effect=fake_chat):
            resp = await self.client.post("/api/chat", json={"message": "测试双语错误上报"})
            self.assertEqual(resp.status, 200)
            data = await resp.json()
            self.assertEqual(data["reply"], "这是中文回复。")
            self.assertIn("未使用固定台词替代", data["translation_error"])
            self.assertIn("GPT-SoVITS", data["tts_error"])

            st_resp = await self.client.get("/api/status")
            self.assertEqual(st_resp.status, 200)
            st = await st_resp.json()
            self.assertIn("未使用固定台词替代", st["translation_error"])
            self.assertIn("GPT-SoVITS", st["tts_error"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
