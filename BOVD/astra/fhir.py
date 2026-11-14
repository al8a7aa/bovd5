"""
BÖVD · FHIR R4 mapping
==============================
Every reading is stored as an HL7 FHIR R4 ``Observation`` resource with
LOINC codes (where one exists), UCUM units, ISO 8601 timestamps, measurement
conditions (microgravity rule 2) and a provenance tag (PART 2).

Standards alignment (designed in alignment with, not certified):
  * HL7 FHIR R4 – Observation resource (status, code, subject, effectiveDateTime,
    valueQuantity, component, meta.tag).
  * LOINC – codes listed in config/thresholds.json.
  * UCUM – ``valueQuantity.system = http://unitsofmeasure.org``.
  * ISO 8601 – all times are UTC with a 'Z' suffix.
  * ISO 13606 – reading + context + provenance kept together as one entry.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from . import config

PROVENANCE_TYPES = ("REAL", "SYNTHETIC", "USER-ENTERED")
EXT_CONDITIONS = "https://bovd.local/fhir/StructureDefinition/measurement-conditions"
EXT_GRAVITY = "https://bovd.local/fhir/StructureDefinition/gravity-context"


def now_iso() -> str:
    """Current UTC time, ISO 8601 with seconds precision."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_iso(ts: str) -> datetime:
    """Parse an ISO 8601 timestamp (accepts trailing 'Z')."""
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def make_observation(
    astronaut_id: str,
    indicator: str,
    value: float,
    effective: str | None = None,
    provenance: dict[str, str] | None = None,
    conditions: dict[str, Any] | None = None,
    gravity_context: str = "iss",
) -> dict[str, Any]:
    """Build a FHIR R4 Observation for one indicator value."""
    ind = config.thresholds()["indicators"][indicator]
    prov = provenance or {"type": "USER-ENTERED", "ref": "unknown"}
    if prov["type"] not in PROVENANCE_TYPES:
        raise ValueError(f"invalid provenance type {prov['type']}")
    coding: list[dict[str, str]] = []
    if ind.get("loinc"):
        coding.append({"system": "http://loinc.org", "code": ind["loinc"], "display": ind["label_en"]})
    coding.append({"system": "https://bovd.local/indicator", "code": indicator})
    obs: dict[str, Any] = {
        "resourceType": "Observation",
        "id": str(uuid.uuid4()),
        "meta": {"tag": [{"system": "https://bovd.local/provenance",
                          "code": prov["type"], "display": prov.get("ref", "")}]},
        "status": "final",
        "code": {"coding": coding, "text": ind["label_en"]},
        "subject": {"reference": f"Patient/{astronaut_id}"},
        "effectiveDateTime": effective or now_iso(),
        "valueQuantity": {"value": value, "unit": ind["unit"],
                          "system": "http://unitsofmeasure.org", "code": ind["ucum"]},
        "extension": [
            {"url": EXT_CONDITIONS, "valueString": _cond_str(conditions or {})},
            {"url": EXT_GRAVITY, "valueCode": gravity_context},
        ],
    }
    return obs


def _cond_str(c: dict[str, Any]) -> str:
    import json
    return json.dumps(c, sort_keys=True, ensure_ascii=False)


def indicator_of(obs: dict[str, Any]) -> str:
    """Return the internal indicator id of an Observation."""
    for c in obs["code"]["coding"]:
        if c["system"] == "https://bovd.local/indicator":
            return str(c["code"])
    raise KeyError("indicator coding missing")


def value_of(obs: dict[str, Any]) -> float:
    return float(obs["valueQuantity"]["value"])


def provenance_of(obs: dict[str, Any]) -> dict[str, str]:
    t = obs["meta"]["tag"][0]
    return {"type": t["code"], "ref": t.get("display", "")}


def conditions_of(obs: dict[str, Any]) -> dict[str, Any]:
    import json
    for e in obs.get("extension", []):
        if e["url"] == EXT_CONDITIONS:
            return dict(json.loads(e["valueString"]))
    return {}


def gravity_of(obs: dict[str, Any]) -> str:
    for e in obs.get("extension", []):
        if e["url"] == EXT_GRAVITY:
            return str(e["valueCode"])
    return "iss"


def bundle(resources: list[dict[str, Any]]) -> dict[str, Any]:
    """Wrap resources into a FHIR ``collection`` Bundle."""
    return {"resourceType": "Bundle", "id": str(uuid.uuid4()), "type": "collection",
            "timestamp": now_iso(),
            "entry": [{"fullUrl": f"urn:uuid:{r.get('id', uuid.uuid4())}", "resource": r} for r in resources]}
