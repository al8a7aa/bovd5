"""
Build the REAL-data bundle from NASA OSDR study OSD-575 (SpaceX Inspiration4).

Input  : data/raw/OSD-575/LSDS-8_Comprehensive_Metabolic_Panel_CMP_TRANSFORMED.csv
         (download it first:  python -m astra.ingest.osdr download 575
          "/geode-py/ws/studies/OSD-575/download?source=datamanager&file=LSDS-8_Comprehensive_Metabolic_Panel_CMP_TRANSFORMED.csv")
Output : data/real/OSD-575/  – derived CSVs, mapping files and OSD-575_glucose.fhir.json

The OSDR table labels each sample with a crew ID and a day relative to launch (L-n) or
return (R+n), not a date. Dates are derived from the mission dates below, at 12:00 UTC
because the sampling time of day is not in the table. Every observation is tagged
REAL (OSD-575) and keeps the source file, licence and study citation.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from astra import fhir  # noqa: E402
from astra.ingest import osdr  # noqa: E402

SRC = ROOT / "data" / "raw" / "OSD-575" / "LSDS-8_Comprehensive_Metabolic_Panel_CMP_TRANSFORMED.csv"
OUT = ROOT / "data" / "real" / "OSD-575"
LAUNCH = datetime(2021, 9, 16, 12, tzinfo=timezone.utc)      # Inspiration4 launch day (UTC)
SPLASHDOWN = datetime(2021, 9, 18, 12, tzinfo=timezone.utc)  # Inspiration4 return day (UTC)
CITATION = ("Overbey, E. G., et al. (2024). The Space Omics and Medical Atlas (SOMA) and international astronaut "
            "biobank. Nature. https://doi.org/10.1038/s41586-024-07639-y. Dataset: NASA OSDR OSD-575, SpaceX "
            "Inspiration4 Blood Serum Metabolic Panel and Immune/Cardiac Cytokine Arrays, https://osdr.nasa.gov/bio/repo/data/studies/OSD-575")
LICENSE = "NASA open data – Data are courtesy of the NASA Open Science Data Repository"
SAMPLE = re.compile(r"^(C\d{3})_serum_([LR])([+-])(\d+)$")


def derive() -> dict[str, list[dict[str, str]]]:
    rows: dict[str, list[dict[str, str]]] = {"earth_preflight": [], "earth_postflight": []}
    with open(SRC, newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            m = SAMPLE.match(r["Sample Name"])
            if not m:
                raise ValueError(f"unexpected sample name {r['Sample Name']!r}")
            crew, phase, sign, days = m.group(1), m.group(2), m.group(3), int(m.group(4))
            anchor = LAUNCH if phase == "L" else SPLASHDOWN
            ts = anchor + timedelta(days=days if sign == "+" else -days)
            ctx = "earth_preflight" if phase == "L" else "earth_postflight"
            rows[ctx].append({"subject": crew, "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                              "day_label": f"{phase}{sign}{days}", "sample": r["Sample Name"],
                              "glucose_mg_dl": r["glucose_value_milligram_per_deciliter"]})
    return rows


def main() -> int:
    if not SRC.exists():
        print(f"Missing {SRC}. Download it first (see this script's docstring).")
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    obs: list[dict] = []
    for ctx, rows in derive().items():
        csv_path = OUT / f"glucose_{ctx}.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        mapping = {"dataset_id": "OSD-575", "license": LICENSE, "citation": CITATION,
                   "subject_column": "subject", "time_column": "timestamp", "gravity_context": ctx,
                   "columns": {"glucose_mg_dl": {"indicator": "glucose", "unit": "mg/dL"}}}
        (OUT / f"mapping_{ctx}.json").write_text(json.dumps(mapping, indent=1, ensure_ascii=False), encoding="utf-8")
        part, errors = osdr.map_csv(csv_path, mapping)
        if errors:
            print("\n".join(errors))
            return 1
        obs += part
        print(f"{ctx}: {len(part)} observations")
    bundle_path = OUT / "OSD-575_glucose.fhir.json"
    bundle_path.write_text(json.dumps(fhir.bundle(obs), indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{len(obs)} REAL observations → {bundle_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
