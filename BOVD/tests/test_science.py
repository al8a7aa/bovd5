"""Scientific verification: equations vs published reference values, evidence registry integrity,
and evidence-bound simulation (no invented relations)."""
from __future__ import annotations

import re

import pytest

from astra import config, physio


# ------------------------------------------------ equations against published numbers
@pytest.mark.parametrize("h,expected_pa", [(0, 101325), (5000, 54020), (11000, 22632), (15000, 12045), (20000, 5475)])
def test_ussa1976_pressure(h: float, expected_pa: float) -> None:
    """U.S. Standard Atmosphere 1976 table values (E-EQ-01), ±0.1 %."""
    assert physio.pressure_at_altitude(h) == pytest.approx(expected_pa, rel=1e-3)


def test_exploration_atmosphere_pio2_matches_nasa() -> None:
    """NASA reports PIO2 = 128 mmHg for 8.2 psia / 34 % O2 (E-ATM-02)."""
    o = physio.oxygenation(8.2 * physio.PSI_TO_KPA, 0.34)
    assert o["pio2"] == pytest.approx(128, abs=1)


def test_emu_pio2_matches_nasa() -> None:
    """NASA-STD-3001 V2 §6.2.1.2: EMU 4.3 psia 100 % O2 → PIO2 175 mmHg (E-ATM-04)."""
    assert physio.oxygenation(4.3 * physio.PSI_TO_KPA, 1.0)["pio2"] == pytest.approx(175, abs=1)


def test_sea_level_alveolar_gas() -> None:
    """StatPearls worked example: (760−47)·0.21 − 40/0.8 = 99.7 mmHg (E-EQ-02)."""
    assert physio.pao2(physio.pio2(760, 0.21)) == pytest.approx(99.7, abs=0.1)


def test_iss_cabin_is_normoxic() -> None:
    o = physio.oxygenation(physio.CABINS["iss"]["kpa"], 0.21)
    assert o["pio2_normoxic"] and 139 <= o["pio2"] <= 168


def test_severinghaus_p50_and_monotonic() -> None:
    assert physio.severinghaus(26.8) == pytest.approx(0.5, abs=0.01)  # P50 of normal blood ≈ 26.8 mmHg
    sats = [physio.severinghaus(p) for p in range(10, 150, 10)]
    assert all(b > a for a, b in zip(sats, sats[1:]))
    assert physio.severinghaus(0) == 0


def test_altitude_lowers_estimated_saturation() -> None:
    c = physio.altitude_curve()
    assert c[0]["sao2"] > c[-1]["sao2"] and c[0]["alt_m"] == 0
    with pytest.raises(ValueError):
        physio.pressure_at_altitude(50000)
    with pytest.raises(ValueError):
        physio.oxygenation(101, 2.0)


def test_co2_partial_pressure_depends_on_cabin() -> None:
    sea = physio.co2_level(3500, 101.325)
    ea = physio.co2_level(3500, 56.54)
    assert sea["level"] == "yellow" and ea["level"] == "green"  # same ppm, lower cabin pressure → lower ppCO2
    assert sea["ppm_at_limit"] == pytest.approx(3947, abs=5)


# ------------------------------------------------ gravity is NOT pressure, no invented curves
def test_gravity_effects_are_evidence_bound() -> None:
    r = physio.gravity_effects("flight", 120, baseline={"sys": 120, "dia": 78, "hr": 64})
    keys = {i["key"]: i for i in r["items"]}
    assert keys["bp_sys_24h"]["simulated_range"] == [110, 112]  # 120 − 10 … 120 − 8 (E-CV-04)
    assert all(i["evidence"] for i in r["items"] if i["status"] in ("evidence", "simulated"))


def test_gap_reported_not_interpolated() -> None:
    r = physio.gravity_effects("flight", 45)
    co = [i for i in r["items"] if i["key"] == "cardiac_output"][0]
    assert co["status"] == "gap" and co["simulated_range"] is None
    p = physio.gravity_effects("flight", 30, gravity="partial")
    assert p["items"] == [] and p["gap"]["id"] == "E-GAP-01"


def test_bone_extrapolation_flagged() -> None:
    proj = physio.bone_projection(360)
    assert proj[-1]["evidenced"] is False and proj[0]["evidenced"] is True
    r = physio.gravity_effects("flight", 300)
    assert any(i["status"] == "extrapolated" for i in r["items"])


def test_return_orthostatic_by_mission_length() -> None:
    assert physio.gravity_effects("return", 0, mission_days=14)["items"][0]["evidence"] == ["E-OI-01"]
    assert physio.gravity_effects("return", 0, mission_days=180)["items"][0]["evidence"] == ["E-OI-02"]
    assert physio.gravity_effects("return", 0, mission_days=60)["items"][0]["status"] == "gap"


# ------------------------------------------------ evidence registry integrity
REQUIRED = ("id", "indicator_ar", "value", "unit", "conditions_ar", "population_ar", "title", "organization",
            "date", "url", "locator", "limitations_ar", "kind", "finding_ar")


def test_evidence_entries_complete() -> None:
    ids = set()
    for e in physio.evidence():
        for k in REQUIRED:
            assert k in e, (e["id"], k)
        assert e["id"] not in ids
        ids.add(e["id"])
        assert e["kind"] in ("measured", "standard", "model", "default", "gap")
        if e["kind"] != "default":
            assert re.match(r"https://", e["url"]), e["id"]
        else:
            assert "CITATION NEEDED" in e["title"]  # defaults are never presented as NASA values


def test_every_threshold_links_to_evidence() -> None:
    ids = {e["id"] for e in physio.evidence()}
    for k, ind in config.thresholds()["indicators"].items():
        assert ind.get("evidence"), k
        assert set(ind["evidence"]) <= ids, k


def test_bundled_real_osdr_data_is_tagged_and_cited() -> None:
    import json

    path = config.ROOT / "data" / "real" / "OSD-575" / "OSD-575_glucose.fhir.json"
    obs = [e["resource"] for e in json.loads(path.read_text(encoding="utf-8"))["entry"]]
    assert len(obs) == 28
    for o in obs:
        assert o["meta"]["tag"][0]["code"] == "REAL" and o["meta"]["tag"][0]["display"] == "OSD-575"
        assert o["subject"]["reference"].startswith("Patient/OSD-575-C00")
        assert "10.1038/s41586-024-07639-y" in json.dumps(o)


def test_clinical_defaults_not_attributed_to_nasa() -> None:
    for k in ("heart_rate", "spo2", "systolic", "body_temp", "glucose"):
        assert config.thresholds()["indicators"][k]["citation"][0] == "clinical_default"
