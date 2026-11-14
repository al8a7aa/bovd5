"""API + role-based access tests (ISO/IEC 27002 §5.15 access control)."""
from __future__ import annotations


def test_health_and_login(client) -> None:  # type: ignore[no-untyped-def]
    c = client()
    assert c.get("/api/health")[0] == 200
    assert c.post("/api/login", {"username": "astro1", "password": "wrong"})[0] == 401
    assert c.get("/api/dashboard?aid=A1")[0] == 401


def test_astronaut_own_data_only(client) -> None:  # type: ignore[no-untyped-def]
    a = client("astro1")
    assert a.get("/api/dashboard")[0] == 200
    assert a.get("/api/dashboard?aid=A3")[0] == 403
    st, r = a.post("/api/readings", {"readings": [{"indicator": "heart_rate", "value": 66}],
                                     "conditions": {"time_of_day": "07:00", "restrained": True, "arm_position": "left", "rested_5min": True}})
    assert st == 200 and r["results"][0]["ok"]
    st, r = a.post("/api/readings", {"readings": [{"indicator": "systolic", "value": 80}, {"indicator": "diastolic", "value": 90}]})
    assert not r["results"][0]["ok"]


def test_researcher_cannot_read_health(client) -> None:  # type: ignore[no-untyped-def]
    r = client("research1")
    assert r.get("/api/dashboard?aid=A1")[0] == 403
    assert r.get("/api/crew")[1]["crew"] == []
    st, data = r.get("/api/export")
    assert st == 200 and data[:2] == b"PK"


def test_isolation_signal_visibility(client) -> None:  # type: ignore[no-untyped-def]
    assert client("astro1").get("/api/crew/isolation")[0] == 200
    assert client("astro1").get("/api/crew/isolation?aid=A3")[0] == 403
    assert client("cmo1").get("/api/crew/isolation?aid=A1")[0] == 403
    assert client("surgeon1").get("/api/crew/isolation?aid=A1")[0] == 403
    assert client("bhs1").get("/api/crew/isolation?aid=A1")[0] == 200


def test_flight_surgeon_sees_only_delivered(client, app) -> None:  # type: ignore[no-untyped-def]
    fs = client("surgeon1")
    app.store.set_setting("delay_s_override", 99999)
    cm = client("cmo1")
    cm.post("/api/readings", {"aid": "A1", "readings": [{"indicator": "spo2", "value": 85}]})
    ids_fs = {a["id"] for a in fs.get("/api/alerts")[1]["alerts"]}
    new = [a for a in cm.get("/api/alerts")[1]["alerts"] if a["indicator"] == "spo2" and a["astronaut_id"] == "A1"]
    assert new and new[0]["id"] not in ids_fs
    app.store.set_setting("delay_s_override", None)


def test_thresholds_edit_permission(client) -> None:  # type: ignore[no-untyped-def]
    assert client("cmo1").post("/api/thresholds", {"indicator": "heart_rate"})[0] == 403
    assert client("astro1").post("/api/flags", {"feature": "F1_voice", "enabled": False})[0] == 403


def test_consent_only_self(client) -> None:  # type: ignore[no-untyped-def]
    assert client("cmo1").post("/api/consent", {"aid": "A1", "category": "vision", "granted": False})[0] == 403
    assert client("astro1").post("/api/consent", {"category": "vision", "granted": True})[0] == 200


def test_misc_endpoints(client) -> None:  # type: ignore[no-untyped-def]
    a = client("astro1")
    for p in ("/api/meta", "/api/coach", "/api/urine", "/api/radiation", "/api/crew/index", "/api/connection",
              "/api/voice", "/api/vision", "/api/cdss/protocols", "/api/poll", "/api/events", "/api/openapi.json",
              "/api/series?indicator=heart_rate&days=7", "/api/radiation/heatmap?spe=1", "/api/urine/schema"):
        assert a.get(p)[0] == 200, p
    cm = client("cmo1")
    assert cm.get("/api/queue")[0] == 200 and cm.get("/api/blackbox/verify")[1]["ok"]
    assert cm.post("/api/blackbox/tamper_demo")[1]["tampered_copy"]["ok"] is False
    assert a.get("/api/blackbox")[0] == 403
    assert a.get("/api/nope")[0] == 404
    assert a.post("/api/voice", {"features": {"raw": "x", "f0_mean": 1}})[0] == 400
