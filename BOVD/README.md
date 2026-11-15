# 🛰️ BÖVD

**NASA Space Apps Challenge 2026 – Create Health Monitoring Software for Astronauts on Space Missions**

> Hackathon prototype for decision support and training only. NOT a certified medical device. Designed in alignment with the listed standards; not audited or certified. The app never gives a diagnosis: it gives status + explanation + recommended next step + who to contact. All thresholds are configurable and must be reviewed by a flight surgeon. Experimental features are labelled "EXPERIMENTAL – research concept".

Offline-first, explainable health decision support for astronauts in 0 g, on the Moon (1/6 g), in Mars transit and on Mars (3/8 g).
Interface: **HTML/JavaScript** · Logic: **Python (standard library only)** · Start: **`start.bat`** · Data stays on `127.0.0.1`.

## Quick start (Windows)
1. Install Python 3.10 or newer from python.org and tick **Add python.exe to PATH**.
2. Unzip the folder and double-click **`start.bat`**.
3. The browser opens `http://127.0.0.1:8765`. Log in with a demo account (password `astra2026`).
4. To stop, close the command window. Reset the demo data with `reset_data.bat`; run the tests with `run_tests.bat`.

macOS/Linux: `./start.sh` · Docker: `docker compose up`

| User | Role |
|---|---|
| astro1 / astro3 | astronaut |
| cmo1 | crew medical officer |
| bhs1 | behavioral health specialist |
| surgeon1 | ground flight surgeon |
| research1 | researcher (pseudonymised export only) |

## 2-minute judge demo
1. Double-click start.bat → browser opens http://127.0.0.1:8765 (demo crew is created with SYNTHETIC data, purple badges).
2. Log in as astro1 → Dashboard: status ring 0–20, body figure, latest readings with provenance; tap the heart → WHY panel with citations.
3. Measure → conditions step (restrained, 5-min rest) → enter HR 128, sleep 4.5, mood 2 → Submit: RED with explanation, next step, who to contact, Smart Doctor link.
4. Top banner flashes red (HIGH priority). Log out → surgeon1: only alerts that ARRIVED over the delayed link are visible; acknowledge → 'in transit'.
5. Mission & Routine → add event 'landing' to mars_surface → Gravity Transition Protocol + stand test (HR +36 → yellow). Delay chip shows Mars minutes.
6. Radiation → Start SPE → purple banner, countdown, shelter zone, dose saved. Black Box → tamper demo shows the hash chain catching an edit.

## What is inside
- Core: validation → personal baseline (gravity-aware) → thresholds → trends → composite 0–20 → WHY → alerts (3 priorities, escalation, Moon/Mars delay).
- F1 Voice (EXPERIMENTAL) · F2 Eye of Truth · F3 Crew Harmony · F4 Smart Doctor · F5 Radiation Map · F6 Urine analytics · F7 Coach · F8 Smart Nostalgia · F9 Black Box · F10 camera posture check.
- Encryption at rest (AES-256-GCM), FHIR R4 + LOINC + UCUM, provenance badges, Arabic/English RTL, glove & high-contrast modes.
- Version 2 (November 2026): new visual identity, animated intro, 3D body with how-to animations for each check, camera posture check (OpenCV + MediaPipe, with a manual mode), 29-entry evidence register, environment simulation, 11-step guided tour, responsive layout. The camera checks posture only; it never measures vital signs.

## NASA data
- **REAL:** NASA Open Science Data Repository study **OSD-575** (SpaceX Inspiration4): serum glucose for 4 crew members at 7 time points before and after flight, loaded on first start with a REAL badge. See `data/real/OSD-575/README.md`.
- The built-in OSDR loader imports any other OSDR study (`astra/ingest/README.md`).
- Everything else in the demo crew is clearly labelled SYNTHETIC.

## Documents (English)
- Submission: `deliverables/English/BOVD_Demo_7_slides.pptx` (7-slide demo) · `deliverables/English/SUBMISSION_REFERENCES.md` (text for the References field)
- Full deck and reports: `deliverables/English/BOVD_Presentation.pptx` · `deliverables/English/CODE_EXPLAINED.docx` · `deliverables/English/ISO_STANDARDS_ALIGNMENT.docx`
- `deliverables/English/`: `SOURCES.md` · `RISK_REGISTER.md` · `TRACEABILITY.md` · `PROJECT_STATUS.md` · `PRIVACY.md` · `CODE_EXPLAINED.md` · `sbom.spdx.json`
- Arabic versions: `README_AR.md` and the files in `deliverables/` and the project root.

## Quality
140 pytest tests · coverage (stdlib tracer) engine+validation+features ≈ 97 % · ruff clean · mypy --strict clean.
