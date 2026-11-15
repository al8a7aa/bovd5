# 🛰️ BÖVD – health monitoring for astronauts

**NASA Space Apps Challenge 2026 – Create Health Monitoring Software for Astronauts on Space Missions**

BÖVD is an offline, explainable health decision-support app for astronauts on the ISS, on the Moon, in Mars transit and on Mars. For every reading it answers four questions: what is my status, why, what should I do next, and who should I contact. It runs on a laptop with no internet and uses real NASA data from the Open Science Data Repository (study OSD-575, SpaceX Inspiration4).

> Hackathon prototype for decision support and training only. Not a certified medical device.
> AI assistants helped write parts of the code, documents and demo deck; see "Use of AI tools" in [BOVD/README.md](BOVD/README.md).

## Start
1. Install Python 3.10 or newer (tick **Add python.exe to PATH**).
2. Double-click `BOVD/start.bat`. The app opens at `http://127.0.0.1:8765`.
3. Log in as `astro1`, `cmo1` or `surgeon1` with the password `astra2026`.

macOS/Linux: `BOVD/start.sh` · Docker: `docker compose up` in `BOVD/`

## Where to look
- [BOVD/README.md](BOVD/README.md) – full description, judge demo script, features and data
- [BOVD/deliverables/English/BOVD_Demo_7_slides.pdf](BOVD/deliverables/English/BOVD_Demo_7_slides.pdf) – 7-slide demo (also as .pptx)
- [BOVD/deliverables/English/BOVD_Full_Presentation.pdf](BOVD/deliverables/English/BOVD_Full_Presentation.pdf) – full 16-slide presentation
- [BOVD/deliverables/English/SOURCES.md](BOVD/deliverables/English/SOURCES.md) – references (APA 7) and datasets
- [BOVD/data/real/OSD-575/README.md](BOVD/data/real/OSD-575/README.md) – the real NASA data and how it was transformed
- [BOVD/README_AR.md](BOVD/README_AR.md) – Arabic version
