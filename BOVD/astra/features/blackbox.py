"""
F9 · HEALTH BLACK BOX
=====================
* The append-only, SHA-256 hash-chained, AES-256-GCM encrypted log lives in
  storage.py (table ``blackbox``, UPDATE/DELETE blocked by triggers).
* :func:`verify` – tamper-check tool (recomputes the chain + GCM tags).
* :func:`research_export` – consent-gated, pseudonymised (keyed HMAC-SHA256,
  ISO 25237) FHIR Bundle + data dictionary, packaged as an OAIS-style
  (ISO 14721) Submission Information Package: content + preservation
  description information + SHA-256 fixity manifest, zipped.

Why: mirrors NASA's lifetime astronaut health surveillance and the Life
Sciences Data Archive practice of reusing data while protecting privacy
(vanbaalen_2017, lsda_2024).
"""
from __future__ import annotations

import hashlib
import hmac
import io
import json
import zipfile
from typing import Any

from .. import config, fhir
from ..storage import Store


def verify(store: Store) -> dict[str, Any]:
    return store.bb_verify()


def pseudonym(secret: bytes, aid: str) -> str:
    """Keyed, non-reversible pseudonym (ISO 25237 §5)."""
    return "P-" + hmac.new(secret, aid.encode(), hashlib.sha256).hexdigest()[:12]


def research_export(store: Store, secret: bytes, actor: str) -> tuple[bytes, dict[str, Any]]:
    """Return (zip bytes, manifest). Only astronauts with consent are included."""
    included, excluded = [], []
    resources: list[dict[str, Any]] = []
    for a in store.astronauts():
        if not store.consents(a["id"]).get("research_export"):
            excluded.append("(not consented)")
            continue
        p = pseudonym(secret, a["id"])
        included.append(p)
        resources.append({"resourceType": "Patient", "id": p, "meta": {"security": [{"code": "PSEUDED"}]}})
        for o in store.observations(a["id"]):
            o = json.loads(json.dumps(o))
            o["subject"] = {"reference": f"Patient/{p}"}
            o["effectiveDateTime"] = o["effectiveDateTime"][:10]  # date-level generalisation
            o["extension"] = [e for e in o.get("extension", []) if "gravity" in e["url"]]
            resources.append(o)
    bundle = fhir.bundle(resources)
    dictionary = {k: {"label": v["label_en"], "loinc": v.get("loinc"), "ucum": v["ucum"], "unit": v["unit"]}
                  for k, v in config.thresholds()["indicators"].items()}
    pdi = {"title": "BÖVD research export (SIP)", "created": fhir.now_iso(), "producer": "BÖVD prototype",
           "oais": "ISO 14721 – SIP with content information + PDI (provenance, context, fixity)",
           "pseudonymisation": "HMAC-SHA256 keyed pseudonyms; dates generalised to day; conditions removed (ISO 25237)",
           "provenance_note": "Each Observation keeps meta.tag provenance REAL/SYNTHETIC/USER-ENTERED.",
           "blackbox_head": store.bb_verify().get("head"), "subjects": len(included), "excluded": len(excluded)}
    files = {"content/bundle.json": json.dumps(bundle, ensure_ascii=False, indent=1),
             "content/data_dictionary.json": json.dumps(dictionary, ensure_ascii=False, indent=1),
             "pdi/preservation_description.json": json.dumps(pdi, ensure_ascii=False, indent=1)}
    manifest = {name: hashlib.sha256(body.encode()).hexdigest() for name, body in files.items()}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, body in files.items():
            z.writestr(name, body)
        z.writestr("manifest-sha256.txt", "\n".join(f"{h}  {n}" for n, h in manifest.items()))
    store.bb_append(actor, "research_export", {"subjects": len(included), "manifest": manifest})
    return buf.getvalue(), {"subjects": len(included), "excluded": len(excluded), "manifest": manifest}
