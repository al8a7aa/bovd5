"""
F2 · EYE OF TRUTH – SANS surveillance support
=============================================
* Screen-calibrated visual-acuity chart (logMAR), Amsler grid with tap-to-mark
  distortion, contrast test, symptom questionnaire.
* Import OCT / fundus images (PNG or uncompressed DICOM) and compare with the
  pre-flight baseline image side by side (change slider + annotations in UI).
* Webcam blink rate (EXPERIMENTAL) – numbers only, computed in the browser.

IMPORTANT: the software CANNOT measure intracranial pressure and does NOT
diagnose SANS. It supports the crew's onboard eye exams and flags
"review by flight surgeon".

Basis: nasa_sans_risk, lee_2020, brunstetter_2023.
Standards: ISO 12052 / DICOM PS3.10 (file format – minimal reader below),
IEC 62366-1 (calibration step to avoid use error).
"""
from __future__ import annotations

import base64
import hashlib
import math
import struct
import zlib
from typing import Any

from .. import config
from ..consent import require
from ..storage import Store


# ------------------------------------------------------------- acuity chart
def letter_height_px(logmar: float, distance_cm: float, px_per_mm: float) -> float:
    """Height of a Snellen/ETDRS optotype on screen.

    An optotype at logMAR 0 subtends 5 arc-minutes; each 0.1 logMAR step
    multiplies size by 10^0.1.
    """
    arcmin = 5.0 * (10 ** logmar)
    mm = 2 * distance_cm * 10 * math.tan(math.radians(arcmin / 60) / 2)
    return round(mm * px_per_mm, 2)


def chart(distance_cm: float, px_per_mm: float) -> list[dict[str, float]]:
    """Lines from logMAR 1.0 to -0.1 with their pixel height."""
    rows = []
    for i in range(12):
        lm = round(1.0 - 0.1 * i, 1)
        rows.append({"logmar": lm, "snellen_6": round(6 * 10 ** lm, 1), "px": letter_height_px(lm, distance_cm, px_per_mm)})
    return rows


# ------------------------------------------------------------- screening
SYMPTOMS = ["blurred_near", "blurred_far", "headache", "visual_distortion", "scotoma", "eye_pain"]


def evaluate(result: dict[str, Any], baseline: dict[str, Any] | None) -> dict[str, Any]:
    """Compare a screening with the baseline. Returns level + reasons."""
    reasons: list[str] = []
    level = "green"
    for eye in ("od", "os"):
        cur = result.get(f"acuity_{eye}")
        if cur is not None and baseline and baseline.get(f"acuity_{eye}") is not None:
            if cur - baseline[f"acuity_{eye}"] >= 0.2:  # ≥ 2 lines worse
                level = "yellow"
                reasons.append(f"{eye.upper()} acuity ≥ 2 lines worse than baseline")
    if result.get("amsler_marks", 0) > 0:
        level = "yellow"
        reasons.append(f"Amsler grid: {result['amsler_marks']} distortion mark(s)")
    if baseline and result.get("contrast") is not None and baseline.get("contrast") is not None:
        if result["contrast"] < baseline["contrast"] - 0.15:
            level = "yellow"
            reasons.append("contrast sensitivity lower than baseline")
    sy = [s for s in SYMPTOMS if result.get("symptoms", {}).get(s)]
    if sy:
        level = "yellow"
        reasons.append("symptoms: " + ", ".join(sy))
    if result.get("symptoms", {}).get("scotoma") or (result.get("amsler_marks", 0) >= 5):
        level = "red"
    return {"level": level, "reasons": reasons, "action_en": "Review by flight surgeon; CMO to schedule onboard OCT/fundus exam." if level != "green" else "No change flagged. Continue weekly screening.",
            "action_ar": "مراجعة الجراح الجوي؛ يحدد الضابط الطبي فحص OCT/قاع العين." if level != "green" else "لا تغيير. استمر في الفحص الأسبوعي.",
            "cannot_measure": "This software cannot measure intracranial pressure and does not diagnose SANS.",
            "citations": config.cite(["nasa_sans_risk", "lee_2020", "brunstetter_2023"])}


def save_screening(store: Store, aid: str, result: dict[str, Any], actor: str) -> dict[str, Any]:
    require(store, "F2_vision", aid)
    prior = store.records("vision", "screening", aid)
    base = next((r["payload"] for r in prior if r["payload"].get("is_baseline")), prior[0]["payload"] if prior else None)
    ev = evaluate(result, base)
    payload = {**result, **ev}
    store.add_record("vision", "screening", payload, aid, actor)
    if ev["level"] != "green":
        from .. import alerts, engine
        asm = {"indicator": "vision", "label_en": "Vision screening change", "label_ar": "تغير في فحص الرؤية",
               "value": len(ev["reasons"]), "unit": "finding(s)", "level": ev["level"], "earth_level": ev["level"],
               "earth_rule": "; ".join(ev["reasons"]), "baseline": None, "notes": ev["reasons"]}
        asm["why"] = engine.explain(asm, hazard_key="gravity", citations=["nasa_sans_risk", "lee_2020"])
        alerts.raise_alert(store, aid, asm, actor)
    return payload


def save_blink(store: Store, aid: str, blinks_per_min: float, closure_ratio: float, actor: str) -> dict[str, Any]:
    """EXPERIMENTAL webcam fatigue signal – numbers only, no images."""
    require(store, "F2_vision", aid, "webcam_blink")
    signal = "high" if blinks_per_min > 25 or closure_ratio > 0.15 else "medium" if blinks_per_min > 20 else "low"
    p = {"blinks_per_min": blinks_per_min, "closure_ratio": closure_ratio, "fatigue_signal": signal,
         "label": "EXPERIMENTAL – research concept"}
    store.add_record("vision", "blink", p, aid, actor)
    return p


# ------------------------------------------------------------- images
def save_image(store: Store, aid: str, filename: str, data: bytes, eye: str, modality: str,
               is_baseline: bool, actor: str) -> dict[str, Any]:
    """Store an OCT/fundus image encrypted. DICOM is converted to PNG."""
    require(store, "F2_vision", aid)
    meta: dict[str, Any] = {"filename": filename, "eye": eye, "modality": modality, "is_baseline": is_baseline}
    if data[128:132] == b"DICM" or filename.lower().endswith(".dcm"):
        png, dmeta = dicom_to_png(data)
        meta["dicom"] = dmeta
        data = png
    elif data[:8] != b"\x89PNG\r\n\x1a\n" and data[:3] != b"\xff\xd8\xff":
        raise ValueError("only PNG, JPEG or uncompressed DICOM are accepted")
    mime = "image/png" if data[:4] == b"\x89PNG" else "image/jpeg"
    digest = hashlib.sha256(data).hexdigest()
    rid = store.add_record("vision", "image", {**meta, "mime": mime, "sha256": digest,
                                               "b64": base64.b64encode(data).decode()}, aid, actor,
                           bb_payload={**meta, "sha256": digest})
    return {"id": rid, **meta, "review": "Flag: review by flight surgeon – no automatic diagnosis."}


def dicom_to_png(data: bytes) -> tuple[bytes, dict[str, Any]]:
    """Minimal DICOM PS3.10 reader for UNCOMPRESSED monochrome images.

    Supports Explicit/Implicit VR Little Endian, 8/16-bit, 1 sample/pixel.
    Compressed transfer syntaxes (JPEG, JPEG 2000) are rejected with a message.
    """
    if data[128:132] != b"DICM":
        raise ValueError("not a DICOM Part 10 file (missing DICM preamble)")
    pos = 132
    tags: dict[tuple[int, int], bytes] = {}
    explicit = True
    long_vr = {b"OB", b"OW", b"OF", b"SQ", b"UT", b"UN", b"OD", b"OL", b"UC", b"UR", b"OV", b"SV", b"UV"}
    while pos + 8 <= len(data):
        g, e = struct.unpack_from("<HH", data, pos)
        if g != 0x0002 and (0x0002, 0x0010) in tags:
            ts = tags[(0x0002, 0x0010)].rstrip(b"\x00 ").decode()
            explicit = ts != "1.2.840.10008.1.2"
            if ts not in ("1.2.840.10008.1.2", "1.2.840.10008.1.2.1"):
                raise ValueError(f"compressed DICOM transfer syntax {ts} not supported – export as PNG")
        vr = data[pos + 4:pos + 6]
        if (explicit or g == 0x0002) and vr.isalpha():
            if vr in long_vr:
                ln = struct.unpack_from("<I", data, pos + 8)[0]
                pos += 12
            else:
                ln = struct.unpack_from("<H", data, pos + 6)[0]
                pos += 8
        else:
            ln = struct.unpack_from("<I", data, pos + 4)[0]
            pos += 8
        if ln == 0xFFFFFFFF:
            raise ValueError("undefined-length elements not supported in minimal reader")
        tags[(g, e)] = data[pos:pos + ln]
        pos += ln
        if (g, e) == (0x7FE0, 0x0010):
            break

    def us(tag: tuple[int, int]) -> int:
        return int(struct.unpack("<H", tags[tag][:2])[0])

    rows, cols, bits = us((0x0028, 0x0010)), us((0x0028, 0x0011)), us((0x0028, 0x0100))
    px = tags[(0x7FE0, 0x0010)]
    if bits == 16:
        vals = struct.unpack(f"<{rows * cols}H", px[:rows * cols * 2])
        lo, hi = min(vals), max(vals) or 1
        rng = max(hi - lo, 1)
        img = bytes(int(255 * (v - lo) / rng) for v in vals)
    else:
        img = px[:rows * cols]
    return _png_gray(cols, rows, img), {"rows": rows, "cols": cols, "bits": bits}


def _png_gray(w: int, h: int, pix: bytes) -> bytes:
    """Encode 8-bit grayscale pixels as PNG (zlib, no external libraries)."""
    raw = b"".join(b"\x00" + pix[y * w:(y + 1) * w] for y in range(h))

    def chunk(t: bytes, d: bytes) -> bytes:
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))
