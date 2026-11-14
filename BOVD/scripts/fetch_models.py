"""
Download the MediaPipe Pose Landmarker 'lite' model from Google's official MediaPipe model storage into
data/models/. Run automatically by start.bat (needs internet once). Safe to re-run.
Model card / licence: https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker
"""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from astra.pose.landmarks import MODEL_PATH, MODEL_URL  # noqa: E402


def main() -> int:
    if MODEL_PATH.exists() and MODEL_PATH.stat().st_size > 1_000_000:
        print(f"[OK] model present: {MODEL_PATH}")
        return 0
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        print("[i] downloading MediaPipe pose model (~5 MB) …")
        with urllib.request.urlopen(MODEL_URL, timeout=60) as r:  # noqa: S310 - fixed https URL
            data = r.read()
        tmp = MODEL_PATH.with_suffix(".part")
        tmp.write_bytes(data)
        tmp.replace(MODEL_PATH)
        print(f"[OK] saved {MODEL_PATH} ({len(data) // 1024} KB)")
        return 0
    except Exception as exc:  # offline
        print(f"[i] could not download the model ({exc}). Posture check runs in OpenCV-only / manual mode.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
