# TRACEABILITY

| Requirement | Source | Module | Test / evidence |
|---|---|---|---|
| Personal baseline before Earth ranges | Rule 1 | engine.baseline / assess | test_baseline_first_then_earth, test_gravity_aware_baseline |
| Measurement conditions metadata | Rule 2 | validation.validate, fhir extension | test_conditions_metadata_rule2 |
| Gravity Transition Protocol, no standing in 0 g | Rule 3 | service.add_event/start_gtp/record_stand_test | test_gravity_transition_protocol |
| Mass from mass-measurement device | Rule 4 | indicator body_mass, UI micro panel | test_coach_stays_within_prescription |
| Sleep vs crew schedule | Rule 5 | routine, sleep micro panel, trend rule | test_sleep_three_consecutive_short_nights_red |
| Exercise ARED/treadmill/cycle vs plan | Rule 6 | features/coach | test_coach_stays_within_prescription |
| Gravity context changes delay/tests/advice | Rule 7 | config/gravity_contexts, alerts.current_delay_s | test_green_no_alert_and_delay_contexts |
| UI for floating users | Rule 8 | web/styles.css, glove/contrast modes | Manual formative test |
| Provenance on every value | Part 2 | fhir.make_observation | test_fhir_observation_shape, test_every_synthetic_scenario |
| 10 synthetic scenarios | Part 2 | synthetic.py | test_every_synthetic_scenario[10] |
| REAL loader, never invent | Part 2 | ingest/osdr.py | test_osdr_mapping_from_local_file |
| Default thresholds | Part 3 | config/thresholds.json, engine.earth_level | test_default_thresholds[33] |
| Composite score 0–20 + WHY | Part 3 | engine.composite / explain | test_composite_bounds |
| 3 alarm priorities, escalation, delay queue | Part 3 | alerts.py | test_alert_*, test_escalation_*, test_ground_ack_* |
| JWT + RBAC (5 roles) | Part 3 | auth.py, server.py | test_api.py |
| Encryption at rest | Part 3 | crypto.py, storage.py | test_encrypted_at_rest, test_pure_python_gcm_matches_cryptography |
| F1 voice, raw audio never stored | F1 | web/voice.js, features/voice.py | test_voice_* |
| F2 vision + DICOM + no diagnosis | F2 | features/vision.py | test_vision_*, test_dicom_to_png_and_store |
| F3 crew index, isolation visibility | F3 | features/crew.py, /api/crew/isolation | test_crew_*, test_isolation_signal_visibility |
| F4 offline CDSS with stop criteria | F4 | features/cdss.py | test_cdss_* |
| F5 radiation map + SPE | F5 | features/radiation.py | test_radiation_summary_spe_and_import |
| F6 urinalysis adapter + schema | F6 | features/urine.py | test_urine_schema_and_risk |
| F7 coach within bounds | F7 | features/coach.py | test_coach_stays_within_prescription |
| F8 nostalgia, rating only | F8 | features/connection.py | test_connection_suggest_and_critical_task |
| F9 hash chain + OAIS export | F9 | storage.bb_*, features/blackbox.py | test_hash_chain_tamper_detected, test_research_export_* |
| Consent-off ⇒ no data | Quality gates | consent.require | test_consent_off_collects_nothing[8], test_feature_flag_off_* |
