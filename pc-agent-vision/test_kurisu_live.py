"""
Test script for Makise Kurisu GPT-SoVITS pure voice engine
"""
import sys
import os
import time
import numpy as np
import soundfile as sf
import scipy.signal
import winsound
import io
import wave

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Ensure GPT-SoVITS path
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
gpt_sovits_dir = os.path.join(repo_root, "models", "GPT-SoVITS")
sys.path.insert(0, gpt_sovits_dir)
sys.path.insert(0, os.path.join(gpt_sovits_dir, "GPT_SoVITS"))

from TTS_infer_pack.TTS import TTS_Config, TTS

t0 = time.time()
print("[1] 正在初始化牧濑红莉栖纯正 GPT-SoVITS 模型...")
custom_config = {
    'custom': {
        'device': 'cuda',
        'is_half': False,
        'version': 'v2Pro',
        't2s_weights_path': os.path.join(repo_root, 'models', 'kurisu_tts', 'kurisu-e15.ckpt'),
        'vits_weights_path': os.path.join(repo_root, 'models', 'kurisu_tts', 'kurisu_e4_s972.pth'),
        'bert_base_path': os.path.join(repo_root, 'models', 'pretrained_models', 'chinese-roberta-wwm-ext-large'),
        'cnhuhbert_base_path': os.path.join(repo_root, 'models', 'pretrained_models', 'chinese-hubert-base'),
    }
}
cfg = TTS_Config(custom_config)
tts = TTS(cfg)
print(f"[1] 模型就绪! 耗时: {time.time()-t0:.2f}s")

ref_wav = os.path.join(repo_root, 'models', 'kurisu_tts', 'soundbank', 'not_christina.wav')

def synthesize_sentence(text: str, lang: str):
    req = {
        'text': text,
        'text_lang': lang,
        'ref_audio_path': ref_wav,
        'prompt_text': '私、クリスティーナじゃない！',
        'prompt_lang': 'ja',
        'streaming_mode': False,
        'use_cuda_graph': False,
        'parallel_infer': False,
        'top_k': 15,
        'top_p': 1.0,
        'temperature': 1.0,
    }
    chunks = []
    sr = 32000
    for res_sr, data in tts.run(req):
        sr = res_sr
        if data is not None and len(data) > 0:
            chunks.append(data)
    if not chunks:
        return None
    return np.concatenate(chunks)

print("[2] 正在合成测试对白: 中文 + 日文...")
t_synth = time.time()
audio_zh = synthesize_sentence("都说了我不是助手！你这笨蛋怎么就是不听呢！", "zh")
audio_ja = synthesize_sentence("私、クリスティーナじゃない！", "ja")
print(f"[2] 合成完毕! 耗时: {time.time()-t_synth:.2f}s")

silence = np.zeros(int(32000 * 0.18), dtype=audio_zh.dtype)
combined_32k = np.concatenate([audio_zh, silence, audio_ja])

# Resample to 16kHz
combined_16k = scipy.signal.resample_poly(combined_32k.astype(np.float32), 1, 2)
# Volume scaling (75%)
combined_16k = np.clip(combined_16k * 0.75, -32768, 32767).astype(np.int16)
pcm_bytes = combined_16k.tobytes()

print(f"[3] 输出 16kHz 16-bit 单声道 PCM 流: {len(pcm_bytes)} 字节, 时长: {len(combined_16k)/16000:.2f}s")

wav_io = io.BytesIO()
with wave.open(wav_io, 'wb') as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(16000)
    w.writeframes(pcm_bytes)

print("[4] 播放牧濑红莉栖原声 (PC 本地扬声器)...")
winsound.PlaySound(wav_io.getvalue(), winsound.SND_MEMORY)
print("[5] 测试成功完成！")
