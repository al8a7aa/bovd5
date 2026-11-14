"""
BÖVD · SYNTHETIC data generator
=======================================
Every value produced here carries provenance ``SYNTHETIC (<scenario>)`` and is
shown with a SYNTHETIC badge in the UI. Synthetic values are NEVER presented as
real readings (ISO 14971 risk R-15 "synthetic data mistaken for real").

Calibration (order-of-magnitude, from the cited literature; review needed):
  * sleep in flight ≈ 6 h/night on average (barger_2014);
  * headward fluid shift: slightly lower in-flight HR/BP vs pre-flight
    (hrp_oi_2015, nasa_cv_risk);
  * post-landing orthostatic response: HR rise and systolic drop on standing
    (hrp_oi_2015);
  * urinary calcium rises during flight as bone is resorbed (smith_1999, smith_2012);
  * ISS dose rate of a fraction of a mSv/day; deep space higher (george_2024).

Scenarios (PART 2): normal_0g, orthostatic_mars_landing, sleep_debt,
behavioral_decline, crew_conflict, solar_particle_event, rising_calcium,
sans_progression, fever, co2_buildup.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Any

from . import fhir, service
from .features import crew, radiation, urine, vision, voice
from .storage import Store

SCENARIOS = {
    "normal_0g": {"en": "Normal 0 g day", "ar": "يوم عادي في انعدام الجاذبية"},
    "orthostatic_mars_landing": {"en": "Orthostatic intolerance after Mars landing", "ar": "عدم تحمل الانتصاب بعد الهبوط على المريخ"},
    "sleep_debt": {"en": "5-night sleep debt", "ar": "دين نوم لخمس ليالٍ"},
    "behavioral_decline": {"en": "Behavioral decline in isolation", "ar": "تراجع سلوكي في العزلة"},
    "crew_conflict": {"en": "Crew conflict", "ar": "خلاف بين الطاقم"},
    "solar_particle_event": {"en": "Solar particle event", "ar": "عاصفة جسيمات شمسية"},
    "rising_calcium": {"en": "Rising urinary calcium", "ar": "ارتفاع كالسيوم البول"},
    "sans_progression": {"en": "SANS progression signs", "ar": "علامات تطور SANS"},
    "fever": {"en": "Fever", "ar": "حمى"},
    "co2_buildup": {"en": "Cabin CO2 build-up", "ar": "تراكم ثاني أكسيد الكربون"},
}

PRE = {"heart_rate": (66, 4), "systolic": (118, 5), "diastolic": (76, 4), "spo2": (98, 0.6),
       "body_temp": (36.7, 0.15), "glucose": (95, 7), "sleep_hours": (7.4, 0.4), "sleep_quality": (4, 0.4),
       "mood": (4, 0.3), "stress": (2, 0.4), "workload": (3, 0.4), "body_mass": (75, 0.2), "cabin_co2": (450, 30)}
INFLIGHT_SHIFT = {"heart_rate": -4, "systolic": -6, "diastolic": -3, "sleep_hours": -1.3, "cabin_co2": 1700}
ROUND = {"heart_rate": 0, "systolic": 0, "diastolic": 0, "spo2": 0, "body_temp": 1, "glucose": 0,
         "sleep_hours": 1, "sleep_quality": 0, "mood": 0, "stress": 0, "workload": 0, "body_mass": 1, "cabin_co2": -1}
COND = {"time_of_day": "07:00", "restrained": True, "arm_position": "left, heart level", "rested_5min": True}


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _val(rng: random.Random, ind: str, mean: float, sd: float) -> float:
    v = rng.gauss(mean, sd)
    lo, hi = {"spo2": (90, 100), "sleep_quality": (1, 5), "mood": (1, 5), "stress": (1, 5), "workload": (1, 5)}.get(ind, (-1e9, 1e9))
    v = min(hi, max(lo, v))
    return round(v, ROUND[ind]) if ROUND[ind] >= 0 else round(v, -1)


def _put(store: Store, aid: str, ind: str, v: float, ts: datetime, scen: str, ctx: str, baseline: bool = False) -> None:
    """Fast path for history (no per-point assessment)."""
    obs = fhir.make_observation(aid, ind, v, _iso(ts), {"type": "SYNTHETIC", "ref": scen},
                                {**COND, "baseline": baseline, "confidence": "high"}, ctx)
    store.add_observation(obs, "synthetic-generator")


def generate(store: Store, aid: str, scenario: str, days: int = 21, seed: int = 7) -> dict[str, Any]:
    """Create pre-flight baseline + in-flight history + scenario-specific final days."""
    if scenario not in SCENARIOS:
        raise ValueError(f"unknown scenario {scenario}")
    rng = random.Random(f"{seed}-{aid}-{scenario}")
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start = now - timedelta(days=days + 7)
    # --- 7 days pre-flight baseline (Earth, 1 g)
    for d in range(7):
        t = start + timedelta(days=d, hours=7)
        for ind, (m, sd) in PRE.items():
            if ind == "cabin_co2":
                continue
            _put(store, aid, ind, _val(rng, ind, m, sd), t, scenario, "earth_preflight", baseline=True)
    # --- in-flight days (history, no alerts)
    ctx = "mars_transit" if scenario in ("solar_particle_event", "orthostatic_mars_landing") else "iss"
    for d in range(days - 1):
        t = start + timedelta(days=7 + d, hours=7)
        for ind, (m, sd) in PRE.items():
            mm = m + INFLIGHT_SHIFT.get(ind, 0)
            mm, sd = _modify(scenario, ind, mm, sd, d, days)
            _put(store, aid, ind, _val(rng, ind, mm, sd), t, scenario, ctx)
    # --- final day through the full workflow (assessment + alerts)
    t = now - timedelta(hours=1)
    results = []
    for ind, (m, sd) in PRE.items():
        mm = m + INFLIGHT_SHIFT.get(ind, 0)
        mm, sd2 = _modify(scenario, ind, mm, sd, days - 1, days)
        r = service.record(store, "synthetic-generator", aid, ind, _val(rng, ind, mm, sd2 * 0.3), conditions=COND,
                           provenance={"type": "SYNTHETIC", "ref": scenario}, effective=_iso(t), gravity_context=ctx)
        results.append(r.get("assessment", {}).get("level"))
    _features(store, aid, scenario, rng, start, days, now)
    store.bb_append("synthetic-generator", "scenario", {"astronaut_id": aid, "scenario": scenario, "days": days})
    return {"astronaut_id": aid, "scenario": scenario, "days": days, "final_levels": results}


def _modify(scen: str, ind: str, m: float, sd: float, d: int, days: int) -> tuple[float, float]:
    """Scenario effect on the mean for day index d (0-based)."""
    late = d >= days - 5
    if scen == "sleep_debt" and ind == "sleep_hours" and late:
        return 4.6 + 0.2 * (days - 1 - d), 0.3
    if scen == "sleep_debt" and ind == "sleep_quality" and late:
        return 2, 0.3
    if scen == "behavioral_decline":
        frac = max(0, d - (days - 8)) / 8
        if ind == "mood":
            return 4 - 2.6 * frac, 0.05
        if ind == "stress":
            return 2 + 2.2 * frac, 0.2
        if ind == "sleep_hours" and late:
            return 5.4, 0.3
    if scen == "fever" and ind == "body_temp" and d >= days - 2:
        return 38.7, 0.1
    if scen == "fever" and ind == "heart_rate" and d >= days - 2:
        return 98, 3
    if scen == "co2_buildup" and ind == "cabin_co2":
        return 2000 + max(0, d - (days - 6)) * 520, 60
    if scen == "crew_conflict" and ind == "stress" and late:
        return 4, 0.3
    if scen == "orthostatic_mars_landing" and d == days - 1 and ind in ("heart_rate", "systolic"):
        return (m + 30, 3) if ind == "heart_rate" else (m - 24, 3)
    return m, sd


def _features(store: Store, aid: str, scen: str, rng: random.Random, start: datetime, days: int, now: datetime) -> None:
    for cat in ("voice_features", "vision", "crew_interaction", "radiation", "urine", "connection", "research_export"):
        if store.consents(aid).get(cat) is not False:
            store.set_consent(aid, cat, True, "synthetic-generator")
    # radiation – daily dosimeter
    rate = 1.8 if scen in ("solar_particle_event", "orthostatic_mars_landing") else 0.45
    for d in range(days):
        dose = round(max(0.0, rng.gauss(rate, rate * 0.1)), 3)
        radiation.add_reading(store, aid, dose, _iso(start + timedelta(days=7 + d, hours=12)), "synthetic-generator", "SYNTHETIC")
    if scen == "solar_particle_event":
        radiation.add_reading(store, aid, 28.0, _iso(now - timedelta(hours=2)), "synthetic-generator", "SYNTHETIC")
        store.set_setting("gravity_context", "mars_transit", "synthetic-generator")
        radiation.start_spe(store, arrival_min=45, duration_h=12, current_zone="z1", actor="synthetic-generator")
    # urine – every 3 days
    for i, d in enumerate(range(0, days, 3)):
        ca = 180 + (i * 18 if scen == "rising_calcium" else rng.gauss(0, 8))
        sg = 1.028 if scen == "rising_calcium" and d > days - 7 else round(rng.uniform(1.010, 1.020), 3)
        rec = {"astronaut_id": aid, "timestamp": _iso(start + timedelta(days=7 + d, hours=18)), "source": "simulated_feed",
               "specific_gravity": sg, "calcium_mg_day": round(ca, 0), "ph": 6.0, "volume_ml": 1600,
               "fluid_intake_ml": 1700 if scen == "rising_calcium" else 2400}
        urine.ingest(store, rec, "synthetic-generator")
    # voice – features only
    for d in range(min(days, 12)):
        tired = scen in ("sleep_debt", "behavioral_decline") and d >= 9
        f = {"f0_mean": rng.gauss(140 if not tired else 128, 3), "f0_sd": rng.gauss(22 if not tired else 14, 1.5),
             "energy": rng.gauss(0.08 if not tired else 0.05, 0.004), "speech_rate": rng.gauss(4.2 if not tired else 3.3, 0.15),
             "pause_ratio": rng.gauss(0.22 if not tired else 0.36, 0.02), "jitter": rng.gauss(0.010, 0.001),
             "shimmer": rng.gauss(0.05, 0.004), "duration_s": 60}
        voice.submit(store, aid, f, "synthetic-generator")
    # crew interaction + survey
    for d in range(min(days, 10)):
        iso_ = scen == "behavioral_decline" and d >= 6
        crew.log_interaction(store, aid, {"partner": "crew", "minutes": 25 if iso_ else rng.uniform(70, 120),
                                          "shared_meals": 0 if iso_ else 2, "sleep_overlap_h": 5, "day": f"D{d}"},
                             "synthetic-generator")
    conflict = 5 if scen == "crew_conflict" else 2
    crew.survey(store, aid, cohesion=2 if scen == "crew_conflict" else 4, conflict=conflict,
                workload=4 if scen == "crew_conflict" else 3, actor="synthetic-generator")
    # vision – baseline + latest
    vision.save_screening(store, aid, {"acuity_od": 0.0, "acuity_os": 0.0, "amsler_marks": 0, "contrast": 1.8,
                                       "symptoms": {}, "is_baseline": True, "provenance": "SYNTHETIC"}, "synthetic-generator")
    if scen == "sans_progression":
        vision.save_screening(store, aid, {"acuity_od": 0.2, "acuity_os": 0.1, "amsler_marks": 2, "contrast": 1.6,
                                           "symptoms": {"blurred_near": True}, "provenance": "SYNTHETIC"}, "synthetic-generator")
    if scen == "orthostatic_mars_landing":
        from . import service as svc
        svc.add_event(store, "landing", "mars_surface", "Mars landing (synthetic)", "synthetic-generator",
                      ts=_iso(now - timedelta(hours=2)))
        svc.record_stand_test(store, "synthetic-generator", aid, 62, 112, 98, 86)
