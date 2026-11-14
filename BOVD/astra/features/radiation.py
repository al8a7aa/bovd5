"""
F5 · PERSONAL RADIATION MAP
===========================
* Imports dosimeter readings (CSV: ``timestamp,astronaut_id,dose_msv``) or
  simulates them; cumulative effective dose per astronaut vs the configurable
  limit (``config/thresholds.json → radiation.career_limit_msv``, cited to
  NASA-STD-3001 Vol. 1, REVIEW NEEDED).
* Habitat floor-plan with zones and RELATIVE shielding factors → dose-rate
  heat map (rate_zone = base_rate × shield).
* Solar Particle Event (SPE) mode: alarm, countdown, recommended shelter zone
  (lowest shielding factor), stowage-bag shelter checklist, estimated dose saved.

The physics is deliberately simplified (relative factors, not transport
codes). Basis: george_2024, nasa_artemis_rad, nasa_std_3001_v1.
"""
from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta, timezone
from typing import Any

from .. import config, engine, fhir
from ..consent import require
from ..storage import Store

#: Example background dose rates (mSv/day) – synthetic, order-of-magnitude only.
BASE_RATE_MSV_DAY = {"earth_preflight": 0.01, "iss": 0.5, "mars_transit": 1.8, "lunar_surface": 1.4,
                     "mars_surface": 0.7, "rover": 0.8}
SPE_MULTIPLIER = 50.0


def limit_msv(store: Store, aid: str) -> float:
    per = store.get_setting(f"rad_limit.{aid}")
    return float(per if per is not None else config.thresholds()["radiation"]["career_limit_msv"])


def add_reading(store: Store, aid: str, dose_msv: float, ts: str | None, actor: str,
                provenance: str = "USER-ENTERED") -> dict[str, Any]:
    require(store, "F5_radiation", aid)
    if not 0 <= dose_msv < 1000:
        raise ValueError("dose out of plausible range")
    store.add_record("radiation", "dose", {"dose_msv": dose_msv}, aid, actor, provenance, ts)
    return summary(store, aid)


def import_csv(store: Store, text: str, actor: str) -> dict[str, Any]:
    n, errors = 0, []
    for i, row in enumerate(csv.DictReader(io.StringIO(text)), start=2):
        try:
            add_reading(store, row["astronaut_id"].strip(), float(row["dose_msv"]), row["timestamp"].strip(), actor)
            n += 1
        except Exception as exc:  # report per-line errors, keep going
            errors.append(f"line {i}: {exc}")
    return {"imported": n, "errors": errors}


def summary(store: Store, aid: str) -> dict[str, Any]:
    recs = store.records("radiation", "dose", aid)
    total = round(sum(r["payload"]["dose_msv"] for r in recs), 3)
    lim = limit_msv(store, aid)
    pct = round(100 * total / lim, 2) if lim else 0.0
    level, rule = engine.earth_level("radiation_pct", pct)
    return {"astronaut_id": aid, "cumulative_msv": total, "limit_msv": lim, "pct": pct, "level": level,
            "rule": rule, "readings": recs[-50:], "citations": config.cite(["nasa_std_3001_v1", "george_2024"])}


def heatmap(store: Store, spe: bool = False) -> dict[str, Any]:
    cfg = store.get_setting("rad_zones") or config.features()["radiation_habitat"]["zones"]
    ctx = store.get_setting("gravity_context", "iss")
    base = BASE_RATE_MSV_DAY.get(ctx, 0.5) * (SPE_MULTIPLIER if spe else 1.0)
    zones = [{**z, "rate_msv_day": round(base * float(z["shield"]), 3)} for z in cfg]
    shelter = min(zones, key=lambda z: z["shield"])
    return {"context": ctx, "base_rate_msv_day": base, "zones": zones, "shelter": shelter, "spe": spe}


def save_zones(store: Store, zones: list[dict[str, Any]], actor: str) -> None:
    for z in zones:
        if not 0.05 <= float(z["shield"]) <= 3.0:
            raise ValueError("shield factor must be between 0.05 and 3.0")
    store.set_setting("rad_zones", zones, actor)


def start_spe(store: Store, arrival_min: float, duration_h: float, current_zone: str, actor: str) -> dict[str, Any]:
    """Solar particle event mode with countdown and estimated dose saved."""
    hm = heatmap(store, spe=True)
    cur = next((z for z in hm["zones"] if z["id"] == current_zone), hm["zones"][0])
    days = duration_h / 24
    saved = round((cur["rate_msv_day"] - hm["shelter"]["rate_msv_day"]) * days, 2)
    arrival = datetime.now(timezone.utc) + timedelta(minutes=arrival_min)
    spe = {"active": True, "arrival": arrival.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
           "duration_h": duration_h, "shelter": hm["shelter"], "current_zone": cur,
           "dose_in_current_msv": round(cur["rate_msv_day"] * days, 2),
           "dose_in_shelter_msv": round(hm["shelter"]["rate_msv_day"] * days, 2),
           "estimated_saved_msv": saved,
           "checklist_en": config.features()["radiation_habitat"]["shelter_checklist_en"],
           "checklist_ar": config.features()["radiation_habitat"]["shelter_checklist_ar"],
           "started": fhir.now_iso()}
    store.set_setting("spe", spe, actor)
    from .. import alerts
    for a in store.astronauts():
        asm = {"indicator": "spe", "label_en": "SOLAR PARTICLE EVENT – go to shelter",
               "label_ar": "عاصفة جسيمات شمسية – اذهب إلى الملجأ", "value": arrival_min, "unit": "min to arrival",
               "level": "red", "earth_level": "red", "earth_rule": "SPE alert", "baseline": None,
               "notes": [f"Shelter: {hm['shelter']['name_en']}; est. dose saved {saved} mSv"]}
        asm["why"] = engine.explain(asm, hazard_key="radiation", citations=["george_2024", "nasa_artemis_rad"])
        alerts.raise_alert(store, a["id"], asm, actor)
    return spe


def stop_spe(store: Store, actor: str) -> None:
    store.set_setting("spe", None, actor)
