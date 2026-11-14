"""
BÖVD · alerts, escalation and store-and-forward link
===========================================================
Three alarm priorities in the style of IEC 60601-1-8:

  =========  ===========  ======================  ===================  ==========
  priority   from level   visual                  repeat until ack     escalation
  =========  ===========  ======================  ===================  ==========
  HIGH       red          red, flashing           every 30 s           2 min
  MEDIUM     yellow       amber, steady           every 10 min         30 min
  LOW        info/trend   cyan, steady            no                   none
  =========  ===========  ======================  ===================  ==========

Escalation chain: tier 0 crew member → tier 1 Crew Medical Officer (CMO) →
tier 2 ground flight surgeon. Messages to the ground pass through a
store-and-forward queue whose delivery time is ``now + one-way light time``
(Moon ≈ 1.3 s, Mars 4–24 min). Acknowledgements from the ground travel back
with the same delay.

Alarm-fatigue controls (ISO 14971 risk R-07): de-duplication per astronaut +
indicator, and LOW priority never repeats or escalates.

Standards alignment (designed in alignment with, not certified):
  IEC 60601-1-8 §6.1 priorities, §6.3 visual signals, §6.6 escalation;
  IEC 62366-1 (alarm usability); NASA EIMO concept (exmc_eimo_2024).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from . import config, fhir
from .storage import Store

PRIORITY_OF = {"red": "high", "yellow": "medium", "info": "low"}
POLICY: dict[str, dict[str, int | None]] = {
    "high": {"repeat_s": 30, "escalate_s": 120},
    "medium": {"repeat_s": 600, "escalate_s": 1800},
    "low": {"repeat_s": None, "escalate_s": None},
}
TIERS = ["crew", "CMO", "flight_surgeon"]
_RANK = {"low": 0, "medium": 1, "high": 2}


def current_delay_s(store: Store) -> float:
    """One-way comm delay for the active gravity context (seconds).

    Uses ``settings.delay_s_override`` if set, else the context range midpoint.
    """
    ov = store.get_setting("delay_s_override")
    if ov is not None:
        return float(ov)
    ctx = store.get_setting("gravity_context", "iss")
    lo, hi = config.gravity()["contexts"][ctx]["delay_s"]
    return (float(lo) + float(hi)) / 2


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def raise_alert(store: Store, astronaut_id: str, assessment: dict[str, Any], actor: str) -> str | None:
    """Create (or upgrade) an alert from an assessment. Returns alert id or None."""
    lvl = assessment["level"]
    if lvl == "green":
        if assessment.get("baseline_deviation"):
            lvl = "info"
        else:
            return None
    prio = PRIORITY_OF[lvl]
    for a in store.alerts(status="active", aid=astronaut_id):
        if a["indicator"] == assessment["indicator"]:
            if _RANK[prio] > _RANK[a["priority"]]:
                store.update_alert(a["id"], actor, priority=prio, body_enc=store._enc(_body(assessment)))
                if prio == "high":
                    send_to_ground(store, a["id"], astronaut_id, assessment, actor)
            return str(a["id"])  # de-duplicated (alarm-fatigue control)
    alid = store.add_alert(astronaut_id, prio, assessment["indicator"], _body(assessment), actor)
    if prio == "high":  # red always informs the ground immediately (delayed)
        send_to_ground(store, alid, astronaut_id, assessment, actor)
    return alid


def _body(a: dict[str, Any]) -> dict[str, Any]:
    return {"label_en": a["label_en"], "label_ar": a["label_ar"], "value": a["value"], "unit": a["unit"],
            "level": a["level"], "why": a["why"], "notes": a.get("notes", [])}


def send_to_ground(store: Store, alert_id: str, astronaut_id: str, payload: dict[str, Any], actor: str,
                   kind: str = "alert") -> str:
    """Queue a message to the flight surgeon with light-time delay."""
    delay = current_delay_s(store)
    deliver = _iso(datetime.now(timezone.utc) + timedelta(seconds=delay))
    return store.enqueue("down", {"kind": kind, "alert_id": alert_id, "astronaut_id": astronaut_id,
                                  "payload": payload, "delay_s": delay}, deliver, actor)


def acknowledge(store: Store, alert_id: str, user: dict[str, Any]) -> dict[str, Any]:
    """Acknowledge an alert. Ground acknowledgements travel up with delay."""
    if user["role"] == "flight_surgeon":
        delay = current_delay_s(store)
        deliver = _iso(datetime.now(timezone.utc) + timedelta(seconds=delay))
        store.enqueue("up", {"kind": "ack", "alert_id": alert_id, "by": user["username"]}, deliver, user["username"])
        return {"status": "ack in transit", "arrives": deliver, "delay_s": delay}
    store.update_alert(alert_id, user["username"], status="acknowledged", acked_by=user["username"],
                       acked_at=fhir.now_iso())
    return {"status": "acknowledged"}


def tick(store: Store, now: datetime | None = None) -> dict[str, int]:
    """Periodic processing: repeat, escalate, deliver queued messages."""
    now = now or datetime.now(timezone.utc)
    rep = esc = dlv = 0
    for a in store.alerts(status="active"):
        pol = POLICY[a["priority"]]
        created = fhir.parse_iso(a["created"])
        last = fhir.parse_iso(a["last_notified"])
        if pol["repeat_s"] and (now - last).total_seconds() >= pol["repeat_s"]:
            store.x("UPDATE alerts SET last_notified=?, repeats=repeats+1 WHERE id=?", (_iso(now), a["id"]))
            rep += 1
        if pol["escalate_s"] and a["tier"] < 2:
            due_tier = min(2, int((now - created).total_seconds() // pol["escalate_s"]))
            if due_tier > a["tier"]:
                store.update_alert(a["id"], "escalation", tier=due_tier)
                esc += 1
                if due_tier == 2 and a["priority"] != "high":
                    send_to_ground(store, a["id"], a["astronaut_id"], a["body"], "escalation", kind="escalation")
    for m in store.queue():
        if not m["delivered"] and fhir.parse_iso(m["deliver_at"]) <= now:
            store.mark_delivered(m["id"])
            dlv += 1
            if m["direction"] == "up" and m["body"].get("kind") == "ack":
                store.update_alert(m["body"]["alert_id"], m["body"]["by"], status="acknowledged",
                                   acked_by=m["body"]["by"], acked_at=_iso(now))
    return {"repeated": rep, "escalated": esc, "delivered": dlv}
