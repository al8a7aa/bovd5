"""
BÖVD · assessment engine
================================
Turns validated readings into *status + explanation + recommended next step +
who to contact*. The engine NEVER produces a diagnosis.

Order of evaluation (microgravity rule 1):
  1. PERSONAL BASELINE – mean ± k·SD (k = 2, configurable) of the astronaut's
     pre-flight / early-flight readings. Outside the band ⇒ at least YELLOW
     ("differs from your baseline").
  2. EARTH REFERENCE RANGES – config/thresholds.json (red first, then yellow).
     A YELLOW inside the personal band may be softened to GREEN with a note
     (configurable); a RED is never softened.
  3. TREND RULES – 3 consecutive yellow sleep nights ⇒ RED; mood 3-day decline ⇒
     YELLOW; sharp mood drop + low sleep ⇒ RED; post-landing stand test.
  4. COMPOSITE SCORE 0–20 across indicators.
  5. "WHY" – hazard (NASA HRP five hazards), plain-language explanation,
     actions, who to contact, citations.

Standards alignment (designed in alignment with, not certified):
  * IEC 62304 class B software item; ISO 14971 risk controls R-01..R-06
    (see RISK_REGISTER.md) are implemented here.
  * ISO/IEC 22989 / 25059 – transparency: every output carries its inputs,
    rule and citation (explainability).
  * NASA-STD-3001 Vol. 1 – crew health monitoring intent.
"""
from __future__ import annotations

import statistics
from datetime import timedelta
from typing import Any

from . import config, fhir

LEVELS = ("green", "yellow", "red")
_RANK = {"green": 0, "yellow": 1, "red": 2}


def worst(*levels: str) -> str:
    """Return the most severe level."""
    return max(levels, key=lambda lv: _RANK[lv])


def _match(rule: dict[str, float], v: float) -> bool:
    op, ref = next(iter(rule.items()))
    return {"lt": v < ref, "le": v <= ref, "gt": v > ref, "ge": v >= ref}[op]


def earth_level(indicator: str, value: float) -> tuple[str, str]:
    """Earth-reference level and the rule text that fired."""
    ind = config.thresholds()["indicators"][indicator]
    for rule in ind.get("red_if", []):
        if _match(rule, value):
            return "red", _rule_txt(rule)
    for rule in ind.get("yellow_if", []):
        if _match(rule, value):
            return "yellow", _rule_txt(rule)
    return "green", "within default range"


def _rule_txt(rule: dict[str, float]) -> str:
    op, ref = next(iter(rule.items()))
    return f"value {dict(lt='<', le='≤', gt='>', ge='≥')[op]} {ref:g}"


# --------------------------------------------------------------- baseline
def baseline(history: list[dict[str, Any]], gravity_context: str = "iss") -> dict[str, Any] | None:
    """Personal baseline from FHIR Observations (oldest first).

    * Current context in 0 g → EARLY-FLIGHT baseline: the first ``window_days``
      of readings taken in any 0 g context (the body has already shifted fluid
      headward, so this is the astronaut's own "normal" in microgravity).
    * Current context in 1 g / partial g → PRE-FLIGHT baseline: readings flagged
      ``conditions.baseline`` or taken in ``earth_preflight``.
    Falls back to the other set when there are fewer than ``min_points``.
    """
    cfg = config.thresholds()["baseline"]
    ctxs = config.gravity()["contexts"]
    zero_g = {k for k, v in ctxs.items() if float(v["g"]) == 0.0}
    pre = [o for o in history if fhir.conditions_of(o).get("baseline") or fhir.gravity_of(o) == "earth_preflight"]
    flight = [o for o in history if fhir.gravity_of(o) in zero_g]
    if flight:
        t0 = fhir.parse_iso(flight[0]["effectiveDateTime"])
        flight = [o for o in flight if fhir.parse_iso(o["effectiveDateTime"]) < t0 + timedelta(days=cfg["window_days"])]
    order = [("early-flight (0 g)", flight), ("pre-flight", pre)]
    if gravity_context not in zero_g:
        order.reverse()
    pts: list[dict[str, Any]] = []
    source = ""
    for source, pts in order:  # noqa: B007 - source is used after the loop
        if len(pts) >= cfg["min_points"]:
            break
    else:
        return None
    vals = [fhir.value_of(o) for o in pts]
    mean = statistics.fmean(vals)
    sd = statistics.pstdev(vals) or max(abs(mean) * 0.02, 0.5)  # floor avoids zero-width band
    k = float(cfg["sd_multiplier"])
    return {"mean": round(mean, 2), "sd": round(sd, 2), "n": len(vals), "k": k,
            "low": round(mean - k * sd, 2), "high": round(mean + k * sd, 2), "source": source}


# ---------------------------------------------------------------- assess
def assess(indicator: str, value: float, history: list[dict[str, Any]],
           gravity_context: str = "iss", confidence: str = "high", cabin_kpa: float = 101.325) -> dict[str, Any]:
    """Full assessment of one value against baseline, Earth range and trends."""
    th = config.thresholds()
    ind = th["indicators"][indicator]
    notes: list[str] = []
    base = baseline(history, gravity_context)
    dev = False
    z = None
    if base is not None:
        z = round((value - base["mean"]) / base["sd"], 2) if base["sd"] else 0.0
        dev = not base["low"] <= value <= base["high"]
    e_level, e_rule = earth_level(indicator, value)
    if indicator == "cabin_co2":  # evidence-based: partial pressure at the actual cabin pressure
        from .physio import co2_level
        c = co2_level(value, cabin_kpa)
        e_level, e_rule = c["level"], f"ppCO2 {c['ppco2_mmhg']} mmHg at {c['cabin_kpa']} kPa (limit 3 mmHg ≈ {c['ppm_at_limit']} ppm)"
    level = e_level
    if dev:
        level = worst(level, "yellow")
        notes.append(f"differs from your personal baseline ({base['low']}–{base['high']} {ind['unit']}, z = {z})")  # type: ignore[index]
    elif base is not None and e_level == "yellow" and th["baseline"].get("soften_yellow_within_baseline"):
        level = "green"
        notes.append("Earth range is yellow but the value is inside your personal in-flight baseline")
    trend = trend_rules(indicator, value, history, base)
    if trend:
        level = worst(level, trend["level"])
        notes.append(trend["text"])
    if confidence == "low":
        notes.append("low confidence: measurement conditions incomplete – repeat under standard conditions")
    out = {
        "indicator": indicator, "label_en": ind["label_en"], "label_ar": ind["label_ar"],
        "value": value, "unit": ind["unit"], "level": level, "earth_level": e_level, "earth_rule": e_rule,
        "baseline": base, "baseline_deviation": dev, "z": z, "trend": trend, "notes": notes,
        "confidence": confidence, "gravity_context": gravity_context, "region": ind["region"],
    }
    out["why"] = explain(out)
    return out


def trend_rules(indicator: str, value: float, history: list[dict[str, Any]],
                base: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Trend rules from DEFAULT THRESHOLDS (sleep, mood).

    A night counts as a "yellow night" when it is Earth-red, or Earth-yellow AND
    below the personal baseline band (baseline first – rule 1).
    """
    ind = config.thresholds()["indicators"][indicator]
    vals = [fhir.value_of(o) for o in history][-6:] + [value]
    if indicator == "sleep_hours":
        n = int(ind["consecutive_yellow_to_red"])
        last = vals[-n:]

        def bad(v: float) -> bool:
            lv = earth_level("sleep_hours", v)[0]
            return lv == "red" or (lv == "yellow" and (base is None or v < base["low"]))

        if len(last) == n and all(bad(v) for v in last):
            return {"level": "red", "rule": "sleep_consecutive",
                    "text": f"{n} consecutive short nights – cumulative sleep debt"}
    if indicator == "mood":
        d = int(ind["trend_decline_days"])
        last = vals[-(d + 1):]
        if len(last) == d + 1 and all(last[i + 1] < last[i] for i in range(d)):
            return {"level": "yellow", "rule": "mood_decline", "text": f"mood declined {d} days in a row"}
        if len(vals) >= 2 and vals[-2] - value >= ind["sharp_drop"]:
            return {"level": "yellow", "rule": "mood_sharp_drop", "text": "sharp mood drop since last entry",
                    "needs_sleep_check": True}
    return None


def mood_sleep_combo(mood_assessment: dict[str, Any], last_sleep_h: float | None) -> dict[str, Any] | None:
    """RED when a sharp mood drop coincides with low sleep (< 6 h)."""
    t = mood_assessment.get("trend") or {}
    if t.get("rule") == "mood_sharp_drop" and last_sleep_h is not None and last_sleep_h < 6:
        return {"level": "red", "rule": "mood_drop_low_sleep",
                "text": f"sharp mood drop together with low sleep ({last_sleep_h:g} h)"}
    return None


def stand_test(seated_hr: float, seated_sys: float, stand_hr: float, stand_sys: float) -> dict[str, Any]:
    """Post-landing seated→stand test (microgravity rule 3)."""
    cfg = config.thresholds()["orthostatic_stand_test"]
    rise = stand_hr - seated_hr
    drop = seated_sys - stand_sys
    level = "green"
    reasons = []
    if rise > cfg["hr_rise_yellow"]:
        level = "yellow"
        reasons.append(f"HR rise {rise:g} bpm > {cfg['hr_rise_yellow']}")
    if drop > cfg["systolic_drop_yellow"]:
        level = "yellow"
        reasons.append(f"systolic drop {drop:g} mmHg > {cfg['systolic_drop_yellow']}")
    if stand_sys < 90:
        level = "red"
        reasons.append("standing systolic < 90 mmHg")
    res = {"indicator": "stand_test", "label_en": "Post-landing stand test", "label_ar": "اختبار الوقوف بعد الهبوط",
           "level": level, "hr_rise": rise, "systolic_drop": drop, "notes": reasons, "region": "heart",
           "value": rise, "unit": "bpm rise", "earth_level": level, "baseline": None, "trend": None,
           "confidence": "high", "gravity_context": "mars_surface"}
    res["why"] = explain(res, hazard_key="gravity", citations=cfg["citation"])
    return res


# -------------------------------------------------------------- composite
def composite(assessments: list[dict[str, Any]]) -> dict[str, Any]:
    """Composite concern score 0–20 (0 = all green)."""
    c = config.thresholds()["composite"]
    w = c["weights"]
    score = 0
    for a in assessments:
        score += int(w[a["level"]])
        if a.get("baseline_deviation"):
            score += int(w["baseline_dev"])
    score = min(score, 20)
    band = "green" if score <= c["bands"]["green_max"] else "yellow" if score <= c["bands"]["yellow_max"] else "red"
    if any(a["level"] == "red" for a in assessments):
        band = "red"
    return {"score": score, "max": 20, "band": band}


# ----------------------------------------------------------------- WHY
ACTIONS = {
    "green": {"en": ["Continue your routine and the scheduled measurements."],
              "ar": ["استمر في روتينك والقياسات المجدولة."], "contact": "none"},
    "yellow": {"en": ["Repeat the measurement under standard conditions (restrained, 5-min rest, same time).",
                      "Review today's countermeasures (fluids, exercise, sleep).",
                      "Inform the Crew Medical Officer at the next check-in."],
               "ar": ["أعد القياس في الظروف القياسية (مثبتًا، راحة 5 دقائق، نفس الوقت).",
                      "راجع الإجراءات الوقائية اليوم (السوائل، التمرين، النوم).",
                      "أبلغ الضابط الطبي للطاقم في المتابعة القادمة."], "contact": "CMO"},
    "red": {"en": ["Stop strenuous activity and stay restrained/seated.",
                   "Notify the Crew Medical Officer NOW.",
                   "Open the matching Smart Doctor protocol; the flight surgeon is notified via the delayed link."],
            "ar": ["أوقف النشاط المجهد وابقَ مثبتًا/جالسًا.",
                   "أبلغ الضابط الطبي للطاقم الآن.",
                   "افتح بروتوكول الطبيب الذكي المناسب؛ سيُبلَّغ الجراح الجوي عبر الوصلة المتأخرة."],
            "contact": "CMO → Flight surgeon"},
}
PROTOCOL_HINT = {"heart_rate": "chest_pain", "systolic": "post_landing_dizziness", "body_temp": "fever",
                 "glucose": "hypoglycemia", "sleep_hours": "insomnia", "radiation_pct": "radiation_exposure",
                 "cabin_co2": "headache_vision", "stand_test": "post_landing_dizziness",
                 "spe": "radiation_exposure", "vision": "headache_vision", "mood": "insomnia"}


def explain(a: dict[str, Any], hazard_key: str | None = None, citations: list[str] | None = None) -> dict[str, Any]:
    """Build the WHY panel: hazard, explanation, actions, contact, citations."""
    regions = config.load("body_regions")
    hz_key = hazard_key or regions["indicator_hazard"].get(a["indicator"], "environment")
    hz = regions["hazards"][hz_key]
    lvl = a["level"]
    base = a.get("baseline")
    parts_en = [f"{a['label_en']} = {a['value']:g} {a['unit']} → {lvl.upper()}."]
    parts_ar = [f"{a['label_ar']} = {a['value']:g} {a['unit']} ← {({'green': 'أخضر', 'yellow': 'أصفر', 'red': 'أحمر'})[lvl]}."]
    if base:
        parts_en.append(f"Your personal baseline ({base['source']}, n={base['n']}) is {base['low']}–{base['high']}.")
        parts_ar.append(f"خط أساسك الشخصي ({base['n']} قراءة) هو {base['low']}–{base['high']}.")
    else:
        parts_en.append("No personal baseline yet – Earth reference range used.")
        parts_ar.append("لا يوجد خط أساس شخصي بعد – استُخدم المدى الأرضي المرجعي.")
    parts_en.append(f"Earth reference: {a['earth_level']} ({a.get('earth_rule', '')}).")
    parts_ar.append(f"المرجع الأرضي: {a['earth_level']}.")
    parts_en += a.get("notes", [])
    cites = citations or config.thresholds()["indicators"].get(a["indicator"], {}).get("citation", [])
    act = ACTIONS[lvl]
    return {
        "hazard": {"key": hz_key, **hz},
        "explanation_en": " ".join(parts_en), "explanation_ar": " ".join(parts_ar),
        "actions_en": act["en"], "actions_ar": act["ar"], "contact": act["contact"],
        "protocol": PROTOCOL_HINT.get(a["indicator"]) if lvl != "green" else None,
        "citations": config.cite(list(cites)),
        "disclaimer": "Decision support only – not a diagnosis. Thresholds require flight-surgeon review.",
    }
