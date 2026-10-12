"""
VoiceEngine: 牧濑红莉栖 (Makise Kurisu, CV: 今井麻美) 纯正开源神经声学语音引擎
- 核心模型: 基于开源 GPT-SoVITS (v2Pro) 架构 + 牧濑红莉栖中日双语大模型权重 (kurisu-e15.ckpt + kurisu_e4_s972.pth)
- 语言处理: 中文先发，配合 180ms 自然换气微停顿，再以牧濑红莉栖原作正统傲娇日文台词收束
- 铁律约束: 坚决禁用任何 Microsoft (SAPI/OneCore/系统机械音) 语音包；要么输出清晰纯正红莉栖原声，要么保持静默 (Fail-Silent)
- 硬件直通: 16kHz 16-bit 单声道线性 PCM 零重采样损耗直推 ESP32-S3 MAX98357A I2S 硬件
"""

import os
import sys
import threading
import time
import io
import wave
import re
from typing import Optional

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

import numpy as np
import scipy.signal

# 引入 GPT-SoVITS 环境
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
gpt_sovits_dir = os.path.join(repo_root, "models", "GPT-SoVITS")
sys.path.insert(0, gpt_sovits_dir)
sys.path.insert(0, os.path.join(gpt_sovits_dir, "GPT_SoVITS"))

try:
    from TTS_infer_pack.TTS import TTS_Config, TTS
    _HAS_GPT_SOVITS = True
except Exception as e:
    print(f"[VoiceEngine 致命警报] 无法导入 GPT-SoVITS 依赖: {e}")
    _HAS_GPT_SOVITS = False


class VoiceEngine:
    def __init__(self):
        self._lock = threading.Lock()
        
        # 音量控制 (默认 75% 适度清脆)
        self.current_volume = 75
        
        # 模型与提示音频路径
        self.model_dir = os.path.join(repo_root, "models", "kurisu_tts")
        self.t2s_weights = os.path.join(self.model_dir, "kurisu-e15.ckpt")
        self.vits_weights = os.path.join(self.model_dir, "kurisu_e4_s972.pth")
        self.bert_base_path = os.path.join(repo_root, "models", "pretrained_models", "chinese-roberta-wwm-ext-large")
        self.cnhuhbert_base_path = os.path.join(repo_root, "models", "pretrained_models", "chinese-hubert-base")
        
        # 牧濑红莉栖正统参考音频 (来自原作录音，今井麻美傲娇原声)
        self.ref_audio_path = os.path.join(self.model_dir, "soundbank", "not_christina.wav")
        self.prompt_text = "私、クリスティーナじゃない！"
        self.prompt_lang = "ja"
        
        self.tts: Optional[TTS] = None
        self._init_kurisu_model()

    def _init_kurisu_model(self):
        """初始化牧濑红莉栖纯正 GPT-SoVITS 神经网络"""
        if not _HAS_GPT_SOVITS:
            print("[VoiceEngine] GPT-SoVITS 未加载，遵从用户铁律：绝不使用任何微软语音包，静音备用。")
            return
        
        if not os.path.exists(self.t2s_weights) or not os.path.exists(self.vits_weights):
            print(f"[VoiceEngine] 牧濑红莉栖模型权重不存在 ({self.t2s_weights})，静音就绪。")
            return
        
        try:
            print("[VoiceEngine] 正在载入牧濑红莉栖 (CV: 今井麻美) 专属中日双语大模型...")
            t0 = time.time()
            custom_config = {
                'custom': {
                    'device': 'cuda',
                    'is_half': False,
                    'version': 'v2Pro',
                    't2s_weights_path': self.t2s_weights,
                    'vits_weights_path': self.vits_weights,
                    'bert_base_path': self.bert_base_path,
                    'cnhuhbert_base_path': self.cnhuhbert_base_path,
                }
            }
            cfg = TTS_Config(custom_config)
            self.tts = TTS(cfg)
            print(f"[VoiceEngine] 牧濑红莉栖专属神经声学模型已就绪 (耗时: {time.time()-t0:.2f}s, GPU RTX 加速)")
        except Exception as e:
            print(f"[VoiceEngine 异常] 加载牧濑红莉栖模型失败: {e}。根据用户要求，绝不使用微软备选语音，保持静音。")
            self.tts = None

    @property
    def volume(self) -> int:
        return self.current_volume

    def set_volume(self, pct: int):
        """设置音量百分比 (0-100)"""
        self.current_volume = max(0, min(100, int(pct)))
        print(f"[VoiceEngine] 音量已调整为: {self.current_volume}%")

    def _clean_text_for_tts(self, text: str) -> str:
        """清洗文本中的特殊标签、微表情、系统记号、连续换行"""
        if not text:
            return ""
        # 移除大模型可能产生的系统标记 [smile], (微笑), 【动作】
        t = re.sub(r'\[.*?\]|\(.*?\)|\（.*?\）|\【.*?\】', '', text)
        # 移除 markdown 粗体/斜体
        t = t.replace('*', '').replace('`', '').replace('#', '')
        # 连续换行和多余空格清洗
        t = re.sub(r'\s+', ' ', t).strip()
        return t

    def _contains_japanese(self, text: str) -> bool:
        """检测文本是否包含日文假名"""
        for char in text:
            if '\u3040' <= char <= '\u30ff':
                return True
        return False

    def _pick_kurisu_japanese_suffix(self, context_text: str) -> str:
        """根据回复上下文智能匹配牧濑红莉栖原作正统台词收尾"""
        if any(k in context_text for k in ["助手", "克里斯蒂娜", "老婆", "蒂娜"]):
            return "私、クリスティーナじゃない！"
        elif any(k in context_text for k in ["笨蛋", "玩笑", "生气", "火", "气死"]):
            return "もう、バカ！"
        elif any(k in context_text for k in ["喜欢", "可爱", "害羞", "脸红", "笑"]):
            return "べ、別にアンタのためじゃないんだからね！"
        elif any(k in context_text for k in ["倒计时", "沙漏", "实验", "科学", "装置", "中枢", "系统"]):
            return "実験の進行は順调よ。"
        elif any(k in context_text for k in ["世界线", "命运石", "跳跃", "变动"]):
            return "エル・プサイ・コングルゥ。"
        else:
            return "ふん、次は役に立ちなさいよね。"

    def _synthesize_raw(self, text: str, lang: str) -> Optional[np.ndarray]:
        """调用 GPT-SoVITS 单独合成一段文本 (32kHz numpy float32)"""
        if not self.tts or not text or not text.strip():
            return None
        
        req = {
            'text': text,
            'text_lang': lang,
            'ref_audio_path': self.ref_audio_path,
            'prompt_text': self.prompt_text,
            'prompt_lang': self.prompt_lang,
            'streaming_mode': False,
            'use_cuda_graph': False,
            'parallel_infer': False,
            'top_k': 15,
            'top_p': 1.0,
            'temperature': 1.0,
        }
        chunks = []
        try:
            for res_sr, data in self.tts.run(req):
                if data is not None and len(data) > 0:
                    chunks.append(data)
            if not chunks:
                return None
            return np.concatenate(chunks)
        except Exception as e:
            print(f"[VoiceEngine 异常] GPT-SoVITS 合成异常 ({text[:15]}...): {e}")
            return None

    def synthesize_to_pcm(self, text: str) -> Optional[bytes]:
        """
        合成红莉栖全方位声线:
        架构: 【先中文高保真回答】 + 【180ms 呼吸微停顿】 + 【后牧濑红莉栖正统傲娇日语收束】
        输出标准: 16kHz 16-bit 单声道 PCM 流 (与 ESP32-S3 MAX98357A 纯硬件直通)
        严守铁律: 绝不使用任何微软语音包；若未生成红莉栖人声则返回 None (静默)
        """
        if not text or not text.strip() or not self.tts:
            return None

        cleaned = self._clean_text_for_tts(text)
        if not cleaned:
            return None

        with self._lock:
            try:
                # 判断语言逻辑
                if self._contains_japanese(cleaned):
                    # 如果文本本身已有日文，直接以日文单次合成完整输出
                    audio_res = self._synthesize_raw(cleaned, "ja")
                else:
                    # 先中文回答
                    audio_zh = self._synthesize_raw(cleaned, "zh")
                    # 后配正统傲娇日文台词收束
                    jp_suffix = self._pick_kurisu_japanese_suffix(cleaned)
                    audio_ja = self._synthesize_raw(jp_suffix, "ja")
                    
                    if audio_zh is not None and audio_ja is not None:
                        # 插入 180ms 平滑呼吸换气静音
                        silence = np.zeros(int(32000 * 0.18), dtype=audio_zh.dtype)
                        audio_res = np.concatenate([audio_zh, silence, audio_ja])
                    elif audio_zh is not None:
                        audio_res = audio_zh
                    elif audio_ja is not None:
                        audio_res = audio_ja
                    else:
                        audio_res = None

                if audio_res is None or len(audio_res) == 0:
                    return None

                # 降采样从 32000Hz 到 16000Hz (多相滤波无损抗混叠降采样)
                resampled_16k = scipy.signal.resample_poly(audio_res.astype(np.float32), 1, 2)

                # 音量控制与削波防护 (安全头保留 0.85 上限)
                scale = (self.current_volume / 100.0) * 0.85
                resampled_16k = np.clip(resampled_16k * scale, -32768, 32767).astype(np.int16)
                
                return resampled_16k.tobytes()

            except Exception as e:
                print(f"[VoiceEngine 异常] 牧濑红莉栖语音合成中断: {e}，遵循静音准则，不播放任何杂音。")
                return None

    def speak(self, text: str, block: bool = True, to_board: bool = True):
        """
        合成并播放对白:
        优先通过 ESP32-S3 板载 MAX98357A 扬声器物理发声；
        若硬件未连接，自动回退至 PC 本地扬声器发声。
        严守铁律: 要么听到红莉栖清晰人声，要么完全静音！
        """
        if not text or not text.strip():
            return

        if not block:
            threading.Thread(target=self.speak, args=(text, True, to_board), daemon=True).start()
            return

        pcm = self.synthesize_to_pcm(text)
        if not pcm:
            # 静默原则：未合成出红莉栖人声则绝对不播放任何替代语音
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

        # 本地 PC 扬声器播放
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
    print("[测试]: 牧濑红莉栖中日双语原声输出...")
    test_line = "都说了我不是助手！要我说多少遍你这笨蛋才能记住啊！"
    v.speak(test_line, block=True, to_board=False)
