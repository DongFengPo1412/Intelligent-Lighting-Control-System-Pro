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

        # 默认适中清晰音量 (75%)
        self.current_volume = 75
        
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

            # 缩放至当前音量，并避免 MAX98357A 硬件输出级削波破音失真 (默认 0.65 增益上限，音质更纯净)
            gain = (self.current_volume / 100.0) * 0.65
            if gain < 0.98 or gain > 1.02:
                frames = audioop.mul(frames, 2, gain)
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

    def _pitch_shift_to_kurisu(self, pcm_data: bytes, sample_rate: int = 16000, n_steps: float = 3.5) -> bytes:
        """使用 PyTorch CUDA/CPU 将声音基频提升 (+3.5 半音)，将沉闷播音音色变换为红莉栖 18 岁傲娇声线"""
        if not pcm_data or len(pcm_data) < 320:
            return pcm_data
        try:
            import torch
            import torchaudio
            samples = torch.frombuffer(bytearray(pcm_data), dtype=torch.int16).to(torch.float32) / 32768.0
            samples = samples.unsqueeze(0)
            device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            samples = samples.to(device)
            shifted = torchaudio.functional.pitch_shift(samples, sample_rate, n_steps=n_steps)
            shifted = shifted.squeeze(0).clamp(-1.0, 1.0) * 32767.0
            return shifted.to(torch.int16).cpu().numpy().tobytes()
        except Exception:
            return pcm_data

    def synthesize_to_pcm(self, text: str) -> Optional[bytes]:
        """
        合成红莉栖全方位声线 (先中文回答，后以红莉栖今井麻美原作正统日语对白傲娇收尾)
        输出标准: 16kHz 16-bit 单声道 PCM 流
        """
        if not text or not text.strip():
            return None

        # 1. 优先尝试本地 GPT-SoVITS 原声推理微服务
        gsv_pcm = self._synthesize_gpt_sovits(text)
        if gsv_pcm:
            print(f"[VoiceEngine] 成功使用 GPT-SoVITS 今井麻美真原声合成对白！")
            return gsv_pcm

        # 2. 匹配今井麻美原作正统日语收尾素材 (智能情绪收束)
        soundbank_dir = os.path.join(self.model_dir, "soundbank")
        authentic_suffix = None
        if any(k in text for k in ["助手", "克里斯蒂娜", "老婆"]):
            authentic_suffix = self._wav_file_to_pcm16k(os.path.join(soundbank_dir, "not_christina.wav"))
        elif any(k in text for k in ["笨蛋", "玩笑", "气死", "无聊"]):
            authentic_suffix = self._wav_file_to_pcm16k(os.path.join(soundbank_dir, "baka.wav"))
        elif any(k in text for k in ["害羞", "喜欢", "笑", "可爱"]):
            authentic_suffix = self._wav_file_to_pcm16k(self.prompt_shy)
        elif any(k in text for k in ["实验", "时间跳跃", "科学", "装置", "世界线", "汇报"]):
            authentic_suffix = self._wav_file_to_pcm16k(os.path.join(soundbank_dir, "lab_experiment.wav"))
        else:
            # 默认常驻红莉栖招牌傲娇叹息 / 轻哼
            authentic_suffix = self._wav_file_to_pcm16k(os.path.join(soundbank_dir, "tsundere_humph.wav"))

        # 若未成功加载专用库，回退至全局原声
        if not authentic_suffix:
            authentic_suffix = self._wav_file_to_pcm16k(self.prompt_sigh)

        # 3. 本地中文主干语音合成 + 红莉栖专属声线算法变换
        import tempfile
        temp_wav = os.path.join(tempfile.gettempdir(), f"kurisu_tts_{int(time.time()*1000)}.wav")
        try:
            with self._lock:
                if self._contains_japanese(text) and self.jp_voice_id:
                    self.engine.setProperty('voice', self.jp_voice_id)
                elif self.zh_voice_id:
                    self.engine.setProperty('voice', self.zh_voice_id)
                # 调优语速至 180wpm，体现红莉栖敏捷清晰的思维语调
                self.engine.setProperty('rate', 180)
                self.engine.save_to_file(text, temp_wav)
                self.engine.runAndWait()

            if not os.path.exists(temp_wav):
                return authentic_suffix

            pcm_chinese = self._wav_file_to_pcm16k(temp_wav)
            if pcm_chinese:
                # 提升基频，塑形为傲娇少女天才科学家的标志性声线
                pcm_chinese = self._pitch_shift_to_kurisu(pcm_chinese, 16000, n_steps=3.5)

            # 4. 严谨拼接：【先中文】 + 【0.18s 平滑呼吸停顿】 + 【后今井麻美原作正统日语收尾】
            if pcm_chinese and authentic_suffix:
                silence_gap = b'\x00\x00' * int(16000 * 0.18) # 180ms 无杂音换气停顿
                return pcm_chinese + silence_gap + authentic_suffix
            return pcm_chinese or authentic_suffix
        except Exception as e:
            print(f"[VoiceEngine] 合成音频异常: {e}")
            return authentic_suffix
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
