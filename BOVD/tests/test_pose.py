"""
Posture-verification tests.

1. Rule logic is evaluated on a DOCUMENTED SYNTHETIC landmark set (correct + deliberately wrong postures,
   with random jitter). False positives / false negatives are counted and written to
   tests/pose_rule_eval.json. This measures the RULES, not MediaPipe's detector accuracy.
2. The OpenCV stage (decode, low-light CLAHE, motion) runs on generated images.
3. The full session pipeline runs with an injected fake detector (no camera, no model file needed).
Real-camera detector accuracy must be measured with scripts/pose_eval.py on a labelled image folder.
"""
from __future__ import annotations

import base64
import json
import random
from pathlib import Path

import pytest

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")

from astra.pose import landmarks, quality, rules, session  # noqa: E402

NAMES = landmarks.NAMES


def body(arm_drop: float = 0.0, tilt: float = 0.0, cross: bool = False, seated: bool = True, jitter: float = 0.004,
         rng: random.Random | None = None, cover: str | None = None) -> dict[str, dict[str, float]]:
    """Synthetic front-view landmarks (normalised). arm_drop moves the left upper arm down (torso units)."""
    rng = rng or random.Random(0)
    j = lambda: rng.uniform(-jitter, jitter)  # noqa: E731
    sy, hy, torso = 0.35, 0.65, 0.30
    pts = {n: {"x": 0.5, "y": 0.5, "z": 0.0, "v": 0.99} for n in NAMES}

    def put(n: str, x: float, y: float) -> None:
        pts[n].update(x=x + j(), y=y + j())

    put("nose", 0.5 + tilt * 0.3, 0.2)
    put("l_eye", 0.53, 0.18)
    put("r_eye", 0.47, 0.18)
    put("l_shoulder", 0.62 + tilt * 0.3, sy)
    put("r_shoulder", 0.38 + tilt * 0.3, sy)
    put("l_hip", 0.58, hy)
    put("r_hip", 0.42, hy)
    heart = sy + 0.30 * torso
    # left (cuff) arm: upper-arm midpoint at heart level when arm_drop = 0
    el_y = 2 * heart - sy + arm_drop * torso
    put("l_elbow", 0.70, el_y)
    put("l_wrist", 0.70 + 0.12, el_y + 0.03)
    put("r_elbow", 0.30, 0.55)
    put("r_wrist", 0.33, 0.68)
    if seated:
        put("l_knee", 0.60 if not cross else 0.40, 0.70)
        put("r_knee", 0.40 if not cross else 0.60, 0.70)
        put("l_ankle", 0.60, 0.95)
        put("r_ankle", 0.40, 0.95)
    else:
        put("l_knee", 0.58, 0.80)
        put("r_knee", 0.42, 0.80)
        put("l_ankle", 0.58, 0.97)
        put("r_ankle", 0.42, 0.97)
    if cover:
        e = pts[f"{cover}_eye"]
        put("l_index", e["x"], e["y"])
    else:
        put("l_index", 0.83, el_y + 0.04)
        put("r_index", 0.34, 0.70)
    return pts


def ctx(L, q=None, motion=0.0):  # type: ignore[no-untyped-def]
    return {"L": L, "q": q or {}, "motion": motion, "side": "left", "aspect": 1.0, "state": {}}


def test_individual_checks() -> None:
    assert rules.c_upright(ctx(body()))["ok"] is True
    assert rules.c_upright(ctx(body(tilt=0.4)))["ok"] is False
    assert rules.c_arm_heart_level(ctx(body()))["ok"] is True
    assert rules.c_arm_heart_level(ctx(body(arm_drop=0.5)))["ok"] is False
    assert rules.c_legs_uncrossed(ctx(body(cross=True)))["ok"] is False
    assert rules.c_still(ctx(body(), motion=0.1))["ok"] is False
    assert rules.c_light(ctx(None, q={"too_dark": True}))["ok"] is False
    assert rules.c_upper_body(ctx(None))["ok"] is False
    assert rules.c_cover_left(ctx(body(cover="l")))["ok"] is True
    assert rules.c_cover_left(ctx(body()))["ok"] is False
    assert rules.angle((0, 1), (0, 0), (1, 0)) == pytest.approx(90)


def test_rule_evaluation_dataset() -> None:
    """Documented synthetic evaluation: 400 cases, counts FP/FN for the BP 'arm' and 'posture' steps."""
    rng = random.Random(42)
    cases = []
    for i in range(400):
        kind = i % 4
        if kind == 0:
            lab, L = True, body(arm_drop=rng.uniform(-0.08, 0.08), tilt=rng.uniform(-0.05, 0.05), rng=rng)
        elif kind == 1:
            lab, L = False, body(arm_drop=rng.choice([-1, 1]) * rng.uniform(0.3, 0.7), rng=rng)
        elif kind == 2:
            lab, L = False, body(tilt=rng.choice([-1, 1]) * rng.uniform(0.35, 0.8), rng=rng)
        else:
            lab, L = False, body(cross=True, rng=rng)
        arm = rules.evaluate("blood_pressure", 2, ctx(L))["passed"]
        post = rules.evaluate("blood_pressure", 1, ctx(L))["passed"]
        cases.append({"kind": ["correct", "arm_wrong", "trunk_tilted", "legs_crossed"][kind], "label": lab, "pred": arm and post})
    tp = sum(c["label"] and c["pred"] for c in cases)
    tn = sum(not c["label"] and not c["pred"] for c in cases)
    fp = [c for c in cases if not c["label"] and c["pred"]]
    fn = [c for c in cases if c["label"] and not c["pred"]]
    report = {"description": "Synthetic landmark set (rules only, not MediaPipe accuracy); seed 42; 100 cases per class",
              "n": len(cases), "tp": tp, "tn": tn, "fp": len(fp), "fn": len(fn),
              "fp_by_kind": {k: sum(c["kind"] == k for c in fp) for k in ("arm_wrong", "trunk_tilted", "legs_crossed")},
              "accuracy": round((tp + tn) / len(cases), 4)}
    Path(__file__).with_name("pose_rule_eval.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    assert report["accuracy"] >= 0.95


def _jpeg(brightness: int, noise: bool = True) -> str:
    img = np.full((240, 320, 3), brightness, np.uint8)
    if noise:
        rng = np.random.default_rng(1)
        img = np.clip(img.astype(int) + rng.integers(-40, 40, img.shape), 0, 255).astype(np.uint8)
    cv2.rectangle(img, (100, 60), (220, 200), (min(255, brightness + 80),) * 3, -1)
    ok, buf = cv2.imencode(".jpg", img)
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()


def test_opencv_quality_and_low_light() -> None:
    dark = quality.analyse(quality.decode(_jpeg(25)))
    assert dark["low_light"] and dark["enhanced"]
    ok = quality.analyse(quality.decode(_jpeg(130)))
    assert not ok["too_dark"]
    with pytest.raises(ValueError):
        quality.decode(base64.b64encode(b"not an image").decode())
    a = quality.decode(_jpeg(120))
    g = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY)
    assert quality.motion(None, g) == 0.0
    assert quality.motion(g, 255 - g) > 0.1


def test_session_pipeline_with_fake_detector() -> None:
    landmarks.set_override(lambda img: [dict(name=n, **body()[n]) for n in NAMES])
    try:
        s = session.start("blood_pressure")
        sid = s["session"]
        frame = _jpeg(130)
        for _ in range(60):
            v = session.frame(sid, frame)
            if v["step"] and v["step"]["manual"]:
                v = session.manual(sid, True)
            if v["done"]:
                break
        assert v["done"] and v["score"]["completed_pct"] == 100
        assert v["score"]["auto_verified"] == 4 and v["score"]["manual_confirmed"] == 1
        assert "landmarks" not in json.dumps(session.finish(sid)["log"])  # only summaries leave the session
    finally:
        landmarks.set_override(None)


def test_no_detector_reports_and_manual_mode() -> None:
    landmarks.set_override(lambda img: None)
    try:
        s = session.start("spo2", mode="manual")
        v = session.frame(s["session"], _jpeg(130))
        assert v["result"]["checks"][1]["ok"] is False  # upper body not detected → guidance, no crash
        for _ in range(3):
            v = session.manual(s["session"], True)
        assert v["done"] and v["score"]["manual_confirmed"] == 3
    finally:
        landmarks.set_override(None)
    with pytest.raises(ValueError):
        session.start("x-ray")
    assert session.capabilities()["tier"] in ("full", "opencv_only", "manual")
    assert len(session.exams()) == 5
