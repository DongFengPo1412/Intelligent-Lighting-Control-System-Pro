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
import hashlib
from pathlib import Path
from typing import Optional, Tuple

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

import numpy as np
import scipy.signal
try:
    import noisereduce as nr
    _HAS_NOISEREDUCE = True
except Exception:
    _HAS_NOISEREDUCE = False

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
        
        # 牧濑红莉栖官方纯净参考音频 (来自训练集无杂音切片 prompt_shy.wav, 4.35s, 文本完全对齐, 无底噪无杂音)
        self.ref_audio_path = os.path.join(self.model_dir, "prompt_shy.wav")
        self.prompt_text = "私が言ったのは親子で仲が良くて羨ましいな"
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
        """清洗文本中的特殊标签、微表情、系统记号、工具残渣、连续换行"""
        if not text:
            return ""
        t = re.sub(r'<tool_call>.*?</tool_call>', '', text, flags=re.DOTALL | re.I)
        t = re.sub(r'</?tool_call>', '', t, flags=re.I)
        t = re.sub(r'(?:zion|arton|xon)[,\s]*\{.*?(?:\}|$|\n)', '', t, flags=re.I)
        t = re.sub(r'(?:zion|arton|xon)[,\s]+[a-zA-Z0-9_]+(?:\s+\w+)?', '', t, flags=re.I)
        t = re.sub(r'[a-zA-Z_]+_mode\s+\d+', '', t, flags=re.I)
        t = re.sub(r'[a-zA-Z_]+\([^\)]*\)', '', t)
        t = re.sub(r'\{[^{}]*\}', '', t)
        t = re.sub(r'\b(?:arton|zion|xon)\b', '', t, flags=re.I)
        t = re.sub(r'\[.*?\]|\(.*?\)|\（.*?\）|\【.*?\】', '', t)
        t = t.replace('*', '').replace('`', '').replace('#', '')
        t = re.sub(r'\s+', ' ', t).strip()
        return t

    def _contains_japanese(self, text: str) -> bool:
        """检测文本是否包含日文假名"""
        for char in text:
            if '\u3040' <= char <= '\u30ff':
                return True
        return False

    def _translate_zh_to_ja_kurisu(self, zh_text: str) -> str:
        """
        基于本地端侧 Qwen2.5-7B 实施 100% 动态实时中日互译
        将输入的中文精准、完全一致地翻译为牧濑红莉栖原声傲娇语气的日文对白
        彻底杜绝任何固定死板的模板句子！
        """
        if not zh_text or not zh_text.strip():
            return ""

        # 清洗待翻译的中文，避免工具代码污染翻译
        clean_zh = self._clean_text_for_tts(zh_text)
        if not clean_zh:
            return ""

        try:
            import urllib.request
            import json
            payload = {
                "model": "qwen2.5:7b",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "你是《命运石之门》中的牧濑红莉栖(CV:今井麻美)。\n"
                            "你的任务：将用户提供的【中文台词】精准翻译为【完全对应含义的日语台词】。\n"
                            "翻译铁律：\n"
                            "1. 意思必须与中文分毫不差、完全一致。\n"
                            "2. 语气为牧濑红莉栖经典的傲娇少女、天才学者语调（口癖自然，如「ふん」「〜でしょ」「〜わよ」「アンタ」「バカ」）。\n"
                            "3. 纯正日文输出，严禁任何英文，严禁任何多余解释或前缀。"
                        )
                    },
                    {
                        "role": "user",
                        "content": clean_zh
                    }
                ],
                "stream": False,
                "temperature": 0.2
            }
            req = urllib.request.Request(
                "http://127.0.0.1:11434/api/chat",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(req, timeout=10.0) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                ja = res.get("message", {}).get("content", "").strip()
                ja = re.sub(r'^(日文翻译[：:]|翻译[：:]|日本語[：:]|牧濑红莉栖[：:]|紅莉栖[：:])', '', ja).strip()
                ja = ja.replace('`', '').replace('"', '').strip()
                if ja and re.search(r'[\u3040-\u30ff]', ja):
                    return ja
        except Exception as e:
            print(f"[VoiceEngine 动态中译日异常]: {e}")

        return ""

    def _split_zh_ja(self, text: str):
        """将混合文本拆分为中文段落与日文段落 (严格中日互译对齐)"""
        sentences = re.split(r'([。！？!\?\n]+)', text)
        full_sentences = []
        for i in range(0, len(sentences) - 1, 2):
            s = sentences[i].strip() + sentences[i + 1].strip()
            if s:
                full_sentences.append(s)
        if len(sentences) % 2 == 1 and sentences[-1].strip():
            full_sentences.append(sentences[-1].strip())

        zh_parts = []
        ja_parts = []
        for s in full_sentences:
            if re.search(r'[\u3040-\u30ff]', s):
                ja_parts.append(s)
            else:
                zh_parts.append(s)

        zh_text = " ".join(zh_parts).strip()
        ja_text = " ".join(ja_parts).strip()
        return zh_text, ja_text

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
            'top_k': 10,
            'top_p': 0.85,
            'temperature': 0.6,
            'text_split_method': 'cut5',
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

    def _postprocess_audio_32k(self, audio_32k: np.ndarray) -> np.ndarray:
        """
        录音棚级母带声学塑形与降噪滤波:
        1. 95Hz 二阶高通滤波: 消除低频嗡鸣、杂散交流声与 DC 偏移;
        2. noisereduce 神经静音降噪: 彻底消除 HiFi-GAN 声码器潜伏的底噪与沙沙声;
        3. 300Hz 陷波去浑浊 (De-mud, -3.5dB): 削减发闷发糊的谐波共振, 人声立刻通透;
        4. 3800Hz 临场高频激励 (+3.5dB): 增强今井麻美清澈透亮的傲娇少女原声;
        5. 14500Hz 低通滤波: 阻止超高频数字采样镜象;
        6. 动态电平安全归一化: 保留 -1.2dB (0.88) 净空, 杜绝 DAC 削波失真与爆音。
        """
        if audio_32k is None or len(audio_32k) == 0:
            return audio_32k
        try:
            sr = 32000.0
            y = audio_32k.astype(np.float32)

            # 1. 95Hz 二阶高通滤波
            b_hp, a_hp = scipy.signal.butter(2, 95.0 / (sr / 2.0), btype='high')
            y = scipy.signal.lfilter(b_hp, a_hp, y)

            # 2. noisereduce 神经平稳降噪
            if _HAS_NOISEREDUCE:
                try:
                    y = nr.reduce_noise(y=y, sr=32000, prop_decrease=0.75, stationary=True)
                except Exception as ne:
                    print(f"[VoiceEngine 降噪提示]: {ne}")

            # 3. 300Hz 陷波去浑浊 (De-mud: f0=300Hz, Q=1.0, gain=-3.5dB)
            w0 = 2 * np.pi * 300.0 / sr
            alpha0 = np.sin(w0) / (2 * 1.0)
            A0 = 10.0 ** (-3.5 / 40.0)
            b_demud = [(1 + alpha0 * A0), (-2 * np.cos(w0)), (1 - alpha0 * A0)]
            a_demud = [(1 + alpha0 / A0), (-2 * np.cos(w0)), (1 - alpha0 / A0)]
            b_demud = [c / a_demud[0] for c in b_demud]
            a_demud = [c / a_demud[0] for c in a_demud]
            y = scipy.signal.lfilter(b_demud, a_demud, y)

            # 4. 3800Hz 临场透亮激励 (Presence Boost: f1=3800Hz, Q=1.2, gain=+3.5dB)
            w1 = 2 * np.pi * 3800.0 / sr
            alpha1 = np.sin(w1) / (2 * 1.2)
            A1 = 10.0 ** (3.5 / 40.0)
            b_pres = [(1 + alpha1 * A1), (-2 * np.cos(w1)), (1 - alpha1 * A1)]
            a_pres = [(1 + alpha1 / A1), (-2 * np.cos(w1)), (1 - alpha1 / A1)]
            b_pres = [c / a_pres[0] for c in b_pres]
            a_pres = [c / a_pres[0] for c in a_pres]
            y = scipy.signal.lfilter(b_pres, a_pres, y)

            # 5. 14500Hz 二阶低通滤波
            b_lp, a_lp = scipy.signal.butter(2, 14500.0 / (sr / 2.0), btype='low')
            y = scipy.signal.lfilter(b_lp, a_lp, y)

            # 6. 动态电平安全归一化与音量增益映射
            peak = float(np.max(np.abs(y)))
            if peak > 1e-4:
                target_scale = (self.current_volume / 100.0) * 0.88
                y = (y / peak) * 32767.0 * target_scale
            return np.clip(y, -32768, 32767).astype(np.int16)
        except Exception as e:
            print(f"[VoiceEngine 滤波异常]: {e}")
            return np.clip(audio_32k, -32768, 32767).astype(np.int16)

    def synthesize_speech_bundle(self, text: str) -> Optional[Tuple[bytes, bytes]]:
        """
        合成红莉栖全方位声线:
        返回: (pcm_16k, wav_32k_bytes)
        严格确保: 【先中文高保真回答】 + 【180ms 呼吸微停顿】 + 【后牧濑红莉栖正统日文互译 (完全一致的对应含义)】
        严守铁律: 绝不使用任何微软语音包; 若未生成红莉栖人声则返回 None (静默)
        """
        if not text or not text.strip() or not self.tts:
            return None

        cleaned = self._clean_text_for_tts(text)
        if not cleaned:
            return None

        cache_dir = Path(__file__).resolve().parent / '.voice_cache'
        cache_key = hashlib.sha256(f'original-v1:{self.current_volume}:{cleaned}'.encode('utf-8')).hexdigest()
        cache_file = cache_dir / (cache_key + '.wav')
        with self._lock:
            try:
                if cache_file.exists():
                    wav_bytes = cache_file.read_bytes()
                    with wave.open(io.BytesIO(wav_bytes), 'rb') as w:
                        samples = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
                    pcm = scipy.signal.resample_poly(samples.astype(np.float32), 1, 2)
                    return np.clip(pcm, -32768, 32767).astype(np.int16).tobytes(), wav_bytes
                # 严格分离中文与日文
                zh_text, ja_text = self._split_zh_ja(cleaned)
                
                # 如果没有日文部分，自动根据中文内容生成严格对应的牧濑红莉栖日文互译
                if not ja_text:
                    ja_text = self._translate_zh_to_ja_kurisu(zh_text or cleaned)
                
                audio_zh = None
                audio_ja = None
                
                # 1. 牧濑红莉栖声线：先中文合成 (使用 cut5 标点分句，无论长短句均稳定生成)
                if zh_text:
                    audio_zh = self._synthesize_raw(zh_text, "zh")
                
                # 2. 牧濑红莉栖声线：后日文合成 (精准对应互译)
                if ja_text:
                    audio_ja = self._synthesize_raw(ja_text, "ja")
                
                # 3. 缝合输出：先中文 + 180ms呼吸停顿 + 后日文
                if audio_zh is not None and audio_ja is not None:
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

                # 声学后处理 (录音棚级母带降噪与清晰度 EQ 塑形)
                processed_32k = self._postprocess_audio_32k(audio_res)


                # 生成 PC 专用的 32000Hz 高保真 WAV
                wav_io = io.BytesIO()
                with wave.open(wav_io, 'wb') as w:
                    w.setnchannels(1)
                    w.setsampwidth(2)
                    w.setframerate(32000)
                    w.writeframes(processed_32k.tobytes())
                wav_32k_bytes = wav_io.getvalue()
                cache_dir.mkdir(exist_ok=True)
                cache_file.write_bytes(wav_32k_bytes)
                cached = sorted(cache_dir.glob('*.wav'), key=lambda path: path.stat().st_mtime)
                for old_file in cached[:-64]:
                    old_file.unlink()

                # 生成 ESP32 板载专用的 16000Hz PCM 流
                resampled_16k = scipy.signal.resample_poly(processed_32k.astype(np.float32), 1, 2)
                pcm_16k = np.clip(resampled_16k, -32768, 32767).astype(np.int16).tobytes()

                return pcm_16k, wav_32k_bytes

            except Exception as e:
                print(f"[VoiceEngine 异常] 牧濑红莉栖语音合成中断: {e}，遵循静音准则，不播放任何杂音。")
                return None

    def synthesize_to_pcm(self, text: str) -> Optional[bytes]:
        """向后兼容接口：仅提取 16kHz PCM 用于硬件"""
        bundle = self.synthesize_speech_bundle(text)
        return bundle[0] if bundle else None

    def speak(self, text: str, block: bool = True, to_board: bool = True):
        """
        合成并播放对白:
        优先通过 ESP32-S3 板载 MAX98357A 扬声器物理发声；
        未使用板载输出时在 PC 扬声器播放。
        严守铁律: 要么听到红莉栖清晰人声，要么完全静音！
        """
        if not text or not text.strip():
            return

        if not block:
            threading.Thread(target=self.speak, args=(text, True, to_board), daemon=True).start()
            return

        bundle = self.synthesize_speech_bundle(text)
        if not bundle:
            return

        pcm_16k, wav_32k_bytes = bundle

        from light_controller import get_light_controller
        ctrl = get_light_controller()
        if ctrl.is_connected:
            ctrl.set_board_led("speaking")

        if to_board and ctrl.is_connected:
            # One physical output avoids delayed PC/board copies sounding like echo.
            if not ctrl.play_audio_pcm(pcm_16k):
                print('[VoiceEngine] 板载语音播放失败')
            return
        try:
            import winsound
            winsound.PlaySound(wav_32k_bytes, winsound.SND_MEMORY)
        except Exception as e:
            print(f"[VoiceEngine] 本地电脑扬声器播放异常: {e}")


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
