# REAL data: NASA OSDR OSD-575 (SpaceX Inspiration4)

**Source:** NASA Open Science Data Repository, study OSD-575, “SpaceX Inspiration4 Blood Serum Metabolic Panel and Immune/Cardiac Cytokine Arrays”. https://osdr.nasa.gov/bio/repo/data/studies/OSD-575

**Licence and credit:** NASA open data. Data are courtesy of the NASA Open Science Data Repository.

**Study citation:** Overbey, E. G., et al. (2024). The Space Omics and Medical Atlas (SOMA) and international astronaut biobank. *Nature*. https://doi.org/10.1038/s41586-024-07639-y

## What is used
- File: `LSDS-8_Comprehensive_Metabolic_Panel_CMP_TRANSFORMED.csv` (downloaded to `data/raw/OSD-575/`, not committed).
- Column: `glucose_value_milligram_per_deciliter`.
- 4 crew members (C001–C004) × 7 time points: L-92, L-44, L-3 days before launch and R+1, R+45, R+82, R+194 days after return. 28 values.

## How it was transformed
`python scripts/build_osd575.py`
1. Day labels become dates: L-n counts back from launch day 2021-09-16, R+n counts on from return day 2021-09-18. The time is set to 12:00 UTC because the sampling time is not in the source table.
2. Pre-launch samples get the gravity context `earth_preflight`; post-return samples get `earth_postflight`.
3. `astra.ingest.osdr.map_csv` validates each value and writes FHIR R4 Observations (LOINC 2339-0, mg/dL) tagged `REAL (OSD-575)`, with the licence and citation attached.

## Files here
- `glucose_earth_preflight.csv`, `glucose_earth_postflight.csv`: the derived tables.
- `mapping_earth_preflight.json`, `mapping_earth_postflight.json`: the loader mappings.
- `OSD-575_glucose.fhir.json`: the bundle the app loads on first start (crew “Inspiration4 C001–C004 (REAL, OSD-575)”).

## Notes for interpretation
- Inspiration4 was a 3-day private mission in low Earth orbit; these are not long-duration astronauts.
- There are only 3 pre-flight samples per person, fewer than the 5 the app needs for a personal baseline, so the app compares these values with Earth reference ranges only.
- Some R+45 values are below 54 mg/dL and show as red. They are the values in the source table; the study data alone doesn’t explain them.
