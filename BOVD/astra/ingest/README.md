# REAL data ingest (data/ingest)

The prototype bundles one real dataset: **NASA OSDR OSD-575** (SpaceX Inspiration4 serum glucose, 4 crew × 7 time points),
built with `scripts/build_osd575.py` and loaded on first start. See `data/real/OSD-575/README.md`.
Nothing in this repository is invented and labelled REAL. Other studies get REAL provenance only after you download
and map them with the loader below.

| Source | ID / URL | License / access | Fields used | Transformation |
|---|---|---|---|---|
| NASA Open Science Data Repository (OSDR) | Study accession `OSD-<n>` chosen by you, https://osdr.nasa.gov | NASA open data – credit "Data are courtesy of the NASA Open Science Data Repository" + study citation | Columns you list in `mapping.json` (e.g. heart rate, SpO2, timestamps) | CSV → validation → FHIR R4 Observation (LOINC + UCUM), provenance `REAL (OSD-n)`, subject = `OSD-n-<subject>` |
| NASA Life Sciences Portal (NLSP) | https://nlsp.nasa.gov | Many human datasets require a data request (privacy). Manual download only. | As above, after approval | Same mapping file approach |
| HRP evidence reports | see SOURCES.md | Public PDFs | Not data – used to justify thresholds and explanations | Cited in config/thresholds.json |

## Steps (OSDR)
1. Find a study: `python -m astra.ingest.osdr search "Inspiration4"` (or browse https://osdr.nasa.gov).
2. Save metadata and file list: `python -m astra.ingest.osdr meta <n>` and `... files <n>` → `data/raw/OSD-<n>/`.
3. Download a tabular file: `python -m astra.ingest.osdr download <n> "<remote_url from files.json>"`.
   If the API is unreachable, download manually from the study page into `data/raw/OSD-<n>/`.
4. Copy `mapping.example.json`, fill in `dataset_id`, `license`, `citation`, the subject/time columns and the
   column → indicator map, then run `python -m astra.ingest.osdr map data/raw/OSD-<n>/<file>.csv mapping.json`.
5. Import the resulting `.fhir.json` bundle in the app (Settings → Import FHIR bundle).

Record the dataset ID, URL, license, fields and transformations in `SOURCES.md` before submission.
