"""
F4 · OFFLINE SMART DOCTOR (rule-based clinical decision support)
================================================================
Walks JSON decision trees (config/cdss_protocols.json): question → action →
"stop and call CMO" criteria. Works fully without an Earth link; every finished
or stopped session is logged to the black box and queued for the flight surgeon
with an estimated delivery time.

Safety constraints (ISO 14971 risk R-12 "misuse of CDSS"):
  * all medical logic lives in reviewed JSON rules – no generative model;
  * an action may only reference items in ``approved_onboard_items``
    (validated by :func:`lint_protocols`, run in tests);
  * the separate F11 AI assistant (features/assistant.py) can only explain NASA/CSA
    sources; it never changes these protocols, their answers or the alerts.

Basis: exmc_cdss_2022, exmc_eimo_2024, levin_2023.
Standards alignment: ISO/IEC 23894 (AI risk – rule-based, transparent),
IEC 62304 class B, IEC 62366-1 (step-by-step, one question per screen).
"""
from __future__ import annotations

import uuid
from typing import Any

from .. import alerts, config, fhir
from ..storage import Store


def lint_protocols() -> list[str]:
    """Return a list of problems (empty = OK). Used as a quality gate."""
    p = config.protocols()
    allowed = set(p["approved_onboard_items"])
    errs: list[str] = []
    for pid, proto in p["protocols"].items():
        nodes = proto["nodes"]
        if proto["start"] not in nodes:
            errs.append(f"{pid}: start node missing")
        has_stop = False
        for nid, n in nodes.items():
            for item in n.get("items", []):
                if item not in allowed:
                    errs.append(f"{pid}.{nid}: item '{item}' not in approved onboard list")
            for k in ("yes", "no", "next"):
                if k in n and n[k] not in nodes:
                    errs.append(f"{pid}.{nid}: dangling '{k}' → {n[k]}")
            if n["type"] == "stop":
                has_stop = True
            if n["type"] == "question" and not ("yes" in n and "no" in n):
                errs.append(f"{pid}.{nid}: question without yes/no")
        if not has_stop:
            errs.append(f"{pid}: no 'stop and call CMO' criterion")
    return errs


def list_protocols() -> list[dict[str, Any]]:
    return [{"id": k, "title_en": v["title_en"], "title_ar": v["title_ar"],
             "citations": config.cite(v["citation"])} for k, v in config.protocols()["protocols"].items()]


def start(store: Store, protocol_id: str, aid: str, actor: str) -> dict[str, Any]:
    proto = config.protocols()["protocols"][protocol_id]
    sess = {"id": str(uuid.uuid4()), "protocol": protocol_id, "astronaut_id": aid, "path": [],
            "node": proto["start"], "started": fhir.now_iso(), "status": "open"}
    store.set_setting(f"cdss.{sess['id']}", sess, actor)
    return _view(sess)


def answer(store: Store, session_id: str, ans: str, actor: str) -> dict[str, Any]:
    """Advance a session. ``ans`` is 'yes', 'no' or 'next'."""
    sess = store.get_setting(f"cdss.{session_id}")
    if not sess or sess["status"] != "open":
        raise ValueError("session not open")
    node = config.protocols()["protocols"][sess["protocol"]]["nodes"][sess["node"]]
    key = ans if (node["type"] == "question" and ans in ("yes", "no")) or (node["type"] == "action" and ans == "next") else None
    if key is None or key not in node:
        raise ValueError("invalid answer for this step")
    sess["path"].append({"node": sess["node"], "answer": key, "ts": fhir.now_iso()})
    sess["node"] = node[key]
    nxt = config.protocols()["protocols"][sess["protocol"]]["nodes"][sess["node"]]
    if nxt["type"] in ("stop", "end"):
        sess["status"] = "stopped" if nxt["type"] == "stop" else "completed"
        sess["finished"] = fhir.now_iso()
        msg = alerts.send_to_ground(store, "cdss", sess["astronaut_id"],
                                    {"cdss_session": sess, "outcome_en": nxt["en"]}, actor, kind="cdss_session")
        q = [m for m in store.queue("down") if m["id"] == msg][0]
        sess["queued_to_ground"] = {"message_id": msg, "eta": q["deliver_at"], "delay_s": q["body"]["delay_s"]}
    store.set_setting(f"cdss.{session_id}", sess, actor)
    return _view(sess)


def _view(sess: dict[str, Any]) -> dict[str, Any]:
    proto = config.protocols()["protocols"][sess["protocol"]]
    node = proto["nodes"][sess["node"]]
    return {"session": sess, "node": {"id": sess["node"], **node},
            "title_en": proto["title_en"], "title_ar": proto["title_ar"],
            "citations": config.cite(proto["citation"])}
