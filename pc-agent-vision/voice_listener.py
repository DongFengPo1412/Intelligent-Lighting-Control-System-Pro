"""Board microphone capture, VAD segmentation and acoustic-gated wake state.
Standby audio must pass an independent keyword model before unprompted Whisper.
Awake commands use domain-biased ASR and complete before capture resumes.
"""

import os
import sys
import torch
import re
import time
import queue
import threading
import collections
import json
import wave
from typing import Optional, Callable, Tuple
import numpy as np
import webrtcvad
from faster_whisper.vad import get_speech_timestamps

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from light_controller import get_light_controller
from conversation_session import ConversationSession

# 配置代理兜底
if not os.environ.get("HTTP_PROXY") and not os.environ.get("http_proxy"):
    os.environ["HTTP_PROXY"] = "http://127.0.0.1:7890"
    os.environ["HTTPS_PROXY"] = "http://127.0.0.1:7890"

class VoiceListener:
    INCOMPLETE_PREFIXES = {"我想看", "想看", "要看", "我要看", "帮我开", "帮我换", "换成", "改成", "把灯", "切换到", "显示", "展示"}
    def __init__(self, callback: Optional[Callable[[str], None]] = None):
        self.callback = callback

        self.is_listening = False
        self.is_paused = False
        self._pcm_queue: queue.Queue = queue.Queue(maxsize=400)
        self._utterance_queue: queue.Queue = queue.Queue(maxsize=3)
        self._is_processing = False
        self._current_led_mode = "listening"

        self._process_thread: Optional[threading.Thread] = None
        self._worker_thread: Optional[threading.Thread] = None
        self._watchdog_thread: Optional[threading.Thread] = None
        self._work_lock = threading.Lock()
        self._pending_prefix = ""
        self._speech_active = False

        # 唤醒状态机 (True 表示已唤醒，正在等待具体指令)
        self.is_awake = False
        self.session = ConversationSession(os.environ.get('KURISU_CONTINUOUS', '1') != '0')
        self.duplex = os.environ.get('KURISU_BARGE_IN') == '1' and os.environ.get('KURISU_AUDIO_TRANSPORT') == 'wifi'
        self._barge_audio = bytearray()
        self._barge_last = 0.
        self._barge_thread = None
        self._barge_pending = None
        self._barge_woke = False
        self.last_awake_time = 0.0
        self.awake_timeout = 10.0 # 唤醒后等待具体指令的时间窗口 (10秒)

        # 硬件控制器引用
        self.controller = get_light_controller()
        if self.duplex:
            from echo_cancellation import EchoCanceller
            self.controller.echo_canceller = EchoCanceller(delay_samples=int(os.environ.get('KURISU_ECHO_DELAY_MS','120'))*16)
        self.has_board_audio = False
        self._last_board_frame_time = 0.0
        self._resume_warmup_frames = 0

        # WebRTC VAD 引擎 (模式 2: 工业标准人声/环境噪均衡模式，精准识别人声，彻底免疫风扇杂音)
        self.vad = webrtcvad.Vad(2)

        self.wake_detector = None
        try:
            from wake_detector import WakeDetector
            self.wake_detector = WakeDetector(threshold=.50)
            print('[VoiceListener] 独立声学唤醒检测已就绪：助手 / 红莉栖 / 克里斯 / 牧濑红莉栖；阈值 0.50')
        except Exception as error:
            print(f'[VoiceListener] 声学唤醒未就绪，关闭自动唤醒，保留网页控制：{error}')

        # 初始化本地 faster-whisper 极速离线 ASR 模型 (base 模型：高精度音节辨别，NVIDIA RTX CUDA 加速)
        self.whisper_model = None
        torch_lib = r'C:\Users\Liu\anaconda3\envs\ai_cv_env\Lib\site-packages\torch\lib'
        if os.path.exists(torch_lib):
            if hasattr(os, 'add_dll_directory'):
                try:
                    os.add_dll_directory(torch_lib)
                except Exception:
                    pass
            if 'PATH' in os.environ and torch_lib not in os.environ['PATH']:
                os.environ['PATH'] = torch_lib + os.pathsep + os.environ['PATH']

        try:
            if torch.cuda.is_available():
                from faster_whisper import WhisperModel
                print("[VoiceListener] 正在载入本地 Whisper-Base 离线极速 ASR (NVIDIA RTX CUDA fp16)...")
                self.whisper_model = WhisperModel("base", device="cuda", compute_type="float16")
                print("[VoiceListener] >>> 本地离线 Whisper-Base ASR 已就绪 (GPU CUDA 加速) <<<")
            else:
                raise RuntimeError("CUDA not available")
        except Exception as e:
            print(f"[VoiceListener] CUDA 加速未能启动 ({e})，回退至 CPU int8 引擎...")
            from faster_whisper import WhisperModel
            self.whisper_model = WhisperModel("base", device="cpu", compute_type="int8", cpu_threads=4)
            print("[VoiceListener] >>> 本地离线 Whisper-Base ASR CPU int8 就绪 <<<")

    def _update_board_led(self, mode: str):
        """板载指示灯状态去重发送 (严格只在状态跳变时发送单条指令，杜绝频繁冲击)"""
        if self._current_led_mode != mode:
            self._current_led_mode = mode
            try:
                self.controller.set_board_led(mode)
            except Exception:
                pass

    def _check_wake_word(self, text: str) -> Tuple[bool, str]:
        # Exact configured names at the beginning; never substrings or homophones.
        match = re.match(r'^(?:你好[，, ]*)?(牧濑红莉栖|红莉栖|克里斯|助手)(?:[，,。！!？?\s]*)', text.strip())
        if not match:
            return False, ''
        remaining = text.strip()[match.end():].strip('，,。！!？? ')
        # Words discussing an assistant are not direct address.
        if remaining.startswith(('是什么', '的', '这个词', '这两个字', '不是', '怎么写', '什么意思')):
            return False, ''
        return True, remaining

    def _on_board_pcm(self, pcm_bytes: bytes):
        """来自 ESP32-S3 板载 INMP441 麦克风的原始 16kHz PCM 帧回调"""
        if not self.is_listening:
            return
        if self.duplex:
            pcm_bytes=self.controller.echo_canceller.process(pcm_bytes)
        if self.is_paused:
            if self.duplex:
                self._barge_audio.extend(pcm_bytes)
                self._barge_audio=self._barge_audio[-64000:]
                if len(self._barge_audio)>=32000 and time.monotonic()-self._barge_last>.7 and not(self._barge_thread and self._barge_thread.is_alive()):
                    self._barge_last=time.monotonic()
                    self._barge_thread=threading.Thread(target=self._check_barge,args=(bytes(self._barge_audio),),daemon=True)
                    self._barge_thread.start()
            return
        self.has_board_audio = True
        self._last_board_frame_time = time.time()
        try:
            self._pcm_queue.put_nowait(pcm_bytes)
        except queue.Full:
            pass

    def pause(self):
        """暂停收音并硬件级关闭麦克风 (在播放扬声器或思考时调用，杜绝回声循环与啸叫)"""
        self.is_paused = True
        self._speech_active = False
        try:
            if not self.duplex:self.controller.enable_mic(False)
        except Exception:
            pass
        # 清空所有待处理音频缓冲与队列
        while not self._pcm_queue.empty():
            try:
                self._pcm_queue.get_nowait()
            except queue.Empty:
                break
        while not self._utterance_queue.empty():
            try:
                self._utterance_queue.get_nowait()
            except queue.Empty:
                break

    def resume(self):
        """恢复收音 (播报完毕后重新开启麦克风监听)"""
        if not self.is_listening:
            return
        time.sleep(0.25) # 等待房间声学混响自然衰减
        while not self._pcm_queue.empty():
            try:
                self._pcm_queue.get_nowait()
            except queue.Empty:
                break
        while not self._utterance_queue.empty():
            try:
                self._utterance_queue.get_nowait()
            except queue.Empty:
                break
        self._resume_warmup_frames = 10 # 恢复后前 10 帧 (300ms) 仅用于校准底噪，防止扬声器残留尾音误触发
        try:
            self.controller.enable_mic(True)
        except Exception:
            pass
        self.is_paused = False

    def _worker_loop(self):
        """专属单任务 ASR 消费线程：保证先进先出且不堆积，杜绝延迟积压"""
        while self.is_listening:
            try:
                pcm_bytes = self._utterance_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            if self.is_paused:
                continue

            self._is_processing = True
            try:
                self._process_utterance(pcm_bytes)
            finally:
                self._is_processing = False

    def _process_utterance(self, pcm_bytes: bytes):
        """同步且单线程处理一段完整用户语音，严格遵循唤醒词与指令状态机"""
        with self._work_lock:
            try:
                acoustic_keyword = ''
                if not self.is_awake:
                    detector = getattr(self, 'wake_detector', None)
                    if detector is None:
                        self._update_board_led('listening')
                        return
                    acoustic_keyword = detector.detect(pcm_bytes)
                    if not acoustic_keyword:
                        self._update_board_led('listening')
                        return
                    print(f'[声学唤醒候选]: {acoustic_keyword}')
                text = ""
                if self.whisper_model is not None:
                    try:
                        audio_np = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                        peak = float(np.max(np.abs(audio_np))) if len(audio_np) else 0
                        if peak > 1e-5:
                            audio_np *= min(8.0, .75 / peak)

                        t_asr_start = time.perf_counter()
                        # 注入唤醒词与基础意图先验，杜绝 Whisper 对短音节猜想出 '呵呵'
                        prompt = "助手，克里斯，红莉栖，牧濑红莉栖，你好小智，开灯，关灯，调亮，调暗。我想看蓝灯，我想看红灯，我想看绿灯，换成蓝色，切换成红色。"
                        segments, info = self.whisper_model.transcribe(
                            audio_np,
                            language="zh",
                            beam_size=5,
                            temperature=0.0,
                            initial_prompt=prompt if self.is_awake else None,
                            without_timestamps=True,
                            condition_on_previous_text=False,
                            vad_filter=False, # 关键：由外部 WebRTC VAD 精准切分，严禁内部二次截断破坏音节！
                        )

                        # 如果非语音概率极高 (>0.85)，才判定为环境底噪并静默丢弃
                        if hasattr(info, 'no_speech_prob') and info.no_speech_prob > 0.85:
                            if not self.is_awake:
                                self._update_board_led("listening")
                            return

                        parts = []
                        scores = []
                        for s in segments:
                            if hasattr(s, 'no_speech_prob') and s.no_speech_prob > 0.85:
                                continue
                            parts.append(s.text.strip())
                            if hasattr(s, 'avg_logprob'):
                                scores.append(float(s.avg_logprob))

                        text = "".join(parts).strip()
                        dt_asr = (time.perf_counter() - t_asr_start) * 1000.0
                        if self.is_awake and scores:
                            # Keep only the most recent command for local ASR diagnosis.
                            try:
                                from pro_paths import cache_dir
                                diagnostic_dir = str(cache_dir() / 'voice-diagnostics')
                                os.makedirs(diagnostic_dir, exist_ok=True)
                                with wave.open(os.path.join(diagnostic_dir, 'last_command.wav'), 'wb') as recording:
                                    recording.setnchannels(1)
                                    recording.setsampwidth(2)
                                    recording.setframerate(16000)
                                    recording.writeframes(pcm_bytes)
                                stats = {'text': text, 'avg_logprob': sum(scores) / len(scores),
                                         'duration': len(audio_np) / 16000,
                                         'rms': float(np.sqrt(np.mean(audio_np ** 2))),
                                         'clipped_fraction': float(np.mean(np.abs(audio_np) >= .999))}
                                with open(os.path.join(diagnostic_dir, 'last_command.json'), 'w', encoding='utf-8') as diagnostic:
                                    json.dump(stats, diagnostic, ensure_ascii=False)
                                print(f'[指令音频诊断]: {stats}')
                            except OSError as diagnostic_error:
                                print(f'[诊断录音保存失败]: {diagnostic_error}')
                    except Exception as wex:
                        print(f"[Whisper ASR 异常]: {wex}")
                        text = ""
                        dt_asr = 0.0

                # 过滤 ASR 常见重复字符幻觉
                if re.search(r'(.)\1{4,}', text) or re.search(r'(.{2,4})\1{3,}', text):
                    print(f"[待命监听]: 过滤到 ASR 重复字符噪声: \"{text[:30]}...\"，静默丢弃。")
                    text = ""

                if not text or not text.strip():
                    if not self.is_awake:
                        self._update_board_led("listening")
                    return

                print(f"\n[ESP32 麦克风识别文本]: \"{text}\" (ASR 耗时: {dt_asr:.1f}ms)")

                # =========================================================
                # 状态 A: 当前处于休眠待命状态 (未唤醒，严格等待唤醒词)
                # =========================================================
                if not self.is_awake:
                    # ASR cannot distinguish identical pronunciations on an isolated
                    # word. Correct spelling only after the independent acoustic gate.
                    spellings = {'助手': ('住手',), '红莉栖': ('红丽栖', '红利栖'),
                                 '克里斯': ('克莉丝', '克里丝')}
                    for spelling in spellings.get(acoustic_keyword, ()):
                        text = re.sub(r'^(你好[，, ]*)?' + re.escape(spelling),
                                      lambda match: (match.group(1) or '') + acoustic_keyword, text, count=1)
                    is_wake, stripped_cmd = self._check_wake_word(text)
                    if not is_wake or acoustic_keyword not in text:
                        # 【铁律】：未检测到唤醒词，绝对不作任何语音应答！指示灯严格保持微光暗红
                        print(f"[待命监听]: 未检测到唤醒词 (仅听到: '{text}')，静默丢弃，指示灯保持暗红。")
                        self._update_board_led("listening")
                        return

                    # 命中唤醒词！
                    print(f"\n★★★★★ [专属唤醒成功] 听到唤醒词！进入交互模式 ★★★★★")
                    self._pending_prefix = ""
                    self.is_awake = True
                    self.last_awake_time = time.time()

                    # 情况 1: 一句话指令 (例如: "克里斯，把灯调成烈焰模式" / "克里斯蒂娜，开灯")
                    if len(stripped_cmd) >= 2:
                        prefix = stripped_cmd.rstrip("，。！？、…~ ")
                        if prefix in self.INCOMPLETE_PREFIXES:
                            self._pending_prefix = prefix
                            self._update_board_led("active")
                            return
                        print(f"[即时指令]: 提取到伴随指令 -> \"{stripped_cmd}\"")
                        self._update_board_led("thinking")
                        self.pause()
                        try:
                            if self.callback:
                                self.callback(stripped_cmd)
                        finally:
                            self._finish_turn(stripped_cmd)
                        return

                    # 情况 2: 仅呼唤了名字 (例如: "克里斯" / "牧濑红莉栖")
                    self.pause()
                    try:
                        self.controller.play_beep()
                        self._update_board_led("speaking") # 绿色 (语音播报中)
                        cur_dir = os.path.dirname(os.path.abspath(__file__))
                        wake_pcm = os.path.join(cur_dir, 'kurisu_wake_reply.pcm')
                        if os.path.exists(wake_pcm):
                            with open(wake_pcm, 'rb') as source:
                                self.controller.play_audio_pcm(source.read())
                    except Exception as ex:
                        print(f"[唤醒应答异常]: {ex}")
                    finally:
                        self.resume()
                        self.last_awake_time = time.time()
                        self._update_board_led("active") # 青蓝微呼吸，提示已唤醒，正在等待指令
                        print("[等待指令]: 红莉栖已就绪，请在 10 秒内说出指令...")
                    return

                # =========================================================
                # 状态 B: 当前已处于唤醒等待指令状态 (is_awake == True)
                # =========================================================
                else:
                    self.last_awake_time = time.time()
                    is_wake, stripped_cmd = self._check_wake_word(text)
                    cmd_to_exec = stripped_cmd if (is_wake and len(stripped_cmd) >= 2) else text

                    # 提取纯汉字与字母数字有效字符
                    clean_words = re.sub(r'[，。！？、…~\s\da-zA-Z]', '', cmd_to_exec).strip()
                    hesitation_words = {"我", "看", "说", "我说", "那个", "这个", "在", "喂", "啊", "嗯", "哦", "好的", "对", "呢", "吧"}
                    if len(clean_words) < 2 or clean_words in hesitation_words:
                        print(f"[等待指令]: 捕获到过渡字词/停顿 (仅听到: '{cmd_to_exec}')，保持唤醒状态，静候完整有效指令...")
                        self.last_awake_time = time.time()
                        self._update_board_led("active")
                        return

                    # Retain text across utterances; never recurse while holding
                    # _work_lock or block the ASR worker waiting for its own queue.
                    if self._pending_prefix:
                        cmd_to_exec = self._pending_prefix + cmd_to_exec
                        self._pending_prefix = ""
                        clean_words = re.sub(r'[，。！？、…~\s]', '', cmd_to_exec)
                    if clean_words in self.INCOMPLETE_PREFIXES:
                        self._pending_prefix = cmd_to_exec.rstrip("，。！？、…~ ")
                        self._update_board_led("active")
                        return

                    print(f"[执行指令]: \"{cmd_to_exec}\"")
                    self._update_board_led("thinking")
                    self.pause()
                    try:
                        if self.callback:
                            self.callback(cmd_to_exec)
                    finally:
                        self._finish_turn(cmd_to_exec)

            except Exception as e:
                print(f"[VoiceListener 处理异常]: {e}")
                self._update_board_led("listening")

    def _check_barge(self, pcm):
        # The experimental duplex path keeps the same two-stage wake gate.
        if not self.is_paused or not self.duplex or self.wake_detector is None:return
        if self.wake_detector.detect(pcm) and self.whisper_model is not None:
            audio_np=np.frombuffer(pcm,dtype=np.int16).astype(np.float32)/32768
            try:
                segments,_=self.whisper_model.transcribe(audio_np,language='zh',beam_size=1,temperature=0.0,
                    initial_prompt=None,condition_on_previous_text=False,without_timestamps=True)
                text=''.join(s.text for s in segments).strip()
                confirmed,command=self._check_wake_word(text)
            except Exception:return
            if not confirmed or not self.is_paused:return
            self._barge_woke=True
            self._barge_pending=pcm if len(command)>=2 else None
            audio=getattr(self.controller,'_network_audio',None)
            if audio:audio.cancelled.set()
            self.controller.playback_cancel.set()
            self.controller.send_json({'cmd':'audio_abort'})
            self._barge_audio.clear()

    def _finish_turn(self, text):
        self.is_awake = self.session.after_reply() and not self.session.should_end(text)
        if getattr(self,'_barge_woke',False):self.is_awake=True
        pending=getattr(self,'_barge_pending',None)
        self._barge_pending=None;self._barge_woke=False
        self.last_awake_time = time.time()
        self._pending_prefix = ''
        self.resume()
        if pending:
            try:self._utterance_queue.put_nowait(pending)
            except queue.Full:pass
        self._update_board_led('active' if self.is_awake else 'listening')

    def _watchdog_loop(self):
        """后台看门狗：唤醒后若 10 秒内未收到具体指令，自动退回暗红待命状态"""
        while self.is_listening:
            time.sleep(1.0)
            self._expire_idle_wake()

    def _expire_idle_wake(self):
        # Keep the current wake window while capture/recognition is in flight.
        if (not self.is_awake or self.is_paused or self._speech_active or
                self._is_processing or not self._utterance_queue.empty()):
            return False
        if time.time() - self.last_awake_time <= self.awake_timeout:
            return False
        print("\n[待命超时]: 空闲等待超过 10 秒，退回暗红待命状态。")
        self.is_awake = False
        self._pending_prefix = ""
        self._update_board_led("listening")
        return True

    def _process_loop(self):
        """
        板载麦克风实时音频流处理与工业级 VAD 端点检测中枢
        严格对齐 Intelligent-Lighting-Control-System-Mid (中阶) 的 AFE VAD 核心机制:
        - 帧长: 30ms (480 采样点 @ 16kHz 16-bit Mono, 960 字节)
        - 去直流: 减去帧内均值偏置，彻底滤除 INMP441 的硬件 DC 漂移 (将 3500+ RMS 虚假底噪彻底压至 < 100)
        - WebRTC VAD Mode 2: 基于高斯混合模型 (GMM) 进行语音频段能量及共振峰特征鉴别
        - 起始防抖门限 (afe_config->vad_min_noise_ms = 100): 连续 3 帧 (90ms) 检出语音才确认为说话起始
        - 静音悬挂结束门限 (kListeningModeAutoStop):
          * 待命唤醒期: 连续 10 帧 (~300ms) 静音即切断端点
          * 交互指令期: 连续 16 帧 (~480ms) 静音即切断端点，交付大模型响应
        - 指示灯联动:
          * 用户说话中 -> hearing (鲜亮红光，对齐中阶 HIGH_BRIGHTNESS)
          * 用户停顿/静音 -> listening (微弱暗红，对齐中阶 LOW_BRIGHTNESS)
        - Silero VAD 二次神经验证: 交付前验证是否存在真实人类音素，彻底阻断风扇/环境白噪音虚警
        """
        print("[VoiceListener] 正在接管 ESP32-S3 板载麦克风硬件音频流 (已对齐中阶工业级 WebRTC VAD 端点检测)...")

        FRAME_SAMPLES = 480       # 30ms 帧 (480 个采样)
        FRAME_BYTES = FRAME_SAMPLES * 2  # 960 字节

        raw_stream_buffer = bytearray()
        preroll_frames = collections.deque(maxlen=16) # 预留 480ms 预滚动帧，完整保留起始辅音音素
        speech_frames = []
        is_speaking = False
        silent_count = 0
        speech_trigger_count = 0
        ambient_energy = 1000.0  # 动态环境声能基线
        warmup_frames = 20  # 启动前 600ms 用于麦克风硬件稳定与 DC 校准

        while self.is_listening:
            try:
                pcm_chunk = self._pcm_queue.get(timeout=0.2)
            except queue.Empty:
                if self.is_listening and not self.is_paused and (time.time() - self._last_board_frame_time > 6.0):
                    self._last_board_frame_time = time.time()
                    self._speech_active = False
                    is_speaking = False
                    speech_frames.clear()
                    preroll_frames.clear()
                    raw_stream_buffer.clear()
                    if self.controller.audio_connected:
                        self.controller.enable_mic(True)
                continue

            if self.is_paused:
                raw_stream_buffer.clear()
                speech_frames.clear()
                preroll_frames.clear()
                is_speaking = False
                silent_count = 0
                speech_trigger_count = 0
                continue

            raw_stream_buffer.extend(pcm_chunk)

            # 按 30ms (960 字节) 严格对齐切帧处理
            while len(raw_stream_buffer) >= FRAME_BYTES:
                frame_bytes = bytes(raw_stream_buffer[:FRAME_BYTES])
                del raw_stream_buffer[:FRAME_BYTES]

                # 1. 消除 INMP441 硬件直流偏置 (DC offset)
                frame_np = np.frombuffer(frame_bytes, dtype=np.int16)
                mean_offset = np.mean(frame_np)
                ac_frame = np.clip(frame_np - mean_offset, -32768, 32767).astype(np.int16)
                ac_bytes = ac_frame.tobytes()

                # 2. 测量 AC 真实交流声能 (RMS)
                ac_rms = float(np.sqrt(np.mean(ac_frame.astype(np.float32)**2)))

                # 丢弃启动期瞬态突刺
                if warmup_frames > 0:
                    warmup_frames -= 1
                    preroll_frames.clear()
                    ambient_energy = 0.9 * ambient_energy + 0.1 * ac_rms
                    continue

                # 丢弃扬声器播报后的混响尾音
                if self._resume_warmup_frames > 0:
                    self._resume_warmup_frames -= 1
                    preroll_frames.clear()
                    ambient_energy = 0.9 * ambient_energy + 0.1 * ac_rms
                    continue

                # 3. 动态自适应跟踪环境底噪声能
                if not is_speaking:
                    ambient_energy = 0.98 * ambient_energy + 0.02 * ac_rms

                # 双门限动态自适应计算:
                # 起始门限: 至少 300 RMS (或底噪 1.8 倍)
                # 持续门限: 至少 200 RMS (或底噪 1.3 倍)，确保轻声清辅音与过渡音素不被误当静音
                start_threshold = max(300.0, ambient_energy * 1.8)
                continue_threshold = max(200.0, ambient_energy * 1.3)

                # 4. WebRTC VAD 模式 2 工业级判决
                frame_vad_speech = False
                try:
                    frame_vad_speech = self.vad.is_speech(ac_bytes, 16000)
                except Exception:
                    frame_vad_speech = False

                # 5. 状态机：端点检测 (起始检测 vs 结束判定)
                if not is_speaking:
                    preroll_frames.append(ac_bytes)
                    if frame_vad_speech and ac_rms >= start_threshold:
                        speech_trigger_count += 1
                        # 连续 2 帧 (60ms) 语音即可敏锐确认起始，保留完整句首
                        if speech_trigger_count >= 2:
                            is_speaking = True
                            self._speech_active = True
                            if self.is_awake:
                                self.last_awake_time = time.time()
                            silent_count = 0
                            speech_trigger_count = 0
                            speech_frames = list(preroll_frames)
                            # 对齐中阶 single_led.cc: 说话时点亮鲜红 hearing (HIGH_BRIGHTNESS)
                            self._update_board_led("hearing")
                            tag = "【等待指令中】" if self.is_awake else "【待命·等待唤醒词】"
                            print(f"\n[ESP32 麦克风: {tag} 检测到语音输入 (VAD 触发, RMS: {ac_rms:.0f})...]", end="", flush=True)
                    else:
                        speech_trigger_count = 0
                else:
                    speech_frames.append(ac_bytes)

                    # 最大拾音时长保护：待命期最多 3.5s (116帧)，等待指令期最多 8.0s (266帧)
                    max_frames = 266 if self.is_awake else 116
                    if len(speech_frames) >= max_frames:
                        silent_count = 999 # 达到上限立即强制判停交付
                    elif (not frame_vad_speech) or (ac_rms < continue_threshold):
                        silent_count += 1
                    else:
                        # 只要 WebRTC VAD 确认是人声且能量高于持续门限，保持静音计数为 0
                        silent_count = 0
                        self._update_board_led("hearing")

                    # 悬挂断句门限：
                    # 待命唤醒期 16 帧 (~480ms 干净利落切断唤醒词)；
                    # 等待指令期 36 帧 (~1080ms 充分容纳词间换气与断句，绝不把完整长句腰斩切成两截！)
                    silent_limit = 36 if self.is_awake else 16
                    if silent_count >= silent_limit:
                        is_speaking = False
                        silent_count = 0
                        speech_trigger_count = 0

                        # 语音结束端点已到达！
                        # 指示灯根据当前状态切换：若未唤醒退回微光暗红，已唤醒转入青蓝思考流光
                        if not self.is_awake:
                            self._update_board_led("listening")
                        else:
                            self._update_board_led("thinking")

                        total_samples = len(speech_frames) * FRAME_SAMPLES
                        # 要求有效发音时长至少 0.35 秒 (12 帧以上)
                        if total_samples >= 16000 * 0.35:
                            full_pcm = b"".join(speech_frames)
                            has_real_speech = True

                            # 仅对小于 0.8s 的极短片段做 Silero 二次验证
                            if total_samples < 16000 * 0.8:
                                try:
                                    audio_float = np.frombuffer(full_pcm, dtype=np.int16).astype(np.float32) / 32768.0
                                    timestamps = get_speech_timestamps(audio_float)
                                    has_real_speech = len(timestamps) > 0
                                except Exception:
                                    has_real_speech = True

                            if has_real_speech:
                                print(f" [VAD 端点检测完成: 拾取语音 {(total_samples/16000.0):.2f}s]")
                                if not self.is_paused:
                                    try:
                                        self._utterance_queue.put_nowait(full_pcm)
                                    except queue.Full:
                                        try:
                                            self._utterance_queue.get_nowait()
                                        except queue.Empty:
                                            pass
                                        try:
                                            self._utterance_queue.put_nowait(full_pcm)
                                        except queue.Full:
                                            pass
                            else:
                                state_led = "active" if self.is_awake else "listening"
                                self._update_board_led(state_led)
                        else:
                            state_led = "active" if self.is_awake else "listening"
                            self._update_board_led(state_led)

                        speech_frames.clear()
                        self._speech_active = False

    def start(self):
        if self.is_listening:
            return
        self.is_listening = True
        self.controller._voice_listener = self
        self.is_paused = False
        self.is_awake = False
        self._pending_prefix = ""
        self._is_processing = False

        self.controller.on_mic_data = self._on_board_pcm
        if self.controller.connect_audio():
            self.controller.enable_mic(True)
            self._update_board_led("listening")

        self._process_thread = threading.Thread(target=self._process_loop, daemon=True)
        self._process_thread.start()
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
        self._watchdog_thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self._watchdog_thread.start()

    def stop(self):
        self.is_listening = False
        self.pause()
        if self.controller.audio_connected:
            self.controller.enable_mic(False)
            self._update_board_led("green")

_voice_listener_instance: Optional[VoiceListener] = None

def get_voice_listener(callback: Optional[Callable[[str], None]] = None) -> VoiceListener:
    global _voice_listener_instance
    if _voice_listener_instance is None:
        _voice_listener_instance = VoiceListener(callback)
    elif callback is not None:
        _voice_listener_instance.callback = callback
    return _voice_listener_instance
