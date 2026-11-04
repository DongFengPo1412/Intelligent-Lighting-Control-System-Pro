"""Read-only Pro deployment configuration check; no devices, camera or model loading."""
import argparse
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def inspect():
    errors = []
    versions = {}
    if sys.version_info[:2] != (3, 10):
        errors.append("The verified full-service profile uses Python 3.10.")
    for name in ("aiohttp", "numpy", "scipy", "serial", "jsonschema", "cv2", "mediapipe",
                 "soundfile", "av", "torch", "faster_whisper", "webrtcvad"):
        try:
            available = importlib.util.find_spec(name) is not None
        except (ImportError, ValueError):
            available = False
        if not available:
            errors.append("Missing runtime module: " + name)
    for package in ("transformers", "huggingface-hub", "torch", "faster-whisper"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            errors.append("Missing package metadata: " + package)
    if versions.get("transformers") != "4.46.3" or versions.get("huggingface-hub") != "0.36.0":
        errors.append("Use the tested voice constraints/isolated overlay; do not upgrade shared packages implicitly.")
    settings = {
        "KURISU_AUDIO_TRANSPORT": os.environ.get("KURISU_AUDIO_TRANSPORT", "wifi"),
        "KURISU_ASR_DEVICE": os.environ.get("KURISU_ASR_DEVICE", "auto"),
        "KURISU_TTS_CUDNN": os.environ.get("KURISU_TTS_CUDNN", "1"),
    }
    if settings != {"KURISU_AUDIO_TRANSPORT": "wifi", "KURISU_ASR_DEVICE": "cpu", "KURISU_TTS_CUDNN": "0"}:
        errors.append("First deployment requires the documented explicit WiFi/CPU-ASR/no-cuDNN-TTS profile.")
    def endpoint(value):
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower()
        if host == "localhost":
            host = "127.0.0.1"
        return (parsed.scheme, host, parsed.port or (443 if parsed.scheme == "https" else 80),
                parsed.path.rstrip("/").removesuffix("/v1"))
    chat = endpoint(os.environ.get("OPENAI_BASE_URL", "http://127.0.0.1:11434/v1"))
    translation = endpoint(os.environ.get("KURISU_API_BASE") or os.environ.get("OLLAMA_HOST") or os.environ.get("OPENAI_BASE_URL") or "http://127.0.0.1:11434/v1")
    if chat != translation:
        errors.append("Chat and translation resolve to different endpoints; align the documented profile.")
    models = ["models/kurisu_tts/kurisu-e15.ckpt", "models/kurisu_tts/kurisu_e4_s972.pth",
              "models/kurisu_tts/prompt_shy.wav", "models/pretrained_models/chinese-roberta-wwm-ext-large/config.json",
              "models/pretrained_models/chinese-hubert-base/config.json", "models/wake_kws/tokens.txt"]
    missing = [name for name in models if not (ROOT / name).is_file()]
    if missing:
        errors.append("Missing existing model/reference files: " + ", ".join(missing))
    if not (ROOT / "pc-agent-vision/.runtime_deps/sherpa_onnx").is_dir():
        errors.append("Private documented Sherpa KWS runtime is missing.")
    return {"configuration_check": "FAILED" if errors else "PASSED", "python": sys.version.split()[0],
            "versions": versions, "settings": settings, "errors": errors,
            "boundary": "Configuration/existence only; does not load models, connect devices, validate sound or authorize flashing."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-json")
    args = parser.parse_args()
    result = inspect()
    encoded = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output_json:
        target = Path(args.output_json).resolve()
        if target == ROOT or ROOT in target.parents:
            parser.error("Write preflight results to a task cache/artifact directory, outside the repository.")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(encoded, encoding="utf-8")
    print(encoded)
    raise SystemExit(bool(result["errors"]))
