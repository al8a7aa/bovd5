"""
BÖVD · physiological & environmental simulation (evidence-bound)
================================================================
Two independent factors, never substituted for each other (brief §6 rule 7):

1. ATMOSPHERE (pressure / altitude / oxygen fraction) – published equations only:
   * U.S. Standard Atmosphere 1976 barometric formula (E-EQ-01), 0–20 km.
   * Inspired O2:  PIO2 = (PB − 47) · FiO2              (E-EQ-02, E-ATM-02 check: 128 mmHg)
   * Alveolar gas: PAO2 = PIO2 − PaCO2 / RQ              (E-EQ-02)
   * A–a gradient (normal) = (age + 10) / 4             (StatPearls, same source)
   * SaO2 from PaO2: Severinghaus 1979                   (E-EQ-03)
   The result is an ESTIMATE for a healthy, non-acclimatised adult with the stated
   PaCO2 and RQ – not a measurement.

2. GRAVITY / TIME IN FLIGHT – NO invented equations. The module only returns
   published findings (config/evidence.json) that apply to the selected phase,
   and, where a paper reports a mean change, applies that published range to the
   astronaut's own baseline as a RANGE, clearly labelled SIMULATED. Where no
   evidence exists for a phase (e.g. partial gravity, weeks 2–12 cardiac output),
   it says so (E-GAP-01) instead of interpolating.
"""
from __future__ import annotations

import math
from typing import Any

from . import config

# ---------------------------------------------------------------- constants (USSA 1976)
G0 = 9.80665            # m/s²
M_AIR = 0.0289644       # kg/mol
R_STAR = 8.3144598      # J/(mol·K)
#: (base geopotential height m, base pressure Pa, base temperature K, lapse K/m)
LAYERS = [(0.0, 101325.0, 288.15, -0.0065), (11000.0, 22632.1, 216.65, 0.0), (20000.0, 5474.89, 216.65, 0.001)]
PH2O_37C = 47.0         # mmHg, water vapour at 37 °C (E-EQ-02)
PA_PER_MMHG = 133.322368
PSI_TO_KPA = 6.894757

#: Cabin presets – every value traceable to evidence.json
CABINS: dict[str, dict[str, Any]] = {
    "sea_level": {"label_ar": "مستوى سطح البحر (الأرض)", "kpa": 101.325, "fio2": 0.2095, "evidence": "E-EQ-01"},
    "iss": {"label_ar": "محطة الفضاء الدولية 14.7 psia / 21%", "kpa": 14.7 * PSI_TO_KPA, "fio2": 0.21, "evidence": "E-ATM-01"},
    "exploration": {"label_ar": "جو الاستكشاف (أرتميس) 8.2 psia / 34%", "kpa": 8.2 * PSI_TO_KPA, "fio2": 0.34, "evidence": "E-ATM-02"},
    "emu": {"label_ar": "بدلة السير الفضائي 4.3 psia / 100%", "kpa": 4.3 * PSI_TO_KPA, "fio2": 1.0, "evidence": "E-ATM-04"},
}


def evidence() -> list[dict[str, Any]]:
    return list(config.load("evidence")["entries"])


def ev(eid: str) -> dict[str, Any]:
    for e in evidence():
        if e["id"] == eid:
            return e
    raise KeyError(eid)


# ---------------------------------------------------------------- atmosphere
def pressure_at_altitude(h_m: float) -> float:
    """Static pressure (Pa) at geopotential altitude h (0–32 km), USSA 1976."""
    if not -610 <= h_m <= 32000:
        raise ValueError("altitude outside 0–32 km model range")
    base = LAYERS[0]
    for layer in LAYERS:
        if h_m >= layer[0]:
            base = layer
    hb, pb, tb, lb = base
    if lb == 0.0:
        return pb * math.exp(-G0 * M_AIR * (h_m - hb) / (R_STAR * tb))
    return pb * (tb / (tb + lb * (h_m - hb))) ** (G0 * M_AIR / (R_STAR * lb))


def pio2(pb_mmhg: float, fio2: float) -> float:
    """Inspired O2 partial pressure (mmHg)."""
    return max(0.0, (pb_mmhg - PH2O_37C) * fio2)


def pao2(pio2_mmhg: float, paco2: float = 40.0, rq: float = 0.8) -> float:
    """Alveolar O2 (mmHg) – abbreviated alveolar gas equation."""
    return pio2_mmhg - paco2 / rq


def severinghaus(po2: float) -> float:
    """O2 saturation (0–1) from PO2 (mmHg), Severinghaus 1979."""
    if po2 <= 0:
        return 0.0
    return 1.0 / (23400.0 / (po2 ** 3 + 150.0 * po2) + 1.0)


def aa_gradient(age: float) -> float:
    """Normal alveolar–arterial gradient estimate (mmHg) = (age + 10) / 4."""
    return (age + 10.0) / 4.0


def oxygenation(pb_kpa: float, fio2: float, paco2: float = 40.0, rq: float = 0.8, age: float = 40.0) -> dict[str, Any]:
    """Full chain PB → PIO2 → PAO2 → PaO2 → SaO2 (estimate)."""
    if not 0.05 <= fio2 <= 1.0:
        raise ValueError("FiO2 must be 0.05–1.0")
    pb = pb_kpa * 1000 / PA_PER_MMHG
    pi = pio2(pb, fio2)
    pa = pao2(pi, paco2, rq)
    art = max(0.0, pa - aa_gradient(age))
    sat = severinghaus(art)
    normoxic = 139 <= pi <= 168
    return {"pb_mmhg": round(pb, 1), "pb_kpa": round(pb_kpa, 2), "fio2": fio2, "pio2": round(pi, 1),
            "pao2": round(pa, 1), "pao2_arterial_est": round(art, 1), "sao2_est_pct": round(100 * sat, 1),
            "pio2_normoxic": normoxic, "assumptions_ar": f"PaCO2 = {paco2:g} ملم زئبق ثابت، RQ = {rq:g}، العمر {age:g} لحساب فرق A–a، "
            "شخص سليم غير متأقلم. في الارتفاعات يزداد التنفس فينخفض PaCO2 فيكون التشبع الفعلي أعلى من هذا التقدير.",
            "kind": "SIMULATED", "evidence": ["E-EQ-01", "E-EQ-02", "E-EQ-03", "E-ATM-03"]}


def altitude_curve(fio2: float = 0.2095, paco2: float = 40.0, max_m: int = 8000, step: int = 500) -> list[dict[str, float]]:
    out = []
    for h in range(0, max_m + 1, step):
        pb_kpa = pressure_at_altitude(h) / 1000
        o = oxygenation(pb_kpa, fio2, paco2)
        out.append({"alt_m": h, "pb_kpa": round(pb_kpa, 2), "pio2": o["pio2"], "sao2": o["sao2_est_pct"]})
    return out


def ppco2(ppm: float, cabin_kpa: float) -> float:
    """CO2 partial pressure (mmHg) of a ppm (volume) reading at a cabin pressure."""
    return ppm * 1e-6 * cabin_kpa * 1000 / PA_PER_MMHG


def co2_level(ppm: float, cabin_kpa: float) -> dict[str, Any]:
    """Evidence-based CO2 status: > 3 mmHg red (E-CO2-01), ≥ 2.5 mmHg yellow (E-CO2-02, 7-day guidance)."""
    p = ppco2(ppm, cabin_kpa)
    lvl = "red" if p > 3.0 else "yellow" if p >= 2.5 else "green"
    return {"ppco2_mmhg": round(p, 2), "level": lvl, "cabin_kpa": round(cabin_kpa, 2),
            "ppm_at_limit": round(3.0 / (cabin_kpa * 1000 / PA_PER_MMHG) * 1e6), "evidence": ["E-CO2-01", "E-CO2-02"]}


# ---------------------------------------------------------------- gravity / time in flight
def _r(lo: float, hi: float) -> list[float]:
    return [round(lo, 1), round(hi, 1)]


def gravity_effects(phase: str, day: float, mission_days: float = 180, baseline: dict[str, float] | None = None,
                    gravity: str = "micro") -> dict[str, Any]:
    """Evidence-bound expectations for a mission phase.

    phase: 'pre' | 'flight' | 'return';  day = flight day (flight) or day after landing (return).
    gravity: 'micro' | 'partial'.  baseline: personal values (sys, dia, hr, map) for applying published deltas.
    """
    b = baseline or {}
    items: list[dict[str, Any]] = []

    def add(key: str, label_ar: str, status: str, eids: list[str], value: str = "", sim_range: list[float] | None = None,
            unit: str = "") -> None:
        items.append({"key": key, "label_ar": label_ar, "status": status, "value": value, "unit": unit,
                      "simulated_range": sim_range, "evidence": eids})

    if gravity == "partial" and phase == "flight":
        return {"phase": phase, "day": day, "gravity": gravity, "items": [], "gap": ev("E-GAP-01"),
                "note_ar": "لا توجد بيانات بشرية كافية عن الجاذبية الجزئية؛ لا يحسب التطبيق أي قيم متوقعة لها."}
    if phase == "pre":
        add("baseline", "خط الأساس قبل الرحلة", "evidence", [], "القياس المرجعي الشخصي – لا تغيّر متوقع", None)
    elif phase == "flight":
        add("fluid_shift", "انتقال السوائل نحو الرأس", "evidence", ["E-CV-01"], "≈ 2", None, "L")
        if day <= 14:
            add("plasma", "حجم البلازما", "evidence", ["E-CV-06"], "−10 إلى −17 خلال الأسبوعين الأولين", None, "%")
            add("cardiac_output", "النتاج القلبي (رحلة قصيرة/حاد)", "evidence", ["E-CV-02"], "+18 إلى +26", None, "%")
        if 14 < day < 90:
            add("cardiac_output", "النتاج القلبي", "gap", [], "لا توجد في سجل الأدلة قيمة منشورة محددة لهذه المرحلة (الأسبوع 2 إلى الشهر 3)")
        if day >= 90:
            add("cardiac_output", "النتاج القلبي (3–6 أشهر)", "evidence", ["E-CV-03"], "+41 ± 9", None, "%")
            if "sys" in b and "dia" in b:
                add("bp_sys_24h", "ضغط الدم الانقباضي المتوقع (24 ساعة)", "simulated", ["E-CV-04"],
                    "خط الأساس − 8 إلى 10", _r(b["sys"] - 10, b["sys"] - 8), "mmHg")
                add("bp_dia_24h", "ضغط الدم الانبساطي المتوقع (24 ساعة)", "simulated", ["E-CV-04"],
                    "خط الأساس − 8 إلى 10", _r(b["dia"] - 10, b["dia"] - 8), "mmHg")
            else:
                add("bp_24h", "ضغط الدم على مدار 24 ساعة", "evidence", ["E-CV-04"], "−8 إلى −10", None, "mmHg")
            add("hr", "معدل ضربات القلب", "evidence", ["E-CV-05"], "دون تغيّر دال في المتوسط",
                _r(b["hr"], b["hr"]) if "hr" in b else None, "bpm")
            if day > 180:
                items[-1]["note_ar"] = "البيانات من 3–6 أشهر؛ ما بعد 6 أشهر غير موثق في هذه الدراسة."
        months = day / 30.4375
        spine = _r(0.9 * months, 0.9 * months)
        hip = _r(1.4 * months, 1.5 * months)
        add("bone_spine", "فقد كثافة عظم العمود الفقري (تراكمي)", "simulated", ["E-BONE-01", "E-BONE-02"], "0.9% شهريًا", spine, "%")
        add("bone_hip", "فقد كثافة عظم الورك (تراكمي)", "simulated", ["E-BONE-01", "E-BONE-02"], "1.4–1.5% شهريًا", hip, "%")
        if day > 183:
            for it in items[-2:]:
                it["note_ar"] = "استقراء خطي بعد 6 أشهر – غير مثبت؛ تقرير ناسا يذكر أنه غير معروف إن كان الفقد يستقر."
                it["status"] = "extrapolated"
        add("urine_ca", "إطراح الكالسيوم في البول", "evidence", ["E-CA-01"], "حتى +50", None, "%")
        add("sleep", "مدة النوم المتوقعة (متوسط المحطة)", "evidence", ["E-SLEEP-01", "E-SLEEP-02"], "6.09", None, "ساعة")
    elif phase == "return":
        if mission_days <= 18:
            add("oi", "خطر عدم تحمّل الانتصاب بعد الهبوط", "evidence", ["E-OI-01"], "20–30", None, "% من الرواد")
        elif mission_days >= 120:
            add("oi", "خطر عدم تحمّل الانتصاب بعد الهبوط", "evidence", ["E-OI-02"], "83 (5 من 6 – عينة صغيرة)", None, "% من الرواد")
        else:
            add("oi", "خطر عدم تحمّل الانتصاب", "gap", ["E-OI-01", "E-OI-02"],
                "لا توجد نسبة منشورة لمدة هذه الرحلة بين 18 و120 يومًا في سجل الأدلة")
        if day > 3:
            items[-1]["note_ar"] = "الأرقام تخص يوم الهبوط؛ تقل الأعراض عادة خلال الأيام الأولى بعد العودة."
        months = mission_days / 30.4375
        add("bone_hip_return", "فقد كثافة الورك المتراكم عند العودة", "simulated", ["E-BONE-01"], "1.4–1.5% × عدد الأشهر",
            _r(1.4 * months, 1.5 * months), "%")
    return {"phase": phase, "day": day, "mission_days": mission_days, "gravity": gravity, "items": items,
            "kind": "SIMULATED – published group means applied to a personal baseline; not an individual prediction",
            "disclaimer_ar": "القيم المحاكاة تطبّق متوسطات منشورة لمجموعات صغيرة على خط أساسك؛ ليست قياسًا طبيًا ولا تنبؤًا فرديًا. "
                             "لا يتأثر كل الرواد بالطريقة نفسها."}


def bone_projection(mission_days: int, step: int = 15) -> list[dict[str, Any]]:
    """Cumulative hip/spine aBMD loss range per E-BONE-01; beyond 183 d flagged as extrapolation."""
    out = []
    for d in range(0, mission_days + 1, step):
        m = d / 30.4375
        out.append({"day": d, "spine": round(0.9 * m, 2), "hip_lo": round(1.4 * m, 2), "hip_hi": round(1.5 * m, 2),
                    "evidenced": d <= 183})
    return out


def phase_comparison(baseline: dict[str, float]) -> list[dict[str, Any]]:
    """Pre / early flight / 3–6 months / landing day for the cardiovascular chart."""
    rows = [{"phase_ar": "قبل الرحلة", "co_pct": [0, 0], "bp_delta": [0, 0], "oi_pct": None, "evidence": []},
            {"phase_ar": "بداية الرحلة", "co_pct": [18, 26], "bp_delta": None, "oi_pct": None, "evidence": ["E-CV-02"]},
            {"phase_ar": "3–6 أشهر", "co_pct": [32, 50], "bp_delta": [-10, -8], "oi_pct": None, "evidence": ["E-CV-03", "E-CV-04"]},
            {"phase_ar": "يوم الهبوط (رحلة طويلة)", "co_pct": None, "bp_delta": None, "oi_pct": [83, 83], "evidence": ["E-OI-02"]}]
    if baseline.get("sys"):
        for r in rows:
            r["sys_range"] = [baseline["sys"] + r["bp_delta"][0], baseline["sys"] + r["bp_delta"][1]] if r["bp_delta"] else None
    return rows
