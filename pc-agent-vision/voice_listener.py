"""
VoiceListener: 麦克风实时语音拾音与语音识别中枢 (ASR)
支持本地麦克风监听、静音端点检测 (VAD) 与即时语音转文字
实现免键盘全语音唤醒与双向声光闭环
"""

import sys
import time
import threading
from typing import Optional, Callable

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

import speech_recognition as sr

class VoiceListener:
    def __init__(self, callback: Optional[Callable[[str], None]] = None):
        self.callback = callback
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        self.is_listening = False
        self._thread: Optional[threading.Thread] = None

    def _listen_loop(self):
        print("[VoiceListener] 麦克风实时语音监听已启动 (对着麦克风说话即可)...")
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.6)
            
            while self.is_listening:
                try:
                    audio = self.recognizer.listen(source, timeout=2.0, phrase_time_limit=10.0)
                    try:
                        # 采用 Windows 原生/默认识别通道 (支持普通话与基础英文/日文)
                        text = self.recognizer.recognize_google(audio, language="zh-CN")
                        if text and text.strip():
                            print(f"\n[麦克风捕获语音]: {text}")
                            if self.callback:
                                self.callback(text)
                    except sr.UnknownValueError:
                        pass
                    except sr.RequestError as e:
                        # 网络异常时静默重试
                        pass
                except sr.WaitTimeoutError:
                    continue
                except Exception as e:
                    time.sleep(0.5)

    def start(self):
        if self.is_listening:
            return
        self.is_listening = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.is_listening = False
        if self._thread:
            self._thread.join(timeout=1.0)
        print("[VoiceListener] 麦克风监听已停止")

# 单例导出
_listener_instance: Optional[VoiceListener] = None

def get_voice_listener(callback: Optional[Callable[[str], None]] = None) -> VoiceListener:
    global _listener_instance
    if _listener_instance is None:
        _listener_instance = VoiceListener(callback)
    elif callback:
        _listener_instance.callback = callback
    return _listener_instance
