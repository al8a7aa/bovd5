"""Unit tests: crypto, validation, FHIR, engine, storage/black box, alerts."""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from astra import alerts, auth, config, engine, fhir, service, validation
from astra.crypto import Cipher, py_decrypt, py_encrypt
from astra.storage import Store


# ------------------------------------------------------------------ crypto
def test_pure_python_gcm_matches_cryptography() -> None:
    aesgcm = pytest.importorskip("cryptography.hazmat.primitives.ciphers.aead").AESGCM
    for n in (0, 1, 15, 16, 17, 64, 333):
        k, nonce, pt, aad = os.urandom(32), os.urandom(12), os.urandom(n), os.urandom(n % 5)
        ref = aesgcm(k).encrypt(nonce, pt, aad or None)
        assert py_encrypt(k, nonce, pt, aad) == ref
        assert py_decrypt(k, nonce, ref, aad) == pt


def test_gcm_detects_tampering() -> None:
    k, nonce = os.urandom(32), os.urandom(12)
    ct = bytearray(py_encrypt(k, nonce, b"heart rate 61"))
    ct[0] ^= 1
    with pytest.raises(ValueError):
        py_decrypt(k, nonce, bytes(ct))


def test_cipher_roundtrip_and_key_size() -> None:
    c = Cipher(os.urandom(32))
    assert c.decrypt(c.encrypt(b"x" * 100)) == b"x" * 100
    with pytest.raises(ValueError):
        Cipher(b"short")
    with pytest.raises(ValueError):
        c.decrypt("v2:abc")


# -------------------------------------------------------------- validation
@pytest.mark.parametrize("ind,val,ok", [("heart_rate", 72, True), ("heart_rate", 720, False), ("heart_rate", "abc", False),
                                        ("spo2", 101, False), ("unknown", 1, False), ("body_temp", float("nan"), False)])
def test_validate_ranges(ind: str, val: object, ok: bool) -> None:
    assert validation.validate(ind, val).ok is ok


def test_unit_conversion_si() -> None:
    r = validation.validate("body_temp", 98.6, "°F")
    assert r.ok and abs((r.value or 0) - 37.0) < 0.01
    g = validation.validate("glucose", 5.5, "mmol/L")
    assert g.ok and 98 < (g.value or 0) < 100
    assert not validation.validate("glucose", 5.5, "furlongs").ok


def test_conditions_metadata_rule2() -> None:
    r = validation.validate("heart_rate", 70, conditions={})
    assert r.ok and r.confidence == "low" and r.warnings
    r2 = validation.validate("heart_rate", 70, conditions={"time_of_day": "07:00", "restrained": True,
                                                           "arm_position": "left", "rested_5min": True})
    assert r2.confidence == "high" and not r2.warnings
    r3 = validation.validate("heart_rate", 70, conditions={"time_of_day": "07:00", "restrained": True,
                                                           "arm_position": "left", "rested_5min": False})
    assert r3.confidence == "low"


def test_bp_pair() -> None:
    s, d = validation.validate_bp(80, 90)
    assert not s.ok and "greater" in s.errors[0]
    s, d = validation.validate_bp(120, 80)
    assert s.ok and d.ok


# ----------------------------------------------------------------- engine
@pytest.mark.parametrize("ind,val,lvl", [
    ("heart_rate", 75, "green"), ("heart_rate", 55, "yellow"), ("heart_rate", 110, "yellow"), ("heart_rate", 45, "red"), ("heart_rate", 130, "red"),
    ("spo2", 97, "green"), ("spo2", 93, "yellow"), ("spo2", 90, "red"),
    ("systolic", 120, "green"), ("systolic", 140, "yellow"), ("systolic", 165, "red"), ("systolic", 85, "red"),
    ("diastolic", 80, "green"), ("diastolic", 90, "yellow"), ("diastolic", 100, "red"),
    ("sleep_hours", 7.5, "green"), ("sleep_hours", 6, "yellow"), ("sleep_hours", 4.5, "red"),
    ("body_temp", 37, "green"), ("body_temp", 38, "yellow"), ("body_temp", 38.6, "red"), ("body_temp", 35.0, "red"),
    ("glucose", 100, "green"), ("glucose", 60, "yellow"), ("glucose", 200, "yellow"), ("glucose", 50, "red"), ("glucose", 260, "red"),
    ("radiation_pct", 10, "green"), ("radiation_pct", 55, "yellow"), ("radiation_pct", 85, "red"),
    ("cabin_co2", 2000, "green"), ("cabin_co2", 3500, "yellow"), ("cabin_co2", 4500, "red"),
])
def test_default_thresholds(ind: str, val: float, lvl: str) -> None:
    assert engine.earth_level(ind, val)[0] == lvl


def _hist(ind: str, vals: list[float], ctx: str = "iss", start_days: int = 30, baseline: bool = False) -> list[dict]:
    t0 = datetime.now(timezone.utc) - timedelta(days=start_days)
    def ts(i: int) -> str:
        return (t0 + timedelta(days=i)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return [fhir.make_observation("A1", ind, v, ts(i), {"type": "SYNTHETIC", "ref": "t"}, {"baseline": baseline}, ctx)
            for i, v in enumerate(vals)]


def test_baseline_first_then_earth() -> None:
    h = _hist("heart_rate", [60, 61, 62, 61, 60, 62, 61])
    a = engine.assess("heart_rate", 75, h, "iss")  # Earth-green but > baseline + 2 SD
    assert a["earth_level"] == "green" and a["baseline_deviation"] and a["level"] == "yellow"
    assert a["why"]["citations"] and "not a diagnosis" in a["why"]["disclaimer"]


def test_yellow_softened_inside_baseline_red_never() -> None:
    h = _hist("heart_rate", [56, 57, 58, 57, 56, 58, 57])
    a = engine.assess("heart_rate", 57, h, "iss")
    assert a["earth_level"] == "yellow" and a["level"] == "green"
    h2 = _hist("heart_rate", [46, 47, 48, 47, 46, 48, 47])
    assert engine.assess("heart_rate", 47, h2, "iss")["level"] == "red"


def test_gravity_aware_baseline() -> None:
    pre = _hist("heart_rate", [70] * 3 + [71] * 4, "earth_preflight", 40, baseline=True)
    fl = _hist("heart_rate", [62] * 3 + [63] * 4, "iss", 20)
    b0 = engine.baseline(pre + fl, "iss")
    b1 = engine.baseline(pre + fl, "mars_surface")
    assert b0 and b0["source"].startswith("early-flight") and b0["mean"] < 64
    assert b1 and b1["source"] == "pre-flight" and b1["mean"] > 69
    assert engine.baseline(fl[:2], "iss") is None


def test_sleep_three_consecutive_short_nights_red() -> None:
    h = _hist("sleep_hours", [6.2, 6.0, 6.1])  # no baseline → counted as yellow nights
    a = engine.assess("sleep_hours", 6.0, h, "iss")
    assert a["level"] == "red" and a["trend"]["rule"] == "sleep_consecutive"


def test_mood_decline_and_combo() -> None:
    a = engine.assess("mood", 2, _hist("mood", [5, 4, 3]), "iss")
    assert a["trend"]["rule"] == "mood_decline" and a["level"] == "yellow"
    a2 = engine.assess("mood", 2, _hist("mood", [4, 4]), "iss")
    assert a2["trend"]["rule"] == "mood_sharp_drop"
    assert engine.mood_sleep_combo(a2, 4.5)["level"] == "red"  # type: ignore[index]
    assert engine.mood_sleep_combo(a2, 8) is None


def test_stand_test() -> None:
    assert engine.stand_test(60, 115, 95, 110)["level"] == "yellow"
    assert engine.stand_test(60, 115, 70, 90)["level"] == "yellow"
    assert engine.stand_test(60, 115, 70, 85)["level"] == "red"
    assert engine.stand_test(60, 115, 70, 112)["level"] == "green"


def test_composite_bounds() -> None:
    many = [{"level": "red", "baseline_deviation": True}] * 10
    assert engine.composite(many) == {"score": 20, "max": 20, "band": "red"}
    assert engine.composite([{"level": "green"}])["band"] == "green"
    assert engine.composite([{"level": "yellow", "baseline_deviation": True}] * 3)["band"] == "yellow"


def test_unknown_citation_marked() -> None:
    assert config.cite(["nope"])[0]["apa"] == "[CITATION NEEDED]"


# ----------------------------------------------------------- storage & F9
def test_blackbox_chain_and_append_only(store: Store) -> None:
    for i in range(5):
        store.bb_append("t", "x", {"i": i})
    assert store.bb_verify()["ok"]
    with pytest.raises(sqlite3.DatabaseError):
        store.x("UPDATE blackbox SET actor='x' WHERE seq=1")
    with pytest.raises(sqlite3.DatabaseError):
        store.x("DELETE FROM blackbox WHERE seq=1")


def test_hash_chain_tamper_detected(store: Store) -> None:
    for i in range(6):
        store.bb_append("t", "x", {"i": i})
    store.x("DROP TRIGGER bb_no_update")
    store.x("UPDATE blackbox SET category='forged' WHERE seq=3")
    r = store.bb_verify()
    assert not r["ok"] and r["broken_at"] == 3


def test_encrypted_at_rest(store: Store) -> None:
    service.record(store, "t", "A1", "heart_rate", 77)
    raw = store.path.read_bytes() + (store.path.parent / (store.path.name + "-wal")).read_bytes()
    assert b"Heart rate" not in raw and b'"value": 77' not in raw
    assert store.observations("A1", "heart_rate")[0]["valueQuantity"]["value"] == 77


def test_fhir_observation_shape() -> None:
    o = fhir.make_observation("A1", "spo2", 97, provenance={"type": "REAL", "ref": "OSD-1"})
    assert o["resourceType"] == "Observation" and o["code"]["coding"][0]["code"] == "59408-5"
    assert o["valueQuantity"]["system"] == "http://unitsofmeasure.org" and o["effectiveDateTime"].endswith("Z")
    assert fhir.provenance_of(o) == {"type": "REAL", "ref": "OSD-1"}
    with pytest.raises(ValueError):
        fhir.make_observation("A1", "spo2", 97, provenance={"type": "FAKE", "ref": ""})
    assert fhir.bundle([o])["entry"][0]["resource"]["id"] == o["id"]


# ------------------------------------------------------------------ alerts
def test_alert_dedupe_upgrade_and_ground_delay(store: Store) -> None:
    store.set_setting("delay_s_override", 600)
    r1 = service.record(store, "t", "A1", "heart_rate", 110)  # yellow → medium
    r2 = service.record(store, "t", "A1", "heart_rate", 112)
    assert r1["alert_id"] == r2["alert_id"]  # de-duplicated
    service.record(store, "t", "A1", "heart_rate", 135)  # red → upgrade to high + ground msg
    act = store.alerts(status="active", aid="A1")
    assert len(act) == 1 and act[0]["priority"] == "high"
    q = store.queue("down")
    assert q and not q[0]["delivered"]
    assert alerts.tick(store)["delivered"] == 0
    later = datetime.now(timezone.utc) + timedelta(seconds=601)
    assert alerts.tick(store, later)["delivered"] >= 1


def test_escalation_and_repeat(store: Store) -> None:
    service.record(store, "t", "A1", "spo2", 89)
    a = store.alerts(status="active")[0]
    t = fhir.parse_iso(a["created"]) + timedelta(seconds=250)
    res = alerts.tick(store, t)
    assert res["repeated"] == 1 and res["escalated"] == 1
    assert store.alerts(status="active")[0]["tier"] == 2


def test_ground_ack_travels_with_delay(store: Store) -> None:
    store.set_setting("delay_s_override", 120)
    service.record(store, "t", "A1", "spo2", 89)
    aid = store.alerts(status="active")[0]["id"]
    r = alerts.acknowledge(store, aid, {"username": "fs", "role": "flight_surgeon"})
    assert r["status"] == "ack in transit"
    assert store.alerts(status="active")
    alerts.tick(store, datetime.now(timezone.utc) + timedelta(seconds=121))
    assert not store.alerts(status="active")


def test_crew_ack_immediate(store: Store) -> None:
    service.record(store, "t", "A1", "spo2", 89)
    aid = store.alerts(status="active")[0]["id"]
    assert alerts.acknowledge(store, aid, {"username": "a", "role": "astronaut"})["status"] == "acknowledged"


def test_green_no_alert_and_delay_contexts(store: Store) -> None:
    assert service.record(store, "t", "A1", "heart_rate", 70)["alert_id"] is None
    store.set_setting("gravity_context", "lunar_surface")
    assert alerts.current_delay_s(store) == 1.3
    store.set_setting("gravity_context", "mars_transit")
    assert 240 <= alerts.current_delay_s(store) <= 1440


# --------------------------------------------------------- gravity / GTP
def test_gravity_transition_protocol(store: Store) -> None:
    r = service.add_event(store, "landing", "mars_surface", "", "t")
    assert r["transition"] and store.get_setting("gtp")["active"]
    assert service.record_stand_test(store, "t", "A1", 62, 112, 98, 98)["assessment"]["level"] == "yellow"
    service.set_gravity(store, "iss", "t")
    assert not service.record_stand_test(store, "t", "A1", 62, 112, 98, 86)["ok"]  # no standing in 0 g
    with pytest.raises(ValueError):
        service.set_gravity(store, "pluto", "t")


def test_dashboard_and_series(store: Store) -> None:
    for v in (60, 61, 62, 63, 61, 62):
        service.record(store, "t", "A1", "heart_rate", v)
    d = service.dashboard(store, "A1")
    assert d["regions"]["heart"]["level"] in ("green", "yellow") and 0 <= d["composite"]["score"] <= 20
    s = service.series(store, "A1", "heart_rate", 7)
    assert len(s["points"]) == 6


def test_auth_tokens() -> None:
    sec = os.urandom(32)
    tok = auth.make_token(sec, {"username": "u", "role": "cmo", "astronaut_id": "A2"})
    assert auth.read_token(sec, tok)["role"] == "cmo"  # type: ignore[index]
    assert auth.read_token(os.urandom(32), tok) is None
    assert auth.read_token(sec, auth.make_token(sec, {"username": "u", "role": "cmo"}, ttl_s=-1)) is None
    salt, h = auth.hash_password("pw")
    assert auth.verify_password("pw", salt, h) and not auth.verify_password("x", salt, h)
