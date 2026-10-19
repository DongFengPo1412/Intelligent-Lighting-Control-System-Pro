"""
VoiceListener: ESP32-S3 板载 INMP441 数字麦克风实时音频流采集与语音识别中枢 (ASR)
直接接收来自 ESP32-S3 核心通过 USB-Serial-JTAG 硬件直通的 16kHz 16-bit 原始 PCM 流
- 单极点 DC 阻断器、动态自适应能量端点检测 (VAD)
- 硬件级双工静音 (播放语音时关断麦克风，彻底杜绝自激啸叫与无限回声循环)
- 本地端侧 Whisper 极速离线识别 (毫秒级响应，中日双语)
- 【牧濑红莉栖专属唤醒词严格门禁系统】(未检出唤醒词绝对不答话、不乱动)
"""

import os
import sys
import torch
import re
import time
import queue
import threading
import collections
from typing import Optional, Callable, Tuple
import numpy as np

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

import speech_recognition as sr
from light_controller import get_light_controller

# 配置代理兜底
if not os.environ.get("HTTP_PROXY") and not os.environ.get("http_proxy"):
    os.environ["HTTP_PROXY"] = "http://127.0.0.1:7890"
    os.environ["HTTPS_PROXY"] = "http://127.0.0.1:7890"

class VoiceListener:
    def __init__(self, callback: Optional[Callable[[str], None]] = None):
        self.callback = callback
        self.recognizer = sr.Recognizer()

        self.is_listening = False
        self.is_paused = False
        self._pcm_queue: queue.Queue = queue.Queue(maxsize=300)
        self._process_thread: Optional[threading.Thread] = None
        self._watchdog_thread: Optional[threading.Thread] = None
        self._work_lock = threading.Lock()

        # 唤醒状态机 (True 表示已唤醒，正在等待单轮指令)
        self.is_awake = False
        self.last_awake_time = 0.0
        self.awake_timeout = 10.0 # 唤醒后等待具体指令的时间窗口 (10秒)

        # 硬件控制器引用
        self.controller = get_light_controller()
        self.has_board_audio = False
        self._last_board_frame_time = 0.0

        # DC 阻断滤波器状态
        self._prev_x = 0.0
        self._prev_y = 0.0
        self._dc_alpha = 0.995

        # 初始化本地 faster-whisper 极速离线 ASR 模型
        self.whisper_model = None
        try:
            from faster_whisper import WhisperModel
            print("[VoiceListener] 正在载入本地 Whisper 离线极速语音识别引擎 (CPU int8)...")
            self.whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8", cpu_threads=4)
            print("[VoiceListener] >>> 本地离线 Whisper ASR 引擎就绪 (端侧 0 延迟，0 网络开销，支持中日语) <<<")
        except Exception as e:
            print(f"[VoiceListener 警告] 加载本地 Whisper 失败: {e}，将采用备用引擎")

    def _check_wake_word(self, text: str) -> Tuple[bool, str]:
        """
        严格检验语音文本是否包含牧濑红莉栖专属唤醒词:
        支持:
          - 日语: Makise Kurisu, Kurisu, まきせくりす, くりす, クリス, マキセ
          - 中文: 牧濑红莉栖, 红莉栖, 牧濑, 克里斯, 克里斯蒂娜, 助手, 栗子
        返回: (is_wake, stripped_command_text)
        """
        t = text.strip()
        wake_patterns = [
            r'makise\s*kurisu',
            r'kurisu',
            r'makise',
            r'christina',
            r'kris',
            r'chris',
            r'まきせ\s*くりす',
            r'くりす',
            r'クリス',
            r'マキセ',
            # 中文全称与多音字、同音字容错 (牧濑红莉栖)
            r'[牧木目穆][濑赖赛莱拉来奶][红洪虹][莉利丽立力栗茜][栖茜夕溪七期齐]',
            r'[牧木目穆][濑赖赛莱拉来奶]',
            r'[红洪虹][莉利丽立力栗茜][栖茜夕溪七期齐]',
            # 克里斯 / 克里斯蒂娜 (增加骨皮丝、古皮丝、柯里斯等常见轻量 ASR 谐音)
            r'[克科库刻客骨古顾格柯酷][莉丽里立栗皮匹佩][斯诗思丝四][蒂迪地][娜那]',
            r'[克科库刻客骨古顾格柯酷][莉丽里立栗皮匹佩][斯诗思丝四]',
            r'骨皮丝',
            r'古皮丝',
            r'克里斯蒂娜',
            r'克里斯',
            r'库里斯',
            r'克莉丝',
            r'马奇赛',
            r'马基塞',
            r'苦力苏',
            r'栗子',
            r'助手' # 叫她助手会气愤回怼“都说了我不是助手！”
        ]
        matched = False
        cleaned = t
        for pat in wake_patterns:
            if re.search(pat, cleaned, flags=re.I):
                matched = True
                cleaned = re.sub(pat, '', cleaned, flags=re.I).strip()
        cleaned = re.sub(r'^[，,。！!？?\s~～…]+', '', cleaned).strip()
        cleaned = re.sub(r'[，,。！!？?\s~～…]+$', '', cleaned).strip()
        # 剥离无意义语气词
        cleaned = re.sub(r'^[啊呢吧呀哦啦嗯\s]+', '', cleaned).strip()
        cleaned = re.sub(r'[啊呢吧呀哦啦嗯\s]+$', '', cleaned).strip()

        # 常见打招呼与问候词视为纯唤醒
        greetings = {"在吗", "在不在", "你好", "在嘛", "在呀", "听得到吗", "听得见吗", "出来", "出来呀"}
        if cleaned in greetings:
            cleaned = ""

        return matched, cleaned

    def _on_board_pcm(self, pcm_bytes: bytes):
        """来自 ESP32-S3 板载 INMP441 麦克风的原始 16kHz PCM 帧回调"""
        if not self.is_listening or self.is_paused:
            return
        self.has_board_audio = True
        self._last_board_frame_time = time.time()
        try:
            self._pcm_queue.put_nowait(pcm_bytes)
        except queue.Full:
            pass

    def pause(self):
        """暂停收音并硬件级关闭麦克风 (在播放扬声器时调用，彻底杜绝回声循环)"""
        self.is_paused = True
        try:
            self.controller.enable_mic(False)
        except Exception:
            pass
        while not self._pcm_queue.empty():
            try:
                self._pcm_queue.get_nowait()
            except queue.Empty:
                break

    def resume(self):
        """恢复收音 (播报完毕后重新开启麦克风监听)"""
        time.sleep(0.3) # 等待房间物理混响衰减
        while not self._pcm_queue.empty():
            try:
                self._pcm_queue.get_nowait()
            except queue.Empty:
                break
        self._prev_x = 0.0
        self._prev_y = 0.0
        try:
            self.controller.enable_mic(True)
        except Exception:
            pass
        self.is_paused = False

    def _filter_dc(self, samples: np.ndarray) -> np.ndarray:
        """单极点 IIR 直流滤波"""
        filtered = np.zeros_like(samples, dtype=np.float32)
        curr_x = self._prev_x
        curr_y = self._prev_y
        alpha = self._dc_alpha
        for i in range(len(samples)):
            x = samples[i]
            y = x - curr_x + alpha * curr_y
            filtered[i] = y
            curr_x = x
            curr_y = y
        self._prev_x = curr_x
        self._prev_y = curr_y
        return filtered

    def _process_utterance(self, pcm_bytes: bytes):
        """同步且单线程处理一段完整用户语音，严格遵循唤醒词与指令状态机"""
        with self._work_lock:
            try:
                text = ""
                # 1. 本地离线 Whisper 识别 (锁定为中文 zh，杜绝短语音时误判英文诱发 "Thank you" / "Good" 幻觉)
                if self.whisper_model is not None:
                    try:
                        audio_np = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                        segments, info = self.whisper_model.transcribe(
                            audio_np,
                            language="zh",
                            beam_size=1,
                            initial_prompt=None,
                            condition_on_previous_text=False
                        )
                        parts = [s.text.strip() for s in segments]
                        text = "".join(parts).strip()
                    except Exception as wex:
                        print(f"[Whisper ASR 异常]: {wex}")
                        text = ""

                # 过滤 ASR 常见的重复字符幻觉 (如 "黏黏黏黏黏", "引引引引引")
                if re.search(r'(.)\1{4,}', text) or re.search(r'(.{2,4})\1{3,}', text):
                    print(f"[待命监听]: 过滤到 ASR 重复字符噪声: \"{text[:30]}...\"，静默丢弃。")
                    text = ""

                if not text or not text.strip():
                    if not self.is_awake:
                        self.controller.set_board_led("listening")
                    return

                print(f"\n[ESP32 麦克风识别文本]: \"{text}\"")

                # =========================================================
                # 状态 A: 当前处于休眠待命状态 (未唤醒，严格等待唤醒词)
                # =========================================================
                if not self.is_awake:
                    is_wake, stripped_cmd = self._check_wake_word(text)
                    if not is_wake:
                        # 【铁律】：未检测到唤醒词，绝对不作任何语音应答！指示灯严格保持微光暗红
                        print(f"[待命监听]: 未检测到唤醒词 (仅听到: '{text}')，静默丢弃，指示灯保持暗红。")
                        self.controller.set_board_led("listening")
                        return

                    # 命中唤醒词！
                    print(f"\n★★★★★ [专属唤醒成功] 听到唤醒词！进入交互模式 ★★★★★")
                    self.is_awake = True
                    self.last_awake_time = time.time()

                    # 情况 1: 一句话指令 (例如: "克里斯，把灯调成烈焰模式")
                    if len(stripped_cmd) >= 2:
                        print(f"[即时指令]: 提取到伴随指令 -> \"{stripped_cmd}\"")
                        # 即时指令进入思考计算状态 (青蓝微呼吸)
                        self.controller.set_board_led("thinking")
                        self.pause()
                        try:
                            if self.callback:
                                self.callback(stripped_cmd)
                        finally:
                            # 单轮指令执行完毕，自动恢复暗红待命状态
                            self.is_awake = False
                            self.resume()
                            self.controller.set_board_led("listening")
                        return

                    # 情况 2: 仅呼唤了名字 (例如: "克里斯" / "牧濑红莉栖")
                    # 给出简短唤醒应答并保持 10 秒窗口等待后续指令
                    self.pause()
                    try:
                        self.controller.play_beep()
                        self.controller.set_board_led("speaking") # 绿色 (语音播报中)
                        cur_dir = os.path.dirname(os.path.abspath(__file__))
                        wake_pcm = os.path.join(cur_dir, "kurisu_wake_reply.pcm")
                        if os.path.exists(wake_pcm):
                            with open(wake_pcm, "rb") as f:
                                self.controller.play_audio_pcm(f.read())
                        else:
                            from voice_engine import get_voice_engine
                            get_voice_engine().speak("な、何よ？有事快说！\nふん、何用？早く言いなさいよ！", block=True)
                    except Exception as ex:
                        print(f"[唤醒应答异常]: {ex}")
                    finally:
                        self.resume()
                        self.last_awake_time = time.time()
                        self.controller.set_board_led("active") # 青蓝微呼吸，提示已唤醒，正在等待指令
                        print("[等待指令]: 红莉栖已就绪，请在 10 秒内说出指令...")
                    return

                # =========================================================
                # 状态 B: 当前已处于唤醒等待指令状态 (is_awake == True)
                # =========================================================
                else:
                    self.last_awake_time = time.time()
                    is_wake, stripped_cmd = self._check_wake_word(text)
                    cmd_to_exec = stripped_cmd if (is_wake and len(stripped_cmd) >= 2) else text

                    print(f"[执行指令]: \"{cmd_to_exec}\"")
                    # 进入大模型思考运算状态 (青蓝微呼吸)
                    self.controller.set_board_led("thinking")
                    self.pause()
                    try:
                        if self.callback:
                            self.callback(cmd_to_exec)
                    finally:
                        # 指令交互完毕，退出唤醒状态，回到暗红待命监听
                        self.is_awake = False
                        self.resume()
                        self.controller.set_board_led("listening")
                        print("[交互完毕]: 系统已自动退回微光暗红待命状态，再次呼唤唤醒词即可开启新对话。\n")

            except Exception as e:
                print(f"[VoiceListener 处理异常]: {e}")
                self.controller.set_board_led("listening")

    def _watchdog_loop(self):
        """后台看门狗：唤醒后若 10 秒内未收到具体指令，自动退回暗红待命状态"""
        while self.is_listening:
            time.sleep(1.0)
            if self.is_awake and not self.is_paused:
                if time.time() - self.last_awake_time > self.awake_timeout:
                    print("\n[待命超时]: 超过 10 秒未输入指令，自动退回暗红待命状态。")
                    self.is_awake = False
                    self.controller.set_board_led("listening")

    def _process_loop(self):
        """板载麦克风实时音频流处理与 VAD 端点检测"""
        print("[VoiceListener] 正在接管 ESP32-S3 板载麦克风硬件音频流...")
        preroll_chunks = collections.deque(maxlen=24)
        speech_chunks = []
        is_speaking = False
        silent_count = 0
        ambient_energy = 800.0
        warmup_frames = 60  # 前 60 帧 (约 1.2 秒) 仅用于校准底噪与直流滤波器，严禁触发 VAD 拾音
        speech_trigger_count = 0

        while self.is_listening:
            try:
                pcm_bytes = self._pcm_queue.get(timeout=0.2)
            except queue.Empty:
                if self.is_listening and not self.is_paused and (time.time() - self._last_board_frame_time > 6.0):
                    self._last_board_frame_time = time.time() # 记录时间戳，严禁每 200ms 重入轰炸串口
                    if self.controller.is_connected:
                        self.controller.enable_mic(True)
                continue

            if self.is_paused:
                speech_chunks.clear()
                preroll_chunks.clear()
                is_speaking = False
                silent_count = 0
                speech_trigger_count = 0
                continue

            raw_samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32)
            filtered_samples = self._filter_dc(raw_samples)
            rms = float(np.sqrt(np.mean(filtered_samples**2)))

            # 启动期丢弃瞬态突刺、清空预滚动缓冲并平滑收敛底噪
            if warmup_frames > 0:
                warmup_frames -= 1
                preroll_chunks.clear()
                ambient_energy = 0.9 * ambient_energy + 0.1 * rms
                continue

            ambient_energy = 0.98 * ambient_energy + 0.02 * rms
            
            # 双门限迟滞比较器 (Hysteresis VAD):
            # 实测安静状态下麦克风供电与底噪偶尔脉冲可达 3000~4900 RMS，人声正常说话在 7500~20000 RMS。
            # 起始阈值: 设定为 6200 (并连续 3 帧)，彻底杜绝未说话时底噪引发的忽亮忽暗！
            # 持续阈值: 3500 (防止人声说话字词间停顿断流)
            start_threshold = max(6200.0, ambient_energy * 3.2)
            continue_threshold = max(3500.0, ambient_energy * 1.6)

            if not is_speaking:
                preroll_chunks.append(filtered_samples)
                if rms > start_threshold:
                    speech_trigger_count += 1
                    # 连续 3 帧 (>45ms) 超过阈值才确认为人声起始，杜绝单点杂音脉冲
                    if speech_trigger_count >= 3:
                        is_speaking = True
                        silent_count = 0
                        speech_trigger_count = 0
                        speech_chunks = list(preroll_chunks)
                        speech_chunks.append(filtered_samples)
                        self.controller.set_board_led("hearing") # 鲜亮红光 (检测到人声说话)
                        tag = "【等待指令中】" if self.is_awake else "【待命·等待唤醒词】"
                        print(f"\n[ESP32 麦克风: {tag} 拾音中 (RMS: {rms:.0f})...]", end="", flush=True)
                else:
                    speech_trigger_count = 0
            else:
                speech_chunks.append(filtered_samples)
                if rms < continue_threshold:
                    silent_count += 1
                    # 静音容忍帧数: 待命唤醒 26 帧 (~390ms)，等待指令 32 帧 (~480ms)
                    silent_limit = 32 if self.is_awake else 26
                    if silent_count >= silent_limit:
                        is_speaking = False
                        silent_count = 0
                        speech_trigger_count = 0
                        # 说话结束：
                        # 若当前未唤醒 (待命状态)，指示灯立刻退回【微光暗红】(listening)，绝不闪现浅青蓝！
                        # 仅当已处于唤醒中，才切换为青蓝流光 (thinking) 提示大模型正在运算
                        if not self.is_awake:
                            self.controller.set_board_led("listening")
                        else:
                            self.controller.set_board_led("thinking")

                        total_samples = sum(len(c) for c in speech_chunks)
                        max_chunk_rms = max(float(np.sqrt(np.mean(c**2))) for c in speech_chunks) if speech_chunks else 0.0

                        # 要求至少 0.45 秒语音且峰值能量真实有效 (>6200)，彻底过滤日常环境白噪音
                        if total_samples >= 16000 * 0.45 and max_chunk_rms >= 6200.0:
                            full_pcm = np.clip(np.concatenate(speech_chunks), -32768, 32767).astype(np.int16).tobytes()
                            # 异步分发至工作线程，确保 _process_loop 不被 ASR 推理耗时阻塞
                            threading.Thread(target=self._process_utterance, args=(full_pcm,), daemon=True).start()
                        else:
                            state_led = "active" if self.is_awake else "listening"
                            self.controller.set_board_led(state_led)
                        speech_chunks.clear()
                else:
                    silent_count = 0

    def start(self):
        if self.is_listening:
            return
        self.is_listening = True
        self.is_paused = False
        self.is_awake = False

        self.controller.on_mic_data = self._on_board_pcm
        if self.controller.is_connected:
            self.controller.enable_mic(True)
            self.controller.set_board_led("listening")

        self._process_thread = threading.Thread(target=self._process_loop, daemon=True)
        self._process_thread.start()
        self._watchdog_thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self._watchdog_thread.start()

    def stop(self):
        self.is_listening = False
        self.pause()
        if self.controller.is_connected:
            self.controller.enable_mic(False)
            self.controller.set_board_led("green")

_voice_listener_instance: Optional[VoiceListener] = None

def get_voice_listener(callback: Optional[Callable[[str], None]] = None) -> VoiceListener:
    global _voice_listener_instance
    if _voice_listener_instance is None:
        _voice_listener_instance = VoiceListener(callback)
    elif callback is not None:
        _voice_listener_instance.callback = callback
    return _voice_listener_instance
