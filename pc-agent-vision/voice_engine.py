"""
VoiceEngine: 牧濑红莉栖 (Makise Kurisu, CV: 今井麻美) 开源神经声学语音引擎
- 核心模型: 基于开源 GPT-SoVITS (v2Pro) 架构 + 牧濑红莉栖中日双语权重 (kurisu-e15.ckpt + kurisu_e4_s972.pth)
- 语言处理: 以确定的中文语义为基准先合成中文，经 180ms 换气停顿后合成等义日文译文（不使用固定日语台词替代）
- 铁律约束: 坚决禁用任何 Microsoft (SAPI/OneCore/系统机械音) 语音包；角色 TTS 或翻译失败时保持静默 (Fail-Silent) 并记录可见错误
- 音频链路: 32kHz 声学滤波与电平塑形后，经多相重采样输出 16kHz 16-bit 单声道线性 PCM 推送至 ESP32-S3 MAX98357A I2S 硬件
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

        # 音量控制 (默认 75% 适度清脆，保留已验收电平基线)
        self.current_volume = 75
        self.api_base: Optional[str] = (
            os.environ.get("KURISU_API_BASE")
            or os.environ.get("OLLAMA_HOST")
            or os.environ.get("OPENAI_BASE_URL")
            or "http://127.0.0.1:11434/v1"
        )
        self.model: str = os.environ.get("KURISU_MODEL", "kurisu")
        self.backend: Optional[str] = os.environ.get("KURISU_LLM_BACKEND")
        self.last_translation_error: Optional[str] = None
        self.last_tts_error: Optional[str] = None

        # 模型与提示音频路径
        self.model_dir = os.path.join(repo_root, "models", "kurisu_tts")
        self.t2s_weights = os.path.join(self.model_dir, "kurisu-e15.ckpt")
        self.vits_weights = os.path.join(self.model_dir, "kurisu_e4_s972.pth")
        self.bert_base_path = os.path.join(repo_root, "models", "pretrained_models", "chinese-roberta-wwm-ext-large")
        self.cnhuhbert_base_path = os.path.join(repo_root, "models", "pretrained_models", "chinese-hubert-base")

        # 牧濑红莉栖官方参考音频 (prompt_shy.wav, 4.35s, 文本对齐)
        self.ref_audio_path = os.path.join(self.model_dir, "prompt_shy.wav")
        self.prompt_text = "私が言ったのは親子で仲が良くて羨ましいな"
        self.prompt_lang = "ja"

        self.tts: Optional[TTS] = None
        self._init_kurisu_model()

    def _init_kurisu_model(self):
        """初始化牧濑红莉栖 GPT-SoVITS 神经网络"""
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

    def _clean_text_for_tts(self, text: str, lang: str = "zh") -> str:
        """清洗单语文本中的伪工具残渣、舞台说明、颜文字与多余空白（保留合法专名括号）"""
        if not text:
            return ""
        from bilingual_guard import clean_production_prose
        return clean_production_prose(text, lang=lang)

    def _contains_japanese(self, text: str) -> bool:
        """检测文本是否包含日文假名"""
        for char in text:
            if '\u3040' <= char <= '\u30ff':
                return True
        return False

    def _translate_zh_to_ja_kurisu(self, zh_text: str) -> str:
        """
        基于统一配置的本地模型端点，将已确定的中文台词忠实翻译为等义日文台词。
        经过数字、专名、颜色、否定与无口癖污染校验；若失败则返回空串并记录错误，绝不使用固定台词掩盖。
        """
        self.last_translation_error = None
        if not zh_text or not zh_text.strip():
            self.last_translation_error = "待翻译中文为空"
            return ""

        from bilingual_guard import translate_zh_to_ja
        ja, err = translate_zh_to_ja(
            zh_text,
            api_base=getattr(self, "api_base", None),
            model=getattr(self, "model", "kurisu") or "kurisu",
            backend=getattr(self, "backend", None),
            timeout=15.0,
        )
        if err:
            self.last_translation_error = err
            print(f"[VoiceEngine 动态中译日未通过]: {err}")
            return ""
        return ja

    def _split_zh_ja(self, text: str):
        """将输入文本按行与完整句边界拆分为中文段落与日文段落，避免换行先被合并导致串语"""
        if not text or not text.strip():
            return "", ""
        from bilingual_guard import split_bilingual_text, clean_production_prose
        zh_raw, ja_raw = split_bilingual_text(text)
        zh_text = clean_production_prose(zh_raw, lang="zh") if zh_raw else ""
        ja_text = clean_production_prose(ja_raw, lang="ja") if ja_raw else ""
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
        声学滤波与电平塑形处理链 (保持已验收参数不变):
        1. 95Hz 二阶高通滤波;
        2. noisereduce 平稳降噪 (可选依赖);
        3. 300Hz 去浑浊衰减 (-3.5dB);
        4. 3800Hz 临场激励 (+3.5dB);
        5. 14500Hz 二阶低通滤波;
        6. 动态电平安全归一化 (保留 -1.2dB / 0.88 净空)。
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

    def _synthesize_language_chunks(self, text: str, lang: str) -> Optional[np.ndarray]:
        """按完整句子分块合成单语音频，不切断 UTF-8 或句子；任一分块失败整体返回 None"""
        from bilingual_guard import chunk_sentences_safe
        chunks_text = chunk_sentences_safe(text, max_chars=90)
        if not chunks_text:
            return None
        audio_segments = []
        inter_pause = np.zeros(int(32000 * 0.06), dtype=np.float32)
        for idx, seg_text in enumerate(chunks_text):
            seg_audio = self._synthesize_raw(seg_text, lang)
            if seg_audio is None or len(seg_audio) == 0:
                return None
            if idx > 0:
                audio_segments.append(inter_pause.astype(seg_audio.dtype))
            audio_segments.append(seg_audio)
        return np.concatenate(audio_segments) if len(audio_segments) > 1 else audio_segments[0]

    def synthesize_speech_bundle(self, text: str) -> Optional[Tuple[bytes, bytes]]:
        """
        合成红莉栖双语声线:
        返回: (pcm_16k, wav_32k_bytes)
        确保: 【先完整中文分句】 + 【180ms 呼吸微停顿】 + 【后等义日文分句】
        严守铁律: 绝不使用任何微软/系统语音包；若角色 TTS 不可用、翻译失败或分块合成失败，
        保持静默 (Fail-Silent)、不写入残缺缓存、不误播历史缓存，并记录 last_tts_error。
        """
        self.last_tts_error = None
        if not text or not text.strip():
            return None
        if not self.tts:
            self.last_tts_error = "角色TTS模型未加载，已按静音保护跳过播报（未使用系统替代音色）"
            return None

        import hashlib
        import io
        import wave
        from pro_paths import cache_dir as runtime_cache_dir

        with self._lock:
            try:
                # 先在保留换行的前提下分离并清洗中文与日文
                zh_text, ja_text = self._split_zh_ja(text)
                if not zh_text and not ja_text:
                    self.last_tts_error = "清洗后无可播报有效文本"
                    return None

                # 若仅有中文而无日文，基于已确定的中文动态生成等义日文；失败则静音报错，不用固定台词掩盖
                if zh_text and not ja_text:
                    ja_text = self._translate_zh_to_ja_kurisu(zh_text)
                    if not ja_text:
                        self.last_tts_error = (
                            self.last_translation_error or "动态日文翻译失败，已保持静音（未使用固定台词替代）"
                        )
                        return None

                cache_dir = runtime_cache_dir() / 'voice'
                canonical_pair = f"{zh_text}\n{ja_text}"
                cache_key = hashlib.sha256(
                    f'bilingual-v2:{self.current_volume}:{canonical_pair}'.encode('utf-8')
                ).hexdigest()
                cache_file = cache_dir / (cache_key + '.wav')

                if cache_file.exists():
                    wav_bytes = cache_file.read_bytes()
                    with wave.open(io.BytesIO(wav_bytes), 'rb') as w:
                        samples = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
                    if len(samples) > 0:
                        pcm = scipy.signal.resample_poly(samples.astype(np.float32), 1, 2)
                        return np.clip(pcm, -32768, 32767).astype(np.int16).tobytes(), wav_bytes

                audio_zh = None
                audio_ja = None

                # 1. 先中文完整句分块合成
                if zh_text:
                    audio_zh = self._synthesize_language_chunks(zh_text, "zh")
                    if audio_zh is None or len(audio_zh) == 0:
                        self.last_tts_error = "角色中文语音分块合成失败，已保持静音"
                        return None

                # 2. 后日文完整句分块合成
                if ja_text:
                    audio_ja = self._synthesize_language_chunks(ja_text, "ja")
                    if audio_ja is None or len(audio_ja) == 0:
                        self.last_tts_error = "角色日文语音分块合成失败，已保持静音"
                        return None

                # 3. 缝合输出：先中文 + 180ms呼吸停顿 + 后日文
                if audio_zh is not None and audio_ja is not None:
                    silence = np.zeros(int(32000 * 0.18), dtype=audio_zh.dtype)
                    audio_res = np.concatenate([audio_zh, silence, audio_ja])
                elif audio_ja is not None and not zh_text:
                    audio_res = audio_ja
                else:
                    self.last_tts_error = "双语音频未完整生成，已保持静音"
                    return None

                if audio_res is None or len(audio_res) == 0:
                    self.last_tts_error = "合成音频为空，已保持静音"
                    return None

                # 声学后处理 (保持既有滤波参数与 75% 默认电平基线)
                processed_32k = self._postprocess_audio_32k(audio_res)

                # 生成 PC 专用的 32000Hz WAV 并原子写入内容寻址缓存
                wav_io = io.BytesIO()
                with wave.open(wav_io, 'wb') as w:
                    w.setnchannels(1)
                    w.setsampwidth(2)
                    w.setframerate(32000)
                    w.writeframes(processed_32k.tobytes())
                wav_32k_bytes = wav_io.getvalue()
                cache_dir.mkdir(parents=True, exist_ok=True)
                if len(list(cache_dir.glob('*.wav'))) < 64:
                    tmp_cache = cache_dir / (cache_key + f'.{os.getpid()}.tmp')
                    tmp_cache.write_bytes(wav_32k_bytes)
                    tmp_cache.replace(cache_file)

                # 多相重采样生成 ESP32 板载 16000Hz PCM16LE 流
                resampled_16k = scipy.signal.resample_poly(processed_32k.astype(np.float32), 1, 2)
                pcm_16k = np.clip(resampled_16k, -32768, 32767).astype(np.int16).tobytes()

                return pcm_16k, wav_32k_bytes

            except Exception as e:
                self.last_tts_error = f"角色语音合成中断: {e}"
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
        board_ready = ctrl.audio_connected or (getattr(ctrl, 'audio_transport', 'usb') == 'wifi' and ctrl.connect_audio())
        if board_ready:
            ctrl.set_board_led("speaking")

        if to_board and board_ready:
            # One physical output avoids delayed PC/board copies sounding like echo.
            if not ctrl.play_audio_pcm(pcm_16k):
                self.last_tts_error = "板载语音流发送或播放失败"
                print('[VoiceEngine] 板载语音播放失败')
            return
        try:
            import winsound
            winsound.PlaySound(wav_32k_bytes, winsound.SND_MEMORY)
        except Exception as e:
            self.last_tts_error = f"本地扬声器播放失败: {e}"
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
