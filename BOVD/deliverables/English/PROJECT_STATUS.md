# PROJECT STATUS

## Done
- Local Python server (standard library only) + HTML/JS UI, one-click start.bat
- SQLite WAL storage, AES-256-GCM field encryption, FHIR R4 Observations with LOINC/UCUM and provenance
- Validation, personal-baseline (±2 SD) engine, Earth thresholds, trend rules, composite score 0–20, WHY panels
- 3-priority alerts, escalation crew → CMO → flight surgeon, store-and-forward queue with Moon/Mars delay
- Gravity contexts + Gravity Transition Protocol + post-landing stand test
- F4 Smart Doctor (7 protocols, lint gate), F5 radiation map + SPE mode, F2 vision screening + image compare
- F6 urinalysis adapter + schema, F7 coach within prescription bounds, F9 hash-chained black box + OAIS export
- 10 synthetic scenarios with SYNTHETIC badges; Arabic/English with RTL; role-based access (5 roles)

## Partial
- F1 voice: on-device feature extraction implemented in the browser; accuracy not validated (EXPERIMENTAL)
- F2 webcam blink: crude luminance method, EXPERIMENTAL; MediaPipe not bundled (offline, no download)
- F3 crew index and F8 connection: logic complete, weights are examples awaiting expert review
- REAL data: NASA OSDR OSD-575 (Inspiration4 serum glucose, 4 crew × 7 time points) bundled and loaded on first start; other indicators still use labelled synthetic data. The OSDR loader imports more studies
- PWA: offline cache and IndexedDB outbox; the app also needs the local Python server running

## Next
- Flight-surgeon review of every threshold and protocol
- Usability test with gloved/floating users (analog mission)
- Full-database encryption (SQLCipher) and HSM key storage
- Validate voice / blink signals on consented real data; bias evaluation
- React/FastAPI build variant described in the brief, if the team wants it

