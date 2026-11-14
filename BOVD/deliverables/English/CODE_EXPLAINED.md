# CODE EXPLAINED (Markdown edition)

Hackathon prototype for decision support and training only. NOT a certified medical device. Designed in alignment with the listed standards; not audited or certified. The app never gives a diagnosis: it gives status + explanation + recommended next step + who to contact. All thresholds are configurable and must be reviewed by a flight surgeon. Experimental features are labelled "EXPERIMENTAL – research concept".

## Folder tree
```
BÖVD/
├── start.bat              one-click start (Windows)   · start.sh (macOS/Linux) · docker-compose.yml
├── run_tests.bat          tests + coverage            · reset_data.bat
├── config/                every clinical value lives here (reviewable JSON)
│   ├── thresholds.json    default thresholds + citations + "review needed"
│   ├── gravity_contexts.json   ISS / Moon / Mars transit / Mars surface / rover + GTP
│   ├── cdss_protocols.json     F4 decision trees + approved onboard items
│   ├── features.json      flags, consent categories, coach bounds, menu, habitat zones
│   ├── body_regions.json  body figure texts, five hazards
│   ├── references.json    APA 7 list (PART 7)   · standards.json · project_status.json
├── astra/                 Python package (standard library only)
│   ├── config.py  crypto.py  fhir.py  storage.py  validation.py  engine.py
│   ├── alerts.py  auth.py  consent.py  service.py  synthetic.py  server.py
│   ├── ingest/osdr.py     REAL-data loader (NASA OSDR) + README + mapping example
│   └── features/          cdss · radiation · vision · urine · coach · voice · crew · connection · blackbox
├── web/                   HTML/CSS/JS UI (no build step): index.html app.js features.js voice.js i18n.js sw.js
├── tests/                 pytest: test_core.py test_features.py test_api.py
├── scripts/               coverage_lite.py · build_deliverables.py · content.py
├── data/                  db/ (encrypted SQLite, keys) · raw/ (downloaded datasets) · media/<id>/ (family media)
└── deliverables/          docx · pptx · img/
```
## Modules
### config.py
Loads JSON configuration; resolves citation keys to APA strings; unknown keys become [CITATION NEEDED].
*Standards (alignment):* ISO 13485 §4.2.4 document control
```python
def cite(keys):
    ...
    if r is None:
        out.append({'key': k, 'apa': '[CITATION NEEDED]', 'url': ''})
```
### crypto.py
AES-256-GCM. Uses OpenSSL via 'cryptography' when present; otherwise a pure-Python NIST SP 800-38D implementation (T-table AES + GHASH) verified bit-for-bit against OpenSSL in tests. Tokens are 'v1:' + base64(nonce‖ciphertext‖tag).
*Standards (alignment):* ISO/IEC 27002 §8.24; ISO 27799
```python
def encrypt(self, plaintext, aad=b''):
    nonce = os.urandom(12)
    ct = self._fast.encrypt(nonce, plaintext, aad or None) if self._fast else py_encrypt(...)
    return 'v1:' + base64.b64encode(nonce + ct).decode()
```
### fhir.py
Builds FHIR R4 Observations: LOINC + internal indicator coding, UCUM valueQuantity, ISO 8601 UTC time, measurement-condition and gravity-context extensions, provenance in meta.tag.
*Standards (alignment):* HL7 FHIR R4, LOINC, UCUM, ISO 8601, ISO 13606
```python
'meta': {'tag': [{'system': '.../provenance', 'code': prov['type'], 'display': prov['ref']}]},
'valueQuantity': {'value': value, 'unit': ind['unit'], 'system': 'http://unitsofmeasure.org', 'code': ind['ucum']}
```
### storage.py
SQLite in WAL mode with field-level encryption of all health payloads. The black box table is append-only (triggers) and SHA-256 hash-chained; every write lands there.
*Standards (alignment):* ISO/IEC 27002 §8.15; ISO 14721
```python
CREATE TRIGGER bb_no_update BEFORE UPDATE ON blackbox
  BEGIN SELECT RAISE(ABORT, 'black box is append-only'); END;
h = sha256(prev ‖ ts ‖ actor ‖ category ‖ payload_enc)
```
### validation.py
Plausibility ranges, unit conversion to SI/UCUM, systolic > diastolic, and condition metadata (rule 2) that lowers confidence when incomplete.
*Standards (alignment):* ISO/IEC 25012; ISO 80000; IEC 62366-1 §5.7
```python
REQUIRED_CONDITIONS = ('time_of_day', 'restrained', 'arm_position', 'rested_5min')
```
### engine.py
Gravity-aware personal baseline (early-flight in 0 g, pre-flight in 1 g/partial g) → Earth thresholds → trend rules → composite 0–20 → WHY panel with hazard, explanation, actions, contact, protocol link and citations.
*Standards (alignment):* IEC 62304 class B; ISO 14971 controls R-01…R-06; ISO/IEC 22989 transparency
```python
if dev:
    level = worst(level, 'yellow')
elif base and e_level == 'yellow' and soften:
    level = 'green'   # RED is never softened
```
### alerts.py
Three priorities, de-duplication, repeat-until-ack, escalation crew → CMO → flight surgeon, store-and-forward queue with light-time delay in both directions.
*Standards (alignment):* IEC 60601-1-8 §6.1/§6.3; EIMO
```python
POLICY = {'high': {'repeat_s': 30, 'escalate_s': 120}, 'medium': {...600, 1800}, 'low': {None, None}}
```
### auth.py / consent.py
PBKDF2 passwords, HS256 JWT, 5 roles with least-privilege permissions; consent gate called by every feature before any write.
*Standards (alignment):* ISO/IEC 27002 §5.15, §8.5; ISO/IEC 29100 §5.2
```python
def require(store, feature, aid, category=None):
    if not is_enabled(store, feature): raise ConsentError(...)
```
### service.py
Orchestrates the workflow input → validation → assessment → explanation → action → escalation → follow-up; dashboard aggregation; Gravity Transition Protocol and stand test.
*Standards (alignment):* IEC 62304 §5.3
```python
v = validation.validate(...); a = engine.assess(...); store.add_observation(obs); alerts.raise_alert(store, aid, a)
```
### synthetic.py
Ten scenarios calibrated on published ranges; every value tagged SYNTHETIC(<scenario>).
*Standards (alignment):* ISO 14971 R-15
```python
fhir.make_observation(aid, ind, v, ts, {'type': 'SYNTHETIC', 'ref': scen}, ...)
```
### server.py
Standard-library HTTP server on 127.0.0.1: REST API (route table → OpenAPI 3), static UI, 5-s background tick, polling endpoint instead of WebSocket.
*Standards (alignment):* ISO/IEC 27002 §8.20
```python
@route('POST', '/api/readings')
def r_readings(c): ...
```
### web/*
Vanilla JS UI: Arabic/English with RTL, high-contrast and glove modes, body SVG, SVG charts with baseline band and gravity markers, measurement wizard, IndexedDB offline outbox, service worker.
*Standards (alignment):* IEC 62366-1; ISO 9241-110/-125; WCAG AA
```python
const lvl = (l) => `<span class="lvl ${l}">${ICON[l]} ${t('level_' + l)}</span>`;  // colour + icon + text
```
## Microgravity rules
| Rule | Where | Behaviour |
|---|---|---|
| 1 Personal baseline first | engine.baseline / engine.assess | z-score vs own early-flight (0 g) or pre-flight baseline, then Earth thresholds |
| 2 Fixed measurement conditions | validation.REQUIRED_CONDITIONS, fhir EXT_CONDITIONS, wizard step 1 | conditions stored with every reading; confidence lowered if missing |
| 3 No standing in 0 g | service.record_stand_test, start_gtp | stand test only where context allows; landing triggers GTP |
| 4 Body mass via mass-measurement device | indicator body_mass, MICRO.mass | manual entry; % loss feeds coach |
| 5 Sleep vs crew schedule | DEFAULT_ROUTINE, MICRO.sleep, trend rule | 16 sunrises/day note; consecutive short-night rule |
| 6 Exercise vs plan | features/coach.py | ARED/treadmill/cycle minutes inside prescription bounds |
| 7 Gravity context switch | config/gravity_contexts.json, alerts.current_delay_s, set_gravity | changes baseline, tests, delay and advice |
| 8 UI for floating users | web/styles.css (.big, .hc), wizard | 56–72 px targets, any orientation, visual alarms |

## Features
### F1 · Voice Reading 🎙️ (EXPERIMENTAL)
`features/voice.py + web/voice.js` – Opt-in 60-s check-in (fixed sentence + free talk). The browser computes F0 mean/SD, energy, speech rate, pause ratio, jitter and shimmer with the Web Audio API and drops the samples immediately. Server compares with the astronaut's own baseline (directional z-scores) → low/medium/high signal, then combines with sleep and mood before suggesting a check-in. Wording never labels a condition. Dehydration hypothesis OFF. (Mishra et al., 2026; NASA Human Research Program, 2015b).
### F2 · Eye of Truth 👁️
`features/vision.py` – Screen-calibrated logMAR acuity (card-width calibration, 3 m default), Amsler grid with tap marks, contrast, symptoms; change vs baseline ⇒ flag for flight-surgeon review. OCT/fundus PNG/JPEG/uncompressed DICOM import with side-by-side slider and annotation. Webcam blink (EXPERIMENTAL). Cannot measure intracranial pressure; does not diagnose SANS. (NASA, n.d.-d; Lee et al., 2020; Brunstetter, 2023).
### F3 · Crew Harmony Index 🤝
`features/crew.py` – Metadata-only interaction log, shared meals, sleep overlap, weekly survey → team index 0–100 + trend, evidence-based suggestions. Isolation signal visible only to the individual and the behavioral health specialist (enforced server-side). Content keys rejected. (NASA Human Research Program, 2022; NASA, 2025).
### F4 · Offline Smart Doctor 🤖
`features/cdss.py + config/cdss_protocols.json` – Seven JSON decision trees (chest pain, headache + vision change, fever, hypoglycaemia, insomnia, radiation exposure, post-landing dizziness). Each step question → action → stop-and-call-CMO. Lint gate: every item on the approved onboard list, every tree has a stop criterion. Finished sessions are queued to the flight surgeon with ETA. (NASA Exploration Medical Capability, 2022, 2024; Levin et al., 2023).
### F5 · Personal Radiation Map ☢️
`features/radiation.py` – Dosimeter CSV import or entry; cumulative dose vs configurable limit (50 % yellow, 80 % red). Floor-plan zones with relative shielding factors → heat map. SPE mode: alarm, countdown, shelter = lowest factor zone, stowage-bag checklist, estimated dose saved. (NASA, 2023a; George et al., 2024; NASA, n.d.-e).
### F6 · Smart Toilet Analytics 🚽
`features/urine.py` – One JSON schema for manual strips, lab files and a simulated/future device feed. Hydration from specific gravity, calcium trend (least squares), kidney-stone risk 0–10, intake vs output; mirrored as FHIR Observations for the body figure. (Smith et al., 1999; Smith et al., 2012).
### F7 · Daily Movement & Food Prescription 🏋️
`features/coach.py` – Adjusts ARED/treadmill/cycle minutes inside flight-surgeon min/max bounds from sleep, fatigue, urinary calcium and mass. Greedy meal selection from the onboard menu for calcium, vitamin D, protein with a sodium cap. Streaks/badges, anonymous crew board. (Scott et al., 2023; English et al., 2020).
### F8 · Smart Nostalgia 🌍
`features/connection.py` – Pre-loaded family media in data/media/<id>/. Suggestion card when low mood/isolation persists ≥ 3 days or on demand; skippable; switch-off; suppressed during critical tasks. Stores only helped / didn't help. (NASA Human Research Program, 2015b; Picano, 2024).
### F9 · Health Black Box 📦
`storage.py + features/blackbox.py` – Append-only SHA-256 hash chain of every write, AES-256-GCM payloads, UPDATE/DELETE triggers, tamper check and on-copy tamper demo. Consent-gated research export: pseudonymised FHIR Bundle + data dictionary + PDI + SHA-256 manifest (OAIS-style SIP). Mirrors lifetime astronaut health surveillance and LSDA data reuse. (Van Baalen, 2017; NASA Life Sciences Data Archive, 2024).
## API
| Method | Path | Permission | Purpose |
|---|---|---|---|
| GET | /api/health | public | Liveness + crypto backend. |
| POST | /api/login | public | Log in → JWT. |
| GET | /api/demo-users | public | Demo accounts (prototype only). |
| GET | /api/meta | public | All configuration the UI needs (indicators, contexts, references …). |
| GET | /api/me | auth | Current user. |
| GET | /api/crew | auth | Crew list (filtered by role). |
| GET | /api/dashboard | auth | Dashboard: status ring, composite score, body regions, alerts. |
| GET | /api/series | auth | Time series with baseline band + gravity-transition markers. |
| POST | /api/validate | auth | Dry-run validation (no storage). |
| POST | /api/readings | auth | Submit readings → validation → assessment → alert. |
| POST | /api/stand_test | auth | Post-landing seated→stand test. |
| GET | /api/alerts | auth | Alerts visible to this user. |
| POST | /api/alerts/(?P<id>[^/]+)/ack | auth | Acknowledge an alert (ground acks travel with comm delay). |
| GET | /api/poll | auth | Lightweight poll: counts + SPE + delay (replaces WebSocket). |
| GET | /api/queue | auth | Store-and-forward queue (Earth ↔ spacecraft). |
| POST | /api/tick | auth |  |
| POST | /api/gravity | auth | Switch gravity context (rule 7). |
| POST | /api/delay | auth | Override one-way comm delay (seconds) for demos; null = context default. |
| GET | /api/events | auth |  |
| POST | /api/events | auth | Mission timeline event (landing/return triggers the Gravity Transition Protocol). |
| POST | /api/gtp/step | auth |  |
| GET | /api/consent | auth |  |
| POST | /api/consent | auth | Grant / withdraw consent (only the astronaut themself). |
| POST | /api/flags | thresholds_edit | Enable/disable a feature (flight surgeon). |
| POST | /api/thresholds | thresholds_edit | Edit one threshold rule (flight surgeon); written to config/thresholds.json. |
| GET | /api/scenarios | auth |  |
| POST | /api/scenario | auth | Load a SYNTHETIC scenario for one astronaut (CMO / flight surgeon). |
| POST | /api/import/fhir | auth | Import a FHIR Bundle produced by the REAL-data loader. |
| GET | /api/cdss/protocols | auth |  |
| POST | /api/cdss/start | auth |  |
| POST | /api/cdss/answer | auth |  |
| GET | /api/radiation | auth |  |
| POST | /api/radiation/reading | auth |  |
| POST | /api/radiation/import | auth |  |
| GET | /api/radiation/heatmap | auth |  |
| POST | /api/radiation/zones | auth |  |
| POST | /api/radiation/spe | auth | Start SPE mode (alarm, countdown, shelter, dose saved). |
| POST | /api/radiation/spe/stop | auth |  |
| GET | /api/vision/chart | auth |  |
| GET | /api/vision | auth |  |
| GET | /api/vision/image/(?P<id>[^/]+) | auth |  |
| POST | /api/vision/screening | auth |  |
| POST | /api/vision/image | auth |  |
| POST | /api/vision/blink | auth |  |
| GET | /api/urine | auth |  |
| GET | /api/urine/schema | public |  |
| POST | /api/urine | auth |  |
| POST | /api/urine/import | auth |  |
| GET | /api/coach | auth |  |
| POST | /api/coach/exercise | auth |  |
| GET | /api/coach/board | auth |  |
| POST | /api/voice | auth | Submit prosodic FEATURES only (raw audio rejected). |
| GET | /api/voice | auth |  |
| POST | /api/crew/interaction | auth |  |
| POST | /api/crew/survey | auth |  |
| GET | /api/crew/index | auth | Team-level index (no individual data). |
| GET | /api/crew/isolation | auth | Isolation signal: visible ONLY to the individual and the BHS. |
| GET | /api/connection | auth |  |
| POST | /api/connection/rate | auth |  |
| POST | /api/connection/off | auth |  |
| GET | /api/blackbox | auth |  |
| GET | /api/blackbox/verify | auth | Tamper check of the whole hash chain. |
| POST | /api/blackbox/tamper_demo | auth | Copies the DB, tampers with ONE entry in the copy, verifies the copy. |
| GET | /api/export | research_export | Pseudonymised research export (OAIS SIP zip). |
| GET | /api/openapi.json | public | OpenAPI 3.0 description generated from the route table. |

## Glossary
| English | العربية |
|---|---|
| Microgravity | الجاذبية الصغرى / انعدام الوزن |
| Baseline | خط الأساس |
| Threshold | عتبة |
| Fluid shift | انتقال السوائل |
| Orthostatic intolerance | عدم تحمّل الانتصاب |
| Flight surgeon | الجراح الجوي (طبيب الرحلة) |
| Crew Medical Officer (CMO) | الضابط الطبي للطاقم |
| Escalation | التصعيد |
| Acknowledge | إقرار التنبيه |
| Store-and-forward | التخزين ثم الإرسال |
| Comm delay | تأخر الاتصال |
| Provenance | مصدر البيانات |
| Synthetic data | بيانات مُصطنعة |
| Hash chain | سلسلة تجزئة |
| Pseudonymisation | الترميز بأسماء مستعارة |
| Consent | الموافقة |
| Decision support | دعم القرار |
| SANS | متلازمة العين والأعصاب المرتبطة بالرحلات الفضائية |
| Solar particle event (SPE) | عاصفة الجسيمات الشمسية |
| Shielding factor | معامل التدريع |
| Urinary calcium | كالسيوم البول |
| Kidney stone | حصى الكلى |
| Countermeasure | إجراء وقائي |
| ARED | جهاز التمارين المقاومة المتقدم |
| Gravity transition | انتقال الجاذبية |

## References
- Barger, L. K., Flynn-Evans, E. E., Kubey, A., Walsh, L., Ronda, J. M., Wang, W., Wright, K. P., Jr., & Czeisler, C. A. (2014). Prevalence of sleep deficiency and use of hypnotic drugs in astronauts before, during, and after spaceflight: An observational study. The Lancet Neurology, 13(9), 904–912. https://doi.org/10.1016/S1474-4422(14)70122-X
- Brunstetter, T. (2023). Spaceflight associated neuro-ocular syndrome (SANS): A briefing for astronaut candidates [Presentation]. NASA Technical Reports Server. https://ntrs.nasa.gov/api/citations/20230006218/downloads/Brunstetter%20-%20Crewmember%20SANS%20Overview%20-%20Export%20Control%20-FINAL%20-%2001May23.pdf
- English, K. L., et al. (2020). High intensity training during spaceflight: Results from the NASA Sprint Study. npj Microgravity, 6. https://doi.org/10.1038/s41526-020-00111-x
- George, S. P., et al. (2024). Space radiation measurements during the Artemis I lunar mission. Nature. https://doi.org/10.1038/s41586-024-07927-7
- Lee, A. G., Mader, T. H., Gibson, C. R., Tarver, W., Rabiei, P., Riascos, R. F., Galdamez, L. A., & Brunstetter, T. (2020). Spaceflight associated neuro-ocular syndrome (SANS) and the neuro-ophthalmologic effects of microgravity: A review and an update. npj Microgravity, 6, Article 7. https://doi.org/10.1038/s41526-020-0097-9
- Levin, D. R., Steller, J., Anderson, A., Lemery, J., Easter, B., Hilmers, D. C., & Lehnhardt, K. R. (2023). Enabling human space exploration missions through progressively Earth independent medical operations (EIMO). IEEE Open Journal of Engineering in Medicine and Biology. https://doaj.org/article/ea302510a8594334a608b8e88219e914
- Mishra, S., Wendt, C. J., Begerowski, S., Bell, S., & Chaspari, T. (2026). Machine learning for predicting team functioning in HERA missions [Presentation]. NASA Human Research Program Investigators' Workshop. https://ntrs.nasa.gov/citations/20260002431
- NASA Exploration Medical Capability. (2022). The value of a spaceflight clinical decision support system for Earth-independent medical operations. https://ntrs.nasa.gov/citations/20220007443
- NASA Exploration Medical Capability. (2024). Earth-independent medical operations (EIMO) concept of operations. https://ntrs.nasa.gov/citations/20240001402
- NASA Human Research Program. (2015). Evidence report: Risk of adverse cognitive or behavioral conditions and psychiatric disorders. https://ntrs.nasa.gov/api/citations/20150016966/downloads/20150016966.pdf
- NASA Human Research Program. (2015). Evidence report: Risk of orthostatic intolerance during re-exposure to gravity. https://ntrs.nasa.gov/api/citations/20150007319/downloads/20150007319.pdf
- NASA Human Research Program. (2022). Evidence report: Risk of performance and behavioral health decrements due to inadequate cooperation, coordination, communication, and psychosocial adaptation within a team. https://ntrs.nasa.gov/citations/20220007465
- NASA Human Research Program. (n.d.). Five hazards of human spaceflight. https://www.nasa.gov/hrp/hazards
- NASA Life Sciences Data Archive. (2024). Why we do what we do: Data reuse, open access, and privacy in data management at the Life Sciences Data Archive. https://ntrs.nasa.gov/citations/20240012051
- NASA Office of the Chief Health and Medical Officer. (2023). Sleep accommodations [Technical brief]. https://www.nasa.gov/wp-content/uploads/2023/03/sleep-accomodations-technical-brief-ochmo.pdf
- National Aeronautics and Space Administration. (2023). NASA spaceflight human-system standard: Volume 1, crew health (NASA-STD-3001, Vol. 1, Rev. C). https://standards.nasa.gov/sites/default/files/standards/NASA/C//nasa-std-3001-vol-1-rev-c-signature.pdf
- National Aeronautics and Space Administration. (2023). NASA spaceflight human-system standard: Volume 2, human factors, habitability, and environmental health (NASA-STD-3001, Vol. 2, Rev. D). https://standards.nasa.gov/
- National Aeronautics and Space Administration. (2025, March 18). Team risk. https://www.nasa.gov/directorates/esdmd/hhp/team-risk/
- National Aeronautics and Space Administration. (n.d.). Artemis I space radiation research to help Moon, Mars explorers. https://www.nasa.gov/general/artemis-i-space-radiation-research-to-help-moon-mars-explorers/
- National Aeronautics and Space Administration. (n.d.). Ensuring astronaut health. https://www.nasa.gov/?p=207552
- NASA. (n.d.). NASA Life Sciences Portal. https://nlsp.nasa.gov
- NASA. (n.d.). Open Science Data Repository. https://osdr.nasa.gov
- National Aeronautics and Space Administration. (n.d.). Risk of cardiovascular adaptations contributing to adverse mission performance and health outcomes. https://www.nasa.gov/?p=222800
- National Aeronautics and Space Administration. (n.d.). Risk of spaceflight associated neuro-ocular syndrome (SANS). https://www.nasa.gov/reference/risk-of-spaceflight-associated-neuro-ocular-syndrome-sans
- Picano, J. (2024). Behavioral risk in spaceflight [Presentation]. NASA Technical Reports Server. https://ntrs.nasa.gov/api/citations/20240000994/downloads/Behavioral%20Risk%20In%20Spaceflight_Picano.pdf
- Scott, J. M., et al. (2023). Effects of exercise countermeasures on multisystem function in long duration spaceflight astronauts. npj Microgravity, 9. https://doi.org/10.1038/s41526-023-00256-5
- Smith, S. M., McCoy, T., Gazda, D., Morgan, J. L. L., Heer, M., & Zwart, S. R. (2012). Space flight calcium: Implications for astronaut health, spacecraft operations, and Earth. Nutrients, 4(12), 2047–2068. https://doi.org/10.3390/nu4122047
- Smith, S. M., Wastney, M. E., Morukov, B. V., Larina, I. M., Nyquist, L. E., Abrams, S. A., Taran, E. N., Shih, C. Y., Nillen, J. L., Davis-Street, J. E., Rice, B. L., & Lane, H. W. (1999). Calcium metabolism before, during, and after a 3-mo spaceflight: Kinetic and biochemical changes. American Journal of Physiology–Regulatory, Integrative and Comparative Physiology, 277(1), R1–R10.
- Van Baalen, M. (2017). Accessing NASA astronaut medical and research data [Presentation]. NASA Technical Reports Server. https://ntrs.nasa.gov/api/citations/20170009502/downloads/20170009502.pdf