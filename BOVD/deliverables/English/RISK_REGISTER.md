# RISK REGISTER (ISO 14971 style)

S = severity 1–5, P = probability 1–5 before controls.

| ID | Hazardous situation | Harm | S | P | Control | Where | Verification | Residual |
|---|---|---|---|---|---|---|---|---|
| R-01 | False normal: value inside Earth range but abnormal for this astronaut | Missed deterioration | 4 | 3 | Personal baseline ±2 SD checked FIRST; deviation ⇒ at least yellow | engine.assess | test_baseline_first_then_earth | Low |
| R-02 | Baseline softening hides a dangerous value | Missed emergency | 5 | 2 | Only YELLOW may be softened; RED is never softened (config flag documented) | engine.assess | test_yellow_softened_inside_baseline_red_never | Low |
| R-03 | Wrong baseline after gravity change (0 g vs 1 g) | False alarms / missed signs | 3 | 3 | Gravity-aware baseline: early-flight in 0 g, pre-flight in partial/1 g | engine.baseline | test_gravity_aware_baseline | Low |
| R-04 | Typing error (e.g. HR 720) accepted | Wrong decision | 4 | 3 | Plausibility ranges, unit conversion, systolic > diastolic | validation.py | test_validate_ranges, test_bp_pair | Low |
| R-05 | Measurement taken in non-standard conditions | Spurious alert | 2 | 4 | Condition metadata required; confidence lowered; WHY says 'repeat under standard conditions' | validation.py | test_conditions_metadata_rule2 | Low |
| R-06 | Cumulative sleep debt not recognised | Fatigue error in critical task | 4 | 3 | 3 consecutive short nights ⇒ RED; insomnia protocol stop criterion before EVA/docking | engine.trend_rules, cdss insomnia | test_sleep_three_consecutive_short_nights_red | Medium |
| R-07 | Alarm fatigue from repeated/duplicate alarms | Real alarm ignored | 4 | 4 | De-duplication per astronaut+indicator; LOW never repeats; 3 priorities | alerts.raise_alert | test_alert_dedupe_upgrade_and_ground_delay | Medium |
| R-08 | Unacknowledged high-priority alert | Delayed care | 5 | 2 | Repeat every 30 s; escalation crew→CMO→flight surgeon | alerts.tick | test_escalation_and_repeat | Low |
| R-09 | AI false alarm from voice signal | Stigma, unnecessary intervention | 3 | 4 | Voice never alerts alone; combined with sleep/mood; neutral wording; EXPERIMENTAL; off by flag | features/voice.combined | test_voice_rejects_raw_audio_and_builds_baseline | Medium |
| R-10 | Privacy of voice recordings | Loss of trust / disclosure | 4 | 3 | Raw audio never stored or sent; API rejects audio keys; consent gate | web/voice.js, features/voice.submit | test_voice_rejects_raw_audio…, consent-off tests | Low |
| R-11 | Privacy of webcam images | Disclosure | 4 | 2 | Blink numbers only; separate consent 'webcam_blink' default OFF | web/voice.js blink, vision.save_blink | test_consent_off_collects_nothing | Low |
| R-12 | Misuse of CDSS as diagnosis / new medication | Harm from wrong treatment | 5 | 2 | Rule-based reviewed trees; items limited to approved onboard list (lint gate); stop-and-call-CMO in every protocol | features/cdss.lint_protocols | test_cdss_protocols_lint_clean | Medium |
| R-13 | Comm delay hides urgency from ground | Late advice | 4 | 4 | Onboard protocols work offline (EIMO); delay shown everywhere; red sent to ground immediately | alerts.send_to_ground | test_ground_ack_travels_with_delay | Medium |
| R-14 | Ground believes alert is acknowledged before ack arrives | Coordination error | 3 | 3 | Ground acks travel with delay and show 'in transit' | alerts.acknowledge | test_ground_ack_travels_with_delay | Low |
| R-15 | Synthetic data mistaken for real readings | Wrong conclusions / invalid claims | 4 | 3 | Provenance badge REAL/SYNTHETIC/USER-ENTERED on every value; scenario tests assert SYNTHETIC tag | fhir.make_observation, UI badges | test_every_synthetic_scenario | Low |
| R-16 | Tampering with health records | Loss of evidence | 4 | 2 | SHA-256 hash chain, GCM tags, UPDATE/DELETE triggers, tamper-check tool | storage.bb_* | test_hash_chain_tamper_detected | Low |
| R-17 | Data at rest disclosed if laptop lost | Privacy breach | 4 | 2 | AES-256-GCM field encryption; key file local (HSM in a real system) | crypto.py, storage.py | test_encrypted_at_rest | Medium |
| R-18 | Unauthorised role reads data | Privacy breach | 4 | 2 | JWT + RBAC + object-level checks; isolation signal self+BHS only | auth.py, server.Ctx.aid | test_api.py | Low |
| R-19 | Re-identification from research export | Privacy breach | 4 | 2 | Keyed pseudonyms, date generalisation, consent gate, conditions removed | features/blackbox.research_export | test_research_export_pseudonymised_consent_gated | Medium |
| R-20 | Feature collects data without consent | Privacy breach | 4 | 2 | consent.require before any write; flag off ⇒ nothing stored | consent.py | test_consent_off_collects_nothing, test_feature_flag_off… | Low |
| R-21 | Stand test attempted in 0 g | Invalid result | 2 | 3 | Stand test blocked unless context allows standing (rule 3) | service.record_stand_test | test_gravity_transition_protocol | Low |
| R-22 | Gloved/floating user mis-taps | Wrong entry | 3 | 4 | 56–72 px targets, glove mode, one-question-per-screen, review step before submit | web/styles.css, measure wizard | Manual UI test (formative) | Medium |
| R-23 | Nostalgia content shown during critical task | Distraction | 3 | 2 | Suppressed during 'critical_task' events; always skippable; can be turned off | features/connection.should_suggest | test_connection_suggest_and_critical_task | Low |
| R-24 | Thresholds used without medical review | Inappropriate alerts | 4 | 3 | Every threshold marked REVIEW NEEDED; flight-surgeon edit marks reviewer + time in black box | config/thresholds.json, /api/thresholds | test_thresholds_edit_permission | Medium |
| R-25 | Radiation estimate taken as precise dosimetry | Wrong shelter decision | 3 | 2 | Relative shielding factors labelled simplified; dosimeter readings remain the source of truth | features/radiation.py | test_radiation_summary_spe_and_import | Medium |

## AI risks (ISO/IEC 23894)
| Component | Risk | Mitigation | Further validation |
|---|---|---|---|
| Voice fatigue/stress signal (F1) | False positives across accents, colds, noise | Personal baseline, combination with sleep/mood, neutral wording, EXPERIMENTAL, opt-in | Validate on consented analog-mission data; bias study (ISO/IEC TR 24027) |
| Webcam blink (F2) | Lighting, glasses, head position give wrong counts | Numbers only, separate consent default OFF, fatigue 'signal' not alert | Replace with on-device MediaPipe face mesh; validate |
| Smart Doctor (F4) | Users treat output as diagnosis; protocol gaps | Rule-based, reviewed JSON, lint gate, stop-and-call-CMO, items from approved list | Formal clinical review and simulation testing |
| Optional local LLM (not bundled) | Hallucinated medical advice | May only rephrase explanation text; never decides; disabled | Evaluate rephrasing fidelity |
| Composite score | Over-simplification of multi-system state | Score always shown with per-indicator WHY and citations | Calibration study with flight surgeons |
