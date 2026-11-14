"""Feature logic tests F1–F9, consent-off tests, synthetic scenario tests."""
from __future__ import annotations

import io
import json
import os
import struct
import zipfile
from datetime import datetime, timedelta, timezone

import pytest

from astra import fhir, service, synthetic
from astra.consent import ConsentError
from astra.features import blackbox, cdss, coach, connection, crew, radiation, urine, vision, voice
from astra.storage import Store

from .conftest import grant_all


# ---------------------------------------------------------------- F4
def test_cdss_protocols_lint_clean() -> None:
    assert cdss.lint_protocols() == []
    assert len(cdss.list_protocols()) == 7


def test_cdss_walk_to_stop_queues_ground(store: Store) -> None:
    s = cdss.start(store, "chest_pain", "A1", "t")
    assert s["node"]["type"] == "question"
    s = cdss.answer(store, s["session"]["id"], "yes", "t")
    assert s["node"]["type"] == "stop" and s["session"]["queued_to_ground"]["eta"]
    with pytest.raises(ValueError):
        cdss.answer(store, s["session"]["id"], "yes", "t")


def test_cdss_action_path(store: Store) -> None:
    s = cdss.start(store, "fever", "A1", "t")
    s = cdss.answer(store, s["session"]["id"], "no", "t")
    assert s["node"]["type"] == "action"
    with pytest.raises(ValueError):
        cdss.answer(store, s["session"]["id"], "yes", "t")
    s = cdss.answer(store, s["session"]["id"], "next", "t")
    s = cdss.answer(store, s["session"]["id"], "no", "t")
    assert s["session"]["status"] == "completed"


# ---------------------------------------------------------------- F5
def test_radiation_summary_spe_and_import(store: Store) -> None:
    grant_all(store, "A1")
    grant_all(store, "A2")
    radiation.add_reading(store, "A1", 310, None, "t")
    s = radiation.summary(store, "A1")
    assert s["pct"] > 50 and s["level"] == "yellow"
    with pytest.raises(ValueError):
        radiation.add_reading(store, "A1", -1, None, "t")
    r = radiation.import_csv(store, "timestamp,astronaut_id,dose_msv\n2026-01-01T00:00:00Z,A2,1.5\nbad,A2,x\n", "t")
    assert r["imported"] == 1 and len(r["errors"]) == 1
    hm = radiation.heatmap(store, spe=True)
    assert hm["shelter"]["shield"] == min(z["shield"] for z in hm["zones"])
    spe = radiation.start_spe(store, 30, 10, "z1", "t")
    assert spe["estimated_saved_msv"] > 0 and store.alerts(status="active")
    with pytest.raises(ValueError):
        radiation.save_zones(store, [{"id": "z", "shield": 9}], "t")
    radiation.stop_spe(store, "t")
    assert store.get_setting("spe") is None


# ---------------------------------------------------------------- F2
def test_acuity_letter_size() -> None:
    # logMAR 0 at 6 m ≈ 8.73 mm letter height
    px = vision.letter_height_px(0.0, 600, 1.0)
    assert 8.6 < px < 8.9
    assert vision.chart(300, 3.78)[0]["logmar"] == 1.0


def test_vision_evaluate_and_alert(store: Store) -> None:
    grant_all(store, "A1")
    vision.save_screening(store, "A1", {"acuity_od": 0.0, "acuity_os": 0.0, "amsler_marks": 0, "contrast": 1.8, "is_baseline": True}, "t")
    r = vision.save_screening(store, "A1", {"acuity_od": 0.3, "acuity_os": 0.0, "amsler_marks": 1, "contrast": 1.5,
                                            "symptoms": {"blurred_near": True}}, "t")
    assert r["level"] == "yellow" and len(r["reasons"]) >= 3 and "cannot measure" in r["cannot_measure"]
    assert vision.evaluate({"symptoms": {"scotoma": True}}, None)["level"] == "red"
    assert store.alerts(status="active", aid="A1")


def _dicom(rows: int, cols: int) -> bytes:
    def el(g: int, e: int, vr: bytes, val: bytes) -> bytes:
        if vr in (b"OB", b"OW", b"UN"):
            return struct.pack("<HH", g, e) + vr + b"\0\0" + struct.pack("<I", len(val)) + val
        return struct.pack("<HH", g, e) + vr + struct.pack("<H", len(val)) + val
    ts = b"1.2.840.10008.1.2.1\0"
    meta = el(0x0002, 0x0010, b"UI", ts)
    px = bytes((x * 7) % 256 for x in range(rows * cols * 2))
    body = (el(0x0028, 0x0010, b"US", struct.pack("<H", rows)) + el(0x0028, 0x0011, b"US", struct.pack("<H", cols))
            + el(0x0028, 0x0100, b"US", struct.pack("<H", 16)) + el(0x7FE0, 0x0010, b"OW", px))
    return b"\0" * 128 + b"DICM" + meta + body


def test_dicom_to_png_and_store(store: Store) -> None:
    png, meta = vision.dicom_to_png(_dicom(8, 6))
    assert png.startswith(b"\x89PNG") and meta == {"rows": 8, "cols": 6, "bits": 16}
    grant_all(store, "A1")
    r = vision.save_image(store, "A1", "eye.dcm", _dicom(4, 4), "OD", "OCT", True, "t")
    assert r["dicom"]["rows"] == 4
    with pytest.raises(ValueError):
        vision.save_image(store, "A1", "x.gif", b"GIF89a....", "OD", "OCT", False, "t")
    bb = store.bb_entries(1)[0]["payload"]["payload"]
    assert "b64" not in bb and len(bb["sha256"]) == 64  # black box stores digest only


def test_blink_experimental(store: Store) -> None:
    grant_all(store, "A1")
    assert vision.save_blink(store, "A1", 30, 0.2, "t")["fatigue_signal"] == "high"


# ---------------------------------------------------------------- F6
def test_urine_schema_and_risk(store: Store) -> None:
    grant_all(store, "A1")
    assert urine.validate({"astronaut_id": "A1", "timestamp": "x", "source": "bad", "specific_gravity": 2})  # errors
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for i, ca in enumerate((200, 230, 260, 290)):
        r = urine.ingest(store, {"astronaut_id": "A1", "timestamp": (t0 + timedelta(days=3 * i)).isoformat().replace("+00:00", "Z"),
                                 "source": "manual_strip", "specific_gravity": 1.03, "calcium_mg_day": ca,
                                 "fluid_intake_ml": 1500, "volume_ml": 1200, "ph": 5.2}, "t")
        assert r["ok"]
    a = urine.analyse(store, "A1")
    assert a["calcium_trend_mg_per_day"] == 10.0 and a["stone_risk"]["level"] == "red" and a["hydration"] == "very low"
    assert store.observations("A1", "urine_calcium")
    imp = urine.import_file(store, "astronaut_id,timestamp,specific_gravity\nA1,2026-02-01T00:00:00Z,1.012\nA1,2026-02-02T00:00:00Z,9\n", "lab.csv", "t")
    assert imp["imported"] == 1 and imp["errors"]
    imp2 = urine.import_file(store, json.dumps([{"astronaut_id": "A1", "timestamp": "2026-02-03T00:00:00Z", "specific_gravity": 1.01}]), "lab.json", "t")
    assert imp2["imported"] == 1


# ---------------------------------------------------------------- F7
def test_coach_stays_within_prescription(store: Store) -> None:
    grant_all(store, "A1")
    service.record(store, "t", "A1", "sleep_hours", 4.5)
    for ca in (240, 270, 300):
        urine.ingest(store, {"astronaut_id": "A1", "timestamp": fhir.now_iso(), "source": "manual_strip", "calcium_mg_day": ca}, "t")
    p = coach.plan(store, "A1")
    b = p["bounds"]
    for k, v in p["plan"].items():
        assert b[k]["min"] <= v <= b[k]["max"]
    assert p["plan"]["ared_min"] == b["ared_min"]["max"] and p["plan"]["cycle_min"] == b["cycle_min"]["min"]
    assert p["meals"]["totals"]["sodium_mg"] <= p["meals"]["targets"]["sodium_mg_max"]
    p2 = coach.log_exercise(store, "A1", "ared", 60, "t")
    assert p2["gamification"]["streak_days"] >= 0
    with pytest.raises(ValueError):
        coach.log_exercise(store, "A1", "rowing", 10, "t")
    assert coach.crew_board(store)[0]["who"].startswith("P")


# ---------------------------------------------------------------- F1
def test_voice_rejects_raw_audio_and_builds_baseline(store: Store) -> None:
    grant_all(store, "A1")
    with pytest.raises(ValueError):
        voice.submit(store, "A1", {"audio": "UklGR...", "f0_mean": 1, "f0_sd": 1, "energy": 1, "jitter": 1}, "t")
    base = {"f0_mean": 140, "f0_sd": 22, "energy": 0.08, "speech_rate": 4.2, "pause_ratio": 0.22, "jitter": 0.01, "shimmer": 0.05}
    for i in range(6):
        voice.submit(store, "A1", {k: v * (1 + 0.01 * (i % 3)) for k, v in base.items()}, "t")
    r = voice.submit(store, "A1", {k: v * 1.01 for k, v in base.items()}, "t")
    assert r["signal"] == "low"
    tired = {**base, "f0_sd": 12, "energy": 0.04, "speech_rate": 3.0, "pause_ratio": 0.4}
    r = voice.submit(store, "A1", tired, "t")
    assert r["signal"] == "high" and "check-in" in r["message"]["en"] and "depress" not in json.dumps(r).lower()
    assert r["combined"]["suggest_checkin"] is False  # needs sleep/mood support first
    service.record(store, "t", "A1", "sleep_hours", 4.5)
    assert voice.combined(store, "A1", "high")["suggest_checkin"] is True


# ---------------------------------------------------------------- F3
def test_crew_metadata_only_and_isolation(store: Store) -> None:
    grant_all(store, "A1")
    grant_all(store, "A2")
    with pytest.raises(ValueError):
        crew.log_interaction(store, "A1", {"partner": "A2", "minutes": 10, "transcript": "hello"}, "t")
    for _ in range(5):
        crew.log_interaction(store, "A1", {"partner": "A2", "minutes": 100, "shared_meals": 2}, "t")
        crew.log_interaction(store, "A2", {"partner": "A1", "minutes": 100, "shared_meals": 2}, "t")
    for _ in range(3):
        crew.log_interaction(store, "A1", {"partner": "A2", "minutes": 10}, "t")
    assert crew.isolation_signal(store, "A1")["signal"] == "high"
    crew.survey(store, "A1", 2, 5, 5, "t")
    ti = crew.team_index(store)
    assert 0 <= ti["index"] <= 100 and len(ti["suggestions"]) >= 2
    with pytest.raises(ValueError):
        crew.survey(store, "A1", 9, 1, 1, "t")


# ---------------------------------------------------------------- F8
def test_connection_suggest_and_critical_task(store: Store) -> None:
    grant_all(store, "A1")
    for v in (2, 2, 1):
        service.record(store, "t", "A1", "mood", v)
    assert connection.should_suggest(store, "A1")["suggest"] is True
    store.add_event(fhir.now_iso(), "critical_task", "iss", "3", "t")
    assert connection.should_suggest(store, "A1")["suggest"] is False
    r = connection.rate(store, "A1", True, "t")
    assert r == {"ratings": 1, "helped_pct": 100}
    assert store.records("connection", "rating", "A1")[0]["payload"] == {"helped": True}  # nothing about what was viewed
    store.set_setting("nostalgia_off.A1", True)
    assert connection.should_suggest(store, "A1")["reason"] == "turned off"


# ---------------------------------------------------------------- F9
def test_research_export_pseudonymised_consent_gated(store: Store) -> None:
    grant_all(store, "A1")
    service.record(store, "t", "A1", "heart_rate", 70)
    service.record(store, "t", "A2", "heart_rate", 71)  # A2 has no research consent
    data, man = blackbox.research_export(store, os.urandom(32), "t")
    assert man["subjects"] == 1
    z = zipfile.ZipFile(io.BytesIO(data))
    assert set(z.namelist()) >= {"content/bundle.json", "content/data_dictionary.json", "pdi/preservation_description.json", "manifest-sha256.txt"}
    txt = z.read("content/bundle.json").decode()
    assert "A1" not in json.dumps([e["resource"]["subject"] for e in json.loads(txt)["entry"] if "subject" in e["resource"]])
    assert "Name A1" not in txt
    assert blackbox.verify(store)["ok"]


# ---------------------------------------------------------------- consent-off
@pytest.mark.parametrize("call,feature", [
    (lambda s: voice.submit(s, "A1", {"f0_mean": 1, "f0_sd": 1, "energy": 1, "jitter": 1}, "t"), "voice"),
    (lambda s: vision.save_screening(s, "A1", {"amsler_marks": 0}, "t"), "vision"),
    (lambda s: vision.save_blink(s, "A1", 10, 0.1, "t"), "vision"),
    (lambda s: crew.log_interaction(s, "A1", {"partner": "A2", "minutes": 5}, "t"), "crew"),
    (lambda s: crew.survey(s, "A1", 3, 3, 3, "t"), "crew"),
    (lambda s: radiation.add_reading(s, "A1", 1.0, None, "t"), "radiation"),
    (lambda s: urine.ingest(s, {"astronaut_id": "A1", "timestamp": fhir.now_iso(), "source": "manual_strip"}, "t"), "urine"),
    (lambda s: connection.rate(s, "A1", True, "t"), "connection"),
])
def test_consent_off_collects_nothing(store: Store, call, feature: str) -> None:  # type: ignore[no-untyped-def]
    before = store.count_records(feature)
    with pytest.raises(ConsentError):
        call(store)
    assert store.count_records(feature) == before == 0


def test_feature_flag_off_collects_nothing(store: Store) -> None:
    grant_all(store, "A1")
    store.set_setting("flag.F1_voice", False)
    with pytest.raises(ConsentError):
        voice.submit(store, "A1", {"f0_mean": 1, "f0_sd": 1, "energy": 1, "jitter": 1}, "t")
    assert store.count_records("voice") == 0


def test_core_consent_withdrawn(store: Store) -> None:
    store.set_consent("A1", "core_health", False, "t")
    with pytest.raises(ConsentError):
        service.record(store, "t", "A1", "heart_rate", 70)
    assert store.observations("A1") == []


# ---------------------------------------------------------------- scenarios
EXPECT = {
    "normal_0g": lambda s, a: service.dashboard(s, a)["composite"]["band"] in ("green", "yellow"),
    "orthostatic_mars_landing": lambda s, a: any(r["payload"]["result"]["level"] != "green" for r in s.records("core", "stand_test", a)) and s.get_setting("gtp")["active"],
    "sleep_debt": lambda s, a: _lvl(s, a, "sleep_hours") == "red",
    "behavioral_decline": lambda s, a: _lvl(s, a, "mood") in ("yellow", "red"),
    "crew_conflict": lambda s, a: any(x["en"].startswith("Facilitated") for x in crew.team_index(s)["suggestions"]),
    "solar_particle_event": lambda s, a: s.get_setting("spe")["active"] and any(al["indicator"] == "spe" for al in s.alerts(aid=a)),
    "rising_calcium": lambda s, a: urine.analyse(s, a)["calcium_trend_mg_per_day"] > 0 and urine.analyse(s, a)["stone_risk"]["level"] != "green",
    "sans_progression": lambda s, a: s.records("vision", "screening", a)[-1]["payload"]["level"] != "green",
    "fever": lambda s, a: _lvl(s, a, "body_temp") == "red",
    "co2_buildup": lambda s, a: _lvl(s, a, "cabin_co2") == "red",
}


def _lvl(s: Store, a: str, ind: str) -> str:
    return next(x["level"] for x in service.dashboard(s, a)["latest"] if x["indicator"] == ind)


@pytest.mark.parametrize("scenario", list(synthetic.SCENARIOS))
def test_every_synthetic_scenario(store: Store, scenario: str) -> None:
    r = synthetic.generate(store, "A1", scenario, days=14)
    assert r["scenario"] == scenario
    assert EXPECT[scenario](store, "A1"), scenario
    # provenance: every stored value is labelled SYNTHETIC – never presented as real
    assert {fhir.provenance_of(o)["type"] for o in store.observations("A1")} == {"SYNTHETIC"}


def test_unknown_scenario(store: Store) -> None:
    with pytest.raises(ValueError):
        synthetic.generate(store, "A1", "alien_invasion")


# ---------------------------------------------------------------- REAL loader (local fixture, no network)
def test_osdr_mapping_from_local_file(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from astra.ingest import osdr
    f = tmp_path / "fixture.csv"
    f.write_text("subject,timestamp,hr,spo2\nS1,2026-01-01T07:00:00Z,64,98\nS1,2026-01-02T07:00:00Z,999,97\n", encoding="utf-8")
    m = {"dataset_id": "OSD-TEST-FIXTURE", "license": "test", "citation": "test fixture – not a real dataset",
         "subject_column": "subject", "time_column": "timestamp",
         "columns": {"hr": {"indicator": "heart_rate"}, "spo2": {"indicator": "spo2"}}}
    obs, errs = osdr.map_csv(f, m)
    assert len(obs) == 3 and len(errs) == 1
    assert fhir.provenance_of(obs[0]) == {"type": "REAL", "ref": "OSD-TEST-FIXTURE"}
    with pytest.raises(FileNotFoundError):
        osdr.map_csv(tmp_path / "missing.csv", m)
