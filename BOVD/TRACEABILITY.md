<div dir="rtl">

# مصفوفة التتبع

| المتطلب | المصدر | الوحدة | الاختبار / الدليل |
|---|---|---|---|
| خط الأساس الشخصي قبل المدى الأرضي | القاعدة 1 | engine.baseline / assess | test_baseline_first_then_earth |
| بيانات ظروف القياس | القاعدة 2 | validation.validate | test_conditions_metadata_rule2 |
| بروتوكول انتقال الجاذبية؛ لا وقوف في 0 g | القاعدة 3 | service.start_gtp / record_stand_test | test_gravity_transition_protocol |
| الكتلة من جهاز قياس الكتلة | القاعدة 4 | مؤشر body_mass | test_coach_stays_within_prescription |
| النوم حسب جدول الطاقم | القاعدة 5 | الروتين، قاعدة الاتجاه | test_sleep_three_consecutive_short_nights_red |
| التمارين مقابل الخطة | القاعدة 6 | features/coach | test_coach_stays_within_prescription |
| سياق الجاذبية يغيّر التأخر والاختبارات والنصائح | القاعدة 7 | gravity_contexts, alerts.current_delay_s | test_green_no_alert_and_delay_contexts |
| واجهة للمستخدم الطافي | القاعدة 8 | web/styles.css | اختبار تكويني يدوي |
| مصدر لكل قيمة | الجزء 2 | fhir.make_observation | test_fhir_observation_shape |
| 10 سيناريوهات مُصطنعة | الجزء 2 | synthetic.py | test_every_synthetic_scenario[10] |
| محمّل البيانات الحقيقية دون اختلاق | الجزء 2 | ingest/osdr.py | test_osdr_mapping_from_local_file |
| العتبات الافتراضية | الجزء 3 | config/thresholds.json | test_default_thresholds[33] |
| الدرجة المركّبة 0–20 + «لماذا» | الجزء 3 | engine.composite / explain | test_composite_bounds |
| 3 أولويات، تصعيد، طابور التأخير | الجزء 3 | alerts.py | test_alert_*, test_escalation_* |
| JWT + صلاحيات لخمسة أدوار | الجزء 3 | auth.py, server.py | test_api.py |
| التشفير أثناء التخزين | الجزء 3 | crypto.py, storage.py | test_encrypted_at_rest |
| F1 الصوت الخام لا يُحفظ | F1 | web/voice.js, features/voice.py | test_voice_* |
| F2 الرؤية + DICOM دون تشخيص | F2 | features/vision.py | test_vision_*, test_dicom_* |
| F3 مؤشر الطاقم وخصوصية العزلة | F3 | features/crew.py | test_crew_*, test_isolation_signal_visibility |
| F4 دعم قرار دون اتصال مع معايير توقف | F4 | features/cdss.py | test_cdss_* |
| F5 خريطة الإشعاع والعاصفة الشمسية | F5 | features/radiation.py | test_radiation_summary_spe_and_import |
| F6 محوّل تحليل البول ومخططه | F6 | features/urine.py | test_urine_schema_and_risk |
| F7 المدرب داخل الحدود | F7 | features/coach.py | test_coach_stays_within_prescription |
| F8 الحنين، التقييم فقط | F8 | features/connection.py | test_connection_suggest_and_critical_task |
| F9 سلسلة التجزئة والتصدير | F9 | storage.bb_*, features/blackbox.py | test_hash_chain_tamper_detected |
| سحب الموافقة ← لا بيانات | بوابات الجودة | consent.require | test_consent_off_collects_nothing[8] |


</div>
