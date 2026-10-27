"""Targeted failure and boundary lifecycle tests for VoiceListener, WebServer and Model recovery.
Covers the core lifecycle and recovery requirements for T01:
1. Immediate restart after stop (no duplicate thread leaks, start guards against active threads, no ident recycled assumption)
2. Duplicate / idempotent stop
3. Stop while callback is in flight (stop_pending state, no permanent leak error lockout, recovery allowed)
3b. Worker thread calling stop (retains thread reference, marks pending, guards restart until worker exits)
4. Event loop stop does not deadlock with in-flight worker callback (run_coroutine_threadsafe)
5. Total timeout budget enforcement across lock, pause, and thread waits
6. Model unreachable & recovery via real production WebServer handlers and /api/status route
7. Background warmup task cleanup on shutdown via real production on_startup and on_cleanup
"""
import asyncio
import concurrent.futures
import io
import json
import os
from pathlib import Path
import queue
import shutil
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest.mock import patch

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pc-agent-vision"))

from voice_listener import VoiceListener
from conversation_session import ConversationSession
from semantic_control import SemanticControl
from kurisu_agent import KurisuAgent
from memory_store import MemoryStore
import web_server


class ListenerLifecycleTests(unittest.TestCase):
    def setUp(self):
        tmp_base = os.environ.get("KURISU_TEST_TMP") or tempfile.gettempdir()
        self.tmp_dir = tempfile.mkdtemp(dir=tmp_base, prefix="lifecycle_test_")
        web_server.shutting_down = False
        with web_server.chat_job_lock:
            web_server.active_chat_jobs.clear()
        web_server.active_chat_threads.clear()
        web_server.active_chat_tasks.clear()

    def tearDown(self):
        web_server.shutting_down = False
        with web_server.chat_job_lock:
            web_server.active_chat_jobs.clear()
        web_server.active_chat_threads.clear()
        web_server.active_chat_tasks.clear()
        if os.path.exists(self.tmp_dir):
            try:
                shutil.rmtree(self.tmp_dir, ignore_errors=True)
            except Exception:
                pass

    def _create_isolated_listener(self):
        listener = VoiceListener.__new__(VoiceListener)
        listener.callback = None
        listener.is_listening = False
        listener.is_paused = False
        listener._stop_event = threading.Event()
        listener._ready_event = threading.Event()
        listener._lifecycle_lock = threading.Lock()
        listener.stop_pending = False
        listener.stop_pending_threads = []
        listener._pcm_queue = queue.Queue(maxsize=400)
        listener._utterance_queue = queue.Queue(maxsize=3)
        listener._is_processing = False
        listener._current_led_mode = "listening"
        listener._process_thread = None
        listener._worker_thread = None
        listener._watchdog_thread = None
        listener._work_lock = threading.Lock()
        listener._pending_prefix = ""
        listener._speech_active = False
        listener.is_awake = False
        listener.session = ConversationSession(continuous=False)
        listener.duplex = False
        listener._barge_audio = bytearray()
        listener._barge_last = 0.0
        listener._barge_thread = None
        listener._barge_pending = None
        listener._barge_woke = False
        listener._music_monitor = False
        listener._music_suspended = False
        listener.music_wake_ready = False
        listener.last_awake_time = 0.0
        listener.awake_timeout = 10.0
        listener.has_board_audio = False
        listener._last_board_frame_time = 0.0
        listener._resume_warmup_frames = 0
        listener.vad = types.SimpleNamespace(is_speech=lambda b, r: False)
        listener.wake_detector = types.SimpleNamespace(detect=lambda pcm: "")
        listener.whisper_model = types.SimpleNamespace(transcribe=lambda *a, **k: ([], object()))
        listener._update_board_led = lambda mode: None
        listener.resume = lambda: None
        listener._session_generation = 1
        listener._teardown_thread = None
        listener._heal_attempts = 0
        listener._max_heal_retries = 3
        listener._heal_backoff = 1.0
        listener._last_heal_time = 0.0
        listener._healthy_since = 0.0
        listener._heal_stable_duration = 5.0
        listener._heal_circuit_broken = False
        listener.heal_status = "ok"
        listener.controller = types.SimpleNamespace(
            audio_connected=False,
            connect_audio=lambda: False,
            enable_mic=lambda en: None,
            on_mic_data=None,
            _voice_listener=None
        )
        return listener

    # -------------------------------------------------------------
    # 1. 停止后立即重启（检查对象实例不同与旧线程退出，不假定 ident 不重复）
    # -------------------------------------------------------------
    def test_1_immediate_restart_after_stop(self):
        listener = self._create_isolated_listener()
        
        started = listener.start()
        self.assertTrue(started)
        self.assertTrue(listener.is_listening)
        t_proc_1 = listener._process_thread
        t_work_1 = listener._worker_thread
        t_watch_1 = listener._watchdog_thread
        self.assertIsNotNone(t_proc_1)
        self.assertIsNotNone(t_work_1)
        self.assertIsNotNone(t_watch_1)

        # 验证核心工作线程持续存活（杜绝因标志时序过早退出）
        self.assertTrue(t_proc_1.is_alive(), "启动成功后 process 线程必须持续存活")
        self.assertTrue(t_work_1.is_alive(), "启动成功后 worker 线程必须持续存活")
        self.assertTrue(t_watch_1.is_alive(), "启动成功后 watchdog 线程必须持续存活")

        # 验证工作线程确实能正常消费并处理输入
        input_processed_1 = threading.Event()
        listener._process_utterance = lambda pcm: input_processed_1.set()
        listener._utterance_queue.put_nowait(b"\x00" * 960)
        self.assertTrue(input_processed_1.wait(timeout=2.0), "工作线程启动后必须能实际处理语音输入队列")

        stopped = listener.stop(timeout=1.0)
        self.assertTrue(stopped)
        self.assertFalse(listener.is_listening)

        restarted = listener.start()
        self.assertTrue(restarted)
        self.assertTrue(listener.is_listening)
        
        t_proc_2 = listener._process_thread
        t_work_2 = listener._worker_thread
        t_watch_2 = listener._watchdog_thread
        # 验证新旧线程对象不同，且旧线程确实已经终止
        self.assertIsNot(t_proc_1, t_proc_2)
        self.assertIsNot(t_work_1, t_work_2)
        self.assertIsNot(t_watch_1, t_watch_2)
        self.assertFalse(t_proc_1.is_alive())
        self.assertFalse(t_work_1.is_alive())
        self.assertTrue(t_proc_2.is_alive(), "重启后 process 线程必须持续存活")
        self.assertTrue(t_work_2.is_alive(), "重启后 worker 线程必须持续存活")
        self.assertTrue(t_watch_2.is_alive(), "重启后 watchdog 线程必须持续存活")

        # 验证重启后工作线程依然能实际处理输入
        input_processed_2 = threading.Event()
        listener._process_utterance = lambda pcm: input_processed_2.set()
        listener._utterance_queue.put_nowait(b"\x00" * 960)
        self.assertTrue(input_processed_2.wait(timeout=2.0), "重启后工作线程必须能实际处理语音输入队列")

        listener.stop(timeout=1.0)

    # -------------------------------------------------------------
    # 1c. 监听器部分启动失败原子回滚（连接异常或线程启动异常时完整回滚）
    # -------------------------------------------------------------
    def test_1c_listener_start_failure_rolls_back_cleanly(self):
        listener = self._create_isolated_listener()
        listener.controller.connect_audio = lambda: True

        # 模拟第三个线程 (watchdog) 启动失败
        real_thread_cls = threading.Thread
        def flawed_thread(*args, **kwargs):
            th = real_thread_cls(*args, **kwargs)
            if kwargs.get('name') == "voicelistener_watchdog":
                def flawed_start():
                    raise RuntimeError("Simulated watchdog thread spawn failure")
                th.start = flawed_start
            return th

        with patch('threading.Thread', side_effect=flawed_thread):
            started = listener.start()
            self.assertFalse(started, "部分线程启动异常时 start() 必须返回 False")
            self.assertFalse(listener.is_listening, "启动失败后 is_listening 必须保持 False")

            # 验证先前启动的 process 与 worker 线程被原子级回滚停止并回收
            self.assertIsNone(listener._process_thread)
            self.assertIsNone(listener._worker_thread)
            self.assertIsNone(listener._watchdog_thread)
            self.assertIsNone(listener.controller.on_mic_data, "回滚后麦克风回调必须复位为 None")
            self.assertFalse(listener.stop_pending)
            self.assertEqual(listener.stop_pending_threads, [])

    # -------------------------------------------------------------
    # 1d. 重复启动隔离（存在旧任务或旧监听线程时严禁盲目清空覆盖）
    # -------------------------------------------------------------
    def test_1d_app_reinit_rejected_when_old_tasks_or_threads_alive(self):
        # 1. 存在未完成的 ChatJob 时严禁重新初始化，且拒绝后 shutting_down 状态必须保持不变
        web_server.shutting_down = True
        job = web_server.ChatJob(999, "旧任务", state="running")
        with web_server.chat_job_lock:
            web_server.active_chat_jobs[999] = job

        try:
            with self.assertRaises(RuntimeError, msg="活跃聊天任务未结束时必须拒绝重新初始化"):
                web_server.check_reinit_allowed()

            with self.assertRaises(RuntimeError, msg="活跃聊天任务未结束时 create_app 必须拒绝重新初始化"):
                web_server.create_app(simulate=True)

            self.assertTrue(web_server.shutting_down, "初始化被拒绝后旧服务的 shutting_down 状态必须保持不变！")
        finally:
            job.mark_done("completed")
            with web_server.chat_job_lock:
                web_server.active_chat_jobs.pop(999, None)

        # 2. 存在存活的监听器线程时严禁重新初始化，且拒绝后 shutting_down 状态保持不变
        web_server.shutting_down = True
        live_th = threading.Thread(target=lambda: time.sleep(0.1), daemon=True, name="stubborn_listener")
        live_th.start()
        mock_listener = types.SimpleNamespace(
            has_live_threads=lambda: True,
            _process_thread=live_th,
            _worker_thread=None,
            _watchdog_thread=None,
            _teardown_thread=None
        )
        orig_listener = web_server.listener
        web_server.listener = mock_listener
        try:
            with self.assertRaises(RuntimeError, msg="监听器线程存活时必须拒绝重新初始化"):
                web_server.check_reinit_allowed()
            with self.assertRaises(RuntimeError, msg="监听器线程存活时 create_app 必须拒绝重新初始化"):
                web_server.create_app(simulate=True)
            self.assertTrue(web_server.shutting_down, "监听器线程存活拒绝重建后，shutting_down 必须保持不变！")
        finally:
            live_th.join(timeout=1.0)
            web_server.listener = orig_listener

        # 3. 存在存活的后台模型预热线程时严禁重新初始化
        web_server.shutting_down = True
        warmup_ev = threading.Event()
        warmup_th = threading.Thread(target=warmup_ev.wait, daemon=True, name="kurisu_warmup_attempt_1")
        warmup_th.start()
        try:
            with self.assertRaises(RuntimeError, msg="后台预热线程仍在运行时必须拒绝重新初始化"):
                web_server.check_reinit_allowed()
            with self.assertRaises(RuntimeError, msg="后台预热线程仍在运行时 create_app 必须拒绝重新初始化"):
                web_server.create_app(simulate=True)
            self.assertTrue(web_server.shutting_down, "预热线程存活拒绝重建后，shutting_down 必须保持不变！")
        finally:
            warmup_ev.set()
            warmup_th.join(timeout=1.0)

        # 4. 存在存活的延后清理线程时严禁重新初始化
        web_server.shutting_down = True
        cleanup_ev = threading.Event()
        cleanup_th = threading.Thread(target=cleanup_ev.wait, daemon=True, name="webserver_deferred_cleanup")
        cleanup_th.start()
        try:
            with self.assertRaises(RuntimeError, msg="延后清理线程仍在运行时必须拒绝重新初始化"):
                web_server.check_reinit_allowed()
            with self.assertRaises(RuntimeError, msg="延后清理线程仍在运行时 create_app 必须拒绝重新初始化"):
                web_server.create_app(simulate=True)
            self.assertTrue(web_server.shutting_down, "延后清理线程存活拒绝重建后，shutting_down 必须保持不变！")
        finally:
            cleanup_ev.set()
            cleanup_th.join(timeout=1.0)

        # 5. 旧任务、预热与清理线程已全部退出时，重新初始化允许通过并更新状态
        web_server.check_reinit_allowed()
        app = web_server.create_app(simulate=True, no_audio=True)
        self.assertFalse(web_server.shutting_down, "全部旧资源安全退出后，方可成功重建并放行准入")

    # -------------------------------------------------------------
    # 2. 重复停止（幂等安全）
    # -------------------------------------------------------------
    def test_2_duplicate_stop_is_idempotent(self):
        listener = self._create_isolated_listener()
        listener.start()
        self.assertTrue(listener.is_listening)

        self.assertTrue(listener.stop(timeout=1.0))
        self.assertFalse(listener.is_listening)

        self.assertTrue(listener.stop(timeout=1.0))
        self.assertFalse(listener.is_listening)

        self.assertTrue(listener.stop(timeout=1.0))
        self.assertFalse(listener.is_listening)

    # -------------------------------------------------------------
    # 3. 回调仍在执行（停止超时不等于线程泄漏，保留存活记录与恢复路径）
    # -------------------------------------------------------------
    def test_3_stop_while_callback_in_flight_marks_pending_without_leak_error(self):
        listener = self._create_isolated_listener()
        callback_running = threading.Event()
        callback_release = threading.Event()

        def slow_callback(text):
            callback_running.set()
            callback_release.wait(timeout=2.0)

        listener.callback = slow_callback

        def mock_worker():
            listener._is_processing = True
            try:
                callback_running.set()
                callback_release.wait(timeout=2.0)
            finally:
                listener._is_processing = False

        listener.is_listening = True
        worker_th = threading.Thread(target=mock_worker, daemon=True)
        worker_th.start()
        listener._worker_thread = worker_th

        callback_running.wait(timeout=1.0)
        self.assertTrue(callback_running.is_set())

        t0 = time.monotonic()
        ok = listener.stop(timeout=0.15)
        dt = time.monotonic() - t0
        self.assertLess(dt, 0.45, "Stop exceeded bounded timeout budget")
        self.assertFalse(ok)
        self.assertTrue(listener.stop_pending)
        self.assertIn("worker", listener.stop_pending_threads)
        self.assertFalse(getattr(listener, "has_thread_leak_error", False))

        callback_release.set()
        worker_th.join(timeout=1.0)

        self.assertTrue(listener.check_stopped())
        self.assertFalse(listener.stop_pending)
        self.assertEqual(len(listener.stop_pending_threads), 0)

    # -------------------------------------------------------------
    # 3b. 工作线程自身调用 stop()（保留线程引用、置挂起状态，杜绝新旧线程并存）
    # -------------------------------------------------------------
    def test_3b_worker_thread_calling_stop_retains_reference_and_guards_restart(self):
        listener = self._create_isolated_listener()
        worker_in_stop = threading.Event()
        worker_can_exit = threading.Event()
        stop_results = []

        def worker_body():
            # 由工作线程自身调用 stop
            res = listener.stop(timeout=0.2)
            stop_results.append(res)
            worker_in_stop.set()
            worker_can_exit.wait(timeout=2.0)

        listener.is_listening = True
        worker_th = threading.Thread(target=worker_body, daemon=True)
        listener._worker_thread = worker_th
        worker_th.start()

        worker_in_stop.wait(timeout=1.0)
        self.assertTrue(worker_in_stop.is_set())
        # 工作线程自身调用 stop 不能自 join，且自身仍存活，必须返回 False (挂起)
        self.assertFalse(stop_results[0])
        self.assertTrue(listener.stop_pending)
        self.assertIn("worker", listener.stop_pending_threads)

        # 此时外部调用 start() 必须被拒绝，因为旧工作线程仍存活！
        start_accepted = listener.start()
        self.assertFalse(start_accepted, "start() 必须拒绝在旧 worker 存活时启动新线程组")

        # 允许 worker 退出
        worker_can_exit.set()
        worker_th.join(timeout=1.0)

        # worker 完全退出后，check_stopped 恢复 True，允许启动
        self.assertTrue(listener.check_stopped())
        self.assertFalse(listener.stop_pending)
        self.assertTrue(listener.start())
        listener.stop(timeout=1.0)

    # -------------------------------------------------------------
    # 4. 事件循环参与停止（零死锁）
    # -------------------------------------------------------------
    def test_4_event_loop_stop_does_not_deadlock_with_worker_callback(self):
        listener = self._create_isolated_listener()
        loop = asyncio.new_event_loop()
        callback_started = threading.Event()
        callback_finished = threading.Event()

        async def dummy_voice_interaction():
            await asyncio.sleep(0.05)
            return "ok"

        def worker_callback(text):
            callback_started.set()
            fut = asyncio.run_coroutine_threadsafe(dummy_voice_interaction(), loop)
            fut.result(timeout=2.0)
            callback_finished.set()

        listener.callback = worker_callback

        loop_thread = threading.Thread(target=loop.run_forever, daemon=True)
        loop_thread.start()

        def worker_runner():
            listener._process_utterance(bytes(960))

        listener.is_listening = True
        listener.is_awake = True
        listener._check_wake_word = lambda t: (True, t)
        listener.whisper_model.transcribe = lambda *a, **k: ([types.SimpleNamespace(text="测试指令", no_speech_prob=0)], object())

        worker_t = threading.Thread(target=worker_runner, daemon=True)
        worker_t.start()
        listener._worker_thread = worker_t

        callback_started.wait(timeout=2.0)
        self.assertTrue(callback_started.is_set())

        async def do_stop():
            return await asyncio.to_thread(listener.stop, 1.0)

        fut = asyncio.run_coroutine_threadsafe(do_stop(), loop)
        stop_result = fut.result(timeout=3.0)
        
        callback_finished.wait(timeout=1.0)
        self.assertTrue(callback_finished.is_set())
        worker_t.join(timeout=1.0)

        loop.call_soon_threadsafe(loop.stop)
        loop_thread.join(timeout=1.0)

    # -------------------------------------------------------------
    # 5. 总超时预算真正约束停止全流程（使用真实 pause，验证受管硬件收尾与重启保护）
    # -------------------------------------------------------------
    def test_5_stop_total_timeout_budget_and_hardware_teardown(self):
        listener = self._create_isolated_listener()
        hold_threads = threading.Event()
        hold_threads.set()
        hold_hw = threading.Event()
        hold_hw.set()

        # 放入队列项以验证真实 pause() 瞬间排空队列
        listener._pcm_queue.put(b"test_pcm_frame")
        listener._utterance_queue.put("test_utterance")

        def slow_enable_mic(en):
            if not en and hold_hw.is_set():
                time.sleep(0.15)
        listener.controller.audio_connected = True
        listener.controller.enable_mic = slow_enable_mic

        def slow_loop_1():
            while hold_threads.is_set():
                time.sleep(0.01)

        def slow_loop_2():
            while hold_threads.is_set():
                time.sleep(0.01)

        t1 = threading.Thread(target=slow_loop_1, daemon=True)
        t2 = threading.Thread(target=slow_loop_2, daemon=True)
        t1.start()
        t2.start()

        listener.is_listening = True
        listener._process_thread = t1
        listener._worker_thread = t2

        t0 = time.monotonic()
        # 设定严苛的 50 毫秒总预算
        ok = listener.stop(timeout=0.05)
        elapsed = time.monotonic() - t0

        # 1. 验证全链路受限：总耗时严格约束在 85ms 以内，绝不因硬件收尾或线程等待累加超限
        self.assertLess(elapsed, 0.085, f"Cumulative stop wait {elapsed:.3f}s exceeded strict budget 0.05s")
        self.assertFalse(ok)
        self.assertTrue(listener.stop_pending)
        # 2. 真实 pause 必须已清空队列
        self.assertTrue(listener._pcm_queue.empty())
        self.assertTrue(listener._utterance_queue.empty())
        # 3. 硬件收尾已被正式登记到生命周期管理器中
        th_status = listener.get_thread_status()
        self.assertTrue(th_status["teardown"], "慢速硬件收尾必须被纳入受管线程登记")
        self.assertFalse(listener.is_healthy(), "硬件收尾未完成前 is_healthy 必须为 False")

        # 4. 核心约束：收尾未完成前禁止重启
        self.assertFalse(listener.check_stopped(), "硬件收尾仍存活时 check_stopped 必须返回 False")
        self.assertFalse(listener.start(), "硬件收尾未完成前必须严正拒绝 restart")

        # 5. 释放阻塞并等待收尾完成
        hold_hw.clear()
        hold_threads.clear()
        t1.join(timeout=1.0)
        t2.join(timeout=1.0)
        if listener._teardown_thread:
            listener._teardown_thread.join(timeout=1.0)

        self.assertTrue(listener.check_stopped())
        self.assertFalse(listener.stop_pending)
        self.assertTrue(listener.start())
        listener.stop(timeout=1.0)

    # -------------------------------------------------------------
    # 5b. 会话代次 (session_generation) 隔离：防止旧收尾在新会话后关闭麦克风或篡改指示灯
    # -------------------------------------------------------------
    def test_5b_session_generation_guards_stale_teardown(self):
        listener = self._create_isolated_listener()
        listener._session_generation = 1
        listener.controller.audio_connected = True

        hw_actions = []
        def tracked_enable_mic(en):
            hw_actions.append(('enable_mic', en, listener._session_generation))
        listener.controller.enable_mic = tracked_enable_mic
        listener._update_board_led = lambda mode: hw_actions.append(('led', mode, listener._session_generation))

        # 模拟代次为 1 的旧硬件收尾线程
        old_gen = 1
        stale_executed = threading.Event()

        def stale_hw_teardown():
            # 模拟网络通信延迟：在执行关闭操作前，外部已启动新会话 (代次递增)
            time.sleep(0.05)
            # 执行受代次保护的硬件收尾
            if old_gen != listener._session_generation:
                stale_executed.set()
                return
            if getattr(listener.controller, 'audio_connected', False):
                try:
                    if not listener.duplex and hasattr(listener.controller, 'enable_mic'):
                        listener.controller.enable_mic(False)
                    if old_gen == listener._session_generation:
                        listener._update_board_led("green")
                except Exception:
                    pass
            stale_executed.set()

        t_old_teardown = threading.Thread(target=stale_hw_teardown, daemon=True)
        t_old_teardown.start()

        # 新一轮会话启动：代次自增为 2，开启麦克风并设为 listening
        listener._session_generation = 2
        listener.controller.enable_mic(True)
        listener._update_board_led("listening")

        # 等待旧收尾线程执行完毕
        t_old_teardown.join(timeout=1.0)
        self.assertTrue(stale_executed.is_set())

        # 验证旧收尾未产生破坏性干扰：没有旧代次的 enable_mic(False) 或 led(green)
        for action, val, gen in hw_actions:
            if action == 'enable_mic' and val is False:
                self.fail(f"旧收尾非法关闭了麦克风: {action}={val}, gen={gen}")
            if action == 'led' and val == 'green':
                self.fail(f"旧收尾非法篡改了指示灯: {action}={val}, gen={gen}")

        # 确认新会话的状态完好无损
        self.assertEqual(hw_actions[0], ('enable_mic', True, 2))
        self.assertEqual(hw_actions[1], ('led', 'listening', 2))

    # -------------------------------------------------------------
    # 6. 模型不可达与受控恢复（全链路验证监听自动启动、暂停保护与失败容错）
    # -------------------------------------------------------------
    def test_6_model_unreachable_and_recovery_via_production_code(self):
        loop = asyncio.new_event_loop()

        class FakeVoiceListener:
            def __init__(self):
                self.start_calls = 0
                self.is_listening = False
                self.is_paused = False
                self.stop_pending = False
                self.wake_detector = types.SimpleNamespace(detect=lambda pcm: "")
                self.has_board_audio = True
                self._last_board_frame_time = time.time()
                self.start_return_value = True

            def start(self):
                self.start_calls += 1
                if self.start_return_value:
                    self.is_listening = True
                    return True
                return False

            def is_healthy(self):
                return bool(self.is_listening and not self.is_paused)

            def is_alive(self):
                return self.is_listening

            def has_live_threads(self):
                return self.is_listening

            def get_thread_status(self):
                return {
                    "process": self.is_listening,
                    "worker": self.is_listening,
                    "watchdog": self.is_listening,
                }

            def pause(self, timeout=None):
                self.is_paused = True

            def resume(self):
                self.is_paused = False

            def stop(self, timeout=2.0):
                self.is_listening = False
                return True

        async def run_scenario():
            app = web_server.create_app(simulate=False, no_audio=True)
            fake_listener = FakeVoiceListener()
            web_server.listener = fake_listener

            warmup_attempts = 0
            def fail_first_then_succeed(timeout=30.0, abort_event=None):
                nonlocal warmup_attempts
                warmup_attempts += 1
                if warmup_attempts <= 1:
                    raise RuntimeError("Connection refused: 11434 unreachable")
                return {"status": "ok"}

            server = TestServer(app)
            client = TestClient(server)

            with patch('light_controller.LightController.wait_for_control', return_value=False), \
                 patch('service_discovery.ServiceAdvertisement.start', return_value=None), \
                 patch('service_discovery.ServiceAdvertisement.close', return_value=None), \
                 patch('semantic_control.SemanticControl.warmup', side_effect=fail_first_then_succeed):

                await client.start_server()

                # 等待后台任务首轮失败落盘
                for _ in range(40):
                    if web_server.agent and getattr(web_server.agent, 'model_status', '') == 'error':
                        break
                    await asyncio.sleep(0.05)

                # 1. 验证在首次预热失败时，Web 主服务完全就绪（降级运行），语音监听不启动
                resp = await client.get('/api/status')
                self.assertEqual(resp.status, 200)
                data = await resp.json()
                self.assertFalse(data['model_ready'], "模型失败期间 model_ready 不能为 True")
                self.assertEqual(data['model_status'], 'error')
                self.assertIn("Connection refused", data['model_error'])
                self.assertFalse(data['listener_listening'], "模型失败期间监听器不能处于 listening")
                self.assertEqual(fake_listener.start_calls, 0, "模型失败期间严禁调用 listener.start()")

                # 2. 等待后台受控重试触发（第 2 次尝试成功）
                for _ in range(40):
                    if web_server.agent and getattr(web_server.agent, 'model_ready', False):
                        break
                    await asyncio.sleep(0.1)

                resp2 = await client.get('/api/status')
                self.assertEqual(resp2.status, 200)
                data2 = await resp2.json()
                self.assertTrue(data2['model_ready'], "模型恢复后 model_ready 应为 True")
                self.assertEqual(data2['model_status'], 'ready')
                self.assertIsNone(data2['model_error'])
                # 验证恢复后自动启动监听，且仅启动一次
                self.assertTrue(data2['listener_listening'], "模型恢复后 listener_listening 应自动就绪")
                self.assertEqual(fake_listener.start_calls, 1, "模型恢复后仅应启动监听一次")

                # 3. 验证暂停保护：当监听器处于暂停 (is_paused) 状态时，模型恢复不擅自拉起监听
                fake_listener.is_listening = False
                fake_listener.is_paused = True
                fake_listener.start_calls = 0
                await web_server.background_model_warmup(app, max_retries=1)
                self.assertEqual(fake_listener.start_calls, 0, "暂停状态下模型预热就绪不得擅自启动监听")

                # 4. 验证 start() 失败时的受控容错：不会抛出未捕获异常
                fake_listener.is_paused = False
                fake_listener.is_listening = False
                fake_listener.start_return_value = False
                await web_server.background_model_warmup(app, max_retries=1)
                self.assertEqual(fake_listener.start_calls, 1)
                self.assertFalse(fake_listener.is_listening)

                await client.close()

        orig_listener = web_server.listener
        try:
            loop.run_until_complete(run_scenario())
        finally:
            web_server.listener = orig_listener
            loop.close()

    # -------------------------------------------------------------
    # 6b. 语音依赖缺失时网页服务降级运行（Web 控制直接可用，不阻断网页启动）
    # -------------------------------------------------------------
    def test_6b_missing_voice_dependency_starts_in_degraded_web_mode(self):
        loop = asyncio.new_event_loop()

        async def run_scenario():
            app = web_server.create_app(simulate=False, no_audio=False)
            server = TestServer(app)
            client = TestClient(server)

            # 模拟引入 voice_engine 或 torch 时抛出依赖缺失异常
            def fail_voice_engine():
                raise ImportError("No module named 'torch'")

            with patch('voice_engine.get_voice_engine', side_effect=fail_voice_engine), \
                 patch('light_controller.LightController.wait_for_control', return_value=False), \
                 patch('light_controller.LightController.set_mode', return_value=True), \
                 patch('service_discovery.ServiceAdvertisement.start', return_value=None), \
                 patch('service_discovery.ServiceAdvertisement.close', return_value=None), \
                 patch('semantic_control.SemanticControl.warmup', return_value=None):

                # 启动主服务，验证绝不崩溃阻断，而是顺利完成启动并标记 no_audio
                await client.start_server()
                self.assertTrue(app['no_audio'], "缺少语音依赖时必须自动降级使能 app['no_audio'] = True")

                # 1. 验证 /api/status 正常返回，TTS 状态如实报告为 silent_fallback
                resp = await client.get('/api/status')
                self.assertEqual(resp.status, 200)
                data = await resp.json()
                self.assertEqual(data.get('tts_status'), "silent_fallback", "降级模式下 tts_status 应为 silent_fallback")

                # 2. 验证核心网页直接控制路由（灯效控制等）100% 正常可用
                cmd_resp = await client.post('/api/mode', json={"mode": 1})
                self.assertEqual(cmd_resp.status, 200, "降级模式下网页直接控制接口必须 100% 正常工作")

                await client.close()

        try:
            loop.run_until_complete(run_scenario())
        finally:
            loop.close()

    # -------------------------------------------------------------
    # 6c. 模型重试耗尽后状态如实标记为 unreachable，提供恢复指引并支持手动重试路由
    # -------------------------------------------------------------
    def test_6c_model_unreachable_retry_exhausted_and_manual_retry_route(self):
        loop = asyncio.new_event_loop()

        async def run_scenario():
            app = web_server.create_app(simulate=True, no_audio=True)
            server = TestServer(app)
            client = TestClient(server)

            await client.start_server()

            # 模拟 Ollama 持续不可达
            def fail_warmup(timeout=30.0, abort_event=None):
                raise ConnectionRefusedError("Connection refused: http://localhost:11434 unreachable")

            orig_semantic = web_server.agent.semantic
            web_server.agent.semantic = SemanticControl(api_base="http://localhost:11434/v1")
            try:
                with patch('semantic_control.SemanticControl.warmup', side_effect=fail_warmup):
                    # 触发受控重试耗尽
                    await web_server.background_model_warmup(app, max_retries=2, initial_backoff=0.01)

                    # 验证状态为 unreachable，且恢复操作指引清晰
                    agent = web_server.agent
                    self.assertEqual(agent.model_status, "unreachable")
                    self.assertFalse(agent.model_ready)
                    self.assertIsNotNone(agent.model_recovery_guidance)
                    self.assertIn("ollama serve", agent.model_recovery_guidance)
                    self.assertIn("/api/retry_warmup", agent.model_recovery_guidance)

                    # 验证 /api/status 接口如实展示 unreachable 与 recovery_guidance
                    resp = await client.get('/api/status')
                    self.assertEqual(resp.status, 200)
                    data = await resp.json()
                    self.assertEqual(data["model_status"], "unreachable")
                    self.assertIn("ollama serve", data["model_recovery_guidance"])

                    # 验证手动恢复重试路由 POST /api/retry_warmup
                    retry_resp = await client.post('/api/retry_warmup')
                    self.assertEqual(retry_resp.status, 200)
                    retry_data = await retry_resp.json()
                    self.assertEqual(retry_data["status"], "ok")

                    # 验证重试任务已在后台重新启动
                    new_task = app.get('warmup_task')
                    self.assertIsNotNone(new_task)
                    self.assertFalse(new_task.done())

                    new_task.cancel()
                    try:
                        await new_task
                    except (asyncio.CancelledError, Exception):
                        pass

                    await client.close()
            finally:
                web_server.agent.semantic = orig_semantic

        try:
            loop.run_until_complete(run_scenario())
        finally:
            loop.close()

    # -------------------------------------------------------------
    # 7. 后台预热任务与底层工作线程退出清理（真实阻断与资源回收）
    # -------------------------------------------------------------
    def test_7_background_warmup_cleanup_via_production_code(self):
        loop = asyncio.new_event_loop()

        async def run_scenario():
            app = web_server.create_app(simulate=False, no_audio=True)
            warmup_started = threading.Event()

            def controlled_warmup(timeout=30.0, abort_event=None):
                warmup_started.set()
                if abort_event:
                    # 响应底层中断事件，退出时抛出 InterruptedError
                    if abort_event.wait(timeout=30.0):
                        raise InterruptedError("Warmup aborted cleanly by event")
                else:
                    time.sleep(30.0)

            server = TestServer(app)
            client = TestClient(server)

            with patch('light_controller.LightController.wait_for_control', return_value=False), \
                 patch('service_discovery.ServiceAdvertisement.start', return_value=None), \
                 patch('service_discovery.ServiceAdvertisement.close', return_value=None), \
                 patch('semantic_control.SemanticControl.warmup', side_effect=controlled_warmup):

                await client.start_server()

                warmup_task = app.get('warmup_task')
                self.assertIsNotNone(warmup_task, "生产代码 on_startup 必须真实创建 app['warmup_task']")
                self.assertFalse(warmup_task.done())

                # 确认底层预热线程已进入执行阶段
                warmup_started.wait(timeout=2.0)
                self.assertTrue(warmup_started.is_set())
                warmup_th = app.get('warmup_state', {}).get('thread') or app.get('warmup_thread')
                self.assertIsNotNone(warmup_th, "底层同步工作线程必须被明确记录归属")
                self.assertTrue(warmup_th.is_alive())

                # 退出客户端将触发生产代码 on_cleanup
                await client.close()

                # 验证：1. 异步 Task 包装已结束
                self.assertTrue(warmup_task.done())
                # 验证：2. abort_event 已被置位
                abort_ev = app.get('warmup_state', {}).get('abort_event') or app.get('warmup_abort_event')
                self.assertTrue(abort_ev and abort_ev.is_set())
                # 验证：3. 底层工作线程已被 join 真实退出，绝不遗留无人管理的孤儿工作
                self.assertFalse(warmup_th.is_alive(), "底层工作线程必须在 on_cleanup 中被回收退出")

        try:
            loop.run_until_complete(run_scenario())
        finally:
            loop.close()

    # -------------------------------------------------------------
    # 7b. 预热线程无视取消/底层持续阻塞时的有界退出与资源归属
    # -------------------------------------------------------------
    def test_7b_uncooperative_warmup_thread_timeout_and_resource_tracking(self):
        loop = asyncio.new_event_loop()

        async def run_scenario():
            app = web_server.create_app(simulate=False, no_audio=True)
            warmup_started = threading.Event()
            block_socket = threading.Event()
            block_socket.set()

            def uncooperative_warmup(timeout=30.0, abort_event=None):
                warmup_started.set()
                # 模拟阻塞在底层 socket 网络读取中，不响应任何 abort_event 事件
                while block_socket.is_set():
                    time.sleep(0.02)

            server = TestServer(app)
            client = TestClient(server)

            with patch('light_controller.LightController.wait_for_control', return_value=False), \
                 patch('service_discovery.ServiceAdvertisement.start', return_value=None), \
                 patch('service_discovery.ServiceAdvertisement.close', return_value=None), \
                 patch('semantic_control.SemanticControl.warmup', side_effect=uncooperative_warmup):

                await client.start_server()

                warmup_started.wait(timeout=2.0)
                self.assertTrue(warmup_started.is_set())
                warmup_th = app.get('warmup_state', {}).get('thread')
                self.assertIsNotNone(warmup_th)
                self.assertTrue(warmup_th.is_alive())

                t0 = time.monotonic()
                # 关闭服务触发 on_cleanup，测试对不协作阻塞线程的有界等待
                await client.close()
                elapsed = time.monotonic() - t0

                # 1. 验证有界退出：等待时间受限在 ~1.0s - 1.4s 之间，绝不无限挂起阻塞关停流程
                self.assertLess(elapsed, 1.4, f"Cleanup wait {elapsed:.3f}s exceeded bounded timeout ~1.0s")

                # 2. 验证真实状态报告：绝不虚假宣称线程已回收，如实记录 exit_complete=False
                warmup_st = app.get('warmup_state', {})
                self.assertFalse(warmup_st.get('exit_complete'), "网络持续阻塞时绝不能宣称退出已完成")

                # 3. 验证资源归属：明确保留未响应线程的归属引用，杜绝无主孤儿线程
                self.assertIs(warmup_st.get('unresponsive_thread'), warmup_th)
                self.assertTrue(warmup_th.is_alive(), "未响应线程仍存活并被明确记录")

                # 测试收尾：解除阻塞，回收工作线程
                block_socket.clear()
                warmup_th.join(timeout=1.0)

        try:
            loop.run_until_complete(run_scenario())
        finally:
            loop.close()

    # -------------------------------------------------------------
    # 7c. 监听器停止未完成时的资源保护：优先在活跃事件循环中清理 pro_api，严禁提前关闭 controller，延后安全关闭
    # -------------------------------------------------------------
    def test_7c_cleanup_guards_resources_when_listener_stop_pending(self):
        loop = asyncio.new_event_loop()
        action_log = []

        class MockController:
            def __init__(self):
                self.closed = False
                self.close_calls = 0
                self.actions_while_open = []
            def close(self):
                self.closed = True
                self.close_calls += 1
                action_log.append(('controller_close', time.monotonic()))
            def enable_mic(self, en):
                if self.closed:
                    raise RuntimeError("Controller used after close!")
                self.actions_while_open.append(('enable_mic', en))

        class MockProApi:
            def __init__(self):
                self.tasks_stopped = False
                self.resources_closed = False
                self.stop_tasks_calls = 0
                self.close_resources_calls = 0
            async def stop_tasks(self):
                self.tasks_stopped = True
                self.stop_tasks_calls += 1
                action_log.append(('pro_api_stop_tasks', time.monotonic()))
            def close_resources(self):
                self.resources_closed = True
                self.close_resources_calls += 1
                action_log.append(('pro_api_close_resources', time.monotonic()))
            async def cleanup(self):
                await self.stop_tasks()
                self.close_resources()

        async def run_scenario():
            app = web_server.create_app(simulate=True, no_audio=True)
            mock_ctrl = MockController()
            mock_api = MockProApi()
            orig_controller = web_server.controller
            orig_listener = web_server.listener
            orig_pro_api = web_server.pro_api

            hold_worker = threading.Event()
            hold_worker.set()
            worker_finished = threading.Event()

            # 模拟正在执行慢回调的监听器，尚未退出且持续使用 controller
            class SlowPendingListener:
                def __init__(self):
                    self.stop_pending = False
                    self.stop_pending_threads = []
                    self._worker_thread = None
                    self._process_thread = None
                    self._watchdog_thread = None
                    self._teardown_thread = None
                def stop(self, timeout=2.0):
                    self.stop_pending = True
                    self.stop_pending_threads = ['worker']
                    return False
                def has_live_threads(self):
                    return bool(self._worker_thread and self._worker_thread.is_alive())

            slow_listener = SlowPendingListener()
            def slow_worker_job():
                while hold_worker.is_set():
                    time.sleep(0.01)
                # 在退出前安全使用 controller
                mock_ctrl.enable_mic(False)
                worker_finished.set()

            worker_th = threading.Thread(target=slow_worker_job, daemon=True, name="slow_worker_in_test_7c")
            worker_th.start()
            slow_listener._worker_thread = worker_th

            try:
                server = TestServer(app)
                client = TestClient(server)

                with patch('light_controller.LightController.wait_for_control', return_value=False), \
                     patch('service_discovery.ServiceAdvertisement.start', return_value=None), \
                     patch('service_discovery.ServiceAdvertisement.close', return_value=None):

                    await client.start_server()
                    if web_server.pro_api:
                        await web_server.pro_api.cleanup()
                    web_server.controller = mock_ctrl
                    web_server.pro_api = mock_api
                    web_server.listener = slow_listener

                    # 关闭客户端触发 on_cleanup
                    await client.close()

                    # 1. 验证 pro_api.stop_tasks() 在事件循环仍可用时真实执行
                    cleanup_st = app.get('cleanup_state', {})
                    self.assertTrue(mock_api.tasks_stopped, "pro_api.stop_tasks() 必须在 on_cleanup 开始阶段被真实执行")
                    self.assertEqual(mock_api.stop_tasks_calls, 1)
                    self.assertTrue(cleanup_st.get('pro_api_tasks_stopped'))

                    # 2. 验证监听器 stop 失败时，明确记录退出未完成状态
                    self.assertFalse(cleanup_st.get('listener_stopped'), "监听器未完成 stop 时 listener_stopped 必须为 False")
                    self.assertFalse(cleanup_st.get('exit_complete'), "监听器未完成 stop 时 exit_complete 必须为 False")
                    self.assertTrue(cleanup_st.get('deferred_cleanup_scheduled'), "必须已安排安全延后清理")

                    # 3. 核心断言：在慢工作线程仍存活时，绝不能提前关闭 controller 与共享资源！
                    self.assertFalse(mock_ctrl.closed, "工作线程存活期间严禁提前关闭 controller！")
                    self.assertEqual(mock_ctrl.close_calls, 0)
                    self.assertFalse(mock_api.resources_closed, "工作线程存活期间严禁提前关闭共享资源！")
                    self.assertEqual(mock_api.close_resources_calls, 0)

                    # 4. 释放工作线程，验证其能安全调用 controller 并退出
                    hold_worker.clear()
                    worker_finished.wait(timeout=1.0)
                    self.assertTrue(worker_finished.is_set())
                    self.assertIn(('enable_mic', False), mock_ctrl.actions_while_open)

                    # 5. 验证延后清理线程安全完成了 controller.close() 与 close_resources()
                    deferred_th = cleanup_st.get('deferred_cleanup_thread')
                    if deferred_th:
                        deferred_th.join(timeout=1.0)
                    self.assertTrue(mock_ctrl.closed, "工作线程退出后，延后清理必须已关闭 controller")
                    self.assertEqual(mock_ctrl.close_calls, 1)
                    self.assertTrue(mock_api.resources_closed, "工作线程退出后，延后清理必须已关闭共享资源")
                    self.assertEqual(mock_api.close_resources_calls, 1)

                    # 6. 验证执行顺序：stop_tasks 发生于开始阶段，controller/resources 关闭发生在 worker 退出后
                    event_names = [item[0] for item in action_log]
                    self.assertEqual(event_names[0], 'pro_api_stop_tasks')
                    self.assertIn('controller_close', event_names)
                    self.assertIn('pro_api_close_resources', event_names)
            finally:
                hold_worker.clear()
                worker_th.join(timeout=1.0)
                web_server.controller = orig_controller
                web_server.listener = orig_listener
                web_server.pro_api = orig_pro_api

        try:
            loop.run_until_complete(run_scenario())
        finally:
            loop.close()

    # -------------------------------------------------------------
    # 7d. 工作线程超过等待期限仍不退出：禁止关闭控制器、禁止标记清理完成、继续保留资源归属
    # -------------------------------------------------------------
    def test_7d_deferred_cleanup_timeout_refuses_to_close_controller(self):
        loop = asyncio.new_event_loop()

        class MockController:
            def __init__(self):
                self.closed = False
                self.close_calls = 0
            def close(self):
                self.closed = True
                self.close_calls += 1

        async def run_scenario():
            app = web_server.create_app(simulate=True, no_audio=True)
            mock_ctrl = MockController()
            orig_controller = web_server.controller
            orig_listener = web_server.listener

            never_ending = threading.Event()
            never_ending.set()

            # 模拟持续阻塞且无法在截止时间内退出的工作线程
            def stubborn_worker_job():
                while never_ending.is_set():
                    time.sleep(0.01)

            stubborn_th = threading.Thread(target=stubborn_worker_job, daemon=True, name="stubborn_worker_in_test_7d")
            stubborn_th.start()

            class StubbornListener:
                def __init__(self):
                    self.stop_pending = True
                    self.stop_pending_threads = ['worker']
                    self._worker_thread = stubborn_th
                    self._process_thread = None
                    self._watchdog_thread = None
                    self._teardown_thread = None
                def stop(self, timeout=2.0):
                    return False
                def has_live_threads(self):
                    return True

            stubborn_listener = StubbornListener()

            try:
                server = TestServer(app)
                client = TestClient(server)

                # 将延后清理超时设为 0.1 秒，快速验证有界超时逻辑
                with patch.dict(os.environ, {"KURISU_DEFERRED_CLEANUP_TIMEOUT": "0.1"}), \
                     patch('light_controller.LightController.wait_for_control', return_value=False), \
                     patch('service_discovery.ServiceAdvertisement.start', return_value=None), \
                     patch('service_discovery.ServiceAdvertisement.close', return_value=None):

                    await client.start_server()
                    web_server.controller = mock_ctrl
                    web_server.listener = stubborn_listener

                    t0 = time.monotonic()
                    await client.close()
                    elapsed = time.monotonic() - t0

                    # 1. 验证有界等待已完成且延后清理线程已判定超时
                    cleanup_st = app.get('cleanup_state', {})
                    deferred_th = cleanup_st.get('deferred_cleanup_thread')
                    if deferred_th:
                        deferred_th.join(timeout=1.0)
                        self.assertFalse(deferred_th.is_alive())

                    # 2. 核心约束：线程存活超过等待期限时，禁止关闭控制器！
                    self.assertFalse(mock_ctrl.closed, "工作线程超时仍存活时，严禁关闭控制器！")
                    self.assertEqual(mock_ctrl.close_calls, 0)

                    # 3. 核心约束：禁止标记清理完成，保持未完成状态
                    self.assertFalse(cleanup_st.get('controller_closed'), "禁止将 controller_closed 标记为 True")
                    self.assertFalse(cleanup_st.get('memory_closed'), "禁止将 memory_closed 标记为 True")
                    self.assertFalse(cleanup_st.get('deferred_cleaned'), "禁止将 deferred_cleaned 标记为 True")
                    self.assertFalse(cleanup_st.get('exit_complete'), "禁止将 exit_complete 标记为 True")

                    # 4. 核心约束：继续保留资源归属与未响应存活线程引用
                    self.assertIs(cleanup_st.get('retained_resources', {}).get('controller'), mock_ctrl)
                    self.assertIn(stubborn_th, cleanup_st.get('unresponsive_threads', []))
                    self.assertTrue(stubborn_th.is_alive())
            finally:
                never_ending.clear()
                stubborn_th.join(timeout=1.0)
                web_server.controller = orig_controller
                web_server.listener = orig_listener

        try:
            loop.run_until_complete(run_scenario())
        finally:
            loop.close()

    # -------------------------------------------------------------
    # 7e. 慢语音交互在退出前仍需写记忆：数据库必须在它结束后才关闭 (拆分停止任务与释放共享资源)
    # -------------------------------------------------------------
    def test_7e_slow_voice_interaction_writes_memory_before_db_closed(self):
        loop = asyncio.new_event_loop()
        action_log = []

        async def run_scenario():
            with tempfile.TemporaryDirectory() as tmp_dir:
                db_path = Path(tmp_dir) / "test_memory.sqlite3"
                real_memory = MemoryStore(db_path)

                app = web_server.create_app(simulate=False, no_audio=True)
                orig_controller = web_server.controller
                orig_listener = web_server.listener
                orig_pro_api = web_server.pro_api
                orig_agent = web_server.agent

                class MockController:
                    def __init__(self):
                        self.closed = False
                    def close(self):
                        self.closed = True
                        action_log.append(('controller_close', time.monotonic()))

                mock_ctrl = MockController()

                class MockAgent:
                    def __init__(self, memory, controller):
                        self.memory = memory
                        self.controller = controller
                        self.history = []
                    def _finish_reply(self, reply):
                        # 模拟真实 kurisu_agent.py:143 在语音交互收尾时写记忆
                        action_log.append(('memory_write_start', time.monotonic()))
                        self.history.append({'role': 'assistant', 'content': reply})
                        self.memory.append_turn('assistant', reply)
                        action_log.append(('memory_write_done', time.monotonic()))
                        return reply

                mock_agent = MockAgent(real_memory, mock_ctrl)

                class InstrumentedProApi:
                    def __init__(self, agent):
                        self.agent = agent
                        self.tasks_stopped = False
                        self.resources_closed = False
                    async def stop_tasks(self):
                        self.tasks_stopped = True
                        action_log.append(('pro_api_stop_tasks', time.monotonic()))
                    def close_resources(self):
                        self.resources_closed = True
                        action_log.append(('pro_api_close_resources', time.monotonic()))
                        if self.agent.memory:
                            self.agent.memory.close()
                    async def cleanup(self):
                        await self.stop_tasks()
                        self.close_resources()

                pro_api_inst = InstrumentedProApi(mock_agent)

                hold_worker = threading.Event()
                hold_worker.set()
                worker_finished = threading.Event()
                worker_error = []

                def slow_voice_worker():
                    try:
                        # 模拟正在进行的语音回调识别与大模型思考
                        while hold_worker.is_set():
                            time.sleep(0.01)
                        # 在交互收尾时写入记忆数据库（此时关停可能已经发起）
                        mock_agent._finish_reply("牧濑红莉栖的退出前语音记忆")
                    except Exception as ex:
                        worker_error.append(ex)
                    finally:
                        action_log.append(('worker_exit', time.monotonic()))
                        worker_finished.set()

                worker_th = threading.Thread(target=slow_voice_worker, daemon=True, name="slow_voice_worker_in_7e")
                worker_th.start()

                class SlowVoiceListener:
                    def __init__(self):
                        self.stop_pending = False
                        self.stop_pending_threads = []
                        self._worker_thread = worker_th
                        self._process_thread = None
                        self._watchdog_thread = None
                        self._teardown_thread = None
                    def stop(self, timeout=2.0):
                        self.stop_pending = True
                        self.stop_pending_threads = ['worker']
                        action_log.append(('listener_stop_called', time.monotonic()))
                        return False
                    def has_live_threads(self):
                        return bool(self._worker_thread and self._worker_thread.is_alive())

                slow_listener = SlowVoiceListener()

                try:
                    server = TestServer(app)
                    client = TestClient(server)

                    with patch('light_controller.LightController.wait_for_control', return_value=False), \
                         patch('service_discovery.ServiceAdvertisement.start', return_value=None), \
                         patch('service_discovery.ServiceAdvertisement.close', return_value=None):

                        await client.start_server()
                        if web_server.pro_api:
                            await web_server.pro_api.cleanup()

                        web_server.controller = mock_ctrl
                        web_server.pro_api = pro_api_inst
                        web_server.listener = slow_listener
                        web_server.agent = mock_agent

                        # 触发关闭，进入 on_cleanup
                        # 此时 worker 仍在执行中，尚未写记忆
                        close_task = asyncio.create_task(client.close())
                        # 短暂等待使 on_cleanup 执行到 Step 1 (stop_tasks) 和 Step 2 (listener.stop)
                        await asyncio.sleep(0.05)

                        # 断言阶段 1 已完成：后台任务已停止
                        cleanup_st = app.get('cleanup_state', {})
                        self.assertTrue(pro_api_inst.tasks_stopped, "第一阶段必须已停止后台任务")

                        # 断言阶段 2/3：由于 worker 存活，严禁提前关闭记忆库！
                        self.assertFalse(real_memory.closed, "工作线程存活期间，记忆库必须保持打开！")
                        self.assertFalse(cleanup_st.get('memory_closed'), "禁止将 memory_closed 标记为 True")
                        self.assertFalse(mock_ctrl.closed, "工作线程存活期间，控制器必须保持打开！")

                        # 释放工作线程，让慢语音交互完成记忆写入并退出
                        hold_worker.clear()
                        worker_finished.wait(timeout=2.0)
                        self.assertTrue(worker_finished.is_set())

                        # 确认 worker 在写入记忆时没有抛出任何数据库已关闭异常
                        if worker_error:
                            raise worker_error[0]

                        # 等待 client.close 完全结束与延后清理完成
                        await close_task
                        deferred_th = cleanup_st.get('deferred_cleanup_thread')
                        if deferred_th:
                            deferred_th.join(timeout=2.0)

                        # 验证阶段 3：worker 安全退出后，记忆库与控制器已被延后安全关闭
                        self.assertTrue(real_memory.closed, "worker 退出后，记忆库必须已被延后关闭")
                        self.assertTrue(cleanup_st.get('memory_closed'))
                        self.assertTrue(mock_ctrl.closed, "worker 退出后，控制器必须已被延后关闭")
                        self.assertTrue(cleanup_st.get('controller_closed'))
                        self.assertTrue(cleanup_st.get('deferred_cleaned'))

                        # 重新打开数据库文件，验证 worker 写入的对话记忆确实已被完整持久化保存
                        verify_mem = MemoryStore(db_path)
                        turns = verify_mem.recent_turns()
                        verify_mem.close()
                        self.assertEqual(len(turns), 1)
                        self.assertEqual(turns[0]['role'], 'assistant')
                        self.assertEqual(turns[0]['content'], "牧濑红莉栖的退出前语音记忆")

                        # 验证全局调用顺序：
                        # 1. pro_api_stop_tasks 发生
                        # 2. memory_write_start / memory_write_done 发生 (成功写入打开的库)
                        # 3. worker_exit 发生
                        # 4. pro_api_close_resources (关闭 memory) 与 controller_close 发生
                        event_names = [item[0] for item in action_log]
                        self.assertIn('pro_api_stop_tasks', event_names)
                        self.assertIn('memory_write_done', event_names)
                        self.assertIn('worker_exit', event_names)
                        self.assertIn('pro_api_close_resources', event_names)
                        self.assertIn('controller_close', event_names)

                        idx_stop_tasks = event_names.index('pro_api_stop_tasks')
                        idx_write_done = event_names.index('memory_write_done')
                        idx_worker_exit = event_names.index('worker_exit')
                        idx_close_res = event_names.index('pro_api_close_resources')
                        idx_close_ctrl = event_names.index('controller_close')

                        self.assertLess(idx_stop_tasks, idx_write_done, "后台任务必须先停止")
                        self.assertLess(idx_write_done, idx_worker_exit, "记忆必须在 worker 退出前完成写入")
                        self.assertLess(idx_worker_exit, idx_close_res, "记忆库必须在 worker 退出后才能关闭！")
                        self.assertLess(idx_worker_exit, idx_close_ctrl, "控制器必须在 worker 退出后才能关闭！")
                finally:
                    hold_worker.clear()
                    worker_th.join(timeout=1.0)
                    real_memory.close()
                    web_server.controller = orig_controller
                    web_server.listener = orig_listener
                    web_server.pro_api = orig_pro_api
                    web_server.agent = orig_agent

    # -------------------------------------------------------------
    # 7f. 实际 run_chat 路径 + 底层慢 agent.chat 线程池工作 + 外层协程取消下的写记忆安全保护
    # -------------------------------------------------------------
    def test_7f_run_chat_slow_agent_cancels_coroutine_and_guards_memory_db(self):
        loop = asyncio.new_event_loop()
        action_log = []

        async def run_scenario():
            with tempfile.TemporaryDirectory() as tmp_dir:
                db_path = Path(tmp_dir) / "test_chat_memory.sqlite3"
                real_memory = MemoryStore(db_path)

                app = web_server.create_app(simulate=True, no_audio=True)
                orig_controller = web_server.controller
                orig_listener = web_server.listener
                orig_pro_api = web_server.pro_api
                orig_agent = web_server.agent

                class MockController:
                    def __init__(self):
                        self.closed = False
                    def close(self):
                        self.closed = True
                        action_log.append(('controller_close', time.monotonic()))

                mock_ctrl = MockController()

                chat_entered = threading.Event()
                hold_chat = threading.Event()
                hold_chat.set()
                chat_completed = threading.Event()
                chat_error = []

                class SlowChatAgent:
                    def __init__(self, memory, controller):
                        self.memory = memory
                        self.controller = controller
                        self.last_model_error = None
                        self.last_translation_error = None
                        self.history = []

                    def chat(self, message):
                        chat_entered.set()
                        action_log.append(('agent_chat_entered', time.monotonic()))
                        try:
                            # 模拟底层线程池中耗时较长的大模型思考计算
                            while hold_chat.is_set():
                                time.sleep(0.01)
                            # 思考完毕写入记忆数据库（此时外层协程已触发取消，关停流程已在进行）
                            reply = f"红莉栖回复: {message}"
                            action_log.append(('chat_memory_write_start', time.monotonic()))
                            self.history.append({'role': 'assistant', 'content': reply})
                            self.memory.append_turn('assistant', reply)
                            action_log.append(('chat_memory_write_done', time.monotonic()))
                            return reply
                        except Exception as ex:
                            chat_error.append(ex)
                            raise
                        finally:
                            action_log.append(('chat_worker_exit', time.monotonic()))
                            chat_completed.set()

                mock_agent = SlowChatAgent(real_memory, mock_ctrl)

                class InstrumentedProApi:
                    def __init__(self, agent):
                        self.agent = agent
                        self.tasks_stopped = False
                        self.resources_closed = False
                        self.music = types.SimpleNamespace(running=False)
                    async def stop_tasks(self):
                        self.tasks_stopped = True
                        action_log.append(('pro_api_stop_tasks', time.monotonic()))
                    def close_resources(self):
                        self.resources_closed = True
                        action_log.append(('pro_api_close_resources', time.monotonic()))
                        if self.agent.memory:
                            self.agent.memory.close()
                    async def cleanup(self):
                        await self.stop_tasks()
                        self.close_resources()

                pro_api_inst = InstrumentedProApi(mock_agent)

                try:
                    server = TestServer(app)
                    client = TestClient(server)

                    with patch('light_controller.LightController.wait_for_control', return_value=False), \
                         patch('service_discovery.ServiceAdvertisement.start', return_value=None), \
                         patch('service_discovery.ServiceAdvertisement.close', return_value=None):

                        await client.start_server()
                        if web_server.pro_api:
                            await web_server.pro_api.cleanup()

                        web_server.controller = mock_ctrl
                        web_server.pro_api = pro_api_inst
                        web_server.agent = mock_agent
                        web_server.listener = None

                        # 1. 发起真实 run_chat() 交互协程
                        chat_task = asyncio.create_task(web_server.run_chat("你好红莉栖"))

                        chat_entered.wait(timeout=2.0)
                        self.assertTrue(chat_entered.is_set())
                        self.assertTrue(len(web_server.active_chat_threads) > 0, "底层线程池工作线程必须已被成功登记")
                        self.assertTrue(len(web_server.get_active_chat_jobs()) > 0, "工作记录 ChatJob 必须已被成功登记")

                        # 2. 模拟外层协程被取消（如网络超时断开或取消交互）
                        chat_task.cancel()
                        try:
                            await chat_task
                        except asyncio.CancelledError:
                            pass
                        self.assertTrue(chat_task.cancelled(), "外层协程必须已处于取消状态")

                        # 核心验证：外层协程即使已取消，底层线程池工作线程与 ChatJob 记录仍存活并被登记，绝不丢失！
                        self.assertTrue(len(web_server.active_chat_threads) > 0, "外层协程取消后，底层工作线程必须仍被登记")
                        self.assertTrue(len(web_server.get_active_chat_jobs()) > 0, "外层协程取消后，工作记录 ChatJob 必须仍被登记")

                        # 3. 在底层工作线程仍在执行时，触发服务端关停
                        close_server_task = asyncio.create_task(client.close())
                        await asyncio.sleep(0.05)

                        # 验证关停入口标志与新请求拒绝：
                        self.assertTrue(web_server.shutting_down, "关停入口标志必须已置为 True")
                        with self.assertRaises(RuntimeError) as cm:
                            await web_server.run_chat("关停期新请求")
                        self.assertIn("Server is shutting down", str(cm.exception))

                        # 验证 HTTP 接口对新请求返回 503
                        resp = await client.post('/api/chat', json={"message": "关停期新请求"})
                        self.assertEqual(resp.status, 503)

                        # 验证核心保护：虽然关停已发起，但由于底层工作线程存活，记忆库严禁提前关闭！
                        self.assertFalse(real_memory.closed, "底层工作线程存活期间，记忆库必须保持打开！")
                        self.assertFalse(mock_ctrl.closed, "底层工作线程存活期间，控制器必须保持打开！")

                        # 4. 释放底层工作线程阻塞，允许其安全完成回复生成与写记忆
                        hold_chat.clear()
                        chat_completed.wait(timeout=2.0)
                        self.assertTrue(chat_completed.is_set())
                        if chat_error:
                            raise chat_error[0]

                        # 等待服务关停完全结束与延后守护完成
                        await close_server_task
                        cleanup_st = app.get('cleanup_state', {})
                        deferred_th = cleanup_st.get('deferred_cleanup_thread')
                        if deferred_th:
                            deferred_th.join(timeout=2.0)

                        # 5. 验证底层工作退出后，记忆库与控制器安全关闭
                        self.assertTrue(real_memory.closed, "工作线程退出后，记忆库必须已被安全关闭")
                        self.assertTrue(cleanup_st.get('memory_closed'))
                        self.assertTrue(mock_ctrl.closed, "工作线程退出后，控制器必须已被安全关闭")
                        self.assertTrue(cleanup_st.get('controller_closed'))
                        self.assertTrue(cleanup_st.get('chat_stopped'))

                        # 6. 重新打开数据库，验证在途取消协程对应的底层写记忆确实完整落盘保存
                        verify_mem = MemoryStore(db_path)
                        turns = verify_mem.recent_turns()
                        verify_mem.close()
                        self.assertEqual(len(turns), 1)
                        self.assertEqual(turns[0]['role'], 'assistant')
                        self.assertEqual(turns[0]['content'], "红莉栖回复: 你好红莉栖")

                        # 7. 严格断言全局事件时序：
                        event_names = [item[0] for item in action_log]
                        self.assertIn('agent_chat_entered', event_names)
                        self.assertIn('chat_memory_write_done', event_names)
                        self.assertIn('chat_worker_exit', event_names)
                        self.assertIn('pro_api_close_resources', event_names)
                        self.assertIn('controller_close', event_names)

                        idx_entered = event_names.index('agent_chat_entered')
                        idx_write = event_names.index('chat_memory_write_done')
                        idx_exit = event_names.index('chat_worker_exit')
                        idx_res = event_names.index('pro_api_close_resources')
                        idx_ctrl = event_names.index('controller_close')

                        self.assertLess(idx_entered, idx_write, "进入聊天必须在写记忆之前")
                        self.assertLess(idx_write, idx_exit, "记忆写入必须在工作线程退出之前完成")
                        self.assertLess(idx_exit, idx_res, "工作线程退出后方可关闭记忆数据库！")
                        self.assertLess(idx_exit, idx_ctrl, "工作线程退出后方可关闭控制器！")
                finally:
                    hold_chat.clear()
                    real_memory.close()
                    web_server.controller = orig_controller
                    web_server.listener = orig_listener
                    web_server.pro_api = orig_pro_api
                    web_server.agent = orig_agent

    # -------------------------------------------------------------
    # 7g. 线程池排队期间关停保护 (在排队阶段登记，关停期守护资源，执行后延后关闭)
    # -------------------------------------------------------------
    def test_7g_shutdown_during_chat_job_queueing_guards_resources(self):
        """验证在线程池排队期间发起关停时，资源得到严格守护并在最终执行完毕后安全释放"""
        async def run_test():
            orig_controller = web_server.controller
            orig_listener = web_server.listener
            orig_pro_api = web_server.pro_api
            orig_agent = web_server.agent

            with tempfile.TemporaryDirectory() as tmpdir:
                db_path = Path(tmpdir) / "test_chat_queue_memory.db"
                real_memory = MemoryStore(str(db_path))

                action_log = []

                class MockAgentQueued:
                    def __init__(self, mem):
                        self.memory = mem
                        self.last_model_error = None
                        self.last_translation_error = None

                    def chat(self, msg):
                        action_log.append(('agent_chat_executed', time.monotonic()))
                        self.memory.append_turn('user', msg)
                        self.memory.append_turn('assistant', f"排队回复: {msg}")
                        return f"排队回复: {msg}"

                mock_agent = MockAgentQueued(real_memory)

                class MockControllerQueued:
                    def __init__(self):
                        self.closed = False
                    def close(self):
                        self.closed = True
                        action_log.append(('controller_close', time.monotonic()))

                mock_ctrl = MockControllerQueued()

                class MockProApiQueued:
                    def __init__(self, agent_inst):
                        self.agent = agent_inst
                        self.music = types.SimpleNamespace(running=False)
                        self.playback = types.SimpleNamespace(stop=lambda *a: None)
                        self.closed = False
                    async def stop_tasks(self):
                        action_log.append(('pro_api_stop_tasks', time.monotonic()))
                    def close_resources(self):
                        self.closed = True
                        self.agent.memory.close()
                        action_log.append(('pro_api_close_resources', time.monotonic()))

                pro_api_inst = MockProApiQueued(mock_agent)

                try:
                    app = web_server.create_app(simulate=True, no_audio=True)
                    server = TestServer(app)
                    client = TestClient(server)

                    with patch('light_controller.LightController.wait_for_control', return_value=False), \
                         patch('service_discovery.ServiceAdvertisement.start', return_value=None), \
                         patch('service_discovery.ServiceAdvertisement.close', return_value=None):

                        await client.start_server()
                        if web_server.pro_api:
                            await web_server.pro_api.cleanup()

                        web_server.controller = mock_ctrl
                        web_server.pro_api = pro_api_inst
                        web_server.agent = mock_agent
                        web_server.listener = None

                        loop = asyncio.get_running_loop()
                        old_executor = loop._default_executor

                        # 构造单工作线程池，用于精确控制排队状态
                        single_pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                        loop.set_default_executor(single_pool)

                        blocker_entered = threading.Event()
                        release_blocker = threading.Event()

                        def _blocker_work():
                            blocker_entered.set()
                            release_blocker.wait(timeout=5.0)

                        try:
                            # 1. 提交前置阻塞任务，占满单线程池
                            blocker_fut = loop.run_in_executor(None, _blocker_work)
                            for _ in range(50):
                                if blocker_entered.is_set():
                                    break
                                await asyncio.sleep(0.02)
                            self.assertTrue(blocker_entered.is_set(), "前置任务必须已占用线程池工作线程")

                            # 2. 提交聊天请求：由于线程池已满，该任务必定停留在线程池排队队列中！
                            chat_task = asyncio.create_task(web_server.run_chat("排队阶段测试消息"))
                            await asyncio.sleep(0.05)

                            # 核心验证：即使工作尚未被线程池工作线程提取执行，工作记录必须已被登记！
                            active_jobs = web_server.get_active_chat_jobs()
                            self.assertEqual(len(active_jobs), 1, "排队中的聊天必须在提交到线程池之前即被登记！")
                            queued_job = active_jobs[0]
                            self.assertFalse(queued_job.started, "工作必须尚未开始执行（处于排队中）")
                            self.assertFalse(queued_job.is_done(), "工作必须尚未完成")

                            # 3. 在聊天仍处于排队队列期间，发起服务端关停
                            close_server_task = asyncio.create_task(client.close())
                            await asyncio.sleep(0.05)

                            # 核心验证：关停流程检测到排队中的工作，严禁提前关闭数据库与控制器！
                            self.assertTrue(web_server.shutting_down, "关停标志已生效")
                            self.assertFalse(real_memory.closed, "工作排队期间，记忆数据库必须严加保护，严禁关闭！")
                            self.assertFalse(mock_ctrl.closed, "工作排队期间，控制器必须保持打开！")
                            cleanup_st = app.get('cleanup_state', {})
                            self.assertFalse(cleanup_st.get('chat_stopped'), "存在排队工作，chat_stopped 必须为 False")

                            # 4. 释放前置阻塞，允许排队中的聊天工作被提取执行并完成写记忆
                            release_blocker.set()
                            await blocker_fut

                            # 等待聊天任务完成
                            chat_res = await chat_task
                            self.assertEqual(chat_res['reply'], "排队回复: 排队阶段测试消息")
                            self.assertTrue(queued_job.is_done(), "聊天执行完毕后，done_event 必须置位")

                            # 等待服务端关停与延后清理完成
                            await close_server_task
                            deferred_th = cleanup_st.get('deferred_cleanup_thread')
                            if deferred_th:
                                deferred_th.join(timeout=2.0)

                            # 5. 验证执行完毕后延后关闭记忆库与控制器
                            self.assertTrue(real_memory.closed, "排队工作执行完毕后，记忆库安全关闭")
                            self.assertTrue(cleanup_st.get('memory_closed'))
                            self.assertTrue(cleanup_st.get('controller_closed'))
                            self.assertTrue(cleanup_st.get('deferred_cleaned') or cleanup_st.get('exit_complete'))

                            # 6. 重新打开数据库，验证排队工作写入的记忆数据完好无损
                            verify_mem = MemoryStore(str(db_path))
                            turns = verify_mem.recent_turns()
                            verify_mem.close()
                            self.assertEqual(len(turns), 2)
                            self.assertEqual(turns[0]['content'], "排队阶段测试消息")
                            self.assertEqual(turns[1]['content'], "排队回复: 排队阶段测试消息")

                        finally:
                            release_blocker.set()
                            single_pool.shutdown(wait=False)
                            loop.set_default_executor(old_executor)

                finally:
                    real_memory.close()
                    web_server.controller = orig_controller
                    web_server.listener = orig_listener
                    web_server.pro_api = orig_pro_api
                    web_server.agent = orig_agent

        asyncio.run(run_test())

    # -------------------------------------------------------------
    # 7h. 聊天结束但线程池线程仍存活时，资源能够正常清理
    # -------------------------------------------------------------
    def test_7h_chat_finished_with_pool_threads_alive_cleans_resources_cleanly(self):
        """验证聊天已正常结束、线程池复用线程仍存活时，关停流程能够正常清理资源且不误报退出未完成"""
        async def run_test():
            orig_controller = web_server.controller
            orig_listener = web_server.listener
            orig_pro_api = web_server.pro_api
            orig_agent = web_server.agent

            with tempfile.TemporaryDirectory() as tmpdir:
                db_path = Path(tmpdir) / "test_chat_reuse_memory.db"
                real_memory = MemoryStore(str(db_path))

                class FastAgent:
                    def __init__(self, mem):
                        self.memory = mem
                        self.last_model_error = None
                        self.last_translation_error = None
                    def chat(self, msg):
                        self.memory.append_turn('user', msg)
                        self.memory.append_turn('assistant', f"快速回复: {msg}")
                        return f"快速回复: {msg}"

                mock_agent = FastAgent(real_memory)

                class FastController:
                    def __init__(self):
                        self.closed = False
                    def close(self):
                        self.closed = True

                mock_ctrl = FastController()

                class FastProApi:
                    def __init__(self, agent_inst):
                        self.agent = agent_inst
                        self.music = types.SimpleNamespace(running=False)
                        self.playback = types.SimpleNamespace(stop=lambda *a: None)
                        self.closed = False
                    async def stop_tasks(self):
                        pass
                    def close_resources(self):
                        self.closed = True
                        self.agent.memory.close()

                pro_api_inst = FastProApi(mock_agent)

                try:
                    app = web_server.create_app(simulate=True, no_audio=True)
                    server = TestServer(app)
                    client = TestClient(server)

                    with patch('light_controller.LightController.wait_for_control', return_value=False), \
                         patch('service_discovery.ServiceAdvertisement.start', return_value=None), \
                         patch('service_discovery.ServiceAdvertisement.close', return_value=None):

                        await client.start_server()
                        if web_server.pro_api:
                            await web_server.pro_api.cleanup()

                        web_server.controller = mock_ctrl
                        web_server.pro_api = pro_api_inst
                        web_server.agent = mock_agent
                        web_server.listener = None

                        # 1. 执行一次完整正常的聊天
                        res = await web_server.run_chat("测试复用线程")
                        self.assertEqual(res['reply'], "快速回复: 测试复用线程")

                        # 验证聊天工作已经完全结束并注销
                        self.assertEqual(len(web_server.get_active_chat_jobs()), 0, "聊天工作已结束，活跃记录必须为空")

                        # 核心验证：确认 Python 线程池中的工作线程当前确实存活（被线程池保持待命复用）
                        pool_threads_alive = any(
                            th.is_alive() and ("ThreadPoolExecutor" in th.name or "ThreadPool" in type(th).__name__ or "worker" in th.name.lower())
                            for th in threading.enumerate()
                        )

                        # 2. 触发关停流程
                        await client.close()
                        cleanup_st = app.get('cleanup_state', {})

                        # 核心断言：关停流程依据每次聊天的工作记录而不是依据线程池存活线程进行判断
                        # 因此关停必须立即干净完成，严禁将线程池存活线程误判为未完成工作！
                        self.assertTrue(cleanup_st.get('chat_stopped'), "chat_stopped 必须为 True")
                        self.assertTrue(cleanup_st.get('listener_stopped'), "listener_stopped 必须为 True")
                        self.assertTrue(cleanup_st.get('exit_complete'), "exit_complete 必须为 True")
                        self.assertTrue(cleanup_st.get('memory_closed'), "memory_closed 必须为 True")
                        self.assertTrue(cleanup_st.get('controller_closed'), "controller_closed 必须为 True")
                        self.assertFalse(cleanup_st.get('deferred_cleanup_scheduled'), "正常完成无需延后守护")
                        self.assertEqual(cleanup_st.get('pending_chat_jobs'), [], "待办任务必须为空")
                        self.assertEqual(cleanup_st.get('unresponsive_threads'), [], "线程池存活线程绝不可被误报为未退出线程")

                finally:
                    real_memory.close()
                    web_server.shutting_down = False
                    web_server.controller = orig_controller
                    web_server.listener = orig_listener
                    web_server.pro_api = orig_pro_api
                    web_server.agent = orig_agent

        asyncio.run(run_test())

    # -------------------------------------------------------------
    # 7i. 准备阶段关停：在 run_chat 准备或锁等待阶段触发服务关停
    # -------------------------------------------------------------
    def test_7i_shutdown_during_preparation_stage(self):
        async def run_test():
            web_server.shutting_down = False
            try:
                # 1. 占用 chat_lock 模拟准备阶段前排队
                async with web_server.chat_lock:
                    chat_task = asyncio.create_task(web_server.run_chat("准备阶段关停测试"))
                    # 等待协程执行进入 run_chat 并登记 ChatJob 为 preparing
                    for _ in range(50):
                        jobs = web_server.get_active_chat_jobs()
                        if jobs and any(j.state == "preparing" for j in jobs):
                            break
                        await asyncio.sleep(0.01)

                    jobs = web_server.get_active_chat_jobs()
                    self.assertEqual(len(jobs), 1)
                    prep_job = jobs[0]
                    self.assertEqual(prep_job.state, "preparing")
                    self.assertFalse(prep_job.is_done())

                    # 2. 在准备/等待锁阶段触发全局服务关停
                    web_server.shutting_down = True

                # 释放 chat_lock，run_chat 获得锁后检测 shutting_down
                with self.assertRaises(RuntimeError) as cm:
                    await chat_task
                self.assertIn("Server is shutting down", str(cm.exception))

                # 3. 验证 ChatJob 状态被明确标记为 unsubmitted_cancelled 并安全结束
                self.assertTrue(prep_job.is_done())
                self.assertEqual(prep_job.state, "unsubmitted_cancelled")
                self.assertEqual(len(web_server.get_active_chat_jobs()), 0)
            finally:
                web_server.shutting_down = False

        asyncio.run(run_test())

    # -------------------------------------------------------------
    # 7j. 排队取消与执行中取消：每条取消路径均有明确归属且收音恢复安全
    # -------------------------------------------------------------
    def test_7j_queued_cancelled_and_running_cancelled(self):
        async def run_test():
            web_server.shutting_down = False
            orig_agent = web_server.agent
            orig_listener = web_server.listener
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

            mic_resumed_count = 0
            def nonlocal_resume():
                nonlocal mic_resumed_count
                mic_resumed_count += 1

            listener_mock = types.SimpleNamespace(
                is_paused=False,
                pause=lambda: None,
                resume=nonlocal_resume
            )

            blocker_entered = threading.Event()
            blocker_release = threading.Event()

            def _blocker_work():
                blocker_entered.set()
                blocker_release.wait(timeout=5.0)

            loop = asyncio.get_running_loop()
            loop.set_default_executor(executor)

            try:
                # --- Part A: 排队阶段取消 ---
                # 占用单线程线程池，使下一条任务排队
                blocker_fut = loop.run_in_executor(None, _blocker_work)
                while not blocker_entered.is_set():
                    await asyncio.sleep(0.02)

                web_server.listener = None
                web_server.agent = types.SimpleNamespace(chat=lambda msg: f"reply: {msg}")

                chat_task = asyncio.create_task(web_server.run_chat("排队取消消息"))

                # 等待任务进入排队阶段
                queued_job = None
                for _ in range(50):
                    jobs = web_server.get_active_chat_jobs()
                    if jobs and any(j.state == "queued" for j in jobs):
                        queued_job = [j for j in jobs if j.state == "queued"][0]
                        break
                    await asyncio.sleep(0.02)

                self.assertIsNotNone(queued_job, "聊天任务必须进入 queued 状态")

                # 在排队阶段取消外层协程
                chat_task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await chat_task

                self.assertTrue(queued_job.cancel_requested)
                self.assertEqual(queued_job.state, "queued_cancelled")

                # 释放 blocker，使 worker 线程取出并执行排队的任务
                blocker_release.set()
                await blocker_fut

                # worker 线程检测到 cancel_requested，安全跳过底层 chat 执行并标记完成
                self.assertTrue(queued_job.is_done())
                self.assertEqual(queued_job.state, "queued_cancelled")

                # --- Part B: 执行中取消与收音恢复顺序 ---
                listener_mock.is_paused = False
                web_server.listener = listener_mock
                worker_executing = threading.Event()
                worker_can_finish = threading.Event()
                chat_invoked = False

                def slow_chat(msg):
                    nonlocal chat_invoked
                    chat_invoked = True
                    worker_executing.set()
                    worker_can_finish.wait(timeout=5.0)
                    return f"慢回复: {msg}"

                web_server.agent.chat = slow_chat

                running_task = asyncio.create_task(web_server.run_chat("执行中取消消息"))
                while not worker_executing.is_set():
                    await asyncio.sleep(0.02)

                running_job = [j for j in web_server.get_active_chat_jobs() if j.state == "running"][0]
                self.assertTrue(running_job.started)

                # 外层协程取消
                pre_resume_count = mic_resumed_count
                running_task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await running_task

                # 关键验证：外层协程取消后，由于底层 worker 仍在生成/播报中，绝不能提前恢复收音 (防回声)！
                self.assertEqual(mic_resumed_count, pre_resume_count, "底层任务未退出前严禁提前恢复收音")
                self.assertEqual(running_job.state, "running_cancelled")

                # 底层 worker 真正执行结束
                worker_can_finish.set()
                # 等待 worker 退出
                while not running_job.is_done():
                    await asyncio.sleep(0.02)

                self.assertEqual(running_job.state, "running_cancelled")
                self.assertGreater(mic_resumed_count, pre_resume_count, "底层任务真正结束后方可恢复收音")

            finally:
                web_server.shutting_down = False
                blocker_release.set()
                web_server.agent = orig_agent
                web_server.listener = orig_listener
                executor.shutdown(wait=True)

        asyncio.run(run_test())

    # -------------------------------------------------------------
    # 7k. 线程池提交失败：正确标记未完成记录并释放收音
    # -------------------------------------------------------------
    def test_7k_executor_submission_failure_marks_job_failed_and_cleans_up(self):
        async def run_test():
            web_server.shutting_down = False
            loop = asyncio.get_running_loop()
            resumed = False
            def nonlocal_resume():
                nonlocal resumed
                resumed = True

            fake_listener = types.SimpleNamespace(
                is_paused=False,
                pause=lambda: None,
                resume=nonlocal_resume
            )

            orig_listener = web_server.listener
            web_server.listener = fake_listener

            # 模拟线程池已关闭或达到提交上限抛出 RuntimeError
            orig_run_in_executor = loop.run_in_executor
            def fail_run_in_executor(executor, func, *args):
                if func and "sync_chat_worker" in getattr(func, '__name__', ''):
                    raise RuntimeError("Cannot schedule new futures after shutdown")
                return orig_run_in_executor(executor, func, *args)

            loop.run_in_executor = fail_run_in_executor

            try:
                with self.assertRaises(RuntimeError) as cm:
                    await web_server.run_chat("提交失败测试")
                self.assertIn("Cannot schedule new futures", str(cm.exception))

                # 验证收音被安全恢复
                self.assertTrue(resumed, "提交失败时若拥有暂停权必须恢复收音")

                # 验证 active_chat_jobs 中没有残留活跃任务
                self.assertEqual(len(web_server.get_active_chat_jobs()), 0, "提交失败后严禁在活跃集合中残留工作")
            finally:
                web_server.shutting_down = False
                loop.run_in_executor = orig_run_in_executor
                web_server.listener = orig_listener

        asyncio.run(run_test())

    # -------------------------------------------------------------
    # 7l. 关停结果真实：资源关闭失败时不误报 exit_complete
    # -------------------------------------------------------------
    def test_7l_close_failure_does_not_falsely_report_exit_complete(self):
        async def run_test():
            web_server.shutting_down = False
            app = web_server.create_app(simulate=True, no_audio=True)

            class FaultyController:
                def __init__(self):
                    self.closed = False
                def close(self):
                    raise IOError("Simulated hardware bus disconnect fault on close")

            class FaultyMemory:
                def __init__(self):
                    self.closed = False
                def close(self):
                    raise RuntimeError("Simulated database lock failure on close")

            faulty_ctrl = FaultyController()
            faulty_mem = FaultyMemory()

            orig_ctrl = web_server.controller
            orig_agent = web_server.agent
            orig_listener = web_server.listener

            web_server.controller = faulty_ctrl
            web_server.agent = types.SimpleNamespace(memory=faulty_mem)
            web_server.listener = None

            try:
                await web_server.on_cleanup(app)
                cleanup_st = app.get('cleanup_state', {})

                # 核心断言：只有真正关闭才标记成功；失败时绝不虚假报告 exit_complete=True
                self.assertFalse(cleanup_st.get('exit_complete'), "资源关闭发生异常时 exit_complete 必须为 False")
                self.assertFalse(cleanup_st.get('controller_closed'), "controller 关闭失败必须为 False")
                self.assertFalse(cleanup_st.get('memory_closed'), "memory 关闭失败必须为 False")

                # 验证保留了未正常释放的资源引用与失败原因
                self.assertIn('controller', cleanup_st.get('close_errors', {}))
                self.assertIn('memory', cleanup_st.get('close_errors', {}))
                self.assertIs(cleanup_st.get('retained_resources', {}).get('controller'), faulty_ctrl)
                self.assertIs(cleanup_st.get('retained_resources', {}).get('memory'), faulty_mem)
            finally:
                web_server.shutting_down = False
                web_server.controller = orig_ctrl
                web_server.agent = orig_agent
        asyncio.run(run_test())

    # -------------------------------------------------------------
    # 7m. 准备阶段执行中取消：底层暂停操作未完成前绝不提前注销记录，也绝不提前恢复收音
    # -------------------------------------------------------------
    def test_7m_cancellation_during_preparation_awaits_pause_and_preserves_mic_safety(self):
        async def run_test():
            web_server.shutting_down = False
            pause_started = threading.Event()
            pause_release = threading.Event()
            mic_resumed = threading.Event()

            def slow_pause():
                pause_started.set()
                pause_release.wait(timeout=5.0)

            def mock_resume():
                mic_resumed.set()

            fake_listener = types.SimpleNamespace(
                is_paused=False,
                pause=slow_pause,
                resume=mock_resume
            )

            orig_listener = web_server.listener
            orig_agent = web_server.agent
            web_server.listener = fake_listener
            web_server.agent = types.SimpleNamespace(chat=lambda msg: f"reply: {msg}")

            try:
                # --- Part A: 正常运行中，准备阶段执行 slow_pause 时协程被取消 ---
                chat_task = asyncio.create_task(web_server.run_chat("准备阶段底层暂停取消测试"))
                while not pause_started.is_set():
                    await asyncio.sleep(0.01)

                # 此时 slow_pause 正在线程池执行，取消协程
                chat_task.cancel()
                await asyncio.sleep(0.05)

                # 核心断言 A1：底层 pause 仍在执行时，工作记录 ChatJob 绝不能提前注销或标记完成
                jobs = web_server.get_active_chat_jobs()
                self.assertEqual(len(jobs), 1, "底层暂停真正结束前，ChatJob 记录严禁提前注销")
                prep_job = jobs[0]
                self.assertEqual(prep_job.state, "preparing")
                self.assertFalse(prep_job.is_done(), "底层暂停真正结束前，ChatJob 绝不能提前标记完成")

                # 核心断言 A2：底层 pause 仍未返回时，绝对不能提前执行 resume()！
                self.assertFalse(mic_resumed.is_set(), "底层暂停真正结束前，严禁调用 resume() 恢复收音！")

                # 放行底层 pause()
                pause_release.set()

                # 外层任务正常抛出 CancelledError
                with self.assertRaises(asyncio.CancelledError):
                    await chat_task

                # 核心断言 A3：底层 pause 真正完成后，工作记录方可标记完成并安全注销
                self.assertTrue(prep_job.is_done(), "底层 pause 真正完成后，ChatJob 方可标记完成")
                self.assertEqual(prep_job.state, "unsubmitted_cancelled")
                self.assertEqual(len(web_server.get_active_chat_jobs()), 0, "工作安全退出后活跃记录清空")

                # 核心断言 A4：底层 pause 真正完成后，非关停状态下方可恢复收音
                self.assertTrue(mic_resumed.is_set(), "底层 pause 真正结束后方可恢复收音")

                # --- Part B: 关停期间准备阶段取消，底层 pause 完成后严禁恢复收音 ---
                pause_started_2 = threading.Event()
                pause_release_2 = threading.Event()
                mic_resumed_2 = threading.Event()

                def slow_pause_2():
                    pause_started_2.set()
                    pause_release_2.wait(timeout=5.0)

                def mock_resume_2():
                    mic_resumed_2.set()

                fake_listener_2 = types.SimpleNamespace(
                    is_paused=False,
                    pause=slow_pause_2,
                    resume=mock_resume_2
                )
                web_server.listener = fake_listener_2
                chat_task_2 = asyncio.create_task(web_server.run_chat("关停中准备阶段取消测试"))
                while not pause_started_2.is_set():
                    await asyncio.sleep(0.01)

                # 触发关停并取消协程
                web_server.shutting_down = True
                chat_task_2.cancel()
                await asyncio.sleep(0.05)

                jobs_2 = web_server.get_active_chat_jobs()
                self.assertEqual(len(jobs_2), 1)
                self.assertFalse(jobs_2[0].is_done())

                pause_release_2.set()
                with self.assertRaises(asyncio.CancelledError):
                    await chat_task_2

                self.assertTrue(jobs_2[0].is_done())
                self.assertFalse(mic_resumed_2.is_set(), "关停状态下底层暂停完成后严禁恢复收音！")

            finally:
                pause_release.set()
                web_server.shutting_down = False
                web_server.listener = orig_listener
                web_server.agent = orig_agent

        asyncio.run(run_test())

    # -------------------------------------------------------------
    # 8a. 细粒度线程健康状态检测 (杜绝单靠 watchdog 虚假汇报存活)
    # -------------------------------------------------------------
    def test_8a_fine_grained_thread_status_and_health(self):
        listener = self._create_isolated_listener()

        run_process = threading.Event()
        run_worker = threading.Event()
        run_watchdog = threading.Event()
        run_process.set()
        run_worker.set()
        run_watchdog.set()

        def p_loop():
            while run_process.is_set(): time.sleep(0.01)
        def w_loop():
            while run_worker.is_set(): time.sleep(0.01)
        def wd_loop():
            while run_watchdog.is_set(): time.sleep(0.01)

        th_p = threading.Thread(target=p_loop, daemon=True)
        th_w = threading.Thread(target=w_loop, daemon=True)
        th_wd = threading.Thread(target=wd_loop, daemon=True)
        th_p.start()
        th_w.start()
        th_wd.start()

        listener.is_listening = True
        listener._process_thread = th_p
        listener._worker_thread = th_w
        listener._watchdog_thread = th_wd

        # 1. 全部线程存活时状态汇报
        st = listener.get_thread_status()
        self.assertTrue(st['process'])
        self.assertTrue(st['worker'])
        self.assertTrue(st['watchdog'])
        self.assertFalse(st['teardown'])
        self.assertTrue(listener.is_healthy())
        self.assertTrue(listener.is_alive())

        # 2. 模拟核心音频处理线程意外退出
        run_process.clear()
        th_p.join(timeout=1.0)
        self.assertFalse(th_p.is_alive())

        st2 = listener.get_thread_status()
        self.assertFalse(st2['process'])
        self.assertTrue(st2['worker'])
        self.assertTrue(st2['watchdog'])

        # 核心处理线程退出后，健康状态和 is_alive 必须为 False
        self.assertFalse(listener.is_healthy(), "核心处理线程退出后 is_healthy 必须为 False")
        self.assertFalse(listener.is_alive(), "核心处理线程退出后 is_alive 必须为 False")

        run_worker.clear()
        run_watchdog.clear()
        listener.stop(timeout=1.0)

    # -------------------------------------------------------------
    # 8b. 看门狗受控自愈保护：暂停期间与停止期间不擅自重建
    # -------------------------------------------------------------
    def test_8b_watchdog_paused_and_stopped_protection(self):
        listener = self._create_isolated_listener()
        listener.is_listening = True
        listener.is_paused = True  # 处于暂停状态 (如正在播报或音乐播放中)
        listener._process_thread = None  # 核心线程死掉
        listener._worker_thread = None

        heal_called = False
        listener._process_loop = lambda: setattr(listener, '_heal_called_flag', True)

        # 1. 验证暂停保护：暂停期间绝不重建
        listener._check_and_heal_threads()
        self.assertIsNone(listener._process_thread, "暂停状态下看门狗严禁重建核心线程")
        self.assertEqual(listener._heal_attempts, 0)

        # 2. 验证停止状态保护：停止中绝不重建
        listener.is_paused = False
        listener.is_listening = False
        listener._check_and_heal_threads()
        self.assertIsNone(listener._process_thread, "未处于监听状态时看门狗严禁重建")

        # 3. 验证 stop_pending 保护：停止挂起时绝不重建
        listener.is_listening = True
        listener.stop_pending = True
        listener._check_and_heal_threads()
        self.assertIsNone(listener._process_thread, "stop_pending 挂起状态下看门狗严禁重建")

    # -------------------------------------------------------------
    # 8c. 反复退出直到熔断：重试上限、指数退避与失败熔断机制
    # -------------------------------------------------------------
    def test_8c_repeated_failure_circuit_breaker_and_backoff(self):
        listener = self._create_isolated_listener()
        listener.is_listening = True
        listener.is_paused = False
        listener.stop_pending = False
        listener._max_heal_retries = 3

        spawn_count = 0
        def dying_process_loop():
            nonlocal spawn_count
            spawn_count += 1
            # 启动即退出，模拟固定错误（如麦克风硬件断开、模型崩溃）
            return

        listener._process_loop = dying_process_loop
        listener._worker_loop = dying_process_loop

        # 模拟看门狗多次触发自愈
        # 第 1 次重试
        listener._check_and_heal_threads()
        self.assertEqual(listener._heal_attempts, 1)
        self.assertEqual(listener.heal_status, "healing")
        self.assertFalse(listener._heal_circuit_broken)

        # 等待已启动线程自然退出
        if listener._process_thread: listener._process_thread.join(timeout=1.0)
        if listener._worker_thread: listener._worker_thread.join(timeout=1.0)

        # 验证指数退避：未跨过退避周期 (当前退避 2.0s) 前再次触发应被跳过
        listener._check_and_heal_threads()
        self.assertEqual(listener._heal_attempts, 1, "未达退避间隔前不应触发下一次重试")

        # 人工推进时间戳绕过退避等待，触发第 2 次重试
        listener._last_heal_time = 0.0
        listener._check_and_heal_threads()
        self.assertEqual(listener._heal_attempts, 2)
        if listener._process_thread: listener._process_thread.join(timeout=1.0)
        if listener._worker_thread: listener._worker_thread.join(timeout=1.0)

        # 人工推进时间戳，触发第 3 次重试 (达到上限 3 次)
        listener._last_heal_time = 0.0
        listener._check_and_heal_threads()
        self.assertEqual(listener._heal_attempts, 3)
        if listener._process_thread: listener._process_thread.join(timeout=1.0)
        if listener._worker_thread: listener._worker_thread.join(timeout=1.0)

        # 第 4 次触发：达到上限，触发熔断！
        listener._last_heal_time = 0.0
        prev_spawn = spawn_count
        listener._check_and_heal_threads()

        self.assertTrue(listener._heal_circuit_broken, "达到重试上限后必须触发熔断 (circuit_broken)")
        self.assertEqual(listener.heal_status, "circuit_broken")
        self.assertFalse(listener.is_healthy(), "熔断状态下 is_healthy 必须返回 False")
        self.assertFalse(listener.is_alive(), "熔断状态下 is_alive 必须返回 False")

        # 验证熔断保护：后续无论如何触发看门狗，绝不再盲目高频拉起新线程
        listener._last_heal_time = 0.0
        listener._check_and_heal_threads()
        self.assertEqual(spawn_count, prev_spawn, "熔断后严禁创建任何新线程")

    # -------------------------------------------------------------
    # 8d. 恢复正常后持续稳定运行方可复位自愈计数 (防抖动保护)
    # -------------------------------------------------------------
    def test_8d_recovery_resets_heal_counters(self):
        listener = self._create_isolated_listener()
        listener.is_listening = True
        listener.is_paused = False
        listener._heal_attempts = 2
        listener._heal_backoff = 4.0
        listener.heal_status = "healing"
        listener._heal_stable_duration = 5.0

        run_th = threading.Event()
        run_th.set()
        def dummy_loop():
            while run_th.is_set(): time.sleep(0.01)

        listener._process_thread = threading.Thread(target=dummy_loop, daemon=True)
        listener._worker_thread = threading.Thread(target=dummy_loop, daemon=True)
        listener._process_thread.start()
        listener._worker_thread.start()

        # 1. 首次检测健康：记录 _healthy_since，但未满 stable_duration 前不立即清零（防高频震荡）
        listener._check_and_heal_threads()
        self.assertGreater(listener._healthy_since, 0.0)
        self.assertEqual(listener._heal_attempts, 2, "未达稳定持续健康周期前严禁提前清零重试计数")

        # 2. 模拟持续稳定健康超过 5.0 秒，再次触发自愈检测
        listener._healthy_since -= 6.0
        listener._check_and_heal_threads()

        # 验证计数与退避完全复位
        self.assertEqual(listener._heal_attempts, 0, "持续健康稳定后重试计数应复位为 0")
        self.assertEqual(listener._heal_backoff, 1.0, "退避倍数应复位为 1.0s")
        self.assertEqual(listener.heal_status, "ok", "自愈状态应更新为 ok")

        run_th.clear()
        listener.stop(timeout=1.0)


if __name__ == "__main__":
    unittest.main()
