"""
F1 · VOICE READING — EXPERIMENTAL – research concept
====================================================
Daily, opt-in 60-second check-in (fixed sentence + 30 s free talk).

PRIVACY BY DESIGN: the browser (web/voice.js) extracts prosodic features with
the Web Audio API on-device – F0 mean/variability, energy, speech rate, pause
ratio, jitter, shimmer – and DISCARDS THE RAW AUDIO. Only the numbers below are
sent to this module. This module rejects any payload that contains audio.

The features are compared with the astronaut's own baseline (z-scores) to give a
"fatigue / stress signal" low/medium/high. The signal is NEVER an alert on its
own: it is combined with sleep and mood (:func:`combined`) first.

Output wording: "voice pattern differs from your baseline — consider a
check-in", never a psychiatric label. Dehydration detection is an untested
hypothesis and is OFF by default.

Basis: mishra_2026 (HERA speech-based team functioning), hrp_bmed_2015.
Standards: ISO/IEC 23894 (AI risk), ISO/IEC TR 24027 (bias – personal baseline
instead of population model), ISO/IEC 29100 (minimisation).
"""
from __future__ import annotations

import statistics
from typing import Any

from .. import config, fhir
from ..consent import require
from ..storage import Store

FEATURES = ("f0_mean", "f0_sd", "energy", "speech_rate", "pause_ratio", "jitter", "shimmer")
#: direction in which a change suggests fatigue/stress (+1 up, -1 down)
DIRECTION = {"f0_mean": +1, "f0_sd": -1, "energy": -1, "speech_rate": -1, "pause_ratio": +1, "jitter": +1, "shimmer": +1}
FORBIDDEN_KEYS = {"audio", "wav", "pcm", "samples", "raw", "blob"}
WORDING = {"low": {"en": "Voice pattern is close to your baseline.", "ar": "نمط الصوت قريب من خط أساسك."},
           "medium": {"en": "Voice pattern differs a little from your baseline.", "ar": "نمط الصوت يختلف قليلًا عن خط أساسك."},
           "high": {"en": "Voice pattern differs from your baseline — consider a check-in.",
                    "ar": "نمط الصوت يختلف عن خط أساسك — فكّر في محادثة متابعة."}}


def submit(store: Store, aid: str, feats: dict[str, Any], actor: str) -> dict[str, Any]:
    require(store, "F1_voice", aid)
    if FORBIDDEN_KEYS & {k.lower() for k in feats}:
        raise ValueError("raw audio is never accepted – send features only")
    clean = {k: float(feats[k]) for k in FEATURES if k in feats}
    if len(clean) < 4:
        raise ValueError("at least 4 prosodic features required")
    prior = [r["payload"]["features"] for r in store.records("voice", "checkin", aid)]
    sig = signal(clean, prior)
    rec = {"features": clean, **sig, "label": "EXPERIMENTAL – research concept",
           "duration_s": float(feats.get("duration_s", 60))}
    store.add_record("voice", "checkin", rec, aid, actor)
    rec["combined"] = combined(store, aid, sig["signal"])
    return rec


def signal(cur: dict[str, float], prior: list[dict[str, float]]) -> dict[str, Any]:
    """Directional z-score vs personal baseline (first ≥ 5 check-ins)."""
    if len(prior) < 5:
        return {"signal": "low", "score": 0.0, "z": {}, "baseline_n": len(prior),
                "message": WORDING["low"], "note": "building personal baseline (needs 5 check-ins)"}
    base = prior[:14]
    z: dict[str, float] = {}
    for k, v in cur.items():
        vals = [p[k] for p in base if k in p]
        if len(vals) >= 3:
            sd = statistics.pstdev(vals) or 1e-6
            z[k] = round((v - statistics.fmean(vals)) / sd, 2)
    score = round(sum(max(0.0, DIRECTION[k] * zz) for k, zz in z.items()) / max(1, len(z)), 2)
    lvl = "high" if score >= 1.5 else "medium" if score >= 0.8 else "low"
    return {"signal": lvl, "score": score, "z": z, "baseline_n": len(base), "message": WORDING[lvl]}


def combined(store: Store, aid: str, voice_signal: str) -> dict[str, Any]:
    """Combine with sleep & mood BEFORE any alert (risk control R-09)."""
    sleep = store.observations(aid, "sleep_hours")[-3:]
    mood = store.observations(aid, "mood")[-3:]
    low_sleep = bool(sleep) and statistics.fmean(fhir.value_of(o) for o in sleep) < 6
    low_mood = bool(mood) and fhir.value_of(mood[-1]) <= 2
    support = int(low_sleep) + int(low_mood)
    suggest = voice_signal == "high" and support >= 1
    return {"low_sleep": low_sleep, "low_mood": low_mood, "suggest_checkin": suggest,
            "text_en": "Voice + sleep/mood together suggest a check-in with the behavioral health specialist." if suggest
            else "No combined signal – no alert raised.",
            "text_ar": "الصوت مع النوم/المزاج يقترحان محادثة مع أخصائي الصحة السلوكية." if suggest
            else "لا توجد إشارة مجتمعة – لم يُرفع تنبيه.",
            "citations": config.cite(["mishra_2026", "hrp_bmed_2015"])}
