"""Sound-free regressions for the actual demo command and audio paths."""
import sys
import os
import tempfile
import threading
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'pc-agent-vision'))
from speaker_dsp import limit_peaks, coalesce_speech_chunks
from semantic_control import exact_plan
from music_commands import parse_music_request


class SpeakerLimiterTests(unittest.TestCase):
    def test_speech_peak_bound_preserves_sample_count_and_silence(self):
        from voice_engine import VoiceEngine
        from speaker_dsp import SPEECH_PEAK_CEILING
        engine = VoiceEngine.__new__(VoiceEngine)
        source = (np.sin(np.arange(32000) * .2) * 30000).astype(np.int16)
        result = engine._postprocess_audio_32k(source)
        self.assertEqual(len(result), len(source))
        self.assertLessEqual(float(np.max(np.abs(result.astype(float)))) / 32768,
                             SPEECH_PEAK_CEILING + 1 / 32768)
        np.testing.assert_array_equal(engine._postprocess_audio_32k(np.zeros(1000, dtype=np.int16)),
                                      np.zeros(1000, dtype=np.int16))

    def test_hardware_volume_change_reuses_prepared_speech_pcm(self):
        from voice_engine import VoiceEngine
        with tempfile.TemporaryDirectory(prefix='codex-speech-cache-', dir=os.environ.get('KURISU_TEST_TMP')) as folder:
            with patch.dict(os.environ, {'KURISU_CACHE_DIR': folder}):
                engine = VoiceEngine.__new__(VoiceEngine)
                engine._lock = threading.Lock()
                engine.tts = True
                engine.current_volume = 65
                engine._synthesize_language_chunks = Mock(return_value=np.zeros(3200, dtype=np.int16))
                engine._postprocess_audio_32k = lambda samples: samples
                first = engine._single_language_bundle('已切换为绿灯。', 'zh')
                engine.current_volume = 100
                second = engine._single_language_bundle('已切换为绿灯。', 'zh')
                self.assertEqual(first, second)
                engine._synthesize_language_chunks.assert_called_once()

    def test_control_preparation_only_populates_tts_cache(self):
        from voice_engine import VoiceEngine
        engine = VoiceEngine.__new__(VoiceEngine)
        engine._single_language_bundle = Mock(return_value=(b'pcm', b'wav'))
        self.assertEqual(engine.prepare_control_replies(), 12)
        self.assertEqual(engine._single_language_bundle.call_count, 12)
        languages = [call.args[1] for call in engine._single_language_bundle.call_args_list]
        self.assertEqual(languages, ['zh', 'ja'] * 6)

    def test_loud_sine_remains_a_sine_without_hard_clipping(self):
        t = np.arange(32000) / 32000
        source = 1.2 * np.sin(2 * np.pi * 1000 * t)
        result = limit_peaks(source)
        self.assertLessEqual(float(np.max(np.abs(result))), .8200001)
        spectrum = abs(np.fft.rfft(result[3200:-3200]))
        self.assertLess(spectrum[2400] / spectrum[800], 1e-4)
        clipped = np.clip(source, -.82, .82)
        self.assertGreater(float(np.sqrt(np.mean((result-clipped)**2))), .05)

    def test_isolated_peak_cannot_escape_smooth_gain_envelope(self):
        source = np.full(6400, .1)
        source[3200] = 8
        result = limit_peaks(source)
        self.assertLessEqual(float(np.max(np.abs(result))), .8200001)
        self.assertAlmostEqual(result[0], .1)
        self.assertAlmostEqual(result[-1], .1)
        self.assertLess(float(np.max(np.abs(np.diff(result[2500:3100])))), .002)

    def test_normal_audio_and_silence_are_unchanged(self):
        source = np.linspace(-.3, .3, 1000)
        np.testing.assert_allclose(limit_peaks(source), source)
        np.testing.assert_array_equal(limit_peaks(np.zeros(1000)), np.zeros(1000))

    def test_coalesce_preserves_every_character_and_limits_small_fragments(self):
        chunks = ['第一句。', '第二句。', '第三句。']
        result = coalesce_speech_chunks(chunks)
        self.assertEqual(result, [''.join(chunks)])


class SpokenCommandTests(unittest.TestCase):
    def test_common_game_acknowledgements_already_have_valid_japanese(self):
        from semantic_control import describe_action
        from bilingual_guard import validate_bilingual_alignment
        for gid in (1, 33, 41):
            zh, ja = describe_action({'tool': 'start_game', 'value': gid})
            self.assertTrue(validate_bilingual_alignment(zh, ja)[0], (zh, ja))

    def test_phonetic_game_name_is_resolved_only_in_launch_slot(self):
        for text in ['我想玩贪池蛇', '我想玩摊吃蛇', '打开摊吃蛇游戏']:
            self.assertEqual(exact_plan(text), {'kind': 'control', 'actions': [{'tool': 'start_game', 'value': 33}]})

    def test_questions_negations_and_discussions_never_auto_launch(self):
        for text in ['超级马里奥是一款什么样的游戏？', '我想了解超级马里奥',
                     '我想讨论贪吃蛇', '不要启动贪吃蛇', '假如我想玩超级马里奥会怎样']:
            result = exact_plan(text)
            self.assertFalse(result and result.get('kind') == 'control', text)

    def test_demo_song_spelling_repairs_preserve_negative_requests(self):
        for text in ['不放七里香', '不放Lemon', '不要播放发如雪', '青花瓷是什么歌？']:
            self.assertIsNone(parse_music_request(text))
        for text in ['播放7里香', '播放七理箱']:
            self.assertEqual(parse_music_request(text)['query'], '七里香')
        self.assertEqual(parse_music_request('播放米津玄师的雷门')['query'], '米津玄師的Lemon')
        self.assertEqual(parse_music_request('播放法如学')['query'], '发如雪')

    def make_agent(self):
        from kurisu_agent import KurisuAgent
        memory = Mock()
        memory.recent_turns.return_value = []
        agent = KurisuAgent(controller=types.SimpleNamespace(port='SIMULATION'), voice=Mock(), memory=memory)
        agent.semantic.is_farewell = Mock(return_value=False)
        return agent

    def test_control_interpretation_and_ack_do_not_trigger_second_generation(self):
        agent = self.make_agent()
        agent.semantic.plan = Mock(return_value={'kind': 'control', 'actions': [{'tool': 'set_light_mode', 'value': 3}]})
        agent._execute_action = Mock(return_value={'status': 'ok'})
        agent._converse = Mock(side_effect=AssertionError('Redundant model round-trip'))
        reply = agent.chat('给我西兰花的颜色', speak=False)
        self.assertIn('绿', reply)
        agent.semantic.plan.assert_called_once()
        agent._execute_action.assert_called_once()
        agent._converse.assert_not_called()

    def test_music_stop_does_not_wait_for_farewell_classifier(self):
        agent = self.make_agent()
        agent.music_commands = Mock()
        agent.music_commands.handle.return_value = {'reply': '音乐已停止。', 'speak': False}
        agent.voice.last_speech_timings = {'first_pcm_ms': 9999, 'translation_ms': 9999}
        agent.semantic.is_farewell.side_effect = AssertionError('Do not classify music stop as goodbye')
        agent.chat('停止音乐', speak=False)
        agent.semantic.is_farewell.assert_not_called()
        self.assertNotIn('translation_ms', agent.last_turn_timings)

    def test_translation_cannot_race_unfinished_chinese_synthesis(self):
        from voice_engine import VoiceEngine
        engine = VoiceEngine.__new__(VoiceEngine)
        engine.last_speech_timings = {}
        engine.last_spoken_text = ''
        synthesized = []
        engine._single_language_bundle = lambda text, lang: (synthesized.append(text) or b'zh', b'')
        chinese = '第一句话描述当前实验的步骤和结果。' * 4
        def translate(text):
            self.assertEqual(''.join(synthesized), chinese)
            return '', 'translation unavailable'
        engine._request_japanese_translation = translate
        played = []
        controller = types.SimpleNamespace(set_board_led=lambda *a: True,
            play_audio_stream=lambda chunks, **kw: played.extend(chunks) or True)
        import time
        engine._speak_bilingual_stream(controller, chinese, '', None, time.perf_counter())
        self.assertGreater(len(played), 1)
        self.assertEqual(engine.last_spoken_text, chinese)
        self.assertEqual(engine.last_translation_error, 'translation unavailable')


if __name__ == '__main__':
    unittest.main()
