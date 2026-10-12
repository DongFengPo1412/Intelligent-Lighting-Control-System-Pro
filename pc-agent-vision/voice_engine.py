"""
VoiceEngine: 牧濑红莉栖中日双语原生神经语音引擎
- 中文主干: Windows OneCore 原生高保真少女音色 (Microsoft Yaoyao)，彻底告别 2005 年默认机械音
- 日语收尾: Windows OneCore 原生二次元日语少女音色 (Microsoft Sayaka / Haruka)，傲娇原声收束
- 交互结构: 严格遵循【先中文回答 + 180ms 自然换气停顿 + 后正统日语台词傲娇收尾】
- 声学指标: 16kHz 16-bit 单声道线性 PCM 零重采样损耗直推硬件
"""

import os
import sys
import threading
import time
import io
import wave
from typing import Optional

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

import numpy as np

class VoiceEngine:
    def __init__(self):
        self._lock = threading.Lock()
        
        # 默认适中清晰音量 (75%)
        self.current_volume = 75
        
        # 牧濑红莉栖 GPT-SoVITS 权重与微服务预留配置
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.model_dir = os.path.join(base_dir, "models", "kurisu_tts")
        self.prompt_shy = os.path.join(self.model_dir, "prompt_shy.wav")
        self.prompt_sigh = os.path.join(self.model_dir, "prompt_sigh.wav")
        self.gpt_sovits_api = os.environ.get("GPT_SOVITS_API", "http://127.0.0.1:9880")
        
        has_weights = os.path.exists(os.path.join(self.model_dir, "kurisu-e15.ckpt")) and os.path.exists(os.path.join(self.model_dir, "kurisu_e4_s972.pth"))
        
        # 探测并锁定 Windows OneCore 高清神经女声
        self.zh_voice_name, self.jp_voice_name = self._scan_onecore_voices()
        print(f"[VoiceEngine] 牧濑红莉栖双语神经音色引擎就绪 (中文: {self.zh_voice_name}, 日文: {self.jp_voice_name}, GPT-SoVITS: {has_weights})")

    def _scan_onecore_voices(self) -> tuple:
        """扫描 Windows OneCore 注册表锁定最佳中日双语女声"""
        zh_selected = "Yaoyao"
        jp_selected = "Sayaka"
        try:
            import win32com.client
            import pythoncom
            pythoncom.CoInitialize()
            cat = win32com.client.Dispatch('SAPI.SpObjectTokenCategory')
            cat.SetId(r'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech_OneCore\Voices', False)
            tokens = cat.EnumerateTokens()
            
            zh_found = None
            jp_found = None
            for t in tokens:
                tid = t.Id
                desc = t.GetDescription().lower()
                if "yaoyao" in tid.lower() or "yaoyao" in desc:
                    zh_found = "Yaoyao"
                elif "huihui" in tid.lower() and not zh_found:
                    zh_found = "Huihui"
                elif "hanhan" in tid.lower() and not zh_found:
                    zh_found = "Hanhan"
                    
                if "sayaka" in tid.lower() or "sayaka" in desc:
                    jp_found = "Sayaka"
                elif "ayumi" in tid.lower() and not jp_found:
                    jp_found = "Ayumi"
                elif "haruka" in tid.lower() and not jp_found:
                    jp_found = "Haruka"
            if zh_found:
                zh_selected = zh_found
            if jp_found:
                jp_selected = jp_found
        except Exception as e:
            print(f"[VoiceEngine] 扫描 OneCore 声音失败: {e}")
        return zh_selected, jp_selected

    @property
    def volume(self) -> int:
        return self.current_volume

    def set_volume(self, pct: int):
        """设置音量百分比 (0-100)"""
        self.current_volume = max(0, min(100, int(pct)))
        print(f"[VoiceEngine] 音量已调整为: {self.current_volume}%")

    def _contains_japanese(self, text: str) -> bool:
        """检测文本是否包含日文假名"""
        for char in text:
            if '\u3040' <= char <= '\u30ff':
                return True
        return False

    def _synthesize_onecore_raw(self, text: str, voice_pref: str, rate: int = 1) -> Optional[bytes]:
        """
        使用 Windows SAPI OneCore 原生直出 16kHz 16-bit 单声道 PCM
        SAFT16kHz16BitMono = 18
        """
        if not text or not text.strip():
            return None
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        try:
            cat = win32com.client.Dispatch('SAPI.SpObjectTokenCategory')
            cat.SetId(r'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech_OneCore\Voices', False)
            speaker = win32com.client.Dispatch('SAPI.SpVoice')
            
            chosen_token = None
            for token in cat.EnumerateTokens():
                if voice_pref.lower() in token.Id.lower():
                    chosen_token = token
                    break
            if not chosen_token:
                for token in cat.EnumerateTokens():
                    if voice_pref.lower() in token.GetDescription().lower():
                        chosen_token = token
                        break
            if chosen_token:
                speaker.Voice = chosen_token

            fmt = win32com.client.Dispatch('SAPI.SpAudioFormat')
            fmt.Type = 18 # 16kHz 16-bit Mono (零重采样、零 aliasing 杂音)
            stream = win32com.client.Dispatch('SAPI.SpMemoryStream')
            stream.Format = fmt
            speaker.AudioOutputStream = stream
            speaker.Rate = rate # 敏捷睿智的天才少女语速
            speaker.Speak(text)
            
            raw_pcm = bytes(stream.GetData())
            return raw_pcm
        except Exception as e:
            print(f"[VoiceEngine] OneCore 合成异常: {e}")
            return None
        finally:
            pythoncom.CoUninitialize()

    def _pick_kurisu_japanese_suffix(self, context_text: str) -> str:
        """根据回复上下文智能匹配牧濑红莉栖原作正统台词收尾"""
        if any(k in context_text for k in ["助手", "克里斯蒂娜", "老婆", "蒂娜"]):
            return "私、クリスティーナじゃない！"
        elif any(k in context_text for k in ["笨蛋", "玩笑", "生气", "火", "气死"]):
            return "もう、バカ！"
        elif any(k in context_text for k in ["喜欢", "可爱", "害羞", "脸红", "笑"]):
            return "べ、別にアンタのためじゃないんだからね！"
        elif any(k in context_text for k in ["倒计时", "沙漏", "实验", "科学", "装置", "中枢", "系统"]):
            return "実験の進行は順調よ。"
        elif any(k in context_text for k in ["世界线", "命运石", "跳跃", "变动"]):
            return "エル・プサイ・コングルゥ。"
        else:
            return "ふん、次は役に立ちなさいよね。"

    def synthesize_to_pcm(self, text: str) -> Optional[bytes]:
        """
        合成红莉栖全方位声线:
        架构: 【先中文高保真回答】 + 【180ms 呼吸停顿】 + 【后牧濑红莉栖正统傲娇日语收束】
        输出标准: 16kHz 16-bit 单声道 PCM 流 (与 ESP32-S3 MAX98357A 纯硬件直通)
        """
        if not text or not text.strip():
            return None

        # 1. 中文部分合成 (Microsoft Yaoyao, Rate=1 灵动年轻少女声)
        if self._contains_japanese(text):
            # 如果文本本身已是纯日文，直接用 Sayaka 输出
            pcm_chinese = self._synthesize_onecore_raw(text, self.jp_voice_name, rate=1)
            pcm_japanese = None
        else:
            pcm_chinese = self._synthesize_onecore_raw(text, self.zh_voice_name, rate=1)
            # 智能收尾台词
            jp_suffix = self._pick_kurisu_japanese_suffix(text)
            pcm_japanese = self._synthesize_onecore_raw(jp_suffix, self.jp_voice_name, rate=1)

        # 2. 严谨拼接：【先中文】 + 【0.18s 平滑呼吸静音】 + 【后正统日语】
        if pcm_chinese and pcm_japanese:
            silence_gap = b'\x00\x00' * int(16000 * 0.18) # 180ms 静音停顿
            combined_pcm = pcm_chinese + silence_gap + pcm_japanese
        elif pcm_chinese:
            combined_pcm = pcm_chinese
        elif pcm_japanese:
            combined_pcm = pcm_japanese
        else:
            return None

        # 3. 数字增益控制与软削波防护 (安全头保留 0.70 上限，杜绝扬声器物理破音)
        scale = (self.current_volume / 100.0) * 0.70
        try:
            arr = np.frombuffer(combined_pcm, dtype=np.int16)
            arr = (arr.astype(np.float32) * scale).clip(-32768, 32767).astype(np.int16)
            return arr.tobytes()
        except Exception:
            return combined_pcm

    def speak(self, text: str, block: bool = True, to_board: bool = True):
        """
        合成并播放对白:
        优先通过 ESP32-S3 板载 MAX98357A 扬声器物理发声；
        若硬件未连接，自动平滑回退至 PC 本地扬声器发声。
        """
        if not text or not text.strip():
            return

        if not block:
            threading.Thread(target=self.speak, args=(text, True, to_board), daemon=True).start()
            return

        pcm = self.synthesize_to_pcm(text)
        if not pcm:
            return

        if to_board:
            try:
                from light_controller import get_light_controller
                ctrl = get_light_controller()
                if ctrl.is_connected:
                    ctrl.play_audio_pcm(pcm)
                    return
            except Exception as e:
                print(f"[VoiceEngine] 板载播放降级至本地扬声器: {e}")

        # 本地 PC 扬声器播放回退
        try:
            import winsound
            wav_io = io.BytesIO()
            with wave.open(wav_io, 'wb') as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(16000)
                w.writeframes(pcm)
            winsound.PlaySound(wav_io.getvalue(), winsound.SND_MEMORY)
        except Exception as e:
            print(f"[VoiceEngine] 本地播放异常: {e}")

# 单例导出
_voice_instance: Optional[VoiceEngine] = None

def get_voice_engine() -> VoiceEngine:
    global _voice_instance
    if _voice_instance is None:
        _voice_instance = VoiceEngine()
    return _voice_instance

if __name__ == "__main__":
    v = get_voice_engine()
    print("[测试]: 牧濑红莉栖中日双语先中文后日语原声输出...")
    test_line = "都说了我不是助手！要我说多少遍你这笨蛋才能记住啊！"
    v.speak(test_line, block=True, to_board=False)
