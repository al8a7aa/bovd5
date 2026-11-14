"""
BÖVD · config loader
============================
Loads the JSON configuration files from ./config. Every clinical value lives in
configuration, never in code, so that a flight surgeon can review and change it
(HONESTY STATEMENT: all thresholds are configurable and must be reviewed).

Standards alignment (designed in alignment with, not certified):
  * ISO 13485 §4.2.4 – document control: configuration files are versioned
    artefacts with a review status field (`_review_status`).
  * IEC 62304 §5.1 – software development planning: configuration items are
    identified separately from software items.
"""
from __future__ import annotations

import json
import os
from functools import cache
from pathlib import Path
from typing import Any

#: Project root (folder that contains config/, web/, data/).
ROOT: Path = Path(__file__).resolve().parent.parent
CONFIG_DIR: Path = ROOT / "config"
WEB_DIR: Path = ROOT / "web"
DATA_DIR: Path = Path(os.environ.get("ASTRA_DATA_DIR", str(ROOT / "data")))
DB_DIR: Path = DATA_DIR / "db"


@cache
def load(name: str) -> dict[str, Any]:
    """Return the parsed JSON file ``config/<name>.json`` (cached)."""
    with open(CONFIG_DIR / f"{name}.json", encoding="utf-8") as fh:
        data: dict[str, Any] = json.load(fh)
    return data


def thresholds() -> dict[str, Any]:
    """Default thresholds (applied after the personal-baseline check)."""
    return load("thresholds")


def references() -> dict[str, Any]:
    """APA 7 references, keyed by citation id (see config/references.json)."""
    return {k: v for k, v in load("references").items() if not k.startswith("_")}


def gravity() -> dict[str, Any]:
    """Gravity contexts (ISS, Moon, Mars transit, Mars surface, rover)."""
    return load("gravity_contexts")


def features() -> dict[str, Any]:
    """Feature flags + feature configuration."""
    return load("features")


def protocols() -> dict[str, Any]:
    """F4 decision-tree protocols."""
    return load("cdss_protocols")


def cite(keys: list[str]) -> list[dict[str, str]]:
    """Resolve citation keys to ``{key, apa, url}`` dicts.

    Unknown keys are returned as ``[CITATION NEEDED]`` – we never invent a
    reference (PART 7 of the brief).
    """
    refs = references()
    out: list[dict[str, str]] = []
    for k in keys:
        r = refs.get(k)
        if r is None:
            out.append({"key": k, "apa": "[CITATION NEEDED]", "url": ""})
        else:
            out.append({"key": k, "apa": str(r["apa"]), "url": str(r.get("url", ""))})
    return out
