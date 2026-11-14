# PRIVACY

Hackathon prototype for decision support and training only. NOT a certified medical device. Designed in alignment with the listed standards; not audited or certified. The app never gives a diagnosis: it gives status + explanation + recommended next step + who to contact. All thresholds are configurable and must be reviewed by a flight surgeon. Experimental features are labelled "EXPERIMENTAL – research concept".

- **Local only.** The server binds to 127.0.0.1; no data is sent to any cloud service. Optional OSDR download is the only network call and only on explicit command.
- **Encryption at rest.** All health payloads are AES-256-GCM encrypted in SQLite; the key is in `data/db/astra.key` (an HSM in a real system).
- **Consent per category** (voice features, vision, webcam blink, crew interaction, radiation, urine, connection, research export). Withdrawing consent or disabling a feature stops collection – proven by automated consent-off tests.
- **Minimisation.** Voice: raw audio never stored or sent (7 numbers only). Webcam: blink numbers only, default OFF. Crew: who/minutes only, never content. Nostalgia: only "helped / didn't help".
- **Visibility.** Isolation signal: the individual and the behavioral health specialist only. Researchers: pseudonymised export only.
- **Integrity.** Every write is in an append-only SHA-256 hash chain (black box) with a tamper-check tool.
- **Demo accounts** use a shared password (`astra2026`) for the hackathon only; change or remove them before any other use.
- **Rights.** Delete local data with `reset_data.bat`. Research exports are generated only on request by authorised roles.
