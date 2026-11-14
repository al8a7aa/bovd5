"""
F6 · SMART TOILET ANALYTICS (software interface only)
=====================================================
A data adapter that accepts three sources through ONE documented JSON schema
(``URINALYSIS_SCHEMA`` below, also in docs/urinalysis_feed.schema.json) so a
future automated urinalysis device can plug in without code changes:

  * ``manual_strip``  – astronaut types the test-strip result;
  * ``lab_file``      – CSV/JSON export from an onboard analyser;
  * ``simulated_feed``– synthetic generator (provenance SYNTHETIC).

Indicators: specific gravity → hydration estimate; urinary calcium trend (bone
loss, smith_1999 / smith_2012); kidney-stone risk score 0–10; fluid intake vs
output. Results light up bones/kidneys on the body figure and are reported to
the flight surgeon. Score weights are EXAMPLE values – review needed.
"""
from __future__ import annotations

import csv
import io
import json
import statistics
from typing import Any

from .. import config, fhir
from ..consent import require
from ..storage import Store

URINALYSIS_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "BÖVD urinalysis feed v1",
    "type": "object",
    "required": ["astronaut_id", "timestamp", "source"],
    "properties": {
        "astronaut_id": {"type": "string"},
        "timestamp": {"type": "string", "format": "date-time", "description": "ISO 8601 UTC"},
        "source": {"enum": ["manual_strip", "lab_file", "simulated_feed", "device"]},
        "device_id": {"type": "string"},
        "specific_gravity": {"type": "number", "minimum": 1.0, "maximum": 1.05},
        "calcium_mg_day": {"type": "number", "minimum": 0, "maximum": 1000},
        "ph": {"type": "number", "minimum": 4, "maximum": 9},
        "volume_ml": {"type": "number", "minimum": 0, "maximum": 6000},
        "fluid_intake_ml": {"type": "number", "minimum": 0, "maximum": 8000},
        "blood": {"type": "boolean"},
    },
}

_NUM_FIELDS = {k: v for k, v in URINALYSIS_SCHEMA["properties"].items() if v.get("type") == "number"}


def validate(rec: dict[str, Any]) -> list[str]:
    """Light-weight JSON-schema validation (no external library)."""
    errs = [f"missing '{k}'" for k in URINALYSIS_SCHEMA["required"] if k not in rec]
    if rec.get("source") not in URINALYSIS_SCHEMA["properties"]["source"]["enum"]:
        errs.append("invalid source")
    for k, spec in _NUM_FIELDS.items():
        if k in rec and rec[k] is not None:
            try:
                v = float(rec[k])
            except (TypeError, ValueError):
                errs.append(f"{k} not a number")
                continue
            if not spec["minimum"] <= v <= spec["maximum"]:
                errs.append(f"{k}={v} outside {spec['minimum']}–{spec['maximum']}")
    return errs


def ingest(store: Store, rec: dict[str, Any], actor: str) -> dict[str, Any]:
    errs = validate(rec)
    if errs:
        return {"ok": False, "errors": errs}
    aid = rec["astronaut_id"]
    require(store, "F6_urine", aid)
    prov = "SYNTHETIC" if rec["source"] == "simulated_feed" else "USER-ENTERED"
    clean = {k: rec[k] for k in URINALYSIS_SCHEMA["properties"] if k in rec}
    store.add_record("urine", "sample", clean, aid, actor, prov, rec["timestamp"])
    # mirror the two core indicators as FHIR Observations (body figure + alerts)
    from .. import service
    p = {"type": prov, "ref": rec.get("device_id") or rec["source"]}
    for ind, key in (("urine_sg", "specific_gravity"), ("urine_calcium", "calcium_mg_day")):
        if clean.get(key) is not None:
            service.record(store, actor, aid, ind, clean[key], provenance=p, effective=rec["timestamp"])
    return {"ok": True, "analysis": analyse(store, aid)}


def import_file(store: Store, text: str, filename: str, actor: str) -> dict[str, Any]:
    rows: list[dict[str, Any]]
    if filename.lower().endswith(".json"):
        data = json.loads(text)
        rows = data if isinstance(data, list) else [data]
    else:
        rows = [dict(r) for r in csv.DictReader(io.StringIO(text))]
    ok, errors = 0, []
    for i, r in enumerate(rows, start=1):
        r.setdefault("source", "lab_file")
        for k in list(r):
            if k in _NUM_FIELDS and r[k] not in (None, ""):
                r[k] = float(r[k])
            elif r[k] == "":
                r.pop(k)
        res = ingest(store, r, actor)
        if res["ok"]:
            ok += 1
        else:
            errors.append(f"row {i}: {'; '.join(res['errors'])}")
    return {"imported": ok, "errors": errors}


def hydration(sg: float) -> str:
    return "well hydrated" if sg < 1.010 else "adequate" if sg < 1.020 else "low" if sg < 1.030 else "very low"


def slope_per_day(points: list[tuple[str, float]]) -> float:
    """Least-squares slope (unit per day)."""
    if len(points) < 2:
        return 0.0
    t0 = fhir.parse_iso(points[0][0])
    xs = [(fhir.parse_iso(t) - t0).total_seconds() / 86400 for t, _ in points]
    ys = [v for _, v in points]
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    den = sum((x - mx) ** 2 for x in xs)
    return round(sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=False)) / den, 3) if den else 0.0


def analyse(store: Store, aid: str) -> dict[str, Any]:
    recs = store.records("urine", "sample", aid)
    if not recs:
        return {"samples": 0}
    last = recs[-1]["payload"]
    ca = [(r["ts"], float(r["payload"]["calcium_mg_day"])) for r in recs if r["payload"].get("calcium_mg_day") is not None]
    ca_slope = slope_per_day(ca)
    intake = sum(float(r["payload"].get("fluid_intake_ml", 0)) for r in recs[-3:])
    output = sum(float(r["payload"].get("volume_ml", 0)) for r in recs[-3:])
    sg = last.get("specific_gravity")
    # ---- kidney-stone risk score 0–10 (EXAMPLE weights, review needed)
    score = 0
    factors = []
    if sg is not None and sg >= 1.025:
        score += 3
        factors.append("concentrated urine")
    if ca and ca[-1][1] > 250:
        score += 3
        factors.append("high urinary calcium")
    if ca_slope > 2:
        score += 2
        factors.append(f"calcium rising {ca_slope} mg/day per day")
    if intake and intake < 2000 * min(3, len(recs)):
        score += 1
        factors.append("fluid intake below ~2 L/day")
    if last.get("ph") is not None and last["ph"] < 5.5:
        score += 1
        factors.append("acidic urine")
    score = min(score, 10)
    level = "red" if score >= 7 else "yellow" if score >= 4 else "green"
    return {"samples": len(recs), "last": last, "hydration": hydration(sg) if sg else None,
            "calcium_trend_mg_per_day": ca_slope, "calcium_series": ca[-30:],
            "fluid_in_ml_last3": intake, "fluid_out_ml_last3": output,
            "stone_risk": {"score": score, "max": 10, "level": level, "factors": factors},
            "recommend_en": "Increase fluid intake toward ≥ 2–2.5 L/day; keep ARED loading; trend reported to flight surgeon." if level != "green" else "Keep current hydration and exercise.",
            "recommend_ar": "زد السوائل إلى 2–2.5 لتر يوميًا على الأقل؛ حافظ على تمارين ARED؛ يُرسل الاتجاه للجراح الجوي." if level != "green" else "حافظ على الترطيب والتمرين الحاليين.",
            "regions": ["kidneys", "bones"], "citations": config.cite(["smith_1999", "smith_2012"])}
