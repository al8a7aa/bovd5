# Project submission form – draft text for every field

Paste each section into the matching field on the Space Apps Project page. Everything here is in English, as the rules require. Fill in or check the parts marked ✏️.

---

## Project Name
BÖVD – Explainable Offline Health Monitoring for Astronauts

## High-Level Project Summary
BÖVD is an offline health-monitoring app that lets astronauts check their own health on the ISS, on the Moon, in Mars transit and on Mars. An astronaut enters a measurement such as heart rate, blood pressure, blood sugar, temperature, sleep or mood. The app compares it first with that astronaut's own baseline, adjusted for the current gravity, and then with NASA and clinical reference ranges and recent trends. It then gives four clear answers: the status (green, yellow or red), why, the next step to take, and who to contact. Alerts go from the crew to the Crew Medical Officer and on to the flight surgeon over a simulated Earth link with the real Moon or Mars delay, so the crew is never left waiting for an answer from Earth. Every reading and threshold shows its source, and the app loads real NASA data from the Open Science Data Repository (study OSD-575, SpaceX Inspiration4). This matters because on a Mars mission a message to Earth takes 4–24 minutes one way. The crew must be able to understand and act on their own health data, and BÖVD gives them clear, explained guidance without needing medical training.

## Link to Project Demo
✏️ Upload `BOVD/deliverables/English/BOVD_Demo_30s.mp4` to YouTube (Unlisted) and paste that link here – YouTube plays it in the browser for judges.
Backup link (GitHub): https://github.com/al8a7aa/bovd5/blob/main/BOVD/deliverables/English/BOVD_Demo_30s.mp4
(29-second video, English captions, no voice – within the 30-second limit. It tours every slide and every app page. The 7-slide PDF also meets the rules if you prefer slides: https://github.com/al8a7aa/bovd5/blob/main/BOVD/deliverables/English/BOVD_Demo_7_slides.pdf)
Full presentation (16 slides, for the live pitch and for judges who want every detail): https://github.com/al8a7aa/bovd5/blob/main/BOVD/deliverables/English/BOVD_Full_Presentation.pdf – mention it in the Detailed Project Description, not as the demo link.

## Link to Final Project
✏️ https://github.com/al8a7aa/bovd5
(Public repository. Start with `README.md`; the app is in the `BOVD/` folder.)

## Detailed Project Description
**What it does**
- Records health indicators: heart rate, blood pressure, SpO₂, temperature, blood glucose, sleep, mood, stress, workload, cabin CO₂, radiation dose, body mass, exercise and urine values. Input is by keyboard, file import (CSV, FHIR) or camera (posture check only).
- Rates each value green, yellow or red and adds them into one 0–20 status score, shown on a ring and a clickable 3D human body.
- Explains every result in a "Why" panel: which spaceflight hazard it relates to, what rule fired, the next steps, who to contact and the scientific sources.
- Sends alerts at three priority levels from the crew to the Crew Medical Officer and to the ground flight surgeon, with a store-and-forward queue that simulates the Moon (≈1.3 s) and Mars (4–24 min) communication delay.
- Covers all five NASA hazards of human spaceflight: radiation (personal dose map and solar-storm shelter mode), isolation (sleep, mood and crew-harmony trends), distance (7 offline "Smart Doctor" protocols), gravity (gravity-aware baselines and a post-landing stand test) and closed environment (cabin CO₂ judged at the actual cabin pressure).
- Five roles with different access: astronaut, Crew Medical Officer, behavioral health specialist, flight surgeon and researcher.
- Gives guidance for all 17 indicators: why each check matters in space and how to stay healthy and prevent a critical condition, with sources.
- Optional NASA-grounded AI research assistant on the Smart Doctor page: a free OpenRouter model answers the astronaut's questions only from 116 bundled NASA and CSA excerpts and cites each one. It never diagnoses, and only the typed question leaves the device, with consent.
- Full 16-slide presentation: https://github.com/al8a7aa/bovd5/blob/main/BOVD/deliverables/English/BOVD_Full_Presentation.pdf

**How it works**
Validation → personal baseline (mean ± 2 SD of the astronaut's own early-flight or pre-flight readings) → reference thresholds → trend rules (for example, 3 short nights in a row turns red) → composite score → explanation and alert. All thresholds are in configuration files with a citation for each one, so a flight surgeon can review and change them. The app never diagnoses; it gives status, explanation, next step and who to contact.

**Benefits**
- Works with no internet or Earth link, which suits Moon and Mars missions.
- Easy to understand for non-doctors: colours with icons and labels, plain-language explanations, a guided tour, large-button "glove mode", high contrast, Arabic and English.
- Every value shows where it came from (REAL, SYNTHETIC or USER-ENTERED) and every rule shows its source.
- Health data stays on the device and is encrypted (AES-256-GCM); each feature asks for consent first.

**What we hope to achieve**
A tool that crews on the Artemis Moon base and future Mars missions could use for Earth-independent medical care. The same approach also fits Antarctic stations and remote clinics on Earth. Next steps: a flight-surgeon review of every threshold, more NASA data, a neutron-dose input similar to the CSA's CANS instrument, and usability tests with gloves in an analog mission.

**Tools and languages**
Python 3 (standard library only) for the server and the assessment engine; SQLite for storage; HTML, CSS and JavaScript with WebGL for the interface and the 3D body; FHIR R4 with LOINC codes for health records. Optional: OpenCV and MediaPipe for the camera posture check, and the cryptography library for faster encryption. Optional AI assistant through the OpenRouter API (free model router `openrouter/free`). Tested with pytest (151 automated tests). Starts on Windows by double-clicking `start.bat`; on macOS and Linux with `./start.sh`, or with Docker.

## Use of Super Intelligence (SI)
Yes. AI assistants (large language models such as Claude) helped write parts of the code, the documents, the translations between Arabic and English, and the 7-slide demo deck. The idea for the solution, the design decisions, the choice of data and the review of all generated output were the team's own work. The app itself includes an optional AI research assistant (a free OpenRouter language model) that answers only from bundled NASA and CSA sources. We did not use AI to generate images, audio or video for the project; all screenshots are of the running app (the separate Canva pitch deck uses Canva-generated space images). The AI use is stated in the repository README ("Use of AI tools"), in the demo deck (slide 7 and the file properties), in `pyproject.toml` (keyword `ai-assisted`) and in `Co-Authored-By` lines on commits made with an AI assistant.

## NASA Data
- **NASA Open Science Data Repository (OSDR), study OSD-575** – SpaceX Inspiration4 Blood Serum Metabolic Panel. https://osdr.nasa.gov/bio/repo/data/studies/OSD-575 – we use the serum glucose values for 4 crew members at 7 time points (3 before launch, 4 after return). The app loads them on first start as REAL data, converts them to FHIR health records and compares them with reference ranges. The built-in OSDR loader can import any other OSDR study in the same way.
- **NASA Human Research Program**: Five hazards of human spaceflight, Risks of human spaceflight, and Ongoing HRP research. These shape the hazard map in every explanation and the choice of indicators.
- **NASA-STD-3001 Vol. 1 and Vol. 2** (crew health; environmental health) – the 600 mSv career radiation limit and the cabin CO₂ limit.
- **NASA HRP evidence reports and NASA Technical Reports Server papers** – orthostatic intolerance, behavioral health, team risk, Exploration Medical Capability (Earth-independent medical operations), SANS and Artemis I radiation. The full list is in `BOVD/deliverables/English/SOURCES.md`.

## Space Agency Partner Data and Other References
Paste the text from `BOVD/deliverables/English/SUBMISSION_REFERENCES.md`. It lists:
- **CSA (Canadian Space Agency)**: "Monitoring radiation for astronaut health" (2026), used for the radiation module and our planned neutron-dose input, and "Why do we conduct science experiments in space?" (2025).
- The NASA data and publications above, all code libraries with their licences (Python, SQLite, OpenCV, MediaPipe and its model, NumPy, cryptography, pytest, python-docx, python-pptx), and a statement that all images are our own.

---

## Checklist before clicking "Submit for Judging"
- [ ] ✏️ Team name and every member's full name are on slide 1 of the deck (`config/team.json`, then `python scripts/build_demo_deck.py`).
- [ ] Branch merged into `main` and pushed, so the GitHub links above work.
- [ ] Demo and project links open in a private browser window with no login.
- [ ] Every field filled in, all in English.
- [ ] No images, video or audio of anyone under 18 (the app screenshots show no people).
- [ ] No NASA logos or branding in AI-generated content (none are used).
- [ ] Both checkboxes ticked: Terms and Conditions, and Confirm All Work is Original.
- [ ] Submitted before Sunday, November 15, 11:59 p.m. local time of your Local Event. You can still edit and resubmit until then.
