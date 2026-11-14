"""
BÖVD · application service (workflow orchestration)
===========================================================
Implements the end-to-end workflow for the primary scenarios:

    input → validation → assessment → explanation → action → escalation → follow-up

and the dashboard / body-map aggregation.

Standards alignment (designed in alignment with, not certified):
  IEC 62304 §5.3 architecture (this module only orchestrates; clinical logic is
  in engine.py, alarm logic in alerts.py); ISO 13606 (entry + context).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from . import alerts, config, engine, fhir, validation
from .consent import require
from .storage import Store

DEFAULT_ROUTINE = [
    {"time": "06:30", "task_en": "Wake – log sleep (crew schedule, not sunrise)", "task_ar": "الاستيقاظ – سجّل النوم (حسب جدول الطاقم)", "kind": "sleep"},
    {"time": "07:00", "task_en": "Morning vitals: restrained, 5-min rest, same arm", "task_ar": "المؤشرات الصباحية: مثبتًا، راحة 5 دقائق، نفس الذراع", "kind": "vitals"},
    {"time": "07:15", "task_en": "Voice check-in (60 s, optional)", "task_ar": "تسجيل صوتي (60 ثانية، اختياري)", "kind": "voice"},
    {"time": "09:00", "task_en": "ARED resistive exercise", "task_ar": "تمرين المقاومة ARED", "kind": "exercise"},
    {"time": "14:00", "task_en": "Treadmill / cycle ergometer", "task_ar": "جهاز المشي / الدراجة", "kind": "exercise"},
    {"time": "18:00", "task_en": "Urine strip / hydration check", "task_ar": "شريط البول / فحص الترطيب", "kind": "urine"},
    {"time": "20:30", "task_en": "Mood, stress, workload; interaction log", "task_ar": "المزاج والضغط وعبء العمل؛ سجل التفاعل", "kind": "mood"},
    {"time": "Sun 10:00", "task_en": "Weekly: vision screening + team survey", "task_ar": "أسبوعيًا: فحص الرؤية + استبيان الفريق", "kind": "weekly"},
]


def record(store: Store, actor: str, aid: str, indicator: str, value: Any, unit: str | None = None,
           conditions: dict[str, Any] | None = None, provenance: dict[str, str] | None = None,
           effective: str | None = None, raise_alerts: bool = True,
           gravity_context: str | None = None) -> dict[str, Any]:
    """Validate, store and assess one reading; raise an alert if needed."""
    require(store, "F4_cdss", aid, "core_health")
    v = validation.validate(indicator, value, unit, conditions)
    if not v.ok or v.value is None:
        return {"ok": False, "validation": v.as_dict()}
    history = store.observations(aid, indicator)
    if effective:
        history = [o for o in history if o["effectiveDateTime"] < effective]
    ctx = gravity_context or store.get_setting("gravity_context", "iss")
    a = engine.assess(indicator, v.value, history, ctx, v.confidence, cabin_kpa(store))
    if indicator == "mood":
        combo = engine.mood_sleep_combo(a, _last_value(store, aid, "sleep_hours"))
        if combo:
            a["level"] = "red"
            a["notes"].append(combo["text"])
            a["trend"] = combo
            a["why"] = engine.explain(a)
    obs = fhir.make_observation(aid, indicator, v.value, effective,
                                provenance or {"type": "USER-ENTERED", "ref": actor},
                                {**(conditions or {}), "confidence": v.confidence}, ctx)
    store.add_observation(obs, actor)
    alert_id = alerts.raise_alert(store, aid, a, actor) if raise_alerts else None
    return {"ok": True, "validation": v.as_dict(), "assessment": a, "observation_id": obs["id"], "alert_id": alert_id}


def cabin_kpa(store: Store) -> float:
    """Current cabin pressure (kPa) from the selected cabin preset (default ISS/sea level)."""
    from .physio import CABINS
    return float(CABINS.get(store.get_setting("cabin_preset", "iss"), CABINS["iss"])["kpa"])


def _last_value(store: Store, aid: str, indicator: str) -> float | None:
    obs = store.observations(aid, indicator)
    return fhir.value_of(obs[-1]) if obs else None


def dashboard(store: Store, aid: str) -> dict[str, Any]:
    """Latest assessment per indicator, body-map regions, composite score."""
    ctx = store.get_setting("gravity_context", "iss")
    latest: list[dict[str, Any]] = []
    for ind in config.thresholds()["indicators"]:
        obs = store.observations(aid, ind)
        if not obs:
            continue
        last = obs[-1]
        a = engine.assess(ind, fhir.value_of(last), obs[:-1], ctx, fhir.conditions_of(last).get("confidence", "high"), cabin_kpa(store))
        a["effective"] = last["effectiveDateTime"]
        a["provenance"] = fhir.provenance_of(last)
        latest.append(a)
    regions_cfg = config.load("body_regions")["regions"]
    regions: dict[str, Any] = {}
    for rid, r in regions_cfg.items():
        items = [a for a in latest if a["region"] == rid]
        level = engine.worst(*[a["level"] for a in items]) if items else "none"
        regions[rid] = {**r, "level": level, "items": items, "citations": config.cite(r["citation"])}
    from .features import radiation as _rad  # skin & radiation region from dosimetry
    rs = _rad.summary(store, aid)
    if rs["readings"]:
        ra = engine.assess("radiation_pct", rs["pct"], [], ctx)
        ra.update(effective=rs["readings"][-1]["ts"], provenance={"type": rs["readings"][-1]["provenance"], "ref": "dosimeter"})
        latest.append(ra)
        regions["skin"]["items"].append(ra)
        regions["skin"]["level"] = ra["level"]
    vis = store.records("vision", "screening", aid)
    if vis:
        lvl = vis[-1]["payload"].get("level", "green")
        regions["eyes"]["level"] = lvl
        regions["eyes"]["vision"] = vis[-1]
    comp = engine.composite(latest)
    gctx = config.gravity()["contexts"][ctx]
    return {"astronaut_id": aid, "gravity_context": ctx, "gravity": gctx, "delay_s": alerts.current_delay_s(store),
            "composite": comp, "latest": latest, "regions": regions,
            "alerts": store.alerts(status="active", aid=aid), "gtp": gtp_status(store)}


def series(store: Store, aid: str, indicator: str, days: float | None = None) -> dict[str, Any]:
    """Time series with baseline band and gravity-transition markers."""
    obs = store.observations(aid, indicator)
    if days is not None and obs:
        end = fhir.parse_iso(obs[-1]["effectiveDateTime"])
        cut = end - timedelta(days=days)
        obs = [o for o in obs if fhir.parse_iso(o["effectiveDateTime"]) >= cut]
    base = engine.baseline(store.observations(aid, indicator), store.get_setting("gravity_context", "iss"))
    pts = [{"t": o["effectiveDateTime"], "v": fhir.value_of(o), "prov": fhir.provenance_of(o),
            "ctx": fhir.gravity_of(o)} for o in obs]
    markers = [e for e in store.events() if e["type"] in ("landing", "launch", "return", "docking", "critical_task")]
    return {"indicator": indicator, "points": pts, "baseline": base, "markers": markers,
            "unit": config.thresholds()["indicators"][indicator]["unit"]}


def set_gravity(store: Store, ctx: str, actor: str) -> dict[str, Any]:
    if ctx not in config.gravity()["contexts"]:
        raise ValueError("unknown gravity context")
    prev = store.get_setting("gravity_context", "iss")
    store.set_setting("gravity_context", ctx, actor)
    store.set_setting("delay_s_override", None, actor)
    g_prev = config.gravity()["contexts"][prev]["g"]
    g_new = config.gravity()["contexts"][ctx]["g"]
    if g_prev == 0.0 and g_new > 0.0:
        start_gtp(store, ctx, actor)
    return {"gravity_context": ctx, "transition": g_prev == 0.0 and g_new > 0.0}


def add_event(store: Store, etype: str, ctx: str, note: str, actor: str, ts: str | None = None) -> dict[str, Any]:
    """Mission timeline event. 'landing'/'return' triggers the GTP (rule 3)."""
    store.add_event(ts or fhir.now_iso(), etype, ctx, note, actor)
    if etype in ("landing", "return"):
        return set_gravity(store, ctx, actor)
    return {"ok": True}


def start_gtp(store: Store, ctx: str, actor: str) -> None:
    """Gravity Transition Protocol: checklist + stand tests at +2 h / +24 h."""
    now = datetime.now(timezone.utc)
    gtp = config.gravity()["gravity_transition_protocol"]
    store.set_setting("gtp", {
        "active": True, "context": ctx, "started": fhir.now_iso(),
        "steps_en": gtp["steps_en"], "steps_ar": gtp["steps_ar"], "done": [False] * len(gtp["steps_en"]),
        "stand_tests_due": [alerts._iso(now + timedelta(hours=2)), alerts._iso(now + timedelta(hours=24))],
        "citation": config.cite(gtp["citation"])}, actor)


def gtp_status(store: Store) -> dict[str, Any] | None:
    g = store.get_setting("gtp")
    return dict(g) if g else None


def record_stand_test(store: Store, actor: str, aid: str, seated_hr: float, seated_sys: float,
                      stand_hr: float, stand_sys: float) -> dict[str, Any]:
    ctx = store.get_setting("gravity_context", "iss")
    if not config.gravity()["contexts"][ctx]["standing_tests"]:
        return {"ok": False, "error": "stand test not available in 0 g (microgravity rule 3)"}
    res = engine.stand_test(seated_hr, seated_sys, stand_hr, stand_sys)
    store.add_record("core", "stand_test", {"seated_hr": seated_hr, "seated_sys": seated_sys,
                                            "stand_hr": stand_hr, "stand_sys": stand_sys, "result": res}, aid, actor)
    alerts.raise_alert(store, aid, res, actor)
    return {"ok": True, "assessment": res}
