"""
下载 HuggingFace xuanyaox/TTS-KurisuMakise 牧濑红莉栖原声大模型权重
"""

import os
import sys
import time
import urllib.request

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(REPO_ROOT, "models", "kurisu_tts")
os.makedirs(MODEL_DIR, exist_ok=True)

FILES = [
    (
        "https://huggingface.co/xuanyaox/TTS-KurisuMakise/resolve/main/%E7%89%A7%E6%87%92%E7%BA%A2%E8%8E%89%E6%A0%96-e15.ckpt",
        os.path.join(MODEL_DIR, "kurisu-e15.ckpt"),
        "GPT 韵律模型 (kurisu-e15.ckpt)"
    ),
    (
        "https://huggingface.co/xuanyaox/TTS-KurisuMakise/resolve/main/%E7%89%A7%E6%87%92%E7%BA%A2%E8%8E%89%E6%A0%96_e4_s972.pth",
        os.path.join(MODEL_DIR, "kurisu_e4_s972.pth"),
        "SoVITS 声学模型 (kurisu_e4_s972.pth)"
    )
]

def download_file(url, target_path, desc):
    if os.path.exists(target_path) and os.path.getsize(target_path) > 100 * 1024 * 1024:
        print(f"✓ {desc} 已存在，跳过下载 ({os.path.getsize(target_path) / (1024*1024):.1f} MB)")
        return

    print(f"\n正在下载 {desc} ...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    
    with urllib.request.urlopen(req) as resp, open(target_path, "wb") as out_f:
        total = int(resp.headers.get("content-length", 0))
        downloaded = 0
        start_time = time.time()
        last_print = 0
        
        while True:
            chunk = resp.read(1024 * 512) # 512KB chunks
            if not chunk:
                break
            out_f.write(chunk)
            downloaded += len(chunk)
            now = time.time()
            if now - last_print > 1.5 or downloaded == total:
                pct = (downloaded / total * 100) if total else 0
                speed_mb = (downloaded / (now - start_time)) / (1024 * 1024) if (now - start_time) > 0 else 0
                print(f"进度: {downloaded/(1024*1024):.1f}/{total/(1024*1024):.1f} MB ({pct:.1f}%) | 速度: {speed_mb:.2f} MB/s")
                last_print = now

    print(f"✓ {desc} 下载完成！")

if __name__ == "__main__":
    for url, path, desc in FILES:
        download_file(url, path, desc)
    print("\n🎉 牧濑红莉栖全套模型权重已完整就绪！")
