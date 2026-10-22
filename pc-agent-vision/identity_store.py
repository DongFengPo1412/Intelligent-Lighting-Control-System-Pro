"""Local LBPH enrollment, not a security/biometric authentication mechanism."""

import json
import re
import threading
from pro_paths import data_dir


class IdentityStore:
    def __init__(self):
        import cv2

        self.cv2 = cv2
        self.root = data_dir() / "faces"
        self.root.mkdir(exist_ok=True)
        self.lock = threading.RLock()
        self.model = cv2.face.LBPHFaceRecognizer_create()
        self.names = []
        self.ready = False
        self.train()

    def train(self):
        images = []
        labels = []
        self.names = []
        for folder in sorted(self.root.iterdir()):
            if not folder.is_dir():
                continue
            label = len(self.names)
            self.names.append(folder.name)
            for p in folder.glob("*.png"):
                import numpy as np

                image = self.cv2.imdecode(np.fromfile(p, dtype=np.uint8), self.cv2.IMREAD_GRAYSCALE)
                if image is not None:
                    images.append(image)
                    labels.append(label)
        if images:
            import numpy as np

            with self.lock:
                self.model.train(images, np.array(labels))
                self.ready = True

    def enroll(self, name, image):
        if not isinstance(name, str) or not re.fullmatch(r"[\w -]{1,40}", name):
            raise ValueError("Invalid identity name")
        from uuid import uuid4

        folder = self.root / name
        folder.mkdir(exist_ok=True)
        path = folder / (uuid4().hex + ".png")
        ok, encoded = self.cv2.imencode(".png", image)
        if not ok:
            raise OSError("Cannot encode enrollment")
        encoded.tofile(path)
        with self.lock:
            self.train()
        return dict(name=name, samples=len(list(folder.glob("*.png"))))

    def predict(self, image):
        if not self.ready or image is None:
            return None, None
        with self.lock:
            label, distance = self.model.predict(image)
            return (self.names[label] if distance < 65 else None), float(distance)
