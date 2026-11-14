"""
OpenCV stage: decode, lighting analysis + low-light enhancement (CLAHE), blur and motion.
Runs even when MediaPipe is not installed (OpenCV-only tier: lighting, stillness, framing hints).
"""
from __future__ import annotations

import base64
from typing import Any

try:  # pragma: no cover - environment dependent
    import cv2
    import numpy as np
    CV_VERSION: str | None = cv2.__version__
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore[assignment]
    np = None  # type: ignore[assignment]
    CV_VERSION = None

MAX_W = 480  # downscale for latency


def decode(b64: str) -> Any:
    """JPEG/PNG base64 (optionally data-URL) → BGR ndarray, resized to ≤ MAX_W wide."""
    if cv2 is None:
        raise RuntimeError("OpenCV not installed")
    if "," in b64[:64]:
        b64 = b64.split(",", 1)[1]
    buf = np.frombuffer(base64.b64decode(b64), dtype=np.uint8)
    img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("image could not be decoded")
    h, w = img.shape[:2]
    if w > MAX_W:
        img = cv2.resize(img, (MAX_W, int(h * MAX_W / w)), interpolation=cv2.INTER_AREA)
    return img


def analyse(img: Any) -> dict[str, Any]:
    """Lighting/contrast/blur metrics; returns an enhanced copy for detection when light is low."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    mean, std = float(gray.mean()), float(gray.std())
    blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    low_light = mean < 70 or std < 25
    enhanced = img
    if low_light:  # CLAHE on the L channel (lighting robustness)
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l_ch, a_ch, b_ch = cv2.split(lab)
        l_ch = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(l_ch)
        enhanced = cv2.cvtColor(cv2.merge((l_ch, a_ch, b_ch)), cv2.COLOR_LAB2BGR)
    too_dark = mean < 35
    return {"brightness": round(mean, 1), "contrast": round(std, 1), "blur": round(blur, 1),
            "low_light": low_light, "too_dark": too_dark, "too_bright": mean > 225, "blurry": blur < 30,
            "enhanced": low_light, "_img": enhanced, "_gray": gray}


def motion(prev_gray: Any, gray: Any) -> float:
    """Mean absolute frame difference (0–1); used for the 'stay still' checks."""
    if prev_gray is None or prev_gray.shape != gray.shape:
        return 0.0
    small_a = cv2.resize(prev_gray, (160, 120))
    small_b = cv2.resize(gray, (160, 120))
    return float(cv2.absdiff(small_a, small_b).mean() / 255.0)
