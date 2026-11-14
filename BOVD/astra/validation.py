"""
BÖVD · validation layer
===============================
Checks every incoming reading BEFORE it is stored or assessed:
  1. known indicator, numeric value, finite;
  2. unit conversion to the canonical SI/UCUM unit (°F→°C, mmol/L→mg/dL, lb→kg);
  3. physiological plausibility range (rejects typing errors such as HR 720);
  4. cross-field checks (systolic > diastolic);
  5. measurement-condition metadata (microgravity rule 2) – missing items do
     not block the reading but are reported as warnings and lower confidence.

Standards alignment (designed in alignment with, not certified):
  * ISO/IEC 25012 – data quality (accuracy, completeness, consistency).
  * SI / ISO 80000 – canonical units.
  * IEC 62366-1 §5.7 – use-error mitigation (plausibility checks).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from . import config

#: Microgravity rule 2: conditions recorded with every vital-sign reading.
REQUIRED_CONDITIONS = ("time_of_day", "restrained", "arm_position", "rested_5min")
VITALS = {"heart_rate", "spo2", "systolic", "diastolic", "body_temp"}

#: unit → (canonical unit, converter)
CONVERSIONS: dict[str, dict[str, Any]] = {
    "body_temp": {"°F": lambda v: (v - 32) * 5 / 9, "F": lambda v: (v - 32) * 5 / 9},
    "glucose": {"mmol/L": lambda v: v * 18.016},
    "body_mass": {"lb": lambda v: v * 0.45359237},
}


@dataclass
class Result:
    ok: bool
    indicator: str
    value: float | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    confidence: str = "high"

    def as_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "indicator": self.indicator, "value": self.value,
                "errors": self.errors, "warnings": self.warnings, "confidence": self.confidence}


def validate(indicator: str, raw_value: Any, unit: str | None = None,
             conditions: dict[str, Any] | None = None) -> Result:
    """Validate one reading. Returns a :class:`Result` (never raises)."""
    inds = config.thresholds()["indicators"]
    res = Result(ok=False, indicator=indicator)
    if indicator not in inds:
        res.errors.append(f"unknown indicator '{indicator}'")
        return res
    try:
        v = float(raw_value)
    except (TypeError, ValueError):
        res.errors.append("value is not a number")
        return res
    if not math.isfinite(v):
        res.errors.append("value is not finite")
        return res
    if unit and unit not in ("", inds[indicator]["unit"]):
        conv = CONVERSIONS.get(indicator, {}).get(unit)
        if conv is None:
            res.errors.append(f"unit '{unit}' not accepted; use {inds[indicator]['unit']}")
            return res
        v = float(conv(v))
        res.warnings.append(f"converted from {unit} to {inds[indicator]['unit']}")
    lo, hi = inds[indicator]["valid_range"]
    if not lo <= v <= hi:
        res.errors.append(f"value {v:g} outside plausible range {lo}–{hi} – please re-measure")
        return res
    if indicator in VITALS:
        c = conditions or {}
        missing = [k for k in REQUIRED_CONDITIONS if c.get(k) in (None, "")]
        if missing:
            res.warnings.append("measurement conditions incomplete: " + ", ".join(missing))
            res.confidence = "medium" if len(missing) < 3 else "low"
        if c.get("rested_5min") is False:
            res.warnings.append("no 5-minute rest – value may be elevated")
            res.confidence = "low"
    res.ok = True
    res.value = round(v, 3)
    return res


def validate_bp(systolic: Any, diastolic: Any, conditions: dict[str, Any] | None = None) -> tuple[Result, Result]:
    """Validate a blood-pressure pair, including systolic > diastolic."""
    s = validate("systolic", systolic, conditions=conditions)
    d = validate("diastolic", diastolic, conditions=conditions)
    if s.ok and d.ok and s.value is not None and d.value is not None and s.value <= d.value:
        s.ok = d.ok = False
        s.errors.append("systolic must be greater than diastolic")
    return s, d
