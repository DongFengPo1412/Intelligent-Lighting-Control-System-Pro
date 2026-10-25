"""Regression tests without loading CUDA/TTS or touching a physical device.

Load the actual classes/functions via AST so importing the production entrypoint
cannot initialize models, open COM ports or start a web server during these tests.
"""
import ast
import asyncio
import concurrent.futures
import json
import os
from pathlib import Path
import queue
import socket
import threading
import time
import types
import unittest
import sys
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1] / 'pc-agent-vision'
sys.path.insert(0, str(ROOT))
from semantic_control import exact_plan, ARGUMENTS, describe_action
from pro_control import ProControlMixin,DIRECT_MODES,integer
from conversation_session import ConversationSession


def load_nodes(filename, names, **scope):
    source = ast.parse((ROOT / filename).read_text(encoding='utf-8'))
    selected = [node for node in source.body if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names]
    module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0)] + selected, type_ignores=[])
    ns = dict(time=time, threading=threading, json=json, queue=queue, asyncio=asyncio, np=np)
    ns.update(ProControlMixin=ProControlMixin,DIRECT_MODES=DIRECT_MODES,os=os,integer=integer)
    ns.update(scope)
    exec(compile(ast.fix_missing_locations(module), filename, 'exec'), ns)
    return ns


class VoiceRegressionTests(unittest.TestCase):
    def test_whisper_text_cannot_wake_without_acoustic_keyword(self):
        listener = self.listener(iter(['助手']))
        listener.is_awake = False
        listener.wake_detector = types.SimpleNamespace(detect=lambda pcm: '')
        listener.whisper_model.transcribe = lambda *a, **k: self.fail('Whisper must not decode standby noise')
        listener._process_utterance(bytes(960))
        self.assertFalse(listener.is_awake)
        self.assertEqual(listener.commands, [])

    def test_wake_text_requires_exact_address_not_homophones(self):
        listener = self.listener(iter([]))
        del listener.__dict__['_check_wake_word']
        for text in ('住手', '出手', '小智', '我在和助手聊天', '助手是什么', '红莉是谁'):
            self.assertFalse(listener._check_wake_word(text)[0], text)
        self.assertEqual(listener._check_wake_word('助手，给我看星空'), (True, '给我看星空'))

    def listener(self, texts):
        import re
        cls = load_nodes('voice_listener.py', {'VoiceListener'}, re=re)['VoiceListener']
        obj = cls.__new__(cls)
        obj._work_lock = threading.Lock()
        obj._pending_prefix = ''
        obj.session=ConversationSession()
        obj.is_awake = True
        obj.wake_detector = types.SimpleNamespace(detect=lambda pcm: "助手")
        obj.is_listening = True
        obj.last_awake_time = time.time()
        obj.whisper_model = types.SimpleNamespace(transcribe=lambda *a, **k: ([types.SimpleNamespace(text=next(texts), no_speech_prob=0)], object()))
        obj._update_board_led = lambda mode: None
        obj.pause = lambda: None
        obj.resume = lambda: None
        obj._check_wake_word = lambda text: (False, text)
        obj.commands = []
        obj.callback = obj.commands.append
        return obj

    def test_split_command_does_not_deadlock_or_execute_prefix(self):
        listener = self.listener(iter(['我想看。', '红灯。']))
        pcm = bytes(960)
        thread = threading.Thread(target=lambda: (listener._process_utterance(pcm), listener._process_utterance(pcm)), daemon=True)
        thread.start()
        thread.join(1)
        self.assertFalse(thread.is_alive(), 'ASR processing deadlocked')
        self.assertEqual(listener.commands, ['我想看红灯。'])
        self.assertEqual(listener._pending_prefix, '')

    def test_unwoken_non_wake_speech_is_silent(self):
        listener = self.listener(iter(['今天天气不错']))
        listener.is_awake = False
        listener._process_utterance(bytes(960))
        self.assertEqual(listener.commands, [])

    def test_wake_and_partial_command_are_joined_with_next_utterance(self):
        listener = self.listener(iter(['助手，我想看。', '红灯。']))
        listener.is_awake = False
        listener._check_wake_word = lambda text: (True, '我想看。') if text.startswith('助手') else (False, text)
        listener._process_utterance(bytes(960))
        self.assertTrue(listener.is_awake)
        self.assertEqual(listener.commands, [])
        listener._process_utterance(bytes(960))
        self.assertEqual(listener.commands, ['我想看红灯。'])

    def test_voice_callback_waits_for_reply_completion(self):
        async def verify():
            completed = []
            async def process(text):
                await asyncio.sleep(0.04)
                completed.append(text)
            scope = load_nodes('web_server.py', {'on_voice_detected'}, server_loop=asyncio.get_running_loop(), process_voice_interaction=process)
            await asyncio.to_thread(scope['on_voice_detected'], '红灯')
            self.assertEqual(completed, ['红灯'])
        asyncio.run(verify())

    def test_wake_timeout_does_not_discard_in_flight_speech(self):
        listener = self.listener(iter([]))
        listener.is_paused = False
        listener.awake_timeout = 10
        listener.last_awake_time = 0
        listener._speech_active = False
        listener._is_processing = False
        listener._utterance_queue = queue.Queue()
        for flag in ('_speech_active', '_is_processing'):
            setattr(listener, flag, True)
            self.assertFalse(listener._expire_idle_wake())
            self.assertTrue(listener.is_awake)
            setattr(listener, flag, False)
        listener._utterance_queue.put(b'pending speech')
        self.assertFalse(listener._expire_idle_wake())
        listener._utterance_queue.get()
        self.assertTrue(listener._expire_idle_wake())
        self.assertFalse(listener.is_awake)

    def test_duplex_keyword_still_requires_exact_asr_confirmation(self):
        listener=self.listener(iter(['住手']))
        del listener.__dict__['_check_wake_word']
        listener.duplex=True;listener.is_paused=True;listener._barge_audio=bytearray()
        cancel=threading.Event()
        listener.controller=types.SimpleNamespace(_network_audio=None,playback_cancel=cancel,
            send_json=lambda command:listener.commands.append(command))
        listener._check_barge(bytes(960))
        self.assertFalse(cancel.is_set());self.assertEqual(listener.commands,[])

    def test_duplex_interrupt_keeps_the_attached_command_for_next_turn(self):
        listener=self.listener(iter(['助手，我想看蓝灯']))
        del listener.__dict__['_check_wake_word']
        listener.duplex=True;listener.is_paused=True;listener._barge_audio=bytearray()
        listener._utterance_queue=queue.Queue();listener.session=ConversationSession(False)
        cancel=threading.Event()
        listener.controller=types.SimpleNamespace(_network_audio=None,playback_cancel=cancel,
            send_json=lambda command:listener.commands.append(command))
        pcm=bytes(960);listener._check_barge(pcm)
        self.assertTrue(cancel.is_set());self.assertEqual(listener.commands,[{'cmd':'audio_abort'}])
        listener._finish_turn('上一轮')
        self.assertTrue(listener.is_awake);self.assertEqual(listener._utterance_queue.get_nowait(),pcm)

    def test_music_resume_keeps_normal_asr_paused_and_only_arms_wake_monitor(self):
        listener=self.listener(iter([]))
        del listener.__dict__['resume']
        calls=[]
        listener.music_wake_ready=True
        listener.controller=types.SimpleNamespace(_music_player=types.SimpleNamespace(running=True),
            enable_mic=calls.append)
        listener.resume()
        self.assertTrue(listener.is_paused)
        self.assertTrue(listener._music_monitor)
        self.assertFalse(listener.is_awake)
        self.assertEqual(calls,[True])

    def test_music_wake_requires_acoustic_and_exact_asr_then_cancels_song(self):
        listener=self.listener(iter(['助手，下一首']))
        del listener.__dict__['_check_wake_word']
        listener.duplex=False;listener.is_paused=True;listener._music_monitor=True
        listener._music_suspended=True;listener._barge_audio=bytearray()
        listener._utterance_queue=queue.Queue()
        music=types.SimpleNamespace(running=True,cancel=threading.Event())
        listener.controller=types.SimpleNamespace(_music_player=music,_network_audio=None,
            playback_cancel=threading.Event(),send_json=listener.commands.append)
        pcm=bytes(960)
        listener._check_barge(pcm)
        self.assertTrue(music.cancel.is_set())
        self.assertEqual(listener.commands,[{'cmd':'audio_abort'}])
        listener.finish_music()
        self.assertTrue(listener.is_awake)
        self.assertFalse(listener._music_monitor)
        self.assertEqual(listener._utterance_queue.get_nowait(),pcm)

    def test_music_without_acoustic_wake_never_transcribes_lyrics(self):
        listener=self.listener(iter([]))
        listener.duplex=False;listener.is_paused=True;listener._music_monitor=True
        listener.wake_detector=types.SimpleNamespace(detect=lambda pcm:'')
        listener.whisper_model.transcribe=lambda *a,**kw:self.fail('Lyrics must not enter ASR')
        listener._check_barge(bytes(960))
        self.assertEqual(listener.commands,[])

    def test_music_wake_repairs_identical_pronunciation_only_after_acoustic_gate(self):
        listener=self.listener(iter(['住手']))
        del listener.__dict__['_check_wake_word']
        listener.duplex=False;listener.is_paused=True;listener._music_monitor=True
        listener._barge_audio=bytearray()
        music=types.SimpleNamespace(running=True,cancel=threading.Event())
        listener.controller=types.SimpleNamespace(_music_player=music,_network_audio=None,
            playback_cancel=threading.Event(),send_json=listener.commands.append)
        listener._check_barge(bytes(960))
        self.assertTrue(music.cancel.is_set())
        self.assertTrue(listener._barge_woke)


class FakeSocket:
    def __init__(self, gateway, ack_on=1, status='ok'):
        self.gateway = gateway
        self.sent = []
        self.ack_on = ack_on
        self.status = status

    def sendto(self, data, address):
        request = json.loads(data)
        self.sent.append(request)
        if len(self.sent) >= self.ack_on:
            pending = self.gateway._pending[request['request_id']]
            pending['result'] = {'request_id': request['request_id'], 'status': self.status}
            pending['event'].set()


class TransportTests(unittest.TestCase):
    def gateway(self, ack_on=1, status='ok'):
        import uuid
        cls = load_nodes('wifi_gateway.py', {'WiFiGateway'}, socket=socket, uuid=uuid)['WiFiGateway']
        obj = cls.__new__(cls)
        obj.port = 8888
        obj.is_running = True
        obj._pending = {}
        obj._pending_lock = threading.Lock()
        obj._send_lock = threading.Lock()
        obj.get_target_ips = lambda: ['192.0.2.1']
        obj.sock = FakeSocket(obj, ack_on, status)
        return obj

    def test_local_send_without_ack_is_failure(self):
        gw = self.gateway(99)
        self.assertFalse(gw.send_command('mode 1', timeout=.001, retries=1))
        self.assertEqual(gw.last_result['error'], 'ack_timeout')
        self.assertEqual(gw._pending, {})

    def test_retry_preserves_request_id(self):
        gw = self.gateway(2)
        self.assertTrue(gw.send_command('countdown 10', timeout=.001))
        self.assertEqual(len({request['request_id'] for request in gw.sock.sent}), 1)

    def test_board_rejection_is_not_success(self):
        gw = self.gateway(status='error')
        self.assertFalse(gw.send_command('mode 18'))

    def test_worldline_stops_on_failed_step(self):
        cls = load_nodes('light_controller.py', {'LightController'})['LightController']
        obj = cls.__new__(cls)
        calls = []
        obj.set_mode = lambda mode: calls.append(mode) or False
        self.assertFalse(obj.trigger_steins_gate())
        self.assertEqual(calls, [28])

    def test_invalid_theme_and_mode_do_not_send(self):
        cls = load_nodes('light_controller.py', {'LightController'})['LightController']
        obj = cls.__new__(cls)
        obj.send_json = lambda payload: self.fail('Invalid command was sent')
        obj.send_raw = lambda payload: self.fail('Invalid theme was sent')
        with self.assertRaises(ValueError):
            obj.set_theme('invalid')
        with self.assertRaises(ValueError):
            obj.set_mode(18)

    def test_playback_preserves_listener_mute_ownership(self):
        clock = types.SimpleNamespace(perf_counter=lambda: 0, monotonic=lambda: 0, sleep=lambda _: None)
        cls = load_nodes('light_controller.py', {'LightController'}, time=clock,
                         sys=types.SimpleNamespace(platform='test'))['LightController']
        for initially_enabled in (False, True):
            obj = cls.__new__(cls)
            obj._lock = threading.RLock()
            obj.playback_cancel=threading.Event()
            obj.is_connected = True
            obj._mic_enabled = initially_enabled
            obj.ser = types.SimpleNamespace(write=lambda _: None, flush=lambda: None,
                                            reset_input_buffer=lambda: None, reset_output_buffer=lambda: None)
            calls = []
            def mic(enable):
                calls.append(enable)
                obj._mic_enabled = enable
                return True
            obj.enable_mic = mic
            count = [0]
            gateway = types.SimpleNamespace(last_result={})
            def status(payload):
                gateway.last_result = {'status':'ok','audio_rx': count[0], 'audio_played': count[0], 'audio_dropped': 0, 'audio_errors': 0}
                count[0] += 16
                return True
            obj.send_json = status
            gateway.request=lambda command:status(json.loads(command)) and dict(gateway.last_result)
            module = types.ModuleType('wifi_gateway')
            module.get_wifi_gateway = lambda: gateway
            sys.modules['wifi_gateway'] = module
            self.assertTrue(obj.play_audio_pcm(bytes(32)))
            self.assertEqual(calls, [False, True] if initially_enabled else [False])

    def test_web_device_failure_is_not_success(self):
        async def verify():
            function = load_nodes('web_server.py', {'device_call'})['device_call']
            with self.assertRaises(ConnectionError):
                await function(lambda: False)
        asyncio.run(verify())


class AgentRegressionTests(unittest.TestCase):
    def test_direct_blue_command_executes_before_model_and_speech(self):
        agent = self.agent()
        agent.voice.speak = lambda *a, **k: self.assertEqual(agent.calls, [('set_light_mode', {'mode': 2})])
        with patch('urllib.request.build_opener', side_effect=AssertionError('Color command must not wait for LLM')):
            result = agent.chat('我想看蓝灯。')
        self.assertIn('蓝灯', result)

    def test_direct_color_parser_does_not_consume_negation_or_questions(self):
        agent = self.agent()
        for text in ('不要变蓝灯', '我不想看蓝灯', '为什么天空是蓝色', '红灯和蓝灯有什么区别', '我想看蓝灯但是别切换'):
            self.assertIsNone((exact_plan(text)['actions'][0]['value'] if exact_plan(text) else None), text)
        for text in ('我想看蓝灯', '换成蓝色', '请帮我切换成蓝灯', '蓝灯'):
            self.assertEqual((exact_plan(text)['actions'][0]['value'] if exact_plan(text) else None), 2, text)

    def test_direct_color_rejection_is_not_spoken_as_success(self):
        agent = self.agent()
        agent._execute_action = lambda *a: {'status': 'error'}
        self.assertIn('没有确认', agent.chat('我想看蓝灯'))

    def agent(self):
        import re
        calls = []
        cls = load_nodes('kurisu_agent.py', {'KurisuAgent'}, re=re, ARGUMENTS=ARGUMENTS, describe_action=describe_action,
                         execute_tool=lambda name, args: calls.append((name, args)) or {'status': 'success'},
                         LIGHT_TOOL_DEFINITIONS=[])['KurisuAgent']
        obj = cls.__new__(cls)
        obj._tool_results = {}
        obj._chat_lock = threading.Lock()
        obj.history = [{'role': 'system', 'content': 'persona'}]
        obj.memory=types.SimpleNamespace(append_turn=lambda *a:None,search=lambda *a:[],remember=lambda *a,**k:None)
        obj.calls = calls
        obj.api_base = 'http://localhost:11434/v1'
        obj.api_key = 'test'
        obj.model = 'test'
        obj.semantic = types.SimpleNamespace(plan=lambda text, context: exact_plan(text) or {'kind': 'chat', 'actions': []})
        obj.spoken = []
        obj.voice = types.SimpleNamespace(_split_zh_ja=lambda text: (text, ''),
                                         _translate_zh_to_ja_kurisu=lambda text: '',
                                         speak=lambda text, **kwargs: obj.spoken.append(text))
        return obj

    def test_actions_are_deduplicated_within_turn(self):
        agent = self.agent()
        for _ in range(2):
            agent._execute_action('start_countdown', {'seconds': 10})
        self.assertEqual(len(agent.calls), 1)

    def test_history_retains_whole_turns_and_persona(self):
        agent = self.agent()
        for i in range(20):
            agent.history += [{'role': 'user', 'content': str(i)}, {'role': 'assistant', 'content': 'ok'}]
        agent._chat_locked = lambda text: text
        agent.chat('next')
        self.assertEqual(agent.history[0]['role'], 'system')
        self.assertEqual(agent.history[1]['role'], 'user')
        self.assertLessEqual(len(agent.history), 23)

    def test_concurrent_chat_is_serialized(self):
        agent = self.agent()
        active = []
        def chat(text):
            active.append(text)
            self.assertEqual(len(active), 1)
            time.sleep(.01)
            active.remove(text)
            return text
        agent._chat_locked = chat
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            self.assertEqual(list(pool.map(agent.chat, ['one', 'two'])), ['one', 'two'])

    def test_translation_failure_has_no_fixed_japanese_or_speech(self):
        agent = self.agent()
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self): return json.dumps({'message': {'content': '今天过得怎么样？'}}).encode()
        opener = types.SimpleNamespace(open=lambda *a, **k: Response())
        with patch('urllib.request.build_opener', return_value=opener):
            result = agent.chat('你好')
        self.assertEqual(result, '今天过得怎么样？')
        self.assertTrue(agent.last_translation_error)
        self.assertEqual(agent.spoken, [])


class AudioLevelTests(unittest.TestCase):
    def test_speech_level_is_audible_bounded_and_silence_stays_silent(self):
        import scipy.signal
        cls = load_nodes('voice_engine.py', {'VoiceEngine'}, scipy=__import__('scipy'), _HAS_NOISEREDUCE=False)['VoiceEngine']
        obj = cls.__new__(cls)
        obj.current_volume = 90
        t = np.arange(32000) / 32000
        source = np.sin(2 * np.pi * 300 * t) * .30
        source[1000] = .8
        result = obj._postprocess_audio_32k(source)
        self.assertGreater(np.sqrt(np.mean(result.astype(float) ** 2)), 2500)
        self.assertLessEqual(np.max(np.abs(result)), 29000)
        self.assertFalse(np.any(obj._postprocess_audio_32k(np.zeros(32000))))


if __name__ == '__main__':
    unittest.main(verbosity=2)
