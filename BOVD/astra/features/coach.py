"""
F7 · DAILY MOVEMENT & FOOD PRESCRIPTION
=======================================
Adjusts today's exercise plan WITHIN the flight-surgeon-approved prescription
bounds (config/features.json → coach.prescription: default/min/max). The coach
can never exceed those bounds (tested in tests/test_features.py).

Rules (transparent, each produces a reason string):
  * sleep < 6 h or fatigue signal high → aerobic minutes toward minimum;
  * urinary calcium rising or high → ARED toward maximum (bone loading);
  * body-mass loss ≥ 3 % vs baseline → add energy-dense meals;
  * otherwise → defaults.
Meal suggestions: greedy selection from the onboard menu to meet calcium,
vitamin D, protein while keeping sodium under the cap.
Gamification for healthy habits only: streaks and badges; crew board is anonymous.

Basis: scott_2023, english_2020, smith_2012. Targets: review needed.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .. import config, fhir
from ..storage import Store


def _clamp(v: float, lo: float, hi: float) -> int:
    return int(max(lo, min(hi, v)))


def plan(store: Store, aid: str) -> dict[str, Any]:
    cfg = config.features()["coach"]
    rx = cfg["prescription"]
    reasons: list[str] = []
    sleep = store.observations(aid, "sleep_hours")
    last_sleep = fhir.value_of(sleep[-1]) if sleep else None
    voice = store.records("voice", "checkin", aid)
    fatigue = voice[-1]["payload"].get("signal") if voice else None
    urine = store.records("urine", "sample", aid)
    ca = [float(r["payload"]["calcium_mg_day"]) for r in urine if r["payload"].get("calcium_mg_day") is not None]
    mass = store.observations(aid, "body_mass")

    ared = float(rx["ared_min"]["default"])
    tread = float(rx["treadmill_min"]["default"])
    cyc = float(rx["cycle_min"]["default"])
    if (last_sleep is not None and last_sleep < 6) or fatigue == "high":
        tread, cyc = rx["treadmill_min"]["min"], rx["cycle_min"]["min"]
        reasons.append("low sleep / fatigue signal → aerobic reduced to prescribed minimum")
    if ca and (ca[-1] > 250 or (len(ca) >= 3 and ca[-1] - ca[-3] > 20)):
        ared = rx["ared_min"]["max"]
        reasons.append("urinary calcium high/rising → ARED resistive loading at prescribed maximum")
    extra_kcal = 0
    if len(mass) >= 2:
        m0, m1 = fhir.value_of(mass[0]), fhir.value_of(mass[-1])
        loss = 100 * (m0 - m1) / m0
        if loss >= 3:
            extra_kcal = 300
            reasons.append(f"body mass down {loss:.1f} % → +300 kcal suggested")
    if not reasons:
        reasons.append("all inputs within range → default prescription")
    out_plan = {
        "ared_min": _clamp(ared, rx["ared_min"]["min"], rx["ared_min"]["max"]),
        "treadmill_min": _clamp(tread, rx["treadmill_min"]["min"], rx["treadmill_min"]["max"]),
        "cycle_min": _clamp(cyc, rx["cycle_min"]["min"], rx["cycle_min"]["max"]),
    }
    return {"plan": out_plan, "bounds": rx, "reasons": reasons, "meals": meals(extra_kcal),
            "gamification": streak(store, aid, out_plan), "citations": config.cite(cfg["citation"]),
            "note": "Adjustments stay inside the flight-surgeon-approved prescription."}


def meals(extra_kcal: int = 0) -> dict[str, Any]:
    cfg = config.features()["coach"]
    tgt = cfg["daily_targets"]
    menu = list(cfg["onboard_menu"])
    chosen: list[dict[str, Any]] = []
    tot = {"calcium_mg": 0.0, "vitd_iu": 0.0, "protein_g": 0.0, "sodium_mg": 0.0, "kcal": 0.0}
    kcal_target = int(tgt.get("kcal", 3035)) + extra_kcal  # E-NUT-02
    for _ in range(8):
        def gain(m: dict[str, Any]) -> float:
            g = 0.0
            for k in ("calcium_mg", "vitd_iu", "protein_g"):
                g += max(0.0, tgt[k] - tot[k]) and min(m[k], tgt[k] - tot[k]) / tgt[k]
            g += max(0.0, kcal_target - tot["kcal"]) and min(m["kcal"], kcal_target - tot["kcal"]) / kcal_target
            return g
        cands = [m for m in menu if tot["sodium_mg"] + m["sodium_mg"] <= tgt["sodium_mg_max"] and m not in chosen]
        if not cands:
            break
        best = max(cands, key=gain)
        if gain(best) <= 0:
            break
        chosen.append(best)
        for k in tot:
            tot[k] += best[k]
    return {"items": chosen, "totals": tot, "targets": tgt, "kcal_target": kcal_target}


def log_exercise(store: Store, aid: str, device: str, minutes: float, actor: str) -> dict[str, Any]:
    if device not in ("ared", "treadmill", "cycle"):
        raise ValueError("device must be ared, treadmill or cycle")
    store.add_record("coach", "exercise", {"device": device, "minutes": minutes}, aid, actor)
    from .. import service
    day = fhir.now_iso()[:10]
    total = sum(r["payload"]["minutes"] for r in store.records("coach", "exercise", aid) if r["ts"].startswith(day))
    service.record(store, actor, aid, "exercise_min", total, raise_alerts=False)
    return plan(store, aid)


def streak(store: Store, aid: str, today_plan: dict[str, int]) -> dict[str, Any]:
    """Consecutive days where logged minutes ≥ 80 % of the plan total."""
    need = 0.8 * sum(today_plan.values())
    by_day: dict[str, float] = {}
    for r in store.records("coach", "exercise", aid):
        by_day[r["ts"][:10]] = by_day.get(r["ts"][:10], 0) + float(r["payload"]["minutes"])
    s = 0
    d = datetime.now(timezone.utc).date()
    while by_day.get(d.isoformat(), 0) >= need:
        s += 1
        d -= timedelta(days=1)
    badges = [b for n, b in ((1, "🌱 First day"), (3, "🔥 3-day streak"), (7, "🚀 Week strong"), (30, "🏅 Month"))
              if s >= n]
    return {"streak_days": s, "badges": badges}


def crew_board(store: Store) -> list[dict[str, Any]]:
    """Anonymous crew board: pseudonyms + streaks only."""
    rows = []
    for a in store.astronauts():
        p = plan(store, a["id"])
        rows.append({"who": a["pseudonym"], "streak_days": p["gamification"]["streak_days"]})
    return sorted(rows, key=lambda r: -int(r["streak_days"]))
