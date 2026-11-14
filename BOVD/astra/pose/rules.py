"""
Posture rules per exam (extensible registry). Each check returns ok / not ok / unknown plus Arabic and
English guidance and optional overlay guides (normalised coordinates).

Geometric assumptions are heuristics, documented here and in the UI:
  * "Heart level" ≈ shoulder line + 0.30 × (hip − shoulder) distance (mid-sternum approximation).
  * Upright = shoulder-midpoint→hip-midpoint line within 15° of vertical.
  * Thresholds are starting values to be tuned with the evaluation script (scripts/pose_eval.py).
These checks verify VISIBLE posture only; they do not measure any vital sign.
"""
from __future__ import annotations

import math
from typing import Any, Callable

Check = Callable[[dict[str, Any]], dict[str, Any]]
VIS = 0.5


def _p(ctx: dict[str, Any], name: str) -> dict[str, float] | None:
    lm = ctx["L"].get(name) if ctx.get("L") else None
    return lm if lm and lm.get("v", 1) >= VIS else None


def _xy(ctx: dict[str, Any], p: dict[str, float]) -> tuple[float, float]:
    return p["x"] * ctx.get("aspect", 4 / 3), p["y"]


def _mid(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float]:
    return (a[0] + b[0]) / 2, (a[1] + b[1]) / 2


def angle(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
    """Angle ABC in degrees."""
    v1 = (a[0] - b[0], a[1] - b[1])
    v2 = (c[0] - b[0], c[1] - b[1])
    n = math.hypot(*v1) * math.hypot(*v2)
    if n == 0:
        return 0.0
    return math.degrees(math.acos(max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / n))))


def res(ok: bool | None, ar: str, en: str, guides: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {"ok": ok, "ar": ar, "en": en, "guides": guides or []}


def _need(ctx: dict[str, Any], *names: str) -> list[dict[str, float]] | None:
    pts = [_p(ctx, n) for n in names]
    return None if any(p is None for p in pts) else pts  # type: ignore[return-value]


def _torso(ctx: dict[str, Any]) -> dict[str, Any] | None:
    pts = _need(ctx, "l_shoulder", "r_shoulder", "l_hip", "r_hip")
    if not pts:
        return None
    ls, rs, lh, rh = (_xy(ctx, p) for p in pts)
    sm, hm = _mid(ls, rs), _mid(lh, rh)
    length = math.hypot(hm[0] - sm[0], hm[1] - sm[1])
    return {"ls": ls, "rs": rs, "sm": sm, "hm": hm, "len": length, "heart_y": sm[1] + 0.30 * (hm[1] - sm[1])}


# ----------------------------------------------------------------- checks
def c_light(ctx: dict[str, Any]) -> dict[str, Any]:
    q = ctx["q"]
    if q.get("too_dark"):
        return res(False, "الإضاءة ضعيفة جدًا – زد الإضاءة أو اقترب من مصدر الضوء", "Too dark – add light")
    if q.get("too_bright"):
        return res(False, "الإضاءة ساطعة جدًا – ابتعد عن مصدر الضوء المباشر", "Too bright – avoid direct light")
    if q.get("blurry"):
        return res(False, "الصورة غير واضحة – ثبّت الجهاز", "Image blurry – steady the device")
    return res(True, "الإضاءة مناسبة" + (" (حُسّنت الصورة تلقائيًا)" if q.get("enhanced") else ""), "Lighting OK")


def c_upper_body(ctx: dict[str, Any]) -> dict[str, Any]:
    if not ctx.get("L"):
        return res(False, "لم يُكتشف جسم – اجلس أمام الكاميرا بحيث يظهر الجزء العلوي", "No body detected")
    if _need(ctx, "l_shoulder", "r_shoulder", "l_elbow", "r_elbow", "l_hip", "r_hip") is None:
        return res(False, "أظهر الكتفين والمرفقين والوركين في الإطار – ابتعد قليلًا", "Show shoulders, elbows and hips",
                   [{"type": "box", "x": 0.15, "y": 0.05, "w": 0.7, "h": 0.9, "state": "hint"}])
    return res(True, "الجزء العلوي من الجسم ظاهر", "Upper body visible")


def c_centered(ctx: dict[str, Any]) -> dict[str, Any]:
    t = _torso(ctx)
    if not t:
        return res(None, "—", "—")
    x = t["sm"][0] / ctx.get("aspect", 4 / 3)
    if x < 0.3:
        return res(False, "تحرّك نحو وسط الإطار", "Move toward the centre", [{"type": "arrow", "from": [x, 0.5], "to": [0.5, 0.5]}])
    if x > 0.7:
        return res(False, "تحرّك نحو وسط الإطار", "Move toward the centre", [{"type": "arrow", "from": [x, 0.5], "to": [0.5, 0.5]}])
    return res(True, "أنت في وسط الإطار", "Centred")


def c_upright(ctx: dict[str, Any]) -> dict[str, Any]:
    t = _torso(ctx)
    if not t:
        return res(None, "لا يمكن تقدير استقامة الجذع – أظهر الوركين", "Hips not visible")
    dx, dy = t["hm"][0] - t["sm"][0], t["hm"][1] - t["sm"][1]
    tilt = abs(math.degrees(math.atan2(dx, dy)))
    a = ctx.get("aspect", 4 / 3)
    g = [{"type": "line", "a": [t["sm"][0] / a, t["sm"][1]], "b": [t["hm"][0] / a, t["hm"][1]], "state": "ok" if tilt < 15 else "bad"}]
    if tilt >= 15:
        return res(False, f"اعتدل في جلستك – الجذع مائل {tilt:.0f}°", f"Sit upright – trunk tilted {tilt:.0f}°", g)
    return res(True, "الجذع مستقيم", "Trunk upright", g)


def c_shoulders_level(ctx: dict[str, Any]) -> dict[str, Any]:
    t = _torso(ctx)
    if not t:
        return res(None, "—", "—")
    ang = abs(math.degrees(math.atan2(t["rs"][1] - t["ls"][1], t["rs"][0] - t["ls"][0])))
    ang = min(ang, 180 - ang)
    if ang >= 8:
        return res(False, "أرخِ كتفيك واجعلهما في مستوى واحد", "Level your shoulders")
    return res(True, "الكتفان متوازيان", "Shoulders level")


def c_legs_uncrossed(ctx: dict[str, Any]) -> dict[str, Any]:
    pts = _need(ctx, "l_hip", "r_hip", "l_knee", "r_knee")
    if not pts:
        return res(None, "الساقان غير ظاهرتين – تحقق يدويًا من عدم تقاطعهما", "Legs not visible – confirm manually")
    lh, rh, lk, rk = (p["x"] for p in pts)
    if (lh - rh) * (lk - rk) < 0:
        return res(False, "لا تضع ساقًا فوق الأخرى", "Uncross your legs")
    return res(True, "الساقان غير متقاطعتين", "Legs uncrossed")


def _side(ctx: dict[str, Any]) -> str:
    return "l" if ctx.get("side", "left") == "left" else "r"


def c_arm_heart_level(ctx: dict[str, Any]) -> dict[str, Any]:
    s = _side(ctx)
    t = _torso(ctx)
    pts = _need(ctx, f"{s}_shoulder", f"{s}_elbow")
    if not t or not pts:
        return res(False, "أظهر ذراع القياس كاملة للكاميرا", "Show the cuff arm")
    sh, el = (_xy(ctx, p) for p in pts)
    mid_y = (sh[1] + el[1]) / 2
    dev = (mid_y - t["heart_y"]) / max(t["len"], 1e-6)
    a = ctx.get("aspect", 4 / 3)
    g = [{"type": "band", "y": t["heart_y"], "h": 0.15 * t["len"], "label": "مستوى القلب", "state": "ok" if abs(dev) <= 0.15 else "bad"},
         {"type": "box", "x": min(sh[0], el[0]) / a - 0.04, "y": min(sh[1], el[1]), "w": abs(sh[0] - el[0]) / a + 0.08,
          "h": abs(el[1] - sh[1]), "state": "hint", "label": "موضع الكفة"}]
    if dev > 0.15:
        return res(False, "ارفع ذراعك قليلًا: منتصف العضد يجب أن يكون بمستوى القلب – استخدم مسندًا", "Raise the arm to heart level", g)
    if dev < -0.15:
        return res(False, "اخفض ذراعك قليلًا إلى مستوى القلب", "Lower the arm to heart level", g)
    return res(True, "الذراع بمستوى القلب", "Arm at heart level", g)


def c_forearm_supported(ctx: dict[str, Any]) -> dict[str, Any]:
    s = _side(ctx)
    t = _torso(ctx)
    pts = _need(ctx, f"{s}_shoulder", f"{s}_elbow", f"{s}_wrist")
    if not t or not pts:
        return res(None, "أظهر الساعد واليد", "Show forearm")
    sh, el, wr = (_xy(ctx, p) for p in pts)
    ang = angle(sh, el, wr)
    drop = abs(wr[1] - el[1]) / max(t["len"], 1e-6)
    if not 60 <= ang <= 150:
        return res(False, f"اثنِ المرفق قليلًا وأرخِ الذراع (الزاوية الآن {ang:.0f}°)", f"Relax and slightly bend the elbow ({ang:.0f}°)")
    if drop > 0.35:
        return res(False, "اجعل الساعد مسنودًا أفقيًا تقريبًا", "Support the forearm roughly horizontally")
    return res(True, "الساعد مسنود والمرفق مثني قليلًا", "Forearm supported")


def c_hand_heart(ctx: dict[str, Any]) -> dict[str, Any]:
    s = _side(ctx)
    t = _torso(ctx)
    w = _p(ctx, f"{s}_wrist")
    if not t or not w:
        return res(False, "أظهر اليد التي عليها جهاز الإصبع", "Show the oximeter hand")
    dev = (_xy(ctx, w)[1] - t["heart_y"]) / max(t["len"], 1e-6)
    g = [{"type": "band", "y": t["heart_y"], "h": 0.2 * t["len"], "label": "مستوى القلب", "state": "ok" if abs(dev) <= 0.25 else "bad"}]
    if abs(dev) > 0.25:
        return res(False, "ضع اليد مسنودة قرب مستوى القلب", "Rest the hand near heart level", g)
    return res(True, "اليد قرب مستوى القلب", "Hand at heart level", g)


def c_still(ctx: dict[str, Any]) -> dict[str, Any]:
    m = ctx.get("motion", 0.0)
    if m > 0.025:
        return res(False, "ابقَ ساكنًا أثناء القياس", "Stay still")
    return res(True, "ثابت", "Still")


def c_face(ctx: dict[str, Any]) -> dict[str, Any]:
    pts = _need(ctx, "nose", "l_eye", "r_eye")
    if not pts:
        return res(False, "وجّه وجهك نحو الشاشة بحيث تظهر العينان", "Face the screen")
    if not 0.3 <= pts[0]["x"] <= 0.7:
        return res(False, "اجعل وجهك في وسط الإطار", "Centre your face")
    return res(True, "الوجه ظاهر في الوسط", "Face centred")


def c_head_level(ctx: dict[str, Any]) -> dict[str, Any]:
    pts = _need(ctx, "l_eye", "r_eye")
    if not pts:
        return res(None, "—", "—")
    a, b = (_xy(ctx, p) for p in pts)
    ang = abs(math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])))
    ang = min(ang, 180 - ang)
    if ang >= 8:
        return res(False, "اجعل رأسك مستقيمًا (لا تمِل)", "Keep your head level")
    return res(True, "الرأس مستقيم", "Head level")


def _face_scale(ctx: dict[str, Any]) -> float | None:
    pts = _need(ctx, "l_shoulder", "r_shoulder")
    if not pts:
        return None
    a, b = (_xy(ctx, p) for p in pts)
    return math.hypot(a[0] - b[0], a[1] - b[1])


def c_distance_stable(ctx: dict[str, Any]) -> dict[str, Any]:
    st = ctx["state"]
    sc = _face_scale(ctx)
    if sc is None:
        return res(None, "—", "—")
    ref = st.setdefault("ref_scale", sc)
    r = sc / ref
    if r > 1.15:
        return res(False, "اقتربت من الشاشة – عُد إلى مسافة الاختبار", "Too close – return to test distance")
    if r < 0.87:
        return res(False, "ابتعدت عن الشاشة – عُد إلى مسافة الاختبار", "Too far – return to test distance")
    return res(True, "المسافة ثابتة", "Distance stable")


def _covered(ctx: dict[str, Any], eye: str) -> dict[str, Any]:
    e = _p(ctx, f"{eye}_eye")
    scale = _face_scale(ctx) or 0.3
    hands = [p for p in (_p(ctx, "l_index"), _p(ctx, "r_index"), _p(ctx, "l_wrist"), _p(ctx, "r_wrist")) if p]
    if e is None:
        near = bool(hands)  # an occluded eye is often reported with low visibility
    else:
        ex, ey = _xy(ctx, e)
        near = any(math.hypot(_xy(ctx, h)[0] - ex, _xy(ctx, h)[1] - ey) < 0.45 * scale for h in hands)
    label = "اليسرى" if eye == "l" else "اليمنى"
    if not near:
        return res(False, f"غطِّ عينك {label} براحة يدك (دون ضغط)", f"Cover your {'left' if eye == 'l' else 'right'} eye")
    return res(True, f"العين {label} مغطاة", "Eye covered")


def c_cover_left(ctx: dict[str, Any]) -> dict[str, Any]:
    return _covered(ctx, "l")


def c_cover_right(ctx: dict[str, Any]) -> dict[str, Any]:
    return _covered(ctx, "r")


def _knee_angle(ctx: dict[str, Any]) -> float | None:
    for s in ("l", "r"):
        pts = _need(ctx, f"{s}_hip", f"{s}_knee", f"{s}_ankle")
        if pts:
            return angle(*(_xy(ctx, p) for p in pts))
    return None


def c_seated(ctx: dict[str, Any]) -> dict[str, Any]:
    k = _knee_angle(ctx)
    if k is None:
        return res(False, "أظهر الورك والركبة والكاحل في الإطار (الكاميرا من الجانب أفضل)", "Show hip, knee and ankle")
    if k > 130:
        return res(False, "اجلس أولًا لمدة 5 دقائق قبل الاختبار", "Sit down first")
    return res(True, f"وضعية الجلوس (زاوية الركبة {k:.0f}°)", "Seated")


def c_standing(ctx: dict[str, Any]) -> dict[str, Any]:
    k = _knee_angle(ctx)
    if k is None:
        return res(False, "أظهر الساقين كاملتين", "Show the legs")
    if k < 160:
        return res(False, "قف ببطء مع وجود مرافق، وافرد ركبتيك", "Stand up slowly with a spotter")
    return res(True, "واقف", "Standing")


CHECKS: dict[str, Check] = {
    "light": c_light, "upper_body": c_upper_body, "centered": c_centered, "upright": c_upright,
    "shoulders_level": c_shoulders_level, "legs_uncrossed": c_legs_uncrossed, "arm_heart_level": c_arm_heart_level,
    "forearm_supported": c_forearm_supported, "hand_heart": c_hand_heart, "still": c_still, "face": c_face,
    "head_level": c_head_level, "distance_stable": c_distance_stable, "cover_left": c_cover_left,
    "cover_right": c_cover_right, "seated": c_seated, "standing": c_standing,
}

# --------------------------------------------------------------- exams (protocol registry)
EXAMS: dict[str, dict[str, Any]] = {
    "blood_pressure": {"title_ar": "قياس ضغط الدم والنبض", "title_en": "Blood pressure & pulse", "anim": "bp", "steps": [
        {"id": "frame", "ar": "اجلس أمام الكاميرا ليظهر الجزء العلوي من جسمك", "checks": ["light", "upper_body", "centered"], "hold": 4},
        {"id": "posture", "ar": "اجلس مستقيمًا، الظهر مسنود، والساقان غير متقاطعتين", "checks": ["upright", "shoulders_level", "legs_uncrossed"], "hold": 6},
        {"id": "arm", "ar": "ضع ذراع القياس مسنودة بحيث يكون العضد بمستوى القلب", "checks": ["arm_heart_level", "forearm_supported"], "hold": 6},
        {"id": "cuff", "ar": "لفّ الكفة على العضد العاري كما في تعليمات جهازك، ثم أكّد", "manual": True, "checks": ["arm_heart_level"]},
        {"id": "measure", "ar": "ابدأ القياس وابقَ ساكنًا دون كلام حتى ينتهي", "checks": ["upright", "arm_heart_level", "still"], "hold": 10},
    ]},
    "spo2": {"title_ar": "تشبع الأكسجين بجهاز الإصبع", "title_en": "Pulse oximetry", "anim": "spo2", "steps": [
        {"id": "frame", "ar": "اجلس أمام الكاميرا ليظهر الجزء العلوي ويداك", "checks": ["light", "upper_body"], "hold": 4},
        {"id": "hand", "ar": "ضع الجهاز على الإصبع واجعل اليد مسنودة قرب مستوى القلب", "checks": ["hand_heart", "upright"], "hold": 6},
        {"id": "still", "ar": "ابقَ ساكنًا حتى تستقر القراءة", "checks": ["hand_heart", "still"], "hold": 12},
    ]},
    "temperature": {"title_ar": "قياس الحرارة", "title_en": "Temperature", "anim": "temp", "steps": [
        {"id": "frame", "ar": "اجلس أمام الكاميرا", "checks": ["light", "upper_body"], "hold": 4},
        {"id": "still", "ar": "ضع مقياس الحرارة حسب تعليماته وابقَ ساكنًا", "checks": ["upright", "still"], "hold": 10},
    ]},
    "vision": {"title_ar": "فحص حدة البصر", "title_en": "Visual acuity", "anim": "vision", "steps": [
        {"id": "face", "ar": "اجلس على مسافة الاختبار وانظر إلى الشاشة", "checks": ["light", "face", "head_level"], "hold": 5},
        {"id": "distance", "ar": "ثبّت المسافة – سنراقب أي اقتراب أو ابتعاد", "checks": ["distance_stable", "head_level"], "hold": 5},
        {"id": "left", "ar": "غطِّ العين اليسرى واقرأ اللوحة", "checks": ["cover_left", "distance_stable"], "hold": 5},
        {"id": "right", "ar": "الآن غطِّ العين اليمنى واقرأ اللوحة", "checks": ["cover_right", "distance_stable"], "hold": 5},
    ]},
    "stand_test": {"title_ar": "اختبار الجلوس ← الوقوف بعد الهبوط", "title_en": "Seated → stand test", "anim": "stand", "steps": [
        {"id": "seated", "ar": "اجلس مستقيمًا (الكاميرا من الجانب)", "checks": ["light", "seated"], "hold": 6},
        {"id": "spotter", "ar": "تأكد من وجود مرافق بجانبك قبل الوقوف، ثم أكّد", "manual": True, "checks": []},
        {"id": "stand", "ar": "قف ببطء", "checks": ["standing"], "hold": 6},
        {"id": "hold", "ar": "ابقَ واقفًا ساكنًا؛ توقف واجلس فورًا إن شعرت بدوار", "checks": ["standing", "still"], "hold": 10},
    ]},
}


def evaluate(exam: str, step_i: int, ctx: dict[str, Any]) -> dict[str, Any]:
    step = EXAMS[exam]["steps"][step_i]
    results = []
    for cid in step["checks"]:
        r = CHECKS[cid](ctx)
        results.append({"id": cid, **r})
    known = [r for r in results if r["ok"] is not None]
    passed = bool(known) and all(r["ok"] for r in known) if not step.get("manual") else False
    return {"step": step["id"], "checks": results, "passed": passed}
