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
        
        # 牧濑红莉栖 GPT-SoVITS 模型与原声音频路径
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.model_dir = os.path.join(base_dir, "models", "kurisu_tts")
        self.prompt_shy = os.path.join(self.model_dir, "prompt_shy.wav")
        self.prompt_sigh = os.path.join(self.model_dir, "prompt_sigh.wav")
        self.gpt_sovits_api = os.environ.get("GPT_SOVITS_API", "http://127.0.0.1:9880")
        
        has_weights = os.path.exists(os.path.join(self.model_dir, "kurisu-e15.ckpt")) and os.path.exists(os.path.join(self.model_dir, "kurisu_e4_s972.pth"))
        print(f"[VoiceEngine] 牧濑红莉栖专属音色引擎就绪 (GPT-SoVITS 权重就绪: {has_weights})")

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

    def _wav_file_to_pcm16k(self, file_path: str) -> Optional[bytes]:
        """将任意 WAV 文件转换为 16kHz 16-bit 单声道 PCM 硬件字节流"""
        if not os.path.exists(file_path):
            return None
        import wave
        import audioop
        try:
            with wave.open(file_path, 'rb') as w:
                ch = w.getnchannels()
                sw = w.getsampwidth()
                fr = w.getframerate()
                frames = w.readframes(w.getnframes())
            if ch > 1:
                frames = audioop.tomono(frames, sw, 0.5, 0.5)
            if sw != 2:
                frames = audioop.lin2lin(frames, sw, 2)
            if fr != 16000:
                frames, _ = audioop.ratecv(frames, 2, 1, fr, 16000, None)
            return frames
        except Exception as e:
            print(f"[VoiceEngine] 音频转换异常: {e}")
            return None

    def _synthesize_gpt_sovits(self, text: str) -> Optional[bytes]:
        """尝试调用本地 GPT-SoVITS 牧濑红莉栖专属微服务 (今井麻美 100% 神经原声)"""
        try:
            import urllib.request
            import json
            import tempfile
            
            payload = json.dumps({
                "text": text,
                "text_lang": "zh" if not self._contains_japanese(text) else "ja",
                "ref_audio_path": self.prompt_shy,
                "prompt_text": "害羞",
                "prompt_lang": "zh"
            }).encode("utf-8")
            
            req = urllib.request.Request(
                f"{self.gpt_sovits_api}/tts",
                data=payload,
                headers={"Content-Type": "application/json"}
            )
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(req, timeout=2.5) as resp:
                if resp.status == 200:
                    wav_data = resp.read()
                    temp_f = os.path.join(tempfile.gettempdir(), f"gsv_{int(time.time()*1000)}.wav")
                    with open(temp_f, "wb") as f:
                        f.write(wav_data)
                    pcm = self._wav_file_to_pcm16k(temp_f)
                    try:
                        os.remove(temp_f)
                    except Exception:
                        pass
                    return pcm
        except Exception:
            return None

    def synthesize_to_pcm(self, text: str) -> Optional[bytes]:
        """合成语音为 16kHz 16-bit 单声道 PCM 原始字节流 (专为 MAX98357A I2S 硬件直推定制)"""
        if not text or not text.strip():
            return None

        # 1. 优先尝试本地 GPT-SoVITS 原声推理微服务
        gsv_pcm = self._synthesize_gpt_sovits(text)
        if gsv_pcm:
            print(f"[VoiceEngine] 成功使用 GPT-SoVITS 今井麻美真原声合成对白！")
            return gsv_pcm

        # 2. 原声前置特征融合：若触发傲娇/助手词，前置注入今井麻美原作叹息/傲娇语气原声样本
        authentic_prefix = None
        if any(k in text for k in ["助手", "克里斯蒂娜", "笨蛋", "气死"]):
            authentic_prefix = self._wav_file_to_pcm16k(self.prompt_sigh)
        elif any(k in text for k in ["害羞", "笑", "喜欢", "命运石之门"]):
            authentic_prefix = self._wav_file_to_pcm16k(self.prompt_shy)

        # 3. 回退为本地零延迟神经声学引擎 (Windows SAPI5)
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
                return authentic_prefix

            pcm = self._wav_file_to_pcm16k(temp_wav)
            if authentic_prefix and pcm:
                return authentic_prefix + pcm
            return pcm or authentic_prefix
        except Exception as e:
            print(f"[VoiceEngine] 合成音频异常: {e}")
            return authentic_prefix
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
