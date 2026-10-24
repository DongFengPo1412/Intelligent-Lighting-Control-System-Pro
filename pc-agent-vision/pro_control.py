"""Validated extended controls shared by physical and simulated controllers."""

import math
import re

DIRECT_MODES = set(range(32)) - {18, 25}


def integer(value, lo, hi):
    if type(value) is not int or not lo <= value <= hi:
        raise ValueError(f"Expected an integer in [{lo},{hi}]")
    return value


def real(value, lo, hi):
    if (
        isinstance(value, bool)
        or not isinstance(value, (float, int))
        or not math.isfinite(value)
        or not lo <= value <= hi
    ):
        raise ValueError(f"Expected a finite number in [{lo},{hi}]")
    return value


def boolean(value):
    if type(value) is not bool:
        raise ValueError("Expected a boolean")
    return value


class ProControlMixin:
    def track_calibrate(self, x0=0, y0=0, x1=1, y1=1, invert_x=False, invert_y=False):
        real(x0, 0, 1)
        real(y0, 0, 1)
        real(x1, 0, 1)
        real(y1, 0, 1)
        if x1 - x0 < 0.0001 or y1 - y0 < 0.0001:
            raise ValueError("Tracker input window must have positive area")
        return self.send_json(
            dict(
                cmd="track_cal",
                x0=x0,
                y0=y0,
                x1=x1,
                y1=y1,
                invert_x=boolean(invert_x),
                invert_y=boolean(invert_y),
            )
        )

    def track(self, x, y, visible=True, confidence=1):
        return self.send_json(
            dict(
                cmd="track",
                x=real(x, 0, 1),
                y=real(y, 0, 1),
                visible=boolean(visible),
                conf=real(confidence, 0, 1),
            )
        )

    def hand(self, x, y, z, pinch, visible=True):
        return self.send_json(
            dict(
                cmd="hand",
                x=real(x, 0, 1),
                y=real(y, 0, 1),
                z=real(z, -2, 2),
                pinch=boolean(pinch),
                visible=boolean(visible),
            )
        )

    def pet_context(self, hour, gaze=0, present=True, tired=False):
        if type(hour) is not int:
            raise ValueError("Hour must be an integer")
        return self.send_json(
            dict(
                cmd="pet_context",
                hour=real(hour, 0, 23),
                gaze=real(gaze, -1, 1),
                present=boolean(present),
                tired=boolean(tired),
            )
        )

    def difficulty(self, level=0.5, adaptive=True):
        return self.send_json(
            dict(cmd="difficulty", level=real(level, 0, 1), adaptive=boolean(adaptive))
        )

    def performance(self, reaction_ms, frustration=0, success=True):
        return self.send_json(
            dict(
                cmd="performance",
                reaction_ms=real(reaction_ms, 0, 10000),
                frustration=real(frustration, 0, 1),
                success=boolean(success),
            )
        )

    def music_features(self, energy, flux, onset, tempo, phase=0, bands=None):
        payload = dict(
            cmd="mir",
            energy=real(energy, 0, 1),
            flux=real(flux, 0, 1),
            onset=boolean(onset),
            tempo=real(tempo, 30, 240),
            phase=real(phase, 0, 1),
        )
        if bands is not None:
            if not isinstance(bands, (list, tuple)) or len(bands) != 16:
                raise ValueError("Expected 16 FFT band levels")
            payload["bands"] = [integer(value, 0, 15) for value in bands]
        return self.send_json(payload)

    def canvas(self, pixels):
        if not isinstance(pixels, str) or not re.fullmatch(
            r"[0-9a-fA-F]{1536}", pixels
        ):
            raise ValueError("Canvas requires exactly 256 RGB hex pixels")
        return self.send_json(dict(cmd="canvas", hex=pixels.lower()))

    def frame(self):
        return self.command_result(dict(cmd="frame"))
