# References field – text for the NASA Space Apps project submission form

Copy the block below into the **References** field. It lists every external resource the project uses: the challenge resources, data, publications, code, models and images. The full APA list with all 33 publications is in `SOURCES.md`.

---

**Challenge resources (NASA Space Apps 2026 – Create Health Monitoring Software for Astronauts on Space Missions)**
- NASA Human Research Program. (n.d.). Five hazards of human spaceflight. https://www.nasa.gov/hrp/hazards – the five hazards (Radiation, Isolation, Distance, Gravity, Environment) are the app's hazard map and appear in every "Why" panel.
- NASA Human Research Program. (2026, July 21). Risks of human spaceflight. https://www.nasa.gov/hrp/risks/ – the risk areas behind the monitored indicators (cardiovascular, SANS, sleep, behavioral health, bone, nutrition, radiation).
- NASA Human Research Program. (2026, August 18). Ongoing HRP research in space. https://www.nasa.gov/hrp/ongoing-hrp-research/ – background for the sleep, mood and well-being tracking and for the "standard measures" approach.
- Canadian Space Agency. (2026, February 26). Monitoring radiation for astronaut health. https://www.asc-csa.gc.ca/eng/news/articles/2026/2026-02-26-monitoring-radiation-astronaut-health.asp – background for the personal radiation dose module (F5).
- Canadian Space Agency. (2025). Why do we conduct science experiments in space? https://www.asc-csa.gc.ca/eng/iss/science/why-do-we-conduct-science-experiments-in-space.asp – background on how weightlessness affects bones, heart, blood vessels and brain.

**NASA data**
- NASA Open Science Data Repository, study OSD-575: SpaceX Inspiration4 Blood Serum Metabolic Panel and Immune/Cardiac Cytokine Arrays. https://osdr.nasa.gov/bio/repo/data/studies/OSD-575 – serum glucose for 4 crew members at 7 time points, bundled as REAL data. Data are courtesy of the NASA Open Science Data Repository.
- Overbey, E. G., et al. (2024). The Space Omics and Medical Atlas (SOMA) and international astronaut biobank. Nature. https://doi.org/10.1038/s41586-024-07639-y
- NASA Open Science Data Repository. https://osdr.nasa.gov – the built-in loader imports any other OSDR study.

**Standards and evidence used for thresholds** (full list in SOURCES.md)
- NASA-STD-3001 Vol. 1 Rev. C (crew health; 600 mSv career radiation limit) and Vol. 2 Rev. D (cabin CO2). https://standards.nasa.gov/
- NASA HRP evidence reports: orthostatic intolerance (2015), behavioral conditions (2015), team risk (2022).
- Barger et al. (2014) on sleep in spaceflight; George et al. (2024) on Artemis I radiation; Lee et al. (2020) on SANS; Smith et al. (1999, 2012) on calcium; Scott et al. (2023) and English et al. (2020) on exercise.

**Software, libraries and models**
- Python 3 standard library (PSF License) and SQLite (public domain) – the whole app runs on these.
- cryptography (Apache-2.0 / BSD-3-Clause) – optional; speeds up AES-256-GCM encryption.
- OpenCV, opencv-python-headless (Apache-2.0), MediaPipe (Apache-2.0) and NumPy (BSD-3-Clause) – optional camera posture check.
- MediaPipe Pose Landmarker "lite" model from Google, downloaded at first start. Model card and licence: https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker
- pytest (MIT) for tests; python-docx and python-pptx (MIT) to generate the documents and slides.
- OpenRouter API (https://openrouter.ai) with the free model router `openrouter/free` – used only by the optional F11 AI research assistant, which answers from the bundled NASA/CSA sources.

**Images and media**
- All screenshots, diagrams, the 3D body figure, icons and the logo were made by the team. No third-party images, music or fonts are used.

---

Note: if your team used AI coding assistants, say so in the project description too. Being open about it is good practice.
