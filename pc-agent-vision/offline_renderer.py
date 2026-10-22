"""Local Node/WASM worker for the real display algorithms, with no device I/O."""

import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import time


class OfflineRenderer:
    def __init__(self, wasm):
        path = Path(wasm).resolve()
        if not path.is_file():
            raise ValueError("Build the offline engine WASM first")
        self.started = time.monotonic()
        self.lock = threading.RLock()
        self.lines = queue.Queue()
        self.closed = False
        self.process = subprocess.Popen(
            [
                os.environ.get("KURISU_NODE_EXE", "node"),
                str(Path(__file__).with_suffix(".js")),
                str(path),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

        def read():
            for line in self.process.stdout:
                self.lines.put(line)
            self.lines.put(None)

        threading.Thread(target=read, daemon=True).start()

    def call(self, **data):
        with self.lock:
            if self.closed:
                raise RuntimeError("Offline renderer is closed")
            try:
                data["now"] = 1000 + int((time.monotonic() - self.started) * 1000)
                self.process.stdin.write(json.dumps(data) + "\n")
                self.process.stdin.flush()
                line = self.lines.get(timeout=5)
                if line is None:
                    raise RuntimeError("Offline renderer exited")
                value = json.loads(line)
                if "error" in value:
                    raise RuntimeError(value["error"])
                return value
            except (OSError, queue.Empty, ValueError, RuntimeError):
                self.close()
                raise RuntimeError("Offline renderer failed; check the matching engine build")

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.process.stdin.close()
        try:
            self.process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=2)
        self.process.stdout.close()
