/* =====================================================================
   BÖVD · feature views F1–F9 + settings
   Each feature: flag state, consent screen, privacy note, "how it works",
   citations, EXPERIMENTAL badge where stated.
   ===================================================================== */
"use strict";
const ref = (...keys) => keys.map((k) => ({ apa: S.meta.references[k].apa, url: S.meta.references[k].url }));
async function featHead(fkey, icon, titleKey, how, privacy, citeKeys, consentCat, experimental) {
  const on = S.meta.flags_effective[fkey];
  let consentHtml = "";
  if (consentCat && S.aid && S.user.role === "astronaut") {
    const c = await get(withAid("/api/consent")); const g = !!c.consents[consentCat];
    consentHtml = `<div class="row"><b>${t("consent")}:</b> ${esc(L(c.categories[consentCat], "") || c.categories[consentCat][S.lang])} – ${g ? "✔ " + t("granted") : "✖ " + t("withdrawn")}
      <button class="small ${g ? "danger" : "primary"}" data-act="consent" data-c="${consentCat}" data-g="${g ? 0 : 1}">${g ? t("withdraw") : t("grant")}</button></div>`;
  }
  return `<h2>${icon} ${t(titleKey)} ${experimental ? expBadge() : ""}</h2>
   <div class="card"><div class="row">${on ? `<span class="lvl green">● ${S.lang === "ar" ? "مفعّلة" : "enabled"}</span>` : `<span class="lvl red">● ${S.lang === "ar" ? "معطّلة – لا تُجمع بيانات" : "disabled – no data collected"}</span>`}</div>
   ${consentHtml}<details><summary><b>ℹ️ ${t("how")}</b></summary><p>${esc(how[S.lang] || how.en)}</p></details>
   <details><summary><b>🔒 ${t("privacy")}</b></summary><p>${esc(privacy[S.lang] || privacy.en)}</p></details>${cites(ref(...citeKeys))}</div>`;
}
ACTIONS.consent = async (el) => { await post("/api/consent", { aid: S.aid, category: el.dataset.c, granted: el.dataset.g === "1" }); go(S.view); };
ACTIONS.openProtocol = async (el) => { S.cdssStart = el.dataset.p; go("cdss"); };

// ============ F4 Smart Doctor
VIEWS.cdss = async () => {
  const head = await featHead("F4_cdss", "🤖", "cdss", { en: "Reviewed JSON decision trees: one question per screen → action → clear 'stop and call CMO' criteria. Works with no Earth link; the finished session is queued to the flight surgeon with its estimated delivery time. No generative AI makes medical decisions.", ar: "أشجار قرار JSON مُراجَعة: سؤال واحد في كل شاشة ← إجراء ← معايير واضحة 'توقف واتصل بالضابط الطبي'. يعمل بلا اتصال بالأرض؛ تُرسل الجلسة للجراح الجوي مع وقت الوصول المتوقع." },
    { en: "Session answers are stored encrypted in the black box and sent only to the medical team.", ar: "تُحفظ الإجابات مشفّرة في الصندوق الأسود وتُرسل للفريق الطبي فقط." }, ["exmc_cdss_2022", "exmc_eimo_2024", "levin_2023"]);
  const ps = await get("/api/cdss/protocols");
  if (S.cdssStart) { const p = S.cdssStart; S.cdssStart = null; S.cdss = await post("/api/cdss/start", { aid: S.aid, protocol: p }); }
  const s = S.cdss;
  let step = "";
  if (s) {
    const n = s.node; const txt = S.lang === "ar" ? n.ar : n.en;
    step = `<div class="card" style="border:2px solid ${n.type === "stop" ? "var(--red)" : "var(--cyan)"};margin-top:12px"><h3>${esc(L(s, "title"))} · ${s.session.path.length + 1}</h3>
      <p style="font-size:1.25em">${n.type === "stop" ? "⛔ " : n.type === "end" ? "✔ " : n.type === "action" ? "👉 " : "❓ "}${esc(txt)}</p>
      ${(n.items || []).length ? `<p class="muted">Onboard items: ${n.items.map(esc).join(", ")}</p>` : ""}
      ${n.type === "question" ? `<div class="row"><button class="primary" data-act="cdssAns" data-a="yes" style="min-width:140px">${t("yes")}</button><button data-act="cdssAns" data-a="no" style="min-width:140px">${t("no")}</button></div>` : ""}
      ${n.type === "action" ? `<button class="primary" data-act="cdssAns" data-a="next">${t("next")} ▶</button>` : ""}
      ${s.session.queued_to_ground ? `<p>📡 ${S.lang === "ar" ? "أُرسلت الجلسة للجراح الجوي – الوصول المتوقع" : "Session queued to flight surgeon – ETA"} ${esc(s.session.queued_to_ground.eta)} (${fmtDelay(s.session.queued_to_ground.delay_s)})</p>` : ""}
      ${n.type === "stop" ? `<button class="danger" data-act="go" data-v="alerts">📣 CMO</button>` : ""}${cites(s.citations)}</div>`;
  }
  return head + `<div class="grid" style="margin-top:12px">${ps.protocols.map((p) => `<button data-act="cdssStart" data-p="${esc(p.id)}" style="min-height:80px">${esc(L(p, "title"))}</button>`).join("")}</div>
    ${ps.lint.length ? `<div class="card">⚠ ${ps.lint.map(esc).join("<br>")}</div>` : `<p class="muted">✔ protocol lint: all items on the approved onboard list; every protocol has a stop criterion.</p>`}${step}`;
};
ACTIONS.cdssStart = async (el) => { S.cdss = await post("/api/cdss/start", { aid: S.aid, protocol: el.dataset.p }); go("cdss"); };
ACTIONS.cdssAns = async (el) => { S.cdss = await post("/api/cdss/answer", { session: S.cdss.session.id, answer: el.dataset.a }); go("cdss"); };

// ============ F5 Radiation
VIEWS.radiation = async () => {
  const head = await featHead("F5_radiation", "☢️", "radiation", { en: "Cumulative dose from dosimeter readings vs the configurable limit (NASA-STD-3001, review needed). Heat map = background dose rate × relative shielding factor per zone (simplified, not a transport code). SPE mode recommends the zone with the lowest factor and estimates dose saved.", ar: "الجرعة التراكمية من قراءات مقياس الجرعة مقابل الحد القابل للتعديل. الخريطة الحرارية = معدل الجرعة × معامل التدريع النسبي لكل منطقة (مبسط). وضع العاصفة يوصي بالمنطقة الأقل معاملًا ويقدّر الجرعة الموفرة." },
    { en: "Dose values are personal health data, encrypted at rest.", ar: "قيم الجرعة بيانات صحية شخصية مشفرة." }, ["nasa_std_3001_v1", "george_2024", "nasa_artemis_rad"], "radiation");
  const [r, hm] = await Promise.all([get(withAid("/api/radiation")), get("/api/radiation/heatmap?spe=" + (S.speView ? 1 : 0))]);
  const maxR = Math.max(...hm.zones.map((z) => z.rate_msv_day));
  const col = (v) => { const x = v / maxR; return x > 0.75 ? "#ff4d4f" : x > 0.5 ? "#f5a623" : x > 0.3 ? "#ffe066" : "#2ecc71"; };
  const W = Math.max(...hm.zones.map((z) => z.x + z.w)), Hh = Math.max(...hm.zones.map((z) => z.y + z.h));
  const zones = hm.zones.map((z) => `<div class="zone ${S.zone === z.id ? "sel" : ""}" data-act="zone" data-z="${z.id}" style="grid-column:${z.x + 1}/span ${z.w};grid-row:${z.y + 1}/span ${z.h};background:${col(z.rate_msv_day)}">${esc(L(z, "name"))}<br>${z.rate_msv_day} mSv/d<br><small>× ${z.shield}</small>${z.id === hm.shelter.id ? " 🛡️" : ""}</div>`).join("");
  const spe = r.spe;
  const pct = Math.min(100, r.pct);
  return head + `<div class="grid2" style="margin-top:12px"><div class="card"><h3>${esc(r.astronaut_id)} – ${S.lang === "ar" ? "الجرعة التراكمية" : "Cumulative dose"}</h3>
    <div class="big-num">${r.cumulative_msv} mSv</div><p>/ ${r.limit_msv} mSv (${r.pct}%) ${lvl(r.level)}</p>
    <div style="background:#0a1830;border-radius:8px;height:22px;overflow:hidden"><div style="width:${pct}%;height:100%;background:${r.level === "red" ? "var(--red)" : r.level === "yellow" ? "var(--amber)" : "var(--green)"}"></div></div>
    <p class="muted">50% → ${t("level_yellow")}, 80% → ${t("level_red")} · limit is a config value with citation (review needed)</p>
    <label>➕ dosimeter (mSv)</label><div class="row"><input id="dose" inputmode="decimal"><button data-act="addDose">${t("save")}</button></div>
    ${["cmo", "flight_surgeon"].includes(S.user.role) ? `<label>CSV import (timestamp,astronaut_id,dose_msv)</label><input type="file" id="radCsv" accept=".csv">` : ""}
    ${r.crew.length ? `<h3>Crew</h3><table>${r.crew.map((c) => `<tr><td>${esc(c.astronaut_id)}</td><td>${c.cumulative_msv} mSv</td><td>${c.pct}%</td><td>${lvl(c.level)}</td></tr>`).join("")}</table>` : ""}</div>
   <div class="card"><h3>🗺️ ${S.lang === "ar" ? "خريطة الموئل" : "Habitat map"} ${hm.spe ? "(SPE)" : ""}</h3><div class="heat" style="grid-template-columns:repeat(${W},1fr);grid-template-rows:repeat(${Hh},auto)">${zones}</div>
    <div class="row" style="margin-top:8px"><button data-act="speView">${S.speView ? "normal" : "SPE preview"}</button>
    ${S.zone && ["cmo", "flight_surgeon"].includes(S.user.role) ? `<label>shield factor</label><input id="shieldF" type="number" step="0.05" min="0.05" max="3" style="width:110px"><button data-act="saveShield">${t("save")}</button>` : ""}</div>
    <p class="muted">${S.lang === "ar" ? "اختر منطقتك الحالية ثم ابدأ وضع العاصفة." : "Tap your current zone, then start SPE mode."}</p></div></div>
   <div class="card" style="margin-top:14px;border-color:#6a00ff"><h3>☀️ Solar Particle Event</h3>
   ${spe && spe.active ? `<p class="big-num" id="speCount"></p><p>🛡️ ${S.lang === "ar" ? "الملجأ" : "Shelter"}: <b>${esc(L(spe.shelter, "name"))}</b> · ${S.lang === "ar" ? "الجرعة الموفرة المقدرة" : "estimated dose saved"}: <b>${spe.estimated_saved_msv} mSv</b> (${spe.dose_in_current_msv} → ${spe.dose_in_shelter_msv} mSv / ${spe.duration_h} h)</p>
     <ol>${(S.lang === "ar" ? spe.checklist_ar : spe.checklist_en).map((x) => `<li><label class="row"><input type="checkbox"> ${esc(x)}</label></li>`).join("")}</ol><button class="danger" data-act="speStop">■ stop SPE mode</button>`
    : `<div class="row"><label>arrival (min)</label><input id="speArr" value="30" style="width:90px"><label>duration (h)</label><input id="speDur" value="8" style="width:90px"><button class="danger" data-act="speStart">☢️ ${t("start")} SPE</button></div>`}</div>`;
};
MOUNT.radiation = () => {
  const f = $("#radCsv"); if (f) f.addEventListener("change", async () => { const r = await post("/api/radiation/import", { text: await f.files[0].text() }); toast(`✔ ${r.imported} · ⚠ ${r.errors.length}`); go("radiation"); });
  const sc = $("#speCount"); if (sc) { const tick = async () => { if (!document.body.contains(sc)) return; const p = await get("/api/poll"); if (p.spe) sc.textContent = "⏱ " + Math.max(0, (Date.parse(p.spe.arrival) - Date.now()) / 60000).toFixed(1) + " min"; setTimeout(tick, 1000); }; tick(); }
};
ACTIONS.zone = (el) => { S.zone = el.dataset.z; go("radiation"); };
ACTIONS.speView = () => { S.speView = !S.speView; go("radiation"); };
ACTIONS.addDose = async () => { await post("/api/radiation/reading", { aid: S.aid, dose_msv: +$("#dose").value }); go("radiation"); };
ACTIONS.speStart = async () => { await post("/api/radiation/spe", { arrival_min: +$("#speArr").value, duration_h: +$("#speDur").value, zone: S.zone || "z1" }); poll(); go("radiation"); };
ACTIONS.speStop = async () => { await post("/api/radiation/spe/stop"); poll(); go("radiation"); };
ACTIONS.saveShield = async () => { const hm = await get("/api/radiation/heatmap"); const zones = hm.zones.map(({ rate_msv_day, ...z }) => (z.id === S.zone ? { ...z, shield: +$("#shieldF").value } : z)); await post("/api/radiation/zones", { zones }); go("radiation"); };

// ============ F2 Eye of Truth
VIEWS.vision = async () => {
  const head = await featHead("F2_vision", "👁️", "vision", { en: "Supports SANS surveillance: screen-calibrated acuity (logMAR), Amsler grid with tap-to-mark distortion, contrast test, symptoms; OCT/fundus image comparison with the pre-flight baseline. The software CANNOT measure intracranial pressure and does NOT diagnose SANS – changes are flagged for flight-surgeon review. Why SANS? A leading hypothesis is the chronic headward fluid shift in 0 g. Report: blurred near vision, new distortion, scotoma, headache.", ar: "يدعم مراقبة SANS: حدة بصر معايرة للشاشة، شبكة أمسلر، اختبار تباين، أعراض؛ مقارنة صور OCT/قاع العين مع خط الأساس. البرنامج لا يقيس الضغط داخل الجمجمة ولا يشخّص SANS – التغيرات تُعلَّم لمراجعة الجراح الجوي. السبب المرجح: انتقال السوائل نحو الرأس. أبلغ عن: تشوش الرؤية القريبة، تشوه جديد، بقعة عمياء، صداع." },
    { en: "Images are encrypted at rest; the black box keeps only their SHA-256. Webcam (EXPERIMENTAL) sends only blink numbers – no images.", ar: "الصور مشفرة؛ الصندوق الأسود يحفظ بصمتها فقط. الكاميرا (تجريبي) ترسل أرقام الرمش فقط." }, ["nasa_sans_risk", "lee_2020", "brunstetter_2023"], "vision");
  const v = await get(withAid("/api/vision"));
  const dist = S.visDist || 300, pxmm = S.pxmm || 3.78; const ch = await get(`/api/vision/chart?distance=${dist}&pxmm=${pxmm}`);
  const letters = "EFPTOZLDHNCRKSV";
  const rows = ch.rows.filter((r) => r.px >= 4 && r.px <= 220).map((r, i) => `<div style="font-size:${r.px}px;line-height:1.15">${letters.slice(i % 9, i % 9 + 5)}</div><div style="font-size:12px;color:#555;letter-spacing:0">logMAR ${r.logmar.toFixed(1)} · 6/${r.snellen_6}</div>`).join("");
  const last = v.screenings[v.screenings.length - 1];
  const imgs = v.images; const base = imgs.find((i) => i.is_baseline); const cur = [...imgs].reverse().find((i) => !i.is_baseline);
  const src = (i) => `/api/vision/image/${i.id}?aid=${S.aid}&token=${S.token}`;
  return head + `<div class="grid2" style="margin-top:12px"><div class="card"><h3>1 · ${S.lang === "ar" ? "معايرة الشاشة" : "Screen calibration"}</h3>
     <p class="muted">${S.lang === "ar" ? "اضبط الشريط ليطابق عرض بطاقة بنكية (85.6 مم) ثم أدخل المسافة." : "Resize the bar to match a credit card's width (85.6 mm), then enter viewing distance (default 3 m, body restrained so the distance stays fixed)."}</p>
     <div id="calBar" style="height:20px;background:var(--cyan);width:${85.6 * pxmm}px;border-radius:4px"></div><input type="range" id="calR" min="2" max="8" step="0.02" value="${pxmm}">
     <label>distance (cm)</label><input id="visDist" type="number" value="${dist}"><button class="small" data-act="visCal">${t("save")}</button>
     <h3>2 · ${S.lang === "ar" ? "حدة البصر" : "Acuity chart"} (${dist} cm)</h3><div class="acuity">${rows}</div>
     <div class="grid"><div><label>OD logMAR</label><input id="acOD" value="0.0"></div><div><label>OS logMAR</label><input id="acOS" value="0.0"></div><div><label>contrast (log CS)</label><input id="contr" value="1.8"></div></div></div>
   <div class="card"><h3>3 · Amsler grid</h3><p class="muted">${S.lang === "ar" ? "غطِّ عينًا وثبّت النظر على النقطة؛ اضغط على أي خط مشوه." : "Cover one eye, fixate the centre dot, tap any wavy/missing area."}</p>
     <canvas id="amsler" class="amsler" width="300" height="300" style="width:300px;max-width:100%"></canvas><p>marks: <b id="amN">0</b> <button class="small" data-act="amClear">↺</button></p>
     <h3>4 · ${S.lang === "ar" ? "الأعراض" : "Symptoms"}</h3><div class="row">${["blurred_near", "blurred_far", "headache", "visual_distortion", "scotoma", "eye_pain"].map((k) => `<label class="chip row"><input type="checkbox" class="vsym" value="${k}"> ${k.replace("_", " ")}</label>`).join("")}</div>
     <label class="row"><input type="checkbox" id="isBase"> ${S.lang === "ar" ? "هذا فحص خط الأساس (قبل الرحلة)" : "This is the pre-flight baseline"}</label>
     <button class="primary" data-act="visSave">✔ ${t("submit")}</button><div id="visRes">${last ? `<p>${lvl(last.payload.level)} ${esc((last.payload.reasons || []).join("; "))}</p><p class="muted">${esc(last.payload.cannot_measure || "")}</p>` : ""}</div></div></div>
   <div class="card" style="margin-top:14px"><h3>5 · OCT / fundus (PNG, JPEG, uncompressed DICOM)</h3><div class="row"><input type="file" id="eyeImg" accept=".png,.jpg,.jpeg,.dcm"><select id="eyeSide"><option>OD</option><option>OS</option></select><select id="eyeMod"><option>fundus</option><option>OCT</option></select><label class="row"><input type="checkbox" id="imgBase"> baseline</label></div>
    ${base && cur ? `<p>${S.lang === "ar" ? "اسحب لمقارنة خط الأساس مع الحالي" : "Slide to compare baseline ↔ current"}</p><div class="cmp" id="cmp"><img src="${src(base)}" alt="baseline"><img id="cmpTop" src="${src(cur)}" alt="current" style="clip-path:inset(0 0 0 50%)"><canvas id="annot" width="520" height="520"></canvas></div><input type="range" id="cmpR" min="0" max="100" value="50"><p class="muted">✏️ ${S.lang === "ar" ? "ارسم على الصورة للتعليق" : "Draw on the image to annotate"} · ⚠ review by flight surgeon – no automatic diagnosis</p>`
    : `<p class="muted">${imgs.length} image(s). Upload one baseline + one current image to compare.</p>`}</div>
   <div class="card" style="margin-top:14px"><h3>6 · Webcam blink rate ${expBadge()}</h3><p class="muted">Consent category: webcam_blink. Crude luminance method; numbers only; no frames stored.</p>
    <video id="vid" muted playsinline style="width:240px;border-radius:8px;background:#000"></video><br><button data-act="blink">▶ 30 s</button> <span id="blinkRes">${v.blink.length ? JSON.stringify(v.blink[v.blink.length - 1].payload) : ""}</span></div>`;
};
MOUNT.vision = () => {
  const r = $("#calR"); r.addEventListener("input", () => { $("#calBar").style.width = 85.6 * r.value + "px"; S.pxmm = +r.value; });
  const c = $("#amsler"), g = c.getContext("2d"); S.amMarks = [];
  const draw = () => { g.fillStyle = "#fff"; g.fillRect(0, 0, 300, 300); g.strokeStyle = "#000"; for (let i = 0; i <= 20; i++) { g.beginPath(); g.moveTo(i * 15, 0); g.lineTo(i * 15, 300); g.moveTo(0, i * 15); g.lineTo(300, i * 15); g.stroke(); } g.fillStyle = "#000"; g.beginPath(); g.arc(150, 150, 4, 0, 7); g.fill(); g.fillStyle = "rgba(255,0,0,.6)"; S.amMarks.forEach(([x, y]) => { g.beginPath(); g.arc(x, y, 9, 0, 7); g.fill(); }); $("#amN").textContent = S.amMarks.length; };
  c.addEventListener("pointerdown", (e) => { const b = c.getBoundingClientRect(); S.amMarks.push([(e.clientX - b.left) * 300 / b.width, (e.clientY - b.top) * 300 / b.height]); draw(); }); draw();
  const f = $("#eyeImg"); f.addEventListener("change", async () => { const file = f.files[0]; const b64 = await new Promise((res) => { const fr = new FileReader(); fr.onload = () => res(fr.result.split(",")[1]); fr.readAsDataURL(file); }); await post("/api/vision/image", { aid: S.aid, filename: file.name, b64, eye: $("#eyeSide").value, modality: $("#eyeMod").value, is_baseline: $("#imgBase").checked }); toast("✔ image stored (encrypted)"); go("vision"); });
  const cr = $("#cmpR"); if (cr) cr.addEventListener("input", () => ($("#cmpTop").style.clipPath = `inset(0 0 0 ${cr.value}%)`));
  const an = $("#annot"); if (an) { const ag = an.getContext("2d"); ag.strokeStyle = "#00B4D8"; ag.lineWidth = 3; let d = false; const pos = (e) => { const b = an.getBoundingClientRect(); return [(e.clientX - b.left) * 520 / b.width, (e.clientY - b.top) * 520 / b.height]; };
    an.addEventListener("pointerdown", (e) => { d = true; ag.beginPath(); ag.moveTo(...pos(e)); }); an.addEventListener("pointermove", (e) => { if (d) { ag.lineTo(...pos(e)); ag.stroke(); } }); an.addEventListener("pointerup", () => (d = false)); }
};
ACTIONS.visCal = () => { S.visDist = +$("#visDist").value; go("vision"); };
ACTIONS.amClear = () => { S.amMarks = []; go("vision"); };
ACTIONS.visSave = async () => { const sym = {}; document.querySelectorAll(".vsym:checked").forEach((x) => (sym[x.value] = true));
  const r = await post("/api/vision/screening", { aid: S.aid, result: { acuity_od: +$("#acOD").value, acuity_os: +$("#acOS").value, contrast: +$("#contr").value, amsler_marks: S.amMarks.length, symptoms: sym, is_baseline: $("#isBase").checked, screen_px_per_mm: S.pxmm || 3.78, distance_cm: S.visDist || 300 } });
  $("#visRes").innerHTML = `<p>${lvl(r.level)} ${esc(r.reasons.join("; ") || "no change")}</p><p>${esc(L(r, "action"))}</p><p class="muted">${esc(r.cannot_measure)}</p>`; };
ACTIONS.blink = async () => { const res = await ASTRA_DSP.blink($("#vid"), 30, (s) => ($("#blinkRes").textContent = s.toFixed(0) + " s")); const r = await post("/api/vision/blink", { aid: S.aid, ...res }); $("#blinkRes").textContent = JSON.stringify(r); };

// ============ F6 Urine
VIEWS.urine = async () => {
  const head = await featHead("F6_urine", "🚽", "urine", { en: "Software interface only: manual test strip, lab file import (CSV/JSON) or a simulated automated feed – all through one documented JSON schema (GET /api/urine/schema) so future hardware can plug in. Specific gravity → hydration; urinary calcium trend (bone loss); kidney-stone risk score 0–10; fluid intake vs output.", ar: "واجهة برمجية فقط: شريط يدوي، استيراد ملف مختبر، أو تغذية آلية محاكاة – عبر مخطط JSON موثق ليتصل به جهاز مستقبلي. الكثافة النوعية ← الترطيب؛ اتجاه كالسيوم البول (فقد العظم)؛ درجة خطر الحصى 0–10؛ السوائل الداخلة مقابل الخارجة." },
    { en: "Results are encrypted health data; trends are reported to the flight surgeon.", ar: "النتائج بيانات صحية مشفرة؛ تُرسل الاتجاهات للجراح الجوي." }, ["smith_1999", "smith_2012"], "urine");
  const a = await get(withAid("/api/urine"));
  const sr = a.stone_risk || { score: 0, max: 10, level: "none", factors: [] };
  const ser = { points: (a.calcium_series || []).map(([t, v]) => ({ t, v, prov: { type: "SYNTHETIC" }, ctx: "iss" })), unit: "mg/day", indicator: "urine_calcium" };
  return head + `<div class="grid2" style="margin-top:12px"><div class="card"><h3>${S.lang === "ar" ? "إدخال شريط يدوي" : "Manual strip entry"}</h3>
     <div class="grid">${[["specific_gravity", "SG (1.000–1.050)"], ["calcium_mg_day", "Ca mg/day"], ["ph", "pH"], ["volume_ml", "volume ml"], ["fluid_intake_ml", "intake ml"]].map(([k, l]) => `<div><label>${l}</label><input id="u_${k}" inputmode="decimal"></div>`).join("")}</div>
     <button class="primary" data-act="urineAdd">✔ ${t("submit")}</button>${["cmo", "flight_surgeon"].includes(S.user.role) ? `<label>Lab file (CSV/JSON)</label><input type="file" id="uFile" accept=".csv,.json">` : ""}
     <p class="muted"><a href="/api/urine/schema" target="_blank">JSON schema (device feed v1)</a></p></div>
   <div class="card"><h3>${S.lang === "ar" ? "التحليل" : "Analysis"} (${a.samples || 0})</h3>
     <p>💧 ${S.lang === "ar" ? "الترطيب" : "Hydration"}: <b>${esc(a.hydration || "—")}</b></p><p>🦴 Ca trend: <b>${a.calcium_trend_mg_per_day ?? "—"}</b> mg/day per day</p>
     <p>🫘 ${S.lang === "ar" ? "خطر الحصى" : "Stone risk"}: <b>${sr.score}/${sr.max}</b> ${lvl(sr.level)} <span class="muted">${sr.factors.map(esc).join(" · ")}</span></p>
     <p>⇄ in ${a.fluid_in_ml_last3 ?? "—"} ml / out ${a.fluid_out_ml_last3 ?? "—"} ml (last 3)</p><p>${esc(L(a, "recommend"))}</p>${chartSvg(ser)}</div></div>`;
};
MOUNT.urine = () => { const f = $("#uFile"); if (f) f.addEventListener("change", async () => { const r = await post("/api/urine/import", { filename: f.files[0].name, text: await f.files[0].text() }); toast(`✔ ${r.imported} · ⚠ ${r.errors.length}`); go("urine"); }); };
ACTIONS.urineAdd = async () => { const b = { aid: S.aid, source: "manual_strip" }; ["specific_gravity", "calcium_mg_day", "ph", "volume_ml", "fluid_intake_ml"].forEach((k) => { const v = $("#u_" + k).value; if (v !== "") b[k] = +v; }); const r = await post("/api/urine", b); if (!r.ok) return toast("⛔ " + r.errors.join("; "), 5000); go("urine"); };

// ============ F7 Coach
VIEWS.coach = async () => {
  const head = await featHead("F7_coach", "🏋️", "coach", { en: "Adjusts today's ARED / treadmill / cycle minutes ONLY within the flight-surgeon-approved prescription bounds, using sleep, fatigue, urinary calcium and mass. Suggests meals from the onboard menu to cover calcium, vitamin D and protein while capping sodium. Gamification rewards healthy habits only; the crew board is anonymous.", ar: "يعدّل دقائق ARED والمشي والدراجة ضمن حدود الوصفة المعتمدة فقط، بناءً على النوم والإرهاق وكالسيوم البول والكتلة. يقترح وجبات من القائمة لتغطية الكالسيوم وفيتامين د والبروتين مع حد للصوديوم. التحفيز للعادات الصحية فقط؛ لوحة الطاقم مجهولة." },
    { en: "Uses existing health data; the crew board shows pseudonyms only.", ar: "يستخدم البيانات الموجودة؛ لوحة الطاقم بأسماء مستعارة." }, ["scott_2023", "english_2020", "smith_2012"]);
  const [p, b] = await Promise.all([get(withAid("/api/coach")), get("/api/coach/board")]);
  const bar = (k, l) => { const v = p.plan[k], bd = p.bounds[k]; return `<div><b>${l}</b>: ${v} min <span class="muted">(${bd.min}–${bd.max}, default ${bd.default})</span><div style="background:#0a1830;height:14px;border-radius:7px"><div style="width:${(100 * v) / bd.max}%;height:100%;background:var(--cyan);border-radius:7px"></div></div></div>`; };
  return head + `<div class="grid2" style="margin-top:12px"><div class="card"><h3>${S.lang === "ar" ? "خطة اليوم" : "Today's plan"}</h3>${bar("ared_min", "ARED")}${bar("treadmill_min", "Treadmill")}${bar("cycle_min", "Cycle")}
    <ul>${p.reasons.map((r) => `<li>${esc(r)}</li>`).join("")}</ul><p class="muted">${esc(p.note)}</p>
    <div class="row"><select id="exDev"><option value="ared">ARED</option><option value="treadmill">Treadmill</option><option value="cycle">Cycle</option></select><input id="exMin" inputmode="decimal" placeholder="min" style="width:100px"><button data-act="logEx">${t("save")}</button></div>
    <p>🔥 streak: <b>${p.gamification.streak_days}</b> ${p.gamification.badges.map((x) => `<span class="pill">${esc(x)}</span>`).join("")}</p></div>
   <div class="card"><h3>🍽️ ${S.lang === "ar" ? "اقتراح وجبات" : "Meal suggestions"}</h3><ul>${p.meals.items.map((m) => `<li>${esc(L(m, "name"))} – Ca ${m.calcium_mg} mg · D ${m.vitd_iu} IU · P ${m.protein_g} g · Na ${m.sodium_mg} mg</li>`).join("")}</ul>
    <p class="muted">Totals: Ca ${p.meals.totals.calcium_mg}/${p.meals.targets.calcium_mg} mg · D ${p.meals.totals.vitd_iu}/${p.meals.targets.vitd_iu} IU · protein ${p.meals.totals.protein_g}/${p.meals.targets.protein_g} g · Na ${p.meals.totals.sodium_mg}/≤${p.meals.targets.sodium_mg_max} mg · ${p.meals.totals.kcal}/${p.meals.kcal_target} kcal</p><p class="cite">${esc(p.meals.targets._note)}</p>
    <h3>🏆 Crew board (anonymous)</h3><table>${b.board.map((r) => `<tr><td>${esc(r.who)}</td><td>${r.streak_days} d</td></tr>`).join("")}</table></div></div>`;
};
ACTIONS.logEx = async () => { await post("/api/coach/exercise", { aid: S.aid, device: $("#exDev").value, minutes: +$("#exMin").value }); go("coach"); };

// ============ F1 Voice
const VOICE_SENTENCE = { en: "The quick crew checked the oxygen system before the long night shift on the station.", ar: "فحص الطاقم نظام الأكسجين بسرعة قبل نوبة الليل الطويلة في المحطة." };
VIEWS.voice = async () => {
  const head = await featHead("F1_voice", "🎙️", "voice", { en: "Opt-in 60-second check-in: read the fixed sentence (30 s) then talk freely (30 s). Your browser extracts pitch (F0) mean/variability, energy, speech rate, pause ratio, jitter and shimmer, and compares them with YOUR baseline. The signal is combined with sleep and mood before anything is suggested. Inspired by NASA HERA speech-based team-functioning research. Dehydration detection is an untested hypothesis and is OFF.", ar: "تسجيل اختياري 60 ثانية: اقرأ الجملة الثابتة (30 ث) ثم تحدث بحرية (30 ث). يستخرج المتصفح خصائص النبرة والطاقة وسرعة الكلام والتوقفات ويقارنها بخط أساسك. تُدمج الإشارة مع النوم والمزاج قبل أي اقتراح. كشف الجفاف فرضية غير مختبرة ومطفأة." },
    { en: "RAW AUDIO IS NEVER STORED OR SENT – it is processed in memory on this device and discarded. Only 7 numbers are saved. The result is never a diagnosis.", ar: "لا يُحفظ الصوت الخام ولا يُرسل أبدًا – يُعالج في الذاكرة على هذا الجهاز ثم يُحذف. تُحفظ 7 أرقام فقط. النتيجة ليست تشخيصًا." }, ["mishra_2026", "hrp_bmed_2015"], "voice_features", true);
  let hist = { checkins: [] }; try { hist = await get(withAid("/api/voice")); } catch (e) { /* role */ }
  const last = hist.checkins[hist.checkins.length - 1];
  return head + `<div class="grid2" style="margin-top:12px">${S.user.role === "astronaut" ? `<div class="card"><h3>🎙️ ${S.lang === "ar" ? "التسجيل اليومي" : "Daily check-in"}</h3><p style="font-size:1.2em">“${esc(VOICE_SENTENCE[S.lang])}”</p>
     <p class="muted" id="vPrompt"></p><button class="primary" data-act="voiceRec">● 60 s</button> <button data-act="voiceRec" data-s="10">● 10 s (demo)</button><div id="vRes"></div></div>` : ""}
   <div class="card"><h3>${S.lang === "ar" ? "آخر النتائج" : "Recent"}</h3>${last ? `<p>${esc(L(last.payload.message, "") || last.payload.message[S.lang])} (score ${last.payload.score})</p>` : ""}
     <table><tr><th>ts</th><th>signal</th><th>F0</th><th>rate</th><th>pause</th></tr>${hist.checkins.slice(-8).reverse().map((c) => `<tr><td>${esc(c.ts.slice(0, 10))}</td><td>${esc(c.payload.signal)}</td><td>${c.payload.features.f0_mean?.toFixed?.(0) ?? ""}</td><td>${c.payload.features.speech_rate?.toFixed?.(2) ?? ""}</td><td>${c.payload.features.pause_ratio?.toFixed?.(2) ?? ""}</td></tr>`).join("")}</table></div></div>`;
};
ACTIONS.voiceRec = async (el) => {
  const secs = +(el.dataset.s || 60);
  const f = await ASTRA_DSP.voiceFeatures(secs, (s) => { $("#vPrompt").textContent = `${s.toFixed(0)} / ${secs} s – ${s < secs / 2 ? (S.lang === "ar" ? "اقرأ الجملة" : "read the sentence") : (S.lang === "ar" ? "تحدث بحرية" : "talk freely")}`; });
  const r = await post("/api/voice", { aid: S.aid, features: f });
  $("#vRes").innerHTML = `<p>${esc(r.message[S.lang] || r.message.en)}</p><p class="muted">${esc(r.note || "")}</p><p>${esc(L(r.combined, "text"))}</p><pre class="cite">${esc(JSON.stringify(r.features))}</pre>`;
};

// ============ F3 Crew Harmony
VIEWS.crew = async () => {
  const head = await featHead("F3_crew", "🤝", "crew", { en: "Team index 0–100 from the weekly survey (cohesion, conflict, workload) and shared meals. The individual isolation signal compares your interaction minutes with the crew median and your own early weeks – visible ONLY to you and the behavioral health specialist. Suggests evidence-based actions (debrief, shared meal, schedule adjustment).", ar: "مؤشر الفريق 0–100 من الاستبيان الأسبوعي والوجبات المشتركة. إشارة العزلة الفردية تقارن دقائق تفاعلك مع وسيط الطاقم وأسابيعك الأولى – مرئية لك ولأخصائي الصحة السلوكية فقط. يقترح إجراءات مبنية على الأدلة." },
    { en: "Metadata only (who, minutes, meals) – conversation content is never recorded.", ar: "بيانات وصفية فقط (مع من، كم دقيقة، وجبات) – لا يُسجّل محتوى المحادثات أبدًا." }, ["hrp_team_2022", "nasa_team_risk_2025", "mishra_2026"], "crew_interaction");
  const ti = await get("/api/crew/index");
  let iso = null; if (["bhs", "astronaut"].includes(S.user.role)) try { iso = await get(withAid("/api/crew/isolation")); } catch (e) { /* not visible */ }
  return head + `<div class="grid2" style="margin-top:12px"><div class="card"><h3>👥 Team index</h3><div class="big-num">${ti.index ?? "—"}</div><p class="muted">${ti.trend.map((x) => `${esc(x.day)}: ${x.index}`).join(" · ")}</p>
     <ul>${ti.suggestions.map((s) => `<li>${esc(s[S.lang])}</li>`).join("") || "<li>—</li>"}</ul></div>
   <div class="card"><h3>🔒 ${S.lang === "ar" ? "إشارة العزلة" : "Isolation signal"}</h3>${iso ? `<p class="big-num">${esc(iso.signal)}</p><p class="muted">${esc(JSON.stringify(iso))}</p>` : `<p class="muted">${S.lang === "ar" ? "مرئية فقط للفرد ولأخصائي الصحة السلوكية." : "Visible only to the individual and the behavioral health specialist."}</p>`}</div></div>
   ${S.user.role === "astronaut" ? `<div class="grid2" style="margin-top:14px"><div class="card"><h3>${S.lang === "ar" ? "سجل التفاعل اليومي" : "Daily interaction log"}</h3><div class="grid"><div><label>partner</label><input id="ciP" value="crew"></div><div><label>minutes</label><input id="ciM" inputmode="decimal"></div><div><label>shared meals</label><input id="ciS" inputmode="decimal" value="1"></div><div><label>sleep overlap h</label><input id="ciO" inputmode="decimal" value="6"></div></div><button data-act="ciSave">${t("save")}</button></div>
     <div class="card"><h3>${S.lang === "ar" ? "الاستبيان الأسبوعي" : "Weekly survey"}</h3>${["cohesion", "conflict", "workload"].map((k) => `<label>${k} (1–5)</label><div class="row">${[1, 2, 3, 4, 5].map((n) => `<label class="chip"><input type="radio" name="sv_${k}" value="${n}" ${n === 3 ? "checked" : ""}> ${n}</label>`).join("")}</div>`).join("")}<button data-act="svSave">${t("save")}</button></div></div>` : ""}`;
};
ACTIONS.ciSave = async () => { await post("/api/crew/interaction", { aid: S.aid, partner: $("#ciP").value, minutes: +$("#ciM").value, shared_meals: +$("#ciS").value, sleep_overlap_h: +$("#ciO").value }); go("crew"); };
ACTIONS.svSave = async () => { const v = (k) => +document.querySelector(`input[name=sv_${k}]:checked`).value; await post("/api/crew/survey", { aid: S.aid, cohesion: v("cohesion"), conflict: v("conflict"), workload: v("workload") }); go("crew"); };

// ============ F8 Smart Nostalgia
VIEWS.connection = async () => {
  const head = await featHead("F8_connection", "🌍", "connection", { en: "A family media library chosen before flight (put files in data/media/<astronaut id>/). A gentle card appears only when mood or isolation signals persist ≥ 3 days, or on demand; always skippable, can be switched off, never during a critical task.", ar: "مكتبة وسائط عائلية تُختار قبل الرحلة. تظهر بطاقة لطيفة فقط عند استمرار إشارات المزاج أو العزلة 3 أيام أو عند الطلب؛ قابلة للتخطي ويمكن إيقافها ولا تظهر أثناء مهمة حرجة." },
    { en: "Only a 1-tap 'helped / didn't help' rating is stored – never what you viewed.", ar: "يُحفظ فقط تقييم 'ساعد/لم يساعد' – وليس ما شاهدته." }, ["hrp_bmed_2015", "picano_2024"], "connection");
  const c = await get(withAid("/api/connection"));
  const media = c.library.map((m) => { const u = `${m.url}?token=${S.token}`; return /\.(mp3|wav|ogg)$/i.test(m.name) ? `<audio controls src="${u}"></audio>` : /\.(mp4|webm)$/i.test(m.name) ? `<video controls src="${u}" style="max-width:100%"></video>` : `<img src="${u}" alt="" style="max-width:220px;border-radius:10px">`; }).join("");
  return head + `<div class="card" style="margin-top:12px">${c.suggest.suggest ? `<div class="why green"><b>💌 ${S.lang === "ar" ? "لحظة من الوطن؟" : "A moment from home?"}</b> <span class="muted">(${esc(c.suggest.reason)})</span></div>` : `<p class="muted">${esc(c.suggest.reason)}</p>`}
    <div class="row">${media || `<p class="muted">${S.lang === "ar" ? "لا توجد وسائط بعد. ضع الملفات في data/media/" : "No media yet. Place files in data/media/"}${esc(S.aid)}/</p>`}</div>
    ${S.user.role === "astronaut" ? `<div class="row"><button data-act="nRate" data-h="1">👍 ${S.lang === "ar" ? "ساعدني" : "Helped"}</button><button data-act="nRate" data-h="0">👎 ${S.lang === "ar" ? "لم يساعد" : "Didn't help"}</button><button data-act="nOff" data-o="${c.off ? 0 : 1}">${c.off ? "▶ on" : "⏸ off"}</button></div>` : ""}</div>`;
};
ACTIONS.nRate = async (el) => { const r = await post("/api/connection/rate", { aid: S.aid, helped: el.dataset.h === "1" }); toast(`✔ ${r.helped_pct}% helped (${r.ratings})`); };
ACTIONS.nOff = async (el) => { await post("/api/connection/off", { aid: S.aid, off: el.dataset.o === "1" }); go("connection"); };

// ============ F9 Black box
VIEWS.blackbox = async () => {
  const head = await featHead("F9_blackbox", "📦", "blackbox", { en: "Every reading, alert, decision, consent change and login is appended to a SHA-256 hash chain; payloads are AES-256-GCM encrypted; UPDATE/DELETE are blocked. The tamper check recomputes the chain. Research export: consent-gated, pseudonymised FHIR bundle + data dictionary in an OAIS-style package – mirroring NASA's lifetime astronaut health surveillance and LSDA data-reuse practice.", ar: "كل قراءة وتنبيه وقرار وتغيير موافقة ودخول يُلحق بسلسلة تجزئة SHA-256؛ المحتوى مشفر؛ التعديل والحذف ممنوعان. فحص العبث يعيد حساب السلسلة. التصدير البحثي: بأسماء مستعارة وبموافقة، حزمة FHIR وقاموس بيانات بأسلوب OAIS." },
    { en: "Research export includes only astronauts who granted 'research_export'; ids are keyed pseudonyms; dates are generalised to the day.", ar: "يشمل التصدير فقط من منح الموافقة؛ المعرفات مستعارة؛ التواريخ بمستوى اليوم." }, ["vanbaalen_2017", "lsda_2024"]);
  let ents = { entries: [] }; if (["cmo", "flight_surgeon"].includes(S.user.role)) ents = await get("/api/blackbox?limit=40");
  return head + `<div class="row" style="margin-top:12px"><button class="primary" data-act="bbVerify">🔍 tamper check</button><button data-act="bbTamper">🧪 tamper demo (on a copy)</button>${["flight_surgeon", "researcher"].includes(S.user.role) ? `<button data-act="bbExport">⬇ research export (zip)</button>` : ""}</div><div id="bbRes"></div>
   ${ents.entries.length ? `<div class="card" style="margin-top:12px;overflow-x:auto"><table><tr><th>#</th><th>ts</th><th>actor</th><th>category</th><th>hash</th></tr>${ents.entries.map((e) => `<tr><td>${e.seq}</td><td>${esc(e.ts)}</td><td>${esc(e.actor)}</td><td>${esc(e.category)}</td><td><code>${esc(e.hash.slice(0, 16))}…</code></td></tr>`).join("")}</table></div>` : ""}`;
};
ACTIONS.bbVerify = async () => { const r = await get("/api/blackbox/verify"); $("#bbRes").innerHTML = `<div class="card">${r.ok ? `✔ chain intact – ${r.entries} entries – head <code>${esc(r.head)}</code>` : `⛔ broken at #${r.broken_at}`}</div>`; };
ACTIONS.bbTamper = async () => { const r = await post("/api/blackbox/tamper_demo"); $("#bbRes").innerHTML = `<div class="card">original: ${r.original.ok ? "✔ intact" : "⛔"} · tampered copy (entry #${r.tampered_seq} edited): ${r.tampered_copy.ok ? "✔" : `⛔ detected at #${r.tampered_copy.broken_at}`}</div>`; };
ACTIONS.bbExport = async () => { const b = await get("/api/export"); const a = document.createElement("a"); a.href = URL.createObjectURL(b); a.download = "bovd_research_export_SIP.zip"; a.click(); };

// ============ Settings (incl. Standards page, scenario lab, thresholds, flags)
VIEWS.settings = async () => {
  const m = S.meta; const fs = S.user.role === "flight_surgeon"; const lab = ["cmo", "flight_surgeon"].includes(S.user.role);
  let cons = ""; if (S.user.role === "astronaut") { const c = await get(withAid("/api/consent")); cons = `<div class="card"><h3>🔐 ${t("consent")}</h3><table>${Object.entries(c.categories).map(([k, v]) => `<tr><td>${esc(v[S.lang])}</td><td>${c.consents[k] ? "✔" : "✖"}</td><td><button class="small" data-act="consent" data-c="${k}" data-g="${c.consents[k] ? 0 : 1}">${c.consents[k] ? t("withdraw") : t("grant")}</button></td></tr>`).join("")}</table></div>`; }
  const flags = Object.entries(m.flags_effective).map(([k, on]) => `<tr><td>${esc(k)} ${m.features.flags[k].experimental ? expBadge() : ""}</td><td>${on ? "✔" : "✖"}</td><td>${fs ? `<button class="small" data-act="flag" data-f="${k}" data-e="${on ? 0 : 1}">${on ? "disable" : "enable"}</button>` : ""}</td></tr>`).join("");
  const A = (s, k) => (S.lang === "ar" && s[k + "_ar"]) || s[k];
  const std = m.standards.register.map((s) => `<tr><td><b>${esc(s.id)}</b><br><span class="muted">${esc(A(s, "title"))}</span></td><td>${esc(A(s, "area"))}</td><td>${esc(A(s, "clauses"))}</td><td><code>${esc(s.where)}</code></td><td>${esc(A(s, "evidence"))}</td><td class="muted">${esc(A(s, "gap"))}</td></tr>`).join("");
  const AR = S.lang === "ar"; const sw = (id, on, lab) => `<label class="row" style="margin:6px 0;color:var(--ink)"><input type="checkbox" id="${id}" ${on ? "checked" : ""}> ${lab}</label>`;
  const disp = `<div class="card"><h3>${ic("settings")} ${AR ? "العرض والحركة" : "Display & motion"}</h3>
    ${sw("stDark", S.theme === "dark", AR ? "الوضع الليلي" : "Dark mode")}${sw("stHc", document.body.classList.contains("hc"), AR ? "تباين عالٍ" : "High contrast")}
    ${sw("stBig", document.body.classList.contains("big"), AR ? "وضع القفازات (أزرار أكبر)" : "Glove mode")}${sw("stRm", document.body.classList.contains("reduce-motion"), AR ? "تقليل الحركة" : "Reduce motion")}
    ${sw("stIntro", localStorage.getItem("astra.intro") !== "0", AR ? "عرض الانترو عند فتح التطبيق" : "Show intro on start")}
    <h4 style="margin:12px 0 6px">${AR ? "أسلوب الانتقال بين الصفحات" : "Page transition"}</h4>
    <div class="chips" role="radiogroup">${Object.entries(Motion.STYLES).map(([k, v]) => `<button class="small ${Motion.style() === k ? "on" : ""}" role="radio" aria-checked="${Motion.style() === k}" data-act="setTrans" data-s="${k}">${esc(v[AR ? 0 : 1])}</button>`).join("")}</div>
    <p class="small muted" id="transDesc">${esc(Motion.STYLES[Motion.style()][2])}</p>
    <button class="small" data-act="tryTrans">${ic("play")} ${AR ? "جرّب الانتقال" : "Try transition"}</button>
    <div class="row" style="margin-top:8px"><button class="small" data-act="tourStart">${ic("play")} ${AR ? "أعد تشغيل الجولة التعريفية" : "Replay tour"}</button><button class="small" data-act="introReplay">${ic("restart")} ${AR ? "أعد عرض الانترو" : "Replay intro"}</button></div>
    <p class="small muted">${AR ? "مقصورة تقييم CO₂ الحالية" : "Cabin for CO₂ assessment"}: <b>${esc(m.cabin_preset || "iss")}</b> – <a href="#" data-act="go" data-v="simulate">${AR ? "غيّرها من صفحة المحاكاة" : "change in Simulation"}</a></p></div>`;
  return `<h2>${t("settings")}</h2><div class="grid2">${disp}${cons}<div class="card"><h3>🚩 Feature flags</h3><table>${flags}</table></div>
   ${lab ? `<div class="card"><h3>🧪 Scenario lab (SYNTHETIC)</h3><select id="scA">${S.crew.map((c) => `<option value="${c.id}">${esc(c.id)}</option>`).join("")}</select><select id="scS">${Object.entries(m.scenarios).map(([k, v]) => `<option value="${k}">${esc(v[S.lang])}</option>`).join("")}</select><button data-act="runScen">▶</button><p class="muted">Adds SYNTHETIC history + final day through the full workflow. All values carry the SYNTHETIC badge.</p>
     <h3>Import FHIR bundle (REAL loader output)</h3><input type="file" id="fhirF" accept=".json"></div>` : ""}
   ${fs ? `<div class="card"><h3>🎚️ Thresholds (flight surgeon review)</h3><select id="thI">${Object.entries(m.indicators).map(([k, v]) => `<option value="${k}">${esc(v.label_en)}</option>`).join("")}</select><label>yellow_if (JSON)</label><input id="thY" style="width:100%"><label>red_if (JSON)</label><input id="thR" style="width:100%"><button data-act="thSave">${t("save")} + mark reviewed</button></div>` : ""}</div>
   <div class="card" style="margin-top:14px"><h3>📏 ${S.lang === "ar" ? "المعايير (صُمّم بما يتماشى معها – دون اعتماد)" : "Settings → Standards (designed in alignment with – not certified)"}</h3><div style="overflow-x:auto"><table><tr>${(S.lang === "ar" ? ["المعيار", "المجال", "البنود", "موضعه في الكود", "الدليل", "الفجوة حتى الاعتماد"] : ["Standard", "Area", "Clauses", "Where in code", "Evidence", "Gap to certification"]).map((h) => `<th>${h}</th>`).join("")}</tr>${std}</table></div></div>`;
};
MOUNT.settings = () => {
  const bind = (id, fn) => $(id) && $(id).addEventListener("change", (e) => fn(e.target.checked));
  bind("#stDark", (v) => { S.theme = v ? "dark" : "light"; localStorage.setItem("astra.theme", S.theme); applyTheme(); });
  bind("#stHc", (v) => { document.body.classList.toggle("hc", v); localStorage.setItem("astra.hc", v ? "1" : "0"); });
  bind("#stBig", (v) => { document.body.classList.toggle("big", v); localStorage.setItem("astra.big", v ? "1" : "0"); });
  bind("#stRm", (v) => { document.body.classList.toggle("reduce-motion", v); localStorage.setItem("astra.reduce", v ? "1" : "0"); });
  bind("#stIntro", (v) => localStorage.setItem("astra.intro", v ? "1" : "0"));
  const ti = $("#thI"); if (ti) { const fill = () => { const v = S.meta.indicators[ti.value]; $("#thY").value = JSON.stringify(v.yellow_if); $("#thR").value = JSON.stringify(v.red_if); }; ti.addEventListener("change", fill); fill(); }
  const ff = $("#fhirF"); if (ff) ff.addEventListener("change", async () => { const r = await post("/api/import/fhir", { bundle: JSON.parse(await ff.files[0].text()) }); toast(`✔ ${r.imported} REAL observations`); });
};
ACTIONS.flag = async (el) => { await post("/api/flags", { feature: el.dataset.f, enabled: el.dataset.e === "1" }); S.meta = await get("/api/meta"); go("settings"); };
ACTIONS.runScen = async () => { toast("…"); const r = await post("/api/scenario", { aid: $("#scA").value, scenario: $("#scS").value, days: 14 }); toast(`✔ ${r.scenario} → ${r.astronaut_id}`); S.meta = await get("/api/meta"); };
ACTIONS.thSave = async () => { await post("/api/thresholds", { indicator: $("#thI").value, yellow_if: JSON.parse($("#thY").value), red_if: JSON.parse($("#thR").value) }); S.meta = await get("/api/meta"); toast("✔ saved & logged to black box"); };
ACTIONS.introReplay = () => { sessionStorage.removeItem("astra.introShown"); const d = document.createElement("div"); d.id = "splash"; d.innerHTML = '<div class="stage" id="splashStage"></div><p class="tag" id="splashTag"></p><button class="skip ghost" id="splashSkip" type="button">تخطي ›</button>';
  document.body.appendChild(d); const prev = localStorage.getItem("astra.intro"); localStorage.removeItem("astra.intro"); splash().then(() => { if (prev) localStorage.setItem("astra.intro", prev); }); };
ACTIONS.setTrans = (el) => { localStorage.setItem("astra.trans", el.dataset.s); document.querySelectorAll("[data-act=setTrans]").forEach((b) => { b.classList.toggle("on", b === el); b.setAttribute("aria-checked", b === el); }); $("#transDesc").textContent = Motion.STYLES[el.dataset.s][2]; };
ACTIONS.tryTrans = () => Motion.transition(() => go("settings", { keepScroll: true }));
