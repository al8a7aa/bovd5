"""
F3 · CREW HARMONY INDEX
=======================
Inputs (metadata only, opt-in, consent category ``crew_interaction``):
  * self-reported daily interaction log: partner + minutes (NEVER content);
  * shared meals count; sleep-schedule overlap (hours);
  * weekly team survey: cohesion 1–5, conflict 1–5 (5 = most), workload 1–5.

Outputs:
  * team-level index 0–100 and its trend (visible to the whole crew);
  * individual "isolation signal" – visible ONLY to that individual and the
    behavioral health specialist (enforced in api layer + tested);
  * evidence-based suggestions (team debrief, shared meal, schedule adjustment).

Index weights are EXAMPLE values (review needed).
Basis: hrp_team_2022, nasa_team_risk_2025, mishra_2026.
"""
from __future__ import annotations

import statistics
from typing import Any

from .. import config
from ..consent import require
from ..storage import Store

CONTENT_KEYS = {"content", "text", "transcript", "message", "audio"}


def log_interaction(store: Store, aid: str, entry: dict[str, Any], actor: str) -> dict[str, Any]:
    require(store, "F3_crew", aid)
    if CONTENT_KEYS & {k.lower() for k in entry}:
        raise ValueError("conversation content is never recorded – metadata only")
    clean = {"partner": str(entry.get("partner", "")), "minutes": float(entry.get("minutes", 0)),
             "shared_meals": int(entry.get("shared_meals", 0)), "sleep_overlap_h": float(entry.get("sleep_overlap_h", 0)),
             "day": str(entry.get("day", ""))}
    store.add_record("crew", "interaction", clean, aid, actor)
    return clean


def survey(store: Store, aid: str, cohesion: int, conflict: int, workload: int, actor: str) -> dict[str, Any]:
    require(store, "F3_crew", aid)
    for v in (cohesion, conflict, workload):
        if not 1 <= int(v) <= 5:
            raise ValueError("survey items are 1–5")
    p = {"cohesion": int(cohesion), "conflict": int(conflict), "workload": int(workload)}
    store.add_record("crew", "survey", p, aid, actor)
    return p


def team_index(store: Store) -> dict[str, Any]:
    surveys = store.records("crew", "survey")
    inter = store.records("crew", "interaction")
    if not surveys and not inter:
        return {"index": None, "trend": [], "suggestions": [], "citations": config.cite(["hrp_team_2022"])}
    # weekly buckets by ISO week of record timestamp
    weeks: dict[str, list[float]] = {}
    for s in surveys:
        p = s["payload"]
        score = 100 * (0.5 * (p["cohesion"] - 1) / 4 + 0.3 * (5 - p["conflict"]) / 4 + 0.2 * (5 - p["workload"]) / 4)
        weeks.setdefault(s["ts"][:10], []).append(score)
    meals = statistics.fmean([i["payload"]["shared_meals"] for i in inter]) if inter else 0
    trend = [{"day": d, "index": round(statistics.fmean(v), 1)} for d, v in sorted(weeks.items())]
    idx = float(trend[-1]["index"]) if trend else 50.0  # type: ignore[arg-type]
    idx = round(min(100.0, idx + min(10.0, meals * 2)), 1)
    sugg = []
    last = surveys[-1]["payload"] if surveys else {}
    if last.get("conflict", 0) >= 4:
        sugg.append({"en": "Facilitated team debrief", "ar": "جلسة نقاش جماعية مُيسّرة"})
    if meals < 1:
        sugg.append({"en": "Schedule a shared crew meal", "ar": "جدولة وجبة مشتركة للطاقم"})
    if last.get("workload", 0) >= 4:
        sugg.append({"en": "Ask mission control for a schedule adjustment", "ar": "اطلب من مركز التحكم تعديل الجدول"})
    return {"index": idx, "trend": trend, "suggestions": sugg,
            "citations": config.cite(["hrp_team_2022", "nasa_team_risk_2025", "mishra_2026"])}


def isolation_signal(store: Store, aid: str) -> dict[str, Any]:
    """Individual isolation signal (self + behavioral health specialist only)."""
    mins: dict[str, float] = {}
    for r in store.records("crew", "interaction"):
        mins[r["astronaut_id"]] = mins.get(r["astronaut_id"], 0) + r["payload"]["minutes"]
    mine = [r for r in store.records("crew", "interaction", aid)]
    if not mine:
        return {"signal": "unknown", "reason": "no interaction log"}
    median = statistics.median(mins.values()) if mins else 0
    own = mins.get(aid, 0)
    recent = statistics.fmean(r["payload"]["minutes"] for r in mine[-3:])
    early = statistics.fmean(r["payload"]["minutes"] for r in mine[:5])
    sig = "high" if own < 0.4 * median or recent < 0.5 * early else "medium" if own < 0.7 * median else "low"
    return {"signal": sig, "own_minutes": own, "crew_median_minutes": median, "recent_avg": round(recent, 1),
            "early_avg": round(early, 1), "visibility": "you + behavioral health specialist only"}
