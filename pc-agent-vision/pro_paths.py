"""Persistent application data is separate from sources and task test outputs."""

import os
from pathlib import Path


def data_dir():
    root = Path(
        os.environ.get("KURISU_DATA_DIR")
        or (Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share")) / "KurisuPro")
    )
    root.mkdir(parents=True, exist_ok=True)
    return root


def cache_dir():
    root = Path(
        os.environ.get("KURISU_CACHE_DIR")
        or (data_dir() / "cache")
    )
    root.mkdir(parents=True, exist_ok=True)
    return root
