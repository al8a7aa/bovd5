"""
F8 · SMART NOSTALGIA (connection to home)
=========================================
* Preloaded family media library chosen before flight. Files placed in
  ``data/media/<astronaut_id>/`` are listed; in a flight build they would be
  encrypted on disk (prototype: served locally only to the owner).
* A gentle suggestion card appears when mood/isolation signals persist for
  ≥ 3 days, or on demand. It is always skippable, can be turned off by the
  astronaut, and is NEVER shown during a critical task (mission event
  ``critical_task`` active).
* Only a 1-tap "helped / didn't help" rating is stored – never what was viewed.

Basis: hrp_bmed_2015, picano_2024. Consent category ``connection``.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .. import config, fhir
from ..config import DATA_DIR
from ..consent import is_enabled, require
from ..storage import Store

MEDIA_EXT = {".jpg", ".jpeg", ".png", ".mp3", ".wav", ".ogg", ".mp4", ".webm"}


def library(aid: str) -> list[dict[str, str]]:
    d = DATA_DIR / "media" / aid
    if not d.exists():
        return []
    return [{"name": p.name, "url": f"/media/{aid}/{p.name}"} for p in sorted(d.iterdir()) if p.suffix.lower() in MEDIA_EXT]


def critical_task_active(store: Store, now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    for e in store.events():
        if e["type"] == "critical_task":
            start = fhir.parse_iso(e["ts"])
            note = (e.get("note") or "").strip()
            hours = float(note) if note.replace(".", "", 1).isdigit() else 2.0  # note = duration in hours
            if start <= now <= start + timedelta(hours=hours):
                return True
    return False


def should_suggest(store: Store, aid: str) -> dict[str, Any]:
    if not is_enabled(store, "F8_connection") or store.get_setting(f"nostalgia_off.{aid}"):
        return {"suggest": False, "reason": "turned off"}
    if critical_task_active(store):
        return {"suggest": False, "reason": "critical task in progress"}
    mood = store.observations(aid, "mood")[-3:]
    low_days = sum(1 for o in mood if fhir.value_of(o) <= 2)
    from .crew import isolation_signal
    iso = isolation_signal(store, aid).get("signal")
    persist = len(mood) == 3 and low_days == 3
    return {"suggest": persist or iso == "high", "reason": "mood low ≥ 3 days" if persist else
            "isolation signal" if iso == "high" else "no persistent signal",
            "skippable": True, "citations": config.cite(["hrp_bmed_2015", "picano_2024"])}


def rate(store: Store, aid: str, helped: bool, actor: str) -> dict[str, Any]:
    """Store only whether it helped – never what was viewed."""
    require(store, "F8_connection", aid)
    store.add_record("connection", "rating", {"helped": bool(helped)}, aid, actor)
    rs = store.records("connection", "rating", aid)
    return {"ratings": len(rs), "helped_pct": round(100 * sum(r["payload"]["helped"] for r in rs) / len(rs))}
