"""
Guided posture session: frame → OpenCV quality/motion → MediaPipe landmarks → rules → step progression.
Frames are processed in memory and dropped immediately; only the per-step summary is kept (and saved
to the black box when the session finishes, if the astronaut consented to 'pose_camera').
"""
from __future__ import annotations

import time
import uuid
from typing import Any

from . import landmarks, quality, rules

_SESSIONS: dict[str, dict[str, Any]] = {}
TTL_S = 1800


def capabilities() -> dict[str, Any]:
    st = landmarks.status()
    return {"opencv": quality.CV_VERSION, **st,
            "tier": "full" if quality.CV_VERSION and st["ready"] else "opencv_only" if quality.CV_VERSION else "manual",
            "note_ar": {"full": "OpenCV + MediaPipe جاهزان: تحقق تلقائي من الوضعية.",
                        "opencv_only": "OpenCV فقط (الإضاءة والثبات). لتفعيل كشف معالم الجسم ثبّت MediaPipe ونموذجه بتشغيل install_camera.bat مرة واحدة.",
                        "manual": "الوضع اليدوي: اتبع الرسوم والتعليمات وأكّد كل خطوة بنفسك. لتفعيل التحقق التلقائي شغّل install_camera.bat مرة واحدة ثم أعد تشغيل start.bat."}[
                "full" if quality.CV_VERSION and st["ready"] else "opencv_only" if quality.CV_VERSION else "manual"]}


def exams() -> list[dict[str, Any]]:
    return [{"id": k, "title_ar": v["title_ar"], "title_en": v["title_en"], "anim": v["anim"],
             "steps": [{"id": s["id"], "ar": s["ar"], "manual": bool(s.get("manual")), "checks": s["checks"]} for s in v["steps"]]}
            for k, v in rules.EXAMS.items()]


def start(exam: str, side: str = "left", mode: str = "camera") -> dict[str, Any]:
    if exam not in rules.EXAMS:
        raise ValueError("unknown exam")
    _gc()
    sid = str(uuid.uuid4())
    _SESSIONS[sid] = {"id": sid, "exam": exam, "side": side, "mode": mode, "step": 0, "streak": 0, "frames": 0,
                      "prev_gray": None, "started": time.time(), "state": {},
                      "log": [{"step": s["id"], "frames": 0, "fail_frames": 0, "passed": False, "how": None, "issues": {}}
                              for s in rules.EXAMS[exam]["steps"]]}
    return view(sid)


def _gc() -> None:
    now = time.time()
    for k in [k for k, s in _SESSIONS.items() if now - s["started"] > TTL_S]:
        _SESSIONS.pop(k, None)


def get(sid: str) -> dict[str, Any]:
    s = _SESSIONS.get(sid)
    if not s:
        raise ValueError("session expired or unknown")
    return s


def view(sid: str, last: dict[str, Any] | None = None) -> dict[str, Any]:
    s = get(sid)
    steps = rules.EXAMS[s["exam"]]["steps"]
    done = s["step"] >= len(steps)
    cur = None if done else steps[s["step"]]
    hold = cur.get("hold", 1) if cur else 1
    return {"session": sid, "exam": s["exam"], "step_index": s["step"], "steps_total": len(steps), "done": done,
            "step": None if done else {"id": cur["id"], "ar": cur["ar"], "manual": bool(cur.get("manual"))},  # type: ignore[index]
            "hold": {"have": s["streak"], "need": hold}, "result": last, "log": s["log"],
            "score": score(s) if done else None}


def frame(sid: str, b64: str) -> dict[str, Any]:
    """Process ONE frame. The image is never stored."""
    s = get(sid)
    steps = rules.EXAMS[s["exam"]]["steps"]
    if s["step"] >= len(steps):
        return view(sid)
    t0 = time.perf_counter()
    img = quality.decode(b64)
    q = quality.analyse(img)
    mot = quality.motion(s["prev_gray"], q["_gray"])
    s["prev_gray"] = q["_gray"]
    lm_list = landmarks.detect(q["_img"])
    h, w = img.shape[:2]
    ctx = {"L": {p["name"]: p for p in lm_list} if lm_list else None, "q": q, "motion": mot, "side": s["side"],
           "aspect": w / h, "state": s["state"]}
    ev = rules.evaluate(s["exam"], s["step"], ctx)
    del img, q["_img"], q["_gray"]  # drop pixels immediately
    lg = s["log"][s["step"]]
    lg["frames"] += 1
    s["frames"] += 1
    if ev["passed"]:
        s["streak"] += 1
    else:
        s["streak"] = 0
        lg["fail_frames"] += 1
        for c in ev["checks"]:
            if c["ok"] is False:
                lg["issues"][c["id"]] = lg["issues"].get(c["id"], 0) + 1
    if s["streak"] >= steps[s["step"]].get("hold", 1):
        lg["passed"], lg["how"] = True, "auto"
        _advance(s)
    out = {"quality": {k: v for k, v in q.items() if not k.startswith("_")}, "motion": round(mot, 4),
           "landmarks": [{"x": round(p["x"], 4), "y": round(p["y"], 4), "v": round(p["v"], 2)} for p in lm_list] if lm_list else None,
           "checks": ev["checks"], "ms": round((time.perf_counter() - t0) * 1000, 1), "detector": capabilities()["tier"]}
    return view(sid, out)


def manual(sid: str, confirmed: bool) -> dict[str, Any]:
    """Manual confirmation (manual steps, or any step in manual/no-camera mode)."""
    s = get(sid)
    if s["step"] < len(s["log"]) and confirmed:
        s["log"][s["step"]].update(passed=True, how="manual")
        _advance(s)
    return view(sid)


def _advance(s: dict[str, Any]) -> None:
    s["step"] += 1
    s["streak"] = 0


def score(s: dict[str, Any]) -> dict[str, Any]:
    """Procedure-compliance score: share of steps completed, split by how they were verified."""
    n = len(s["log"])
    auto = sum(1 for lg in s["log"] if lg["how"] == "auto")
    man = sum(1 for lg in s["log"] if lg["how"] == "manual")
    corrections = sum(len(lg["issues"]) for lg in s["log"])
    pct = round(100 * (auto + man) / n)
    return {"completed_pct": pct, "auto_verified": auto, "manual_confirmed": man, "steps": n, "corrections": corrections,
            "duration_s": round(time.time() - s["started"]),
            "note_ar": "النسبة تقيس الالتزام بخطوات الإجراء المرئية فقط، وليست قياسًا طبيًا."}


def finish(sid: str) -> dict[str, Any]:
    s = get(sid)
    out = {"exam": s["exam"], "side": s["side"], "mode": s["mode"], "score": score(s),
           "log": [{k: v for k, v in lg.items()} for lg in s["log"]]}
    _SESSIONS.pop(sid, None)
    return out
