"""Calibratable gaze/head pose and temporal face/hand features.

Monocular relative hand z is not metric depth. Fatigue/expression outputs are
heuristic interaction cues, not medical or psychological classifications.
"""

from collections import deque
import math
import numpy as np


def clipped(x, lo=0.0, hi=1.0):
    return float(np.clip(x, lo, hi))


class GazeCalibration:
    def __init__(self):
        self.coefficients = None

    def fit(self, samples):
        data = np.asarray(samples, dtype=float)
        if data.ndim != 2 or data.shape[1] != 4 or len(data) < 5 or not np.isfinite(data).all():
            raise ValueError("Need >=5 samples [iris_x,iris_y,target_x,target_y]")
        design = np.c_[data[:, :2], np.ones(len(data))]
        if np.linalg.matrix_rank(design) < 3:
            raise ValueError("Calibration points do not cover both axes")
        coefficients = np.linalg.lstsq(design, data[:, 2:], rcond=None)[0]
        self.coefficients = coefficients
        return float(np.sqrt(np.mean((design @ coefficients - data[:, 2:]) ** 2)))

    def predict(self, x, y):
        if self.coefficients is None:
            return (clipped(x), clipped(y))
        value = np.array([x, y, 1]) @ self.coefficients
        return tuple(clipped(v) for v in value)


class VisualFeatures:
    def __init__(self):
        self.closed_since = None
        self.history = deque()
        self.gaze = GazeCalibration()

    def face(self, points, now, width=640, height=480):
        p = np.asarray(points, float)
        if p.ndim != 2 or p.shape[0] < 478 or p.shape[1] != 3 or not np.isfinite(p).all():
            raise ValueError("Expected 478 finite face landmarks")

        def dist(a, b):
            return float(np.linalg.norm(p[a, :2] - p[b, :2]))

        def ratio(a, b, c, d):
            return dist(a, b) / max(1e-6, dist(c, d))

        ear = (ratio(159, 145, 33, 133) + ratio(386, 374, 362, 263)) / 2
        closed = ear < 0.16
        if closed and self.closed_since is None:
            self.closed_since = now
        if not closed:
            self.closed_since = None
        self.history.append((now, closed))
        while self.history and now - self.history[0][0] > 30:
            self.history.popleft()
        perclos = sum(v for _, v in self.history) / max(1, len(self.history))
        elapsed = now - self.history[0][0] if self.history else 0
        tired = (closed and now - self.closed_since > 1.2) or (elapsed > 10 and perclos > 0.3)
        mar = ratio(13, 14, 61, 291)
        smiling = ratio(61, 291, 33, 263) > 0.65 and mar < 0.5
        frown = clipped((0.19 - ratio(70, 300, 33, 263)) * 5)
        iris = []
        for center, left, right, top, bottom in [
            (468, 33, 133, 159, 145),
            (473, 362, 263, 386, 374),
        ]:
            x = (p[center, 0] - min(p[left, 0], p[right, 0])) / max(
                1e-6, abs(p[left, 0] - p[right, 0])
            )
            y = (p[center, 1] - p[top, 1]) / max(1e-6, p[bottom, 1] - p[top, 1])
            iris.append((clipped(x), clipped(y)))
        raw = np.mean(iris, axis=0)
        gx, gy = self.gaze.predict(*raw)
        return dict(
            gaze_x=gx,
            gaze_y=gy,
            iris_x=float(raw[0]),
            iris_y=float(raw[1]),
            calibrated=self.gaze.coefficients is not None,
            ear=ear,
            perclos=perclos,
            tired=bool(tired),
            yawning=mar > 0.55,
            smiling=bool(smiling),
            frustration=frown,
            head_pose=self.head_pose(p, width, height),
        )

    @staticmethod
    def head_pose(p, width, height):
        import cv2

        ids = [1, 152, 33, 263, 61, 291]
        model = np.array(
            [
                (0, 0, 0),
                (0, -330, -65),
                (-225, 170, -135),
                (225, 170, -135),
                (-150, -150, -125),
                (150, -150, -125),
            ],
            float,
        )
        image = np.array([(p[i, 0] * width, p[i, 1] * height) for i in ids], float)
        camera = np.array([[width, 0, width / 2], [0, width, height / 2], [0, 0, 1]], float)
        ok, rvec, _ = cv2.solvePnP(model, image, camera, np.zeros(4), flags=cv2.SOLVEPNP_ITERATIVE)
        if not ok:
            return None
        angles = cv2.RQDecomp3x3(cv2.Rodrigues(rvec)[0])[0]
        return dict(
            pitch=float(angles[0]),
            yaw=float(angles[1]),
            roll=float(angles[2]),
            camera_calibrated=False,
        )

    @staticmethod
    def hand(points):
        p = np.asarray(points, float)
        if p.shape != (21, 3) or not np.isfinite(p).all():
            raise ValueError("Expected 21 finite hand landmarks")
        scale = max(1e-6, float(np.linalg.norm(p[5, :2] - p[17, :2])))
        closed = (
            float(np.mean([np.linalg.norm(p[i, :2] - p[0, :2]) for i in (8, 12, 16, 20)])) / scale
            < 1.25
        )
        pinch = np.linalg.norm(p[4, :2] - p[8, :2]) / scale < 0.35 or closed
        return dict(
            x=clipped(p[8, 0]),
            y=clipped(p[8, 1]),
            z=clipped(p[8, 2], -2, 2),
            pinch=bool(pinch),
            closed=bool(closed),
            visible=True,
        )
