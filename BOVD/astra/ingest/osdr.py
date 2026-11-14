"""
BÖVD · REAL-data loader – NASA Open Science Data Repository (OSDR)
=========================================================================
Downloads study metadata / file lists from the public OSDR REST API and maps a
tabular file (CSV) to FHIR Observations with provenance ``REAL (<OSD-ID>)``.

Public endpoints used (no authentication; documented by NASA OSDR):
  * metadata : https://osdr.nasa.gov/osdr/data/osd/meta/{OSD_NUMBER}
  * files    : https://osdr.nasa.gov/osdr/data/osd/files/{OSD_NUMBER}
  * search   : https://osdr.nasa.gov/osdr/data/search?term={TERM}
  * file download = "https://osdr.nasa.gov" + study_files[i].remote_url

License: OSDR data are NASA open data; cite as "Data are courtesy of the NASA
Open Science Data Repository" plus the study's own citation (record it in the
mapping file – the loader copies it into the provenance tag).

NOTHING IS INVENTED: this loader only transforms what you downloaded. No real
dataset is bundled with the prototype; if a file is not present the loader
stops with instructions (see astra/ingest/README.md).

Usage (when online):
    python -m astra.ingest.osdr search "Inspiration4"
    python -m astra.ingest.osdr meta 575          # saves data/raw/OSD-575/meta.json
    python -m astra.ingest.osdr files 575         # saves file list
    python -m astra.ingest.osdr download 575 <remote_url>
    python -m astra.ingest.osdr map data/raw/OSD-575/<file>.csv mapping.json
"""
from __future__ import annotations

import csv
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from .. import fhir, validation
from ..config import DATA_DIR

BASE = "https://osdr.nasa.gov"


def _get(url: str) -> bytes:
    if not url.startswith(BASE + "/"):
        raise ValueError("only https://osdr.nasa.gov URLs are allowed")
    req = urllib.request.Request(url, headers={"User-Agent": "BÖVD-prototype"})  # noqa: S310 - https host checked above
    with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310  # nosec B310
        return bytes(r.read())


def raw_dir(osd: str) -> Path:
    d = DATA_DIR / "raw" / f"OSD-{osd.replace('OSD-', '')}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def search(term: str) -> Any:
    return json.loads(_get(f"{BASE}/osdr/data/search?term={urllib.parse.quote(term)}"))


def meta(osd: str) -> Path:
    n = osd.replace("OSD-", "")
    p = raw_dir(n) / "meta.json"
    p.write_bytes(_get(f"{BASE}/osdr/data/osd/meta/{n}"))
    return p


def files(osd: str) -> Path:
    n = osd.replace("OSD-", "")
    p = raw_dir(n) / "files.json"
    p.write_bytes(_get(f"{BASE}/osdr/data/osd/files/{n}"))
    return p


def download(osd: str, remote_url: str) -> Path:
    n = osd.replace("OSD-", "")
    name = urllib.parse.unquote(remote_url.rsplit("file=", 1)[-1].rsplit("/", 1)[-1])
    p = raw_dir(n) / name
    p.write_bytes(_get(BASE + remote_url))
    return p


def map_csv(path: Path, mapping: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    """Transform a downloaded CSV into Observations using a mapping file.

    mapping = {
      "dataset_id": "OSD-xxx", "license": "...", "citation": "...",
      "subject_column": "subject", "time_column": "timestamp",
      "columns": {"<csv column>": {"indicator": "heart_rate", "unit": "bpm"}},
      "gravity_context": "iss"
    }
    """
    if not path.exists():
        raise FileNotFoundError(f"{path} not found – download it first (see astra/ingest/README.md)")
    out: list[dict[str, Any]] = []
    errors: list[str] = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for i, row in enumerate(csv.DictReader(fh), start=2):
            subj = f"{mapping['dataset_id']}-{row[mapping['subject_column']]}"
            ts = row[mapping["time_column"]]
            for col, spec in mapping["columns"].items():
                if row.get(col) in (None, ""):
                    continue
                v = validation.validate(spec["indicator"], row[col], spec.get("unit"),
                                        {"time_of_day": ts, "restrained": None, "arm_position": None, "rested_5min": None})
                if not v.ok or v.value is None:
                    errors.append(f"line {i} {col}: {'; '.join(v.errors)}")
                    continue
                out.append(fhir.make_observation(subj, spec["indicator"], v.value, ts,
                                                 {"type": "REAL", "ref": mapping["dataset_id"]},
                                                 {"source_file": path.name, "license": mapping.get("license", ""),
                                                  "citation": mapping.get("citation", "")},
                                                 mapping.get("gravity_context", "iss")))
    return out, errors


def main(argv: list[str]) -> int:  # pragma: no cover - network CLI
    cmd, *args = argv
    if cmd == "search":
        print(json.dumps(search(args[0]), indent=1)[:4000])
    elif cmd == "meta":
        print(meta(args[0]))
    elif cmd == "files":
        print(files(args[0]))
    elif cmd == "download":
        print(download(args[0], args[1]))
    elif cmd == "map":
        obs, errs = map_csv(Path(args[0]), json.loads(Path(args[1]).read_text(encoding="utf-8")))
        outp = Path(args[0]).with_suffix(".fhir.json")
        outp.write_text(json.dumps(fhir.bundle(obs), indent=1), encoding="utf-8")
        print(f"{len(obs)} observations → {outp}; {len(errs)} errors")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
