# 🛰️ BÖVD

**NASA Space Apps Challenge 2026 – Create Health Monitoring Software for Astronauts on Space Missions**

> Hackathon prototype for decision support and training only. NOT a certified medical device. Designed in alignment with the listed standards; not audited or certified. The app never gives a diagnosis: it gives status + explanation + recommended next step + who to contact. All thresholds are configurable and must be reviewed by a flight surgeon. Experimental features are labelled "EXPERIMENTAL – research concept".

Offline-first, explainable health decision support for astronauts in 0 g, on the Moon (1/6 g), in Mars transit and on Mars (3/8 g).
Interface: **HTML/JavaScript** · Logic: **Python (standard library only)** · Start: **`start.bat`** · Data stays on `127.0.0.1`.

## تشغيل سريع (Windows)
1. ثبّت Python 3.10 أو أحدث من python.org وفعّل خيار **Add python.exe to PATH**.
2. فك ضغط المجلد، ثم انقر نقرًا مزدوجًا على **`start.bat`**.
3. يفتح المتصفح تلقائيًا على `http://127.0.0.1:8765` – سجّل الدخول بأحد الحسابات التجريبية (كلمة المرور `astra2026`).
4. لإيقاف البرنامج أغلق نافذة الأوامر. لإعادة البيانات التجريبية: `reset_data.bat`. للاختبارات: `run_tests.bat`.

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
- F1 Voice (EXPERIMENTAL) · F2 Eye of Truth · F3 Crew Harmony · F4 Smart Doctor · F5 Radiation Map · F6 Urine analytics · F7 Coach · F8 Smart Nostalgia · F9 Black Box.
- Encryption at rest (AES-256-GCM), FHIR R4 + LOINC + UCUM, provenance badges, Arabic/English RTL, glove & high-contrast modes.

## Documents
`deliverables/CODE_EXPLAINED.docx` · `deliverables/ISO_STANDARDS_ALIGNMENT.docx` · `deliverables/BOVD_Presentation.pptx` ·
`SOURCES.md` · `RISK_REGISTER.md` · `TRACEABILITY.md` · `PROJECT_STATUS.md` · `PRIVACY.md` · `sbom.spdx.json` · `CODE_EXPLAINED.md`

## Quality
109 pytest tests · coverage (stdlib tracer) engine+validation+features ≈ 97 % · ruff clean · mypy --strict clean.
