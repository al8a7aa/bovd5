"""Shared content for the deliverables (docx, pptx, md). Single source of truth."""
from __future__ import annotations

HONESTY = ("Hackathon prototype for decision support and training only. NOT a certified medical device. "
           "Designed in alignment with the listed standards; not audited or certified. The app never gives a "
           "diagnosis: it gives status + explanation + recommended next step + who to contact. All thresholds are "
           "configurable and must be reviewed by a flight surgeon. Experimental features are labelled "
           "\"EXPERIMENTAL – research concept\".")

# ---------------------------------------------------------------- risks (ISO 14971)
# id, hazard / hazardous situation, harm, S(1-5), P(1-5), control, where, verification, residual
RISKS = [
    ("R-01", "False normal: value inside Earth range but abnormal for this astronaut", "Missed deterioration", 4, 3, "Personal baseline ±2 SD checked FIRST; deviation ⇒ at least yellow", "engine.assess", "test_baseline_first_then_earth", "Low"),
    ("R-02", "Baseline softening hides a dangerous value", "Missed emergency", 5, 2, "Only YELLOW may be softened; RED is never softened (config flag documented)", "engine.assess", "test_yellow_softened_inside_baseline_red_never", "Low"),
    ("R-03", "Wrong baseline after gravity change (0 g vs 1 g)", "False alarms / missed signs", 3, 3, "Gravity-aware baseline: early-flight in 0 g, pre-flight in partial/1 g", "engine.baseline", "test_gravity_aware_baseline", "Low"),
    ("R-04", "Typing error (e.g. HR 720) accepted", "Wrong decision", 4, 3, "Plausibility ranges, unit conversion, systolic > diastolic", "validation.py", "test_validate_ranges, test_bp_pair", "Low"),
    ("R-05", "Measurement taken in non-standard conditions", "Spurious alert", 2, 4, "Condition metadata required; confidence lowered; WHY says 'repeat under standard conditions'", "validation.py", "test_conditions_metadata_rule2", "Low"),
    ("R-06", "Cumulative sleep debt not recognised", "Fatigue error in critical task", 4, 3, "3 consecutive short nights ⇒ RED; insomnia protocol stop criterion before EVA/docking", "engine.trend_rules, cdss insomnia", "test_sleep_three_consecutive_short_nights_red", "Medium"),
    ("R-07", "Alarm fatigue from repeated/duplicate alarms", "Real alarm ignored", 4, 4, "De-duplication per astronaut+indicator; LOW never repeats; 3 priorities", "alerts.raise_alert", "test_alert_dedupe_upgrade_and_ground_delay", "Medium"),
    ("R-08", "Unacknowledged high-priority alert", "Delayed care", 5, 2, "Repeat every 30 s; escalation crew→CMO→flight surgeon", "alerts.tick", "test_escalation_and_repeat", "Low"),
    ("R-09", "AI false alarm from voice signal", "Stigma, unnecessary intervention", 3, 4, "Voice never alerts alone; combined with sleep/mood; neutral wording; EXPERIMENTAL; off by flag", "features/voice.combined", "test_voice_rejects_raw_audio_and_builds_baseline", "Medium"),
    ("R-10", "Privacy of voice recordings", "Loss of trust / disclosure", 4, 3, "Raw audio never stored or sent; API rejects audio keys; consent gate", "web/voice.js, features/voice.submit", "test_voice_rejects_raw_audio…, consent-off tests", "Low"),
    ("R-11", "Privacy of webcam images", "Disclosure", 4, 2, "Blink numbers only; separate consent 'webcam_blink' default OFF", "web/voice.js blink, vision.save_blink", "test_consent_off_collects_nothing", "Low"),
    ("R-12", "Misuse of CDSS as diagnosis / new medication", "Harm from wrong treatment", 5, 2, "Rule-based reviewed trees; items limited to approved onboard list (lint gate); stop-and-call-CMO in every protocol", "features/cdss.lint_protocols", "test_cdss_protocols_lint_clean", "Medium"),
    ("R-13", "Comm delay hides urgency from ground", "Late advice", 4, 4, "Onboard protocols work offline (EIMO); delay shown everywhere; red sent to ground immediately", "alerts.send_to_ground", "test_ground_ack_travels_with_delay", "Medium"),
    ("R-14", "Ground believes alert is acknowledged before ack arrives", "Coordination error", 3, 3, "Ground acks travel with delay and show 'in transit'", "alerts.acknowledge", "test_ground_ack_travels_with_delay", "Low"),
    ("R-15", "Synthetic data mistaken for real readings", "Wrong conclusions / invalid claims", 4, 3, "Provenance badge REAL/SYNTHETIC/USER-ENTERED on every value; scenario tests assert SYNTHETIC tag", "fhir.make_observation, UI badges", "test_every_synthetic_scenario", "Low"),
    ("R-16", "Tampering with health records", "Loss of evidence", 4, 2, "SHA-256 hash chain, GCM tags, UPDATE/DELETE triggers, tamper-check tool", "storage.bb_*", "test_hash_chain_tamper_detected", "Low"),
    ("R-17", "Data at rest disclosed if laptop lost", "Privacy breach", 4, 2, "AES-256-GCM field encryption; key file local (HSM in a real system)", "crypto.py, storage.py", "test_encrypted_at_rest", "Medium"),
    ("R-18", "Unauthorised role reads data", "Privacy breach", 4, 2, "JWT + RBAC + object-level checks; isolation signal self+BHS only", "auth.py, server.Ctx.aid", "test_api.py", "Low"),
    ("R-19", "Re-identification from research export", "Privacy breach", 4, 2, "Keyed pseudonyms, date generalisation, consent gate, conditions removed", "features/blackbox.research_export", "test_research_export_pseudonymised_consent_gated", "Medium"),
    ("R-20", "Feature collects data without consent", "Privacy breach", 4, 2, "consent.require before any write; flag off ⇒ nothing stored", "consent.py", "test_consent_off_collects_nothing, test_feature_flag_off…", "Low"),
    ("R-21", "Stand test attempted in 0 g", "Invalid result", 2, 3, "Stand test blocked unless context allows standing (rule 3)", "service.record_stand_test", "test_gravity_transition_protocol", "Low"),
    ("R-22", "Gloved/floating user mis-taps", "Wrong entry", 3, 4, "56–72 px targets, glove mode, one-question-per-screen, review step before submit", "web/styles.css, measure wizard", "Manual UI test (formative)", "Medium"),
    ("R-23", "Nostalgia content shown during critical task", "Distraction", 3, 2, "Suppressed during 'critical_task' events; always skippable; can be turned off", "features/connection.should_suggest", "test_connection_suggest_and_critical_task", "Low"),
    ("R-24", "Thresholds used without medical review", "Inappropriate alerts", 4, 3, "Every threshold marked REVIEW NEEDED; flight-surgeon edit marks reviewer + time in black box", "config/thresholds.json, /api/thresholds", "test_thresholds_edit_permission", "Medium"),
    ("R-25", "Radiation estimate taken as precise dosimetry", "Wrong shelter decision", 3, 2, "Relative shielding factors labelled simplified; dosimeter readings remain the source of truth", "features/radiation.py", "test_radiation_summary_spe_and_import", "Medium"),
]

AI_RISKS = [
    ("Voice fatigue/stress signal (F1)", "False positives across accents, colds, noise", "Personal baseline, combination with sleep/mood, neutral wording, EXPERIMENTAL, opt-in", "Validate on consented analog-mission data; bias study (ISO/IEC TR 24027)"),
    ("Webcam blink (F2)", "Lighting, glasses, head position give wrong counts", "Numbers only, separate consent default OFF, fatigue 'signal' not alert", "Replace with on-device MediaPipe face mesh; validate"),
    ("Smart Doctor (F4)", "Users treat output as diagnosis; protocol gaps", "Rule-based, reviewed JSON, lint gate, stop-and-call-CMO, items from approved list", "Formal clinical review and simulation testing"),
    ("Optional local LLM (not bundled)", "Hallucinated medical advice", "May only rephrase explanation text; never decides; disabled", "Evaluate rephrasing fidelity"),
    ("Composite score", "Over-simplification of multi-system state", "Score always shown with per-indicator WHY and citations", "Calibration study with flight surgeons"),
]

USE_SCENARIOS = [
    ("US-1", "Astronaut floating in Node, gloved, logs morning vitals", "Large targets, glove mode, wizard with conditions step, quick 1–5 buttons"),
    ("US-2", "CMO receives red alert during noisy ARED session", "Flashing red banner (voice-free), repeat every 30 s, escalation"),
    ("US-3", "Crew lands on Mars, dizziness on first stand", "Gravity Transition Protocol + stand test + post-landing dizziness protocol"),
    ("US-4", "Flight surgeon on Earth reviews alerts with 12-min delay", "Delivered inbox only, acks 'in transit'"),
    ("US-5", "SPE warning while in lab module", "Purple SPE banner, countdown, shelter zone, checklist"),
    ("US-6", "Bright cabin light / dim sleep period", "High-contrast toggle; colour + icon + text"),
    ("US-7", "Astronaut withdraws voice consent", "Voice feature refuses to store any data"),
    ("US-8", "One-hand use while holding a handrail", "Bottom-reachable controls, any orientation, no drag-only actions except optional annotation"),
]

ALARMS = [("HIGH", "red result, SPE", "Red, flashing banner + 3-beep burst", "every 30 s", "tier +1 every 2 min", "immediately (delayed)"),
          ("MEDIUM", "yellow result", "Amber steady banner", "every 10 min", "tier +1 every 30 min", "when tier 2 reached"),
          ("LOW", "baseline deviation only", "Cyan info in list", "no", "no", "no")]

SECURITY = [("Access control", "JWT HS256 + 5 roles + object-level checks", "ISO/IEC 27002 §5.15, §8.2"),
            ("Authentication", "PBKDF2-SHA256 200k iterations, salted", "§8.5"),
            ("Cryptography", "AES-256-GCM field encryption (OpenSSL or verified pure-Python fallback)", "§8.24, ISO 27799"),
            ("Logging", "Append-only SHA-256 hash-chained black box", "§8.15"),
            ("Network", "Server binds 127.0.0.1 only; no cloud calls; CSP + nosniff headers", "§8.20, §8.23"),
            ("Privacy", "Consent per category, minimisation (no raw audio/no content), pseudonymised export", "ISO/IEC 29100 §5, 27701 §7.2"),
            ("Secure development", "ruff (incl. flake8-bandit S rules), mypy --strict, tests", "§8.25–8.29")]

TRACE = [  # requirement, source, module, test
    ("Personal baseline before Earth ranges", "Rule 1", "engine.baseline / assess", "test_baseline_first_then_earth, test_gravity_aware_baseline"),
    ("Measurement conditions metadata", "Rule 2", "validation.validate, fhir extension", "test_conditions_metadata_rule2"),
    ("Gravity Transition Protocol, no standing in 0 g", "Rule 3", "service.add_event/start_gtp/record_stand_test", "test_gravity_transition_protocol"),
    ("Mass from mass-measurement device", "Rule 4", "indicator body_mass, UI micro panel", "test_coach_stays_within_prescription"),
    ("Sleep vs crew schedule", "Rule 5", "routine, sleep micro panel, trend rule", "test_sleep_three_consecutive_short_nights_red"),
    ("Exercise ARED/treadmill/cycle vs plan", "Rule 6", "features/coach", "test_coach_stays_within_prescription"),
    ("Gravity context changes delay/tests/advice", "Rule 7", "config/gravity_contexts, alerts.current_delay_s", "test_green_no_alert_and_delay_contexts"),
    ("UI for floating users", "Rule 8", "web/styles.css, glove/contrast modes", "Manual formative test"),
    ("Provenance on every value", "Part 2", "fhir.make_observation", "test_fhir_observation_shape, test_every_synthetic_scenario"),
    ("10 synthetic scenarios", "Part 2", "synthetic.py", "test_every_synthetic_scenario[10]"),
    ("REAL loader, never invent", "Part 2", "ingest/osdr.py", "test_osdr_mapping_from_local_file"),
    ("Default thresholds", "Part 3", "config/thresholds.json, engine.earth_level", "test_default_thresholds[33]"),
    ("Composite score 0–20 + WHY", "Part 3", "engine.composite / explain", "test_composite_bounds"),
    ("3 alarm priorities, escalation, delay queue", "Part 3", "alerts.py", "test_alert_*, test_escalation_*, test_ground_ack_*"),
    ("JWT + RBAC (5 roles)", "Part 3", "auth.py, server.py", "test_api.py"),
    ("Encryption at rest", "Part 3", "crypto.py, storage.py", "test_encrypted_at_rest, test_pure_python_gcm_matches_cryptography"),
    ("F1 voice, raw audio never stored", "F1", "web/voice.js, features/voice.py", "test_voice_*"),
    ("F2 vision + DICOM + no diagnosis", "F2", "features/vision.py", "test_vision_*, test_dicom_to_png_and_store"),
    ("F3 crew index, isolation visibility", "F3", "features/crew.py, /api/crew/isolation", "test_crew_*, test_isolation_signal_visibility"),
    ("F4 offline CDSS with stop criteria", "F4", "features/cdss.py", "test_cdss_*"),
    ("F5 radiation map + SPE", "F5", "features/radiation.py", "test_radiation_summary_spe_and_import"),
    ("F6 urinalysis adapter + schema", "F6", "features/urine.py", "test_urine_schema_and_risk"),
    ("F7 coach within bounds", "F7", "features/coach.py", "test_coach_stays_within_prescription"),
    ("F8 nostalgia, rating only", "F8", "features/connection.py", "test_connection_suggest_and_critical_task"),
    ("F9 hash chain + OAIS export", "F9", "storage.bb_*, features/blackbox.py", "test_hash_chain_tamper_detected, test_research_export_*"),
    ("Consent-off ⇒ no data", "Quality gates", "consent.require", "test_consent_off_collects_nothing[8], test_feature_flag_off_*"),
]

FEATURES = [
    ("F1", "Voice Reading 🎙️ (EXPERIMENTAL)", "features/voice.py + web/voice.js",
     "Opt-in 60-s check-in (fixed sentence + free talk). The browser computes F0 mean/SD, energy, speech rate, pause ratio, jitter and shimmer with the Web Audio API and drops the samples immediately. Server compares with the astronaut's own baseline (directional z-scores) → low/medium/high signal, then combines with sleep and mood before suggesting a check-in. Wording never labels a condition. Dehydration hypothesis OFF.",
     "Mishra et al., 2026; NASA Human Research Program, 2015b"),
    ("F2", "Eye of Truth 👁️", "features/vision.py",
     "Screen-calibrated logMAR acuity (card-width calibration, 3 m default), Amsler grid with tap marks, contrast, symptoms; change vs baseline ⇒ flag for flight-surgeon review. OCT/fundus PNG/JPEG/uncompressed DICOM import with side-by-side slider and annotation. Webcam blink (EXPERIMENTAL). Cannot measure intracranial pressure; does not diagnose SANS.",
     "NASA, n.d.-d; Lee et al., 2020; Brunstetter, 2023"),
    ("F3", "Crew Harmony Index 🤝", "features/crew.py",
     "Metadata-only interaction log, shared meals, sleep overlap, weekly survey → team index 0–100 + trend, evidence-based suggestions. Isolation signal visible only to the individual and the behavioral health specialist (enforced server-side). Content keys rejected.",
     "NASA Human Research Program, 2022; NASA, 2025"),
    ("F4", "Offline Smart Doctor 🤖", "features/cdss.py + config/cdss_protocols.json",
     "Seven JSON decision trees (chest pain, headache + vision change, fever, hypoglycaemia, insomnia, radiation exposure, post-landing dizziness). Each step question → action → stop-and-call-CMO. Lint gate: every item on the approved onboard list, every tree has a stop criterion. Finished sessions are queued to the flight surgeon with ETA.",
     "NASA Exploration Medical Capability, 2022, 2024; Levin et al., 2023"),
    ("F5", "Personal Radiation Map ☢️", "features/radiation.py",
     "Dosimeter CSV import or entry; cumulative dose vs configurable limit (50 % yellow, 80 % red). Floor-plan zones with relative shielding factors → heat map. SPE mode: alarm, countdown, shelter = lowest factor zone, stowage-bag checklist, estimated dose saved.",
     "NASA, 2023a; George et al., 2024; NASA, n.d.-e"),
    ("F6", "Smart Toilet Analytics 🚽", "features/urine.py",
     "One JSON schema for manual strips, lab files and a simulated/future device feed. Hydration from specific gravity, calcium trend (least squares), kidney-stone risk 0–10, intake vs output; mirrored as FHIR Observations for the body figure.",
     "Smith et al., 1999; Smith et al., 2012"),
    ("F7", "Daily Movement & Food Prescription 🏋️", "features/coach.py",
     "Adjusts ARED/treadmill/cycle minutes inside flight-surgeon min/max bounds from sleep, fatigue, urinary calcium and mass. Greedy meal selection from the onboard menu for calcium, vitamin D, protein with a sodium cap. Streaks/badges, anonymous crew board.",
     "Scott et al., 2023; English et al., 2020"),
    ("F8", "Smart Nostalgia 🌍", "features/connection.py",
     "Pre-loaded family media in data/media/<id>/. Suggestion card when low mood/isolation persists ≥ 3 days or on demand; skippable; switch-off; suppressed during critical tasks. Stores only helped / didn't help.",
     "NASA Human Research Program, 2015b; Picano, 2024"),
    ("F9", "Health Black Box 📦", "storage.py + features/blackbox.py",
     "Append-only SHA-256 hash chain of every write, AES-256-GCM payloads, UPDATE/DELETE triggers, tamper check and on-copy tamper demo. Consent-gated research export: pseudonymised FHIR Bundle + data dictionary + PDI + SHA-256 manifest (OAIS-style SIP). Mirrors lifetime astronaut health surveillance and LSDA data reuse.",
     "Van Baalen, 2017; NASA Life Sciences Data Archive, 2024"),
]

GLOSSARY = [("Microgravity", "الجاذبية الصغرى / انعدام الوزن"), ("Baseline", "خط الأساس"), ("Threshold", "عتبة"),
            ("Fluid shift", "انتقال السوائل"), ("Orthostatic intolerance", "عدم تحمّل الانتصاب"), ("Flight surgeon", "الجراح الجوي (طبيب الرحلة)"),
            ("Crew Medical Officer (CMO)", "الضابط الطبي للطاقم"), ("Escalation", "التصعيد"), ("Acknowledge", "إقرار التنبيه"),
            ("Store-and-forward", "التخزين ثم الإرسال"), ("Comm delay", "تأخر الاتصال"), ("Provenance", "مصدر البيانات"),
            ("Synthetic data", "بيانات مُصطنعة"), ("Hash chain", "سلسلة تجزئة"), ("Pseudonymisation", "الترميز بأسماء مستعارة"),
            ("Consent", "الموافقة"), ("Decision support", "دعم القرار"), ("SANS", "متلازمة العين والأعصاب المرتبطة بالرحلات الفضائية"),
            ("Solar particle event (SPE)", "عاصفة الجسيمات الشمسية"), ("Shielding factor", "معامل التدريع"), ("Urinary calcium", "كالسيوم البول"),
            ("Kidney stone", "حصى الكلى"), ("Countermeasure", "إجراء وقائي"), ("ARED", "جهاز التمارين المقاومة المتقدم"), ("Gravity transition", "انتقال الجاذبية")]

ROADMAP = [("0–1 month", "Flight-surgeon review of all thresholds and protocols; usability test in an analog habitat (gloves)"),
           ("1–3 months", "Validate voice/blink signals on consented data; bias evaluation; MediaPipe on-device"),
           ("3–6 months", "SQLCipher full-DB encryption, HSM keys, FHIR validator, IEC 62304 documentation set"),
           ("6–12 months", "ISO 14971 risk file, IEC 62366-1 summative test, ISO 13485 QMS gap assessment; analog mission pilot (HERA-style)")]

SBOM = [("BÖVD", "0.9.0", "MIT (team choice – confirm before submission)", "this project"),
        ("CPython standard library", "≥3.10", "PSF-2.0", "runtime"),
        ("SQLite", "bundled with Python", "blessing (public domain)", "runtime"),
        ("cryptography (optional)", "≥41", "Apache-2.0 OR BSD-3-Clause", "optional fast AES-GCM"),
        ("pytest (dev)", "≥8", "MIT", "tests only")]

DEMO_SCRIPT = [
    "Double-click start.bat → browser opens http://127.0.0.1:8765 (demo crew is created with SYNTHETIC data, purple badges).",
    "Log in as astro1 → Dashboard: status ring 0–20, body figure, latest readings with provenance; tap the heart → WHY panel with citations.",
    "Measure → conditions step (restrained, 5-min rest) → enter HR 128, sleep 4.5, mood 2 → Submit: RED with explanation, next step, who to contact, Smart Doctor link.",
    "Top banner flashes red (HIGH priority). Log out → surgeon1: only alerts that ARRIVED over the delayed link are visible; acknowledge → 'in transit'.",
    "Mission & Routine → add event 'landing' to mars_surface → Gravity Transition Protocol + stand test (HR +36 → yellow). Delay chip shows Mars minutes.",
    "Radiation → Start SPE → purple banner, countdown, shelter zone, dose saved. Black Box → tamper demo shows the hash chain catching an edit.",
]
