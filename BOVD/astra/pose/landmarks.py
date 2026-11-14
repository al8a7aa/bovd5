"""
MediaPipe stage: 33 body landmarks with the Tasks API (PoseLandmarker, 'lite' model).
The model file is not bundled (licence/size); scripts/fetch_models.py downloads it from Google's official
MediaPipe model storage on first run (start.bat). Without it the app falls back to OpenCV-only + manual mode.
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from ..config import DATA_DIR

MODEL_PATH: Path = DATA_DIR / "models" / "pose_landmarker_lite.task"
MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/"
             "float16/latest/pose_landmarker_lite.task")

try:  # pragma: no cover - environment dependent
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions
    from mediapipe.tasks.python import vision as mp_vision
    MP_VERSION: str | None = mp.__version__
except Exception:  # pragma: no cover
    mp = None  # type: ignore[assignment]
    MP_VERSION = None

_lock = threading.Lock()
_detector: Any = None
_override: Any = None  # tests inject a fake detector here

NAMES = ["nose", "l_eye_in", "l_eye", "l_eye_out", "r_eye_in", "r_eye", "r_eye_out", "l_ear", "r_ear", "mouth_l", "mouth_r",
         "l_shoulder", "r_shoulder", "l_elbow", "r_elbow", "l_wrist", "r_wrist", "l_pinky", "r_pinky", "l_index", "r_index",
         "l_thumb", "r_thumb", "l_hip", "r_hip", "l_knee", "r_knee", "l_ankle", "r_ankle", "l_heel", "r_heel", "l_foot", "r_foot"]


def status() -> dict[str, Any]:
    return {"mediapipe": MP_VERSION, "model_present": MODEL_PATH.exists(), "model_path": str(MODEL_PATH),
            "ready": _override is not None or (MP_VERSION is not None and MODEL_PATH.exists())}


def set_override(fn: Any) -> None:
    """Inject a detector function (img → landmarks list or None). Used by tests."""
    global _override
    _override = fn


def _get() -> Any:  # pragma: no cover - needs model file
    global _detector
    if _detector is None:
        opts = mp_vision.PoseLandmarkerOptions(base_options=BaseOptions(model_asset_path=str(MODEL_PATH)),
                                               running_mode=mp_vision.RunningMode.IMAGE, num_poses=1,
                                               min_pose_detection_confidence=0.5, min_tracking_confidence=0.5)
        _detector = mp_vision.PoseLandmarker.create_from_options(opts)
    return _detector


def detect(img_bgr: Any) -> list[dict[str, float]] | None:
    """Return 33 landmarks {name,x,y,z,v} (x,y normalised 0–1, y downwards) or None."""
    if _override is not None:
        return _override(img_bgr)  # type: ignore[no-any-return]
    if not status()["ready"]:  # pragma: no cover
        return None
    import cv2  # pragma: no cover
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)  # pragma: no cover
    with _lock:  # pragma: no cover
        res = _get().detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
    if not res.pose_landmarks:  # pragma: no cover
        return None
    return [{"name": NAMES[i], "x": p.x, "y": p.y, "z": p.z, "v": float(getattr(p, "visibility", 1.0) or 0.0)}
            for i, p in enumerate(res.pose_landmarks[0])]  # pragma: no cover
