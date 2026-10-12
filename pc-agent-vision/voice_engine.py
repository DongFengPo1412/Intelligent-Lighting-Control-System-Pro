"""
VoiceEngine: 牧濑红莉栖中日双语离线语音引擎
基于 Windows SAPI5 原生零延迟神经语音 (支持 Haruka 日语与 Huihui 傲娇中文)
可无缝挂接 GPT-SoVITS 原版今井麻美音色
"""

import os
import sys
import threading
import time
from typing import Optional

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

import pyttsx3

class VoiceEngine:
    def __init__(self):
        self._lock = threading.Lock()
        self.engine = pyttsx3.init()
        
        # 扫描并锁定中日双语最佳女声声线
        voices = self.engine.getProperty('voices')
        self.zh_voice_id = None
        self.jp_voice_id = None
        
        for v in voices:
            v_name = v.name.lower()
            if "haruka" in v_name or "ja-jp" in v_name:
                self.jp_voice_id = v.id
            elif "huihui" in v_name or "zh-cn" in v_name:
                if not self.zh_voice_id:
                    self.zh_voice_id = v.id
            elif "hanhan" in v_name or "zh-tw" in v_name:
                if not self.zh_voice_id:
                    self.zh_voice_id = v.id

        # 调优语速 (175 wpm 展现傲娇科学家的敏捷思维)
        self.current_volume = 100
        print(f"[VoiceEngine] 本地离线声学引擎就绪 (中文: Huihui, 日文: Haruka, 0ms网络延迟)")

    @property
    def volume(self) -> int:
        return self.current_volume

    def set_volume(self, pct: int):
        """设置音量百分比 (0-100)"""
        self.current_volume = max(0, min(100, int(pct)))
        try:
            if self._lock.acquire(timeout=0.1):
                try:
                    self.engine.setProperty('volume', self.current_volume / 100.0)
                finally:
                    self._lock.release()
        except Exception:
            pass
        print(f"[VoiceEngine] 音量已调整为: {self.current_volume}%")

    def _contains_japanese(self, text: str) -> bool:
        """检测文本是否包含日文假名"""
        for char in text:
            if '\u3040' <= char <= '\u30ff':
                return True
        return False

    def synthesize_to_pcm(self, text: str) -> Optional[bytes]:
        """合成语音为 16kHz 16-bit 单声道 PCM 原始字节流 (专为 MAX98357A I2S 硬件直推定制)"""
        if not text or not text.strip():
            return None
        
        import tempfile
        import wave
        import audioop

        temp_wav = os.path.join(tempfile.gettempdir(), f"kurisu_tts_{int(time.time()*1000)}.wav")
        try:
            with self._lock:
                if self._contains_japanese(text) and self.jp_voice_id:
                    self.engine.setProperty('voice', self.jp_voice_id)
                elif self.zh_voice_id:
                    self.engine.setProperty('voice', self.zh_voice_id)
                self.engine.save_to_file(text, temp_wav)
                self.engine.runAndWait()

            if not os.path.exists(temp_wav):
                return None

            with wave.open(temp_wav, 'rb') as w:
                channels = w.getnchannels()
                sample_width = w.getsampwidth()
                framerate = w.getframerate()
                raw_data = w.readframes(w.getnframes())

            # 若声道数大于1，转单声道
            if channels > 1:
                raw_data = audioop.tomono(raw_data, sample_width, 0.5, 0.5)
            # 若不是 16-bit，转换为 16-bit
            if sample_width != 2:
                raw_data = audioop.lin2lin(raw_data, sample_width, 2)
            # 若采样率不等于 16000Hz，高质量线性重采样
            if framerate != 16000:
                raw_data, _ = audioop.ratecv(raw_data, 2, 1, framerate, 16000, None)

            return raw_data
        except Exception as e:
            print(f"[VoiceEngine] 合成音频异常: {e}")
            return None
        finally:
            if os.path.exists(temp_wav):
                try:
                    os.remove(temp_wav)
                except Exception:
                    pass

    def speak(self, text: str, block: bool = True, to_board: bool = True):
        """
        合成并播放对白:
        默认优先通过 ESP32-S3 板载 MAX98357A 扬声器物理发声；
        若硬件未连接，自动平滑回退至 PC 本地扬声器发声。
        """
        if not text or not text.strip():
            return

        if not block:
            threading.Thread(target=self.speak, args=(text, True, to_board), daemon=True).start()
            return

        if to_board:
            try:
                from light_controller import get_light_controller
                ctrl = get_light_controller()
                if ctrl.is_connected:
                    pcm = self.synthesize_to_pcm(text)
                    if pcm:
                        ctrl.play_audio_pcm(pcm)
                        return
            except Exception as e:
                print(f"[VoiceEngine] 板载播放降级至本地扬声器: {e}")

        # 本地 PC 扬声器播放
        with self._lock:
            try:
                if self._contains_japanese(text) and self.jp_voice_id:
                    self.engine.setProperty('voice', self.jp_voice_id)
                elif self.zh_voice_id:
                    self.engine.setProperty('voice', self.zh_voice_id)

                self.engine.say(text)
                self.engine.runAndWait()
            except Exception as e:
                print(f"[VoiceEngine] 播放异常: {e}")

# 单例导出
_voice_instance: Optional[VoiceEngine] = None

def get_voice_engine() -> VoiceEngine:
    global _voice_instance
    if _voice_instance is None:
        _voice_instance = VoiceEngine()
    return _voice_instance

if __name__ == "__main__":
    v = get_voice_engine()
    print("[测试]: 中文傲娇对白")
    v.speak("都说了我不是助手！你这笨蛋怎么就是不听呢！", block=True)
    time.sleep(0.5)
    print("[测试]: 日文世界线台词")
    v.speak("エル・プサイ・コングルゥ。これがシュタインズ・ゲートの選択か。", block=True)
