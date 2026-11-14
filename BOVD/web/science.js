/* =====================================================================
   BÖVD · Science: evidence registry page, environment simulation, measurement history, help.
   Rules enforced here (from the brief):
   - every scientific value shown links to an evidence entry (source, locator, limitations)
   - SIMULATED values are badged and kept apart from MEASURED data
   - no interpolation where the registry has no data → shown as an evidence GAP
   - gravity effects and pressure/altitude effects are separate models
   ===================================================================== */
"use strict";
(function () {
  const AR = () => S.lang === "ar";
  const KIND = { measured: ["نتيجة مقيسة منشورة", "Published measurement"], standard: ["معيار / حد تشغيلي", "Standard / limit"], model: ["نموذج / معادلة منشورة", "Published model"],
    default: ["قيمة افتراضية سريرية (ليست من ناسا)", "Clinical default (not NASA)"], gap: ["دليل غير كافٍ", "Insufficient evidence"] };
  const kindB = (k) => `<span class="kind ${esc(k)}">${esc(KIND[k] ? KIND[k][AR() ? 0 : 1] : k)}</span>`;
  const simB = () => `<span class="badge sim">${AR() ? "محاكاة" : "SIMULATED"}</span>`;
  const srcLine = (ids) => `<div class="srcline">${AR() ? "مصدر هذا الرسم" : "Chart sources"}: ${evChips(ids)}</div>`;

  // ------------------------------------------------------------ tiny accessible SVG chart (one y-axis, hover tooltip, table view)
  function lineChart(o) {
    const W = 640, H = 260, PL = 46, PR = 16, PT = 14, PB = 36;
    const all = o.series.flatMap((s) => [...s.pts.map((p) => p[1]), ...(s.band || []).flatMap((b) => [b[1], b[2]])]);
    let lo = o.yMin ?? Math.min(...all), hi = o.yMax ?? Math.max(...all); if (lo === hi) hi = lo + 1;
    const xs = o.series.flatMap((s) => s.pts.map((p) => p[0])); const x0 = Math.min(...xs), x1 = Math.max(...xs);
    const X = (x) => PL + ((x - x0) / (x1 - x0 || 1)) * (W - PL - PR), Y = (y) => H - PB - ((y - lo) / (hi - lo)) * (H - PT - PB);
    const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => lo + f * (hi - lo));
    const grid = `<g class="grid">${ticks.map((v) => `<line x1="${PL}" x2="${W - PR}" y1="${Y(v)}" y2="${Y(v)}"/>`).join("")}</g>
      <g class="axis">${ticks.map((v) => `<text x="${PL - 6}" y="${Y(v) + 4}" text-anchor="end">${+v.toFixed(1)}</text>`).join("")}
      ${[x0, (x0 + x1) / 2, x1].map((v) => `<text x="${X(v)}" y="${H - PB + 16}" text-anchor="middle">${Math.round(v)}</text>`).join("")}
      <text x="${(W + PL) / 2}" y="${H - 4}" text-anchor="middle">${esc(o.xLabel)}</text><text x="10" y="${PT + 2}" text-anchor="start">${esc(o.yLabel)}</text></g>`;
    const body = o.series.map((s) => {
      const band = s.band ? `<path class="${s.cls}" style="stroke:none;opacity:.16" d="M${s.band.map((b) => `${X(b[0])},${Y(b[2])}`).join("L")}L${s.band.slice().reverse().map((b) => `${X(b[0])},${Y(b[1])}`).join("L")}Z"/>` : "";
      const segs = []; let cur = null; // split solid (evidenced) vs dashed (extrapolated/simulated)
      s.pts.forEach((p, i) => { const d = !!p[2]; if (!cur || cur.d !== d) { cur = { d, pts: i ? [s.pts[i - 1]] : [] }; segs.push(cur); } cur.pts.push(p); });
      const lines = segs.map((g) => `<path class="${s.cls} ${g.d ? "dashed" : ""}" fill="none" stroke-width="2" stroke-linecap="round" d="M${g.pts.map((p) => `${X(p[0]).toFixed(1)},${Y(p[1]).toFixed(1)}`).join("L")}"/>`).join("");
      const last = s.pts[s.pts.length - 1];
      return band + lines + `<text class="lbl" x="${X(last[0]) - 4}" y="${Y(last[1]) - 8}" text-anchor="end">${esc(s.name)}</text>`;
    }).join("");
    const mk = o.marker ? `<line x1="${X(o.marker.x)}" x2="${X(o.marker.x)}" y1="${PT}" y2="${H - PB}" stroke="var(--ink)" stroke-dasharray="3 4"/><circle cx="${X(o.marker.x)}" cy="${Y(o.marker.y)}" r="5" fill="var(--ink)" stroke="var(--surface)" stroke-width="2"/><text class="lbl" x="${X(o.marker.x) + 8}" y="${Y(o.marker.y) - 8}">${esc(o.marker.label)}</text>` : "";
    const xsU = [...new Set(xs)].sort((a, b) => a - b); const step = (W - PL - PR) / Math.max(1, xsU.length - 1);
    const hits = xsU.map((x) => { const tip = `${o.xLabel}: ${x}` + o.series.map((s) => { const p = s.pts.find((q) => q[0] === x); const b = s.band && s.band.find((q) => q[0] === x);
      return p ? ` · ${s.name}: ${b ? `${b[1]}–${b[2]}` : p[1]} ${o.unit || ""}${p[2] ? (AR() ? " (استقراء)" : " (extrapolated)") : ""}` : ""; }).join("");
      return `<rect class="hit" x="${X(x) - step / 2}" y="${PT}" width="${step}" height="${H - PT - PB}" data-tip="${esc(tip)}"/>`; }).join("");
    const legend = o.series.length > 1 ? `<div class="legend">${o.series.map((s) => `<span><i style="background:var(--${s.cls})"></i>${esc(s.name)}</span>`).join("")}${o.legendExtra || ""}</div>` : o.legendExtra ? `<div class="legend">${o.legendExtra}</div>` : "";
    const table = `<details class="small"><summary>${AR() ? "عرض كجدول" : "Table view"}</summary><div class="table-wrap"><table><tr><th>${esc(o.xLabel)}</th>${o.series.map((s) => `<th>${esc(s.name)}</th>`).join("")}</tr>
      ${xsU.map((x) => `<tr><td>${x}</td>${o.series.map((s) => { const p = s.pts.find((q) => q[0] === x); const b = s.band && s.band.find((q) => q[0] === x); return `<td>${p ? (b ? `${b[1]}–${b[2]}` : p[1]) + (p[2] ? " *" : "") : "—"}</td>`; }).join("")}</tr>`).join("")}</table></div></details>`;
    return `${legend}<svg class="vchart" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(o.title)}">${grid}${body}${mk}${hits}</svg>${table}`;
  }
  // hover tooltips for all charts
  let tipEl = null;
  document.addEventListener("pointermove", (e) => {
    const h = e.target.closest && e.target.closest("[data-tip]");
    if (!tipEl) { tipEl = document.createElement("div"); tipEl.className = "ctip"; document.body.appendChild(tipEl); }
    if (!h) { tipEl.style.display = "none"; return; }
    tipEl.textContent = h.dataset.tip; tipEl.style.display = "block";
    tipEl.style.left = Math.min(innerWidth - 270, e.clientX + 14) + "px"; tipEl.style.top = e.clientY + 14 + "px";
  });

  // ============================================================ evidence / sources page
  VIEWS.science = async () => {
    if (!S.evidence || !S.evidence.length) S.evidence = (await get("/api/evidence")).entries;
    const cats = [...new Set(S.evidence.map((e) => e.category))];
    const refs = S.meta.references, inds = S.meta.indicators, th = S.meta.thresholds;
    const fmtR = (rs) => rs.map((r) => Object.entries(r).map(([op, v]) => `${{ lt: "<", le: "≤", gt: ">", ge: "≥" }[op]}${v}`).join("")).join(" or ") || "—";
    const rows = Object.entries(inds).map(([k, m]) => `<tr><td>${esc(L(m, "label"))}</td><td>${esc(m.loinc || "—")}</td><td>${esc(m.ucum)}</td><td>${esc(fmtR(m.yellow_if))}</td><td>${esc(fmtR(m.red_if))}</td><td>${evChips(m.evidence)} ${m.citation.map((c) => `<a href="#ref-${c}">${esc(c)}</a>`).join(", ")}</td><td>${m.review_needed ? "⚠ " + (AR() ? "تحتاج مراجعة" : "review needed") : "✔"}</td></tr>`).join("");
    const byTopic = {}; Object.entries(refs).forEach(([k, r]) => (byTopic[r.topic] = byTopic[r.topic] || []).push([k, r]));
    return `<div class="pagehead"><h2>${ic("science")} ${esc(t("science"))}</h2></div>
    <p class="muted">${AR() ? `كل قيمة علمية في التطبيق مربوطة بمدخل هنا: المؤشر، القيمة، الوحدة، الظروف، العينة، عنوان المصدر، الجهة، التاريخ، الرابط، الموضع داخل المصدر، والقيود. تحقّق من الروابط في ${esc(S.evidenceDate || "2026-11-14")}. القيم «الافتراضية» ليست صادرة عن ناسا، و«دليل غير كافٍ» يعني أن التطبيق لا يعرض رقمًا.` : "Every scientific value in the app links to an entry here."}</p>
    <div class="card"><div class="row"><input id="evQ" type="search" placeholder="${AR() ? "ابحث في المؤشرات والمصادر…" : "Search…"}" style="flex:1;min-width:200px" aria-label="search">
      <select id="evCat" aria-label="category"><option value="">${AR() ? "كل الفئات" : "All categories"}</option>${cats.map((c) => `<option>${esc(c)}</option>`).join("")}</select>
      <select id="evKind" aria-label="kind"><option value="">${AR() ? "كل الأنواع" : "All kinds"}</option>${Object.keys(KIND).map((k) => `<option value="${k}">${esc(KIND[k][AR() ? 0 : 1])}</option>`).join("")}</select></div>
      <p class="small muted" id="evCount"></p><div class="grid2" id="evList"></div></div>
    <div class="card" style="margin-top:14px"><h3>${AR() ? "المؤشرات ← العتبات ← الأدلة" : "Indicators → thresholds → evidence"}</h3><p class="muted">${esc(th.baseline.rationale)} (${th.baseline.sd_multiplier} SD)</p>
      <div class="table-wrap"><table><tr><th>${AR() ? "المؤشر" : "Indicator"}</th><th>LOINC</th><th>UCUM</th><th>${AR() ? "أصفر" : "Yellow"}</th><th>${AR() ? "أحمر" : "Red"}</th><th>${AR() ? "الأدلة" : "Evidence"}</th><th>${AR() ? "المراجعة" : "Review"}</th></tr>${rows}</table></div></div>
    <div class="card" style="margin-top:14px"><h3>${AR() ? "المراجع (APA 7)" : "References (APA 7)"}</h3><div dir="ltr" style="text-align:left">${Object.entries(byTopic).map(([tp, list]) => `<h4>${esc(tp)}</h4><ul>${list.map(([k, r]) => `<li id="ref-${k}"><code>${esc(k)}</code> ${esc(r.apa)} ${r.url ? `<a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.url)}</a>` : "<i>(no URL)</i>"}</li>`).join("")}</ul>`).join("")}</div></div>`;
  };
  function evCard(e) {
    const f = (k, v) => (v ? `<dt>${k}</dt><dd>${v}</dd>` : "");
    return `<article class="evid" id="ev-${esc(e.id)}"><div class="row"><b>${esc(e.id)}</b> ${kindB(e.kind)} <span class="muted small">${esc(e.category)}</span></div>
      <h3 style="margin:6px 0">${esc(AR() ? e.indicator_ar : e.indicator_en)}</h3>
      ${e.finding_ar ? `<p>${esc(e.finding_ar)}</p>` : ""}
      <dl>${f(AR() ? "القيمة" : "Value", `<b>${esc(e.value)}</b> ${esc(e.unit)}`)}${f(AR() ? "الظروف" : "Conditions", esc(e.conditions_ar))}${f(AR() ? "العينة" : "Population", esc(e.population_ar))}
      ${f(AR() ? "العنوان" : "Title", `<span dir="ltr">${esc(e.title)}</span>`)}${f(AR() ? "الجهة" : "Organization", esc(e.organization))}${f(AR() ? "التاريخ" : "Date", esc(e.date))}
      ${f(AR() ? "الموضع" : "Locator", esc(e.locator))}${f(AR() ? "القيود" : "Limitations", esc(e.limitations_ar))}
      ${f(AR() ? "الرابط" : "URL", e.url ? `<a href="${esc(e.url)}" target="_blank" rel="noopener" dir="ltr">${esc(e.url)}</a>` : "—")}</dl></article>`;
  }
  MOUNT.science = () => {
    const draw = () => {
      const q = $("#evQ").value.trim().toLowerCase(), c = $("#evCat").value, k = $("#evKind").value;
      const list = S.evidence.filter((e) => (!c || e.category === c) && (!k || e.kind === k) && (!q || JSON.stringify(e).toLowerCase().includes(q)));
      $("#evList").innerHTML = list.map(evCard).join("") || `<div class="empty">${AR() ? "لا نتائج" : "No results"}</div>`;
      $("#evCount").textContent = `${list.length} / ${S.evidence.length}`;
    };
    ["input", "change"].forEach((ev) => ["#evQ", "#evCat", "#evKind"].forEach((s) => $(s).addEventListener(ev, draw)));
    draw();
    if (S.evFocus) { const el = document.getElementById("ev-" + S.evFocus); S.evFocus = null; if (el) { el.classList.add("hl"); el.scrollIntoView({ block: "center", behavior: reduceMotion() ? "auto" : "smooth" }); } }
  };

  // ============================================================ environment simulation
  const SIM = { phase: "flight", day: 30, mission: 180, gravity: "micro", mode: "cabin", cabin: "iss", alt: 3000, fio2: 0.2095, paco2: 40, co2: 3000 };
  VIEWS.simulate = async () => {
    const canG = !!S.aid && S.user.role !== "bhs" && S.user.role !== "researcher";
    return `<div class="pagehead"><h2>${ic("simulate")} ${esc(t("simulate"))} ${simB()}</h2></div>
    <div class="honesty small">${AR() ? "هذه الصفحة <b>محاكاة</b> مبنية على قيم ومعادلات منشورة فقط (انظر الشارات 📚). لا تُضاف نسب عشوائية، ولا يُستكمل ما لا تغطيه الأدلة (يظهر «دليل غير كافٍ»). الجاذبية والضغط/الارتفاع نموذجان منفصلان: الجاذبية لا تغيّر ضغط الهواء. البيانات المقيسة لرائد الفضاء تبقى في صفحتي الرسوم والسجل ولا تختلط بالمحاكاة." : "Simulation built only from published values/equations. Gravity and pressure/altitude are separate models."}</div>
    <div class="grid2" style="margin-top:14px">
      <div class="card" data-tour="sim-gravity"><h3>${ic("orbit")} ${AR() ? "الجاذبية ومدة التعرّض" : "Gravity & exposure"}</h3>
        ${canG ? `<div class="grid3"><div><label for="smPhase">${AR() ? "المرحلة" : "Phase"}</label><select id="smPhase">${[["preflight", "قبل الرحلة", "Pre-flight"], ["flight", "أثناء الرحلة", "In flight"], ["postflight", "بعد العودة", "Post-flight"]].map(([v, a, e]) => `<option value="${v}" ${SIM.phase === v ? "selected" : ""}>${AR() ? a : e}</option>`).join("")}</select></div>
          <div><label for="smGrav">${AR() ? "الجاذبية" : "Gravity"}</label><select id="smGrav">${[["micro", "انعدام الجاذبية (≈0 g)", "Microgravity"], ["moon", "القمر 0.17 g", "Moon 0.17 g"], ["mars", "المريخ 0.38 g", "Mars 0.38 g"]].map(([v, a, e]) => `<option value="${v}" ${SIM.gravity === v ? "selected" : ""}>${AR() ? a : e}</option>`).join("")}</select></div>
          <div><label for="smMission">${AR() ? "مدة المهمة (يوم)" : "Mission (days)"}</label><input id="smMission" type="number" min="1" max="1000" value="${SIM.mission}"></div></div>
          <label for="smDay">${AR() ? "اليوم في المرحلة" : "Day in phase"}: <b id="smDayV">${SIM.day}</b></label><input id="smDay" type="range" min="0" max="1000" value="${SIM.day}">
          <div id="smGravOut" aria-live="polite">${Motion.loader("pulse")}</div>` : `<p class="muted">${AR() ? "اختر رائد فضاء لعرض أثر الجاذبية على خط أساسه." : "Select an astronaut."}</p>`}
      </div>
      <div class="card" data-tour="sim-pressure"><h3>${ic("lungs")} ${AR() ? "الضغط والارتفاع والأكسجين" : "Pressure, altitude & oxygen"}</h3>
        <div class="row"><label class="row" style="margin:0"><input type="radio" name="smMode" value="cabin" ${SIM.mode === "cabin" ? "checked" : ""}> ${AR() ? "مقصورة" : "Cabin"}</label>
          <label class="row" style="margin:0"><input type="radio" name="smMode" value="alt" ${SIM.mode === "alt" ? "checked" : ""}> ${AR() ? "ارتفاع على الأرض" : "Altitude"}</label></div>
        <div class="grid3"><div id="smCabinBox"><label for="smCabin">${AR() ? "المقصورة" : "Cabin"}</label><select id="smCabin"></select></div>
          <div id="smAltBox"><label for="smAlt">${AR() ? "الارتفاع (م)" : "Altitude (m)"}</label><input id="smAlt" type="number" min="0" max="9000" step="100" value="${SIM.alt}"></div>
          <div><label for="smFio2">FiO₂</label><input id="smFio2" type="number" min="0.15" max="1" step="0.01" value="${SIM.fio2}"></div>
          <div><label for="smPaco2">PaCO₂ (mmHg)</label><input id="smPaco2" type="number" min="20" max="50" step="1" value="${SIM.paco2}"></div>
          <div><label for="smCo2">CO₂ (ppm)</label><input id="smCo2" type="number" min="0" max="20000" step="100" value="${SIM.co2}"></div></div>
        <div id="smAtmOut" aria-live="polite">${Motion.loader("pulse")}</div>
      </div></div>
    <div class="grid2" style="margin-top:14px">
      <div class="card"><h3>${ic("charts")} ${AR() ? "الأرض مقابل الفضاء: مراحل الرحلة" : "Earth vs space: flight phases"} ${simB()}</h3><div id="smPhases">${Motion.loader("dots")}</div></div>
      <div class="card"><h3>${ic("charts")} ${AR() ? "فقد كثافة العظم المتوقع مع مدة المهمة" : "Projected bone loss"} ${simB()}</h3><div id="smBone">${Motion.loader("dots")}</div></div>
      <div class="card"><h3>${ic("charts")} ${AR() ? "تشبع الأكسجين المقدّر مقابل الارتفاع" : "Estimated SaO₂ vs altitude"} ${simB()}</h3><div id="smCurve">${Motion.loader("dots")}</div></div>
    </div>`;
  };
  MOUNT.simulate = async () => {
    const atmo = async () => {
      const q = SIM.mode === "cabin" ? `cabin=${SIM.cabin}` : `alt=${SIM.alt}&fio2=${SIM.fio2}`;
      const r = await get(`/api/physio/atmosphere?${q}&paco2=${SIM.paco2}&co2=${SIM.co2}`);
      const sel = $("#smCabin"); if (!sel.options.length) sel.innerHTML = Object.entries(r.cabins).map(([k, v]) => `<option value="${k}" ${k === SIM.cabin ? "selected" : ""}>${esc(v.label_ar || k)} · ${v.kpa} kPa · ${Math.round(v.fio2 * 100)}% O₂</option>`).join("");
      $("#smCabinBox").style.opacity = SIM.mode === "cabin" ? 1 : 0.45; $("#smAltBox").style.opacity = SIM.mode === "alt" ? 1 : 0.45;
      const o = r.result, c = r.co2;
      $("#smAtmOut").innerHTML = `<div class="grid3" style="margin-top:10px">
        <div class="kpi"><span class="muted small">${AR() ? "الضغط الجوي" : "Barometric"}</span><span class="v">${o.pb_kpa} kPa</span><span class="small muted">${o.pb_mmhg} mmHg</span></div>
        <div class="kpi"><span class="muted small">PIO₂</span><span class="v">${o.pio2}</span><span class="small muted">mmHg ${o.pio2_normoxic ? "✔ " + (AR() ? "مكافئ لمستوى البحر" : "normoxic") : ""}</span></div>
        <div class="kpi"><span class="muted small">PAO₂ ${AR() ? "(سنخي)" : ""}</span><span class="v">${o.pao2}</span><span class="small muted">mmHg</span></div>
        <div class="kpi"><span class="muted small">SaO₂ ${AR() ? "مقدّر" : "est."}</span><span class="v">${o.sao2_est_pct}%</span><span class="small muted">PaO₂ ≈ ${o.pao2_arterial_est}</span></div>
        <div class="kpi"><span class="muted small">ppCO₂</span><span class="v">${c.ppco2_mmhg}</span><span class="small">mmHg ${lvl(c.level)}</span></div>
        <div class="kpi"><span class="muted small">${AR() ? "حد 3 mmHg يعادل" : "3 mmHg limit ="}</span><span class="v">${c.ppm_at_limit}</span><span class="small muted">ppm @ ${c.cabin_kpa} kPa</span></div></div>
        <p class="small muted">${esc(o.assumptions_ar)}</p><div class="row small">${evChips([...o.evidence, ...c.evidence])}</div>
        ${SIM.mode === "cabin" && ["astronaut", "cmo", "flight_surgeon"].includes(S.user.role) ? `<button class="small" data-act="smApplyCabin">${ic("settings")} ${AR() ? "اعتمد هذه المقصورة لتقييم CO₂ في القراءات" : "Use this cabin for CO₂ assessment"}</button>` : ""}`;
      const cur = SIM.mode === "alt" ? { x: SIM.alt, y: r.curve.reduce((a, p) => (Math.abs(p.alt_m - SIM.alt) < Math.abs(a.alt_m - SIM.alt) ? p : a)).sao2 } : null;
      $("#smCurve").innerHTML = lineChart({ title: "SaO2 vs altitude", xLabel: AR() ? "الارتفاع (م)" : "Altitude (m)", yLabel: "SaO₂ %", unit: "%",
        series: [{ name: "SaO₂", cls: "s1", pts: r.curve.map((p) => [p.alt_m, p.sao2]) }], marker: cur ? { ...cur, label: `${cur.y}%` } : null }) +
        `<p class="small muted">${AR() ? `FiO₂ = ${SIM.mode === "alt" ? SIM.fio2 : 0.2095}، PaCO₂ = ${SIM.paco2}. معادلات: صيغة الضغط الجوي القياسية، معادلة الغاز السنخي، ومنحنى سفيرينغهاوس. ليس قياسًا لأي شخص.` : "Published equations; not a measurement."}</p>` + srcLine(o.evidence);
    };
    const grav = async () => {
      if (!$("#smGravOut")) return;
      let r; try { r = await get(withAid(`/api/physio/gravity?phase=${SIM.phase}&day=${SIM.day}&mission=${SIM.mission}&gravity=${SIM.gravity}`)); }
      catch (e) { $("#smGravOut").innerHTML = `<p class="muted">${AR() ? "هذا الدور لا يملك صلاحية قراءة خط الأساس الفسيولوجي لرائد الفضاء." : "This role cannot read the astronaut's physiological baseline."}</p>`; $("#smPhases").innerHTML = $("#smBone").innerHTML = $("#smGravOut").innerHTML; return; }
      const st = { evidence: ["green", AR() ? "قيمة منشورة" : "published"], simulated: ["info", AR() ? "محاكاة من قيمة منشورة" : "simulated"], gap: ["none", AR() ? "دليل غير كافٍ" : "insufficient evidence"], extrapolated: ["yellow", AR() ? "استقراء خارج نطاق البيانات" : "extrapolated"] };
      $("#smGravOut").innerHTML = `<div class="table-wrap" style="margin-top:8px"><table><tr><th>${AR() ? "المؤشر" : "Indicator"}</th><th>${AR() ? "القيمة" : "Value"}</th><th>${AR() ? "الحالة" : "Status"}</th><th>${AR() ? "المصدر" : "Source"}</th></tr>
        ${r.effects.items.map((it) => `<tr><td>${esc(it.label_ar)}</td><td>${it.status === "gap" ? `<span class="muted">${esc(it.value)}</span>` : `<b>${esc(it.value)}</b> ${esc(it.unit)}`}${it.applied ? `<div class="small">${esc(it.applied)}</div>` : ""}</td><td><span class="lvl ${(st[it.status] || st.gap)[0]}">${esc((st[it.status] || [0, it.status])[1])}</span></td><td>${evChips(it.evidence) || "—"}</td></tr>`).join("")}</table></div>
        <p class="small muted">${esc(r.effects.disclaimer_ar || "")} ${r.effects.note_ar ? esc(r.effects.note_ar) : ""}</p>
        <p class="small">${AR() ? "خط الأساس الشخصي (قبل الرحلة)" : "Personal pre-flight baseline"}: ${Object.keys(r.baseline).length ? Object.entries(r.baseline).map(([k, v]) => `${k} ${(+v).toFixed(0)}`).join(" · ") : `<span class="muted">${AR() ? "لا يوجد – القيم تُعرض كنسب فقط" : "none"}</span>`}</p>`;
      // phase comparison – range bars for cardiac-output change, gaps stated explicitly
      const ph = r.phases; const mx = Math.max(...ph.map((p) => (p.co_pct ? p.co_pct[1] : 0)), 10);
      $("#smPhases").innerHTML = `<div class="stack">${ph.map((p) => `<div><div class="row small"><b>${esc(p.phase_ar)}</b> ${evChips(p.evidence)}</div>
        ${p.co_pct ? `<div class="row" style="gap:8px"><div style="flex:1;height:14px;background:var(--surface-2);border-radius:4px;position:relative" data-tip="${esc(`${AR() ? "تغيّر النتاج القلبي" : "Cardiac output change"}: +${p.co_pct[0]}–${p.co_pct[1]}%`)}">
          <i style="position:absolute;inset-inline-start:${(p.co_pct[0] / mx) * 100}%;width:${Math.max(1.5, ((p.co_pct[1] - p.co_pct[0]) / mx) * 100)}%;top:0;bottom:0;background:var(--s1);border-radius:4px"></i></div><span class="small">${p.co_pct[0] === p.co_pct[1] ? p.co_pct[0] : p.co_pct[0] + "–" + p.co_pct[1]}%</span></div>` : ""}
        <div class="small muted">${p.bp_delta ? `${AR() ? "الضغط الانقباضي" : "Systolic"} ${p.bp_delta[0]}…${p.bp_delta[1]} mmHg${p.sys_range ? ` → ${p.sys_range[0]}–${p.sys_range[1]}` : ""}` : ""} ${p.oi_pct ? `${AR() ? "عدم تحمّل الوقوف" : "Orthostatic intolerance"} ${p.oi_pct[0]}%` : ""} ${!p.co_pct && !p.bp_delta && !p.oi_pct ? (AR() ? "لا توجد قيمة منشورة في السجل" : "no published value") : ""}</div></div>`).join("")}</div>
        <p class="small muted">${AR() ? "الشريط = نطاق تغيّر النتاج القلبي المنشور مقارنة بما قبل الرحلة (جالسًا). المراحل بلا شريط ليس لها قيمة منشورة لهذا المؤشر." : "Bar = published range of cardiac-output change vs pre-flight."}</p>` + srcLine([...new Set(ph.flatMap((p) => p.evidence))]);
      const b = r.bone; const ext = (p) => !p.evidenced;
      $("#smBone").innerHTML = lineChart({ title: "bone loss", xLabel: AR() ? "يوم المهمة" : "Mission day", yLabel: AR() ? "% فقد" : "% loss", unit: "%", yMin: 0,
        series: [{ name: AR() ? "العمود الفقري" : "Spine", cls: "s1", pts: b.map((p) => [p.day, p.spine, ext(p)]) },
          { name: AR() ? "الورك" : "Hip", cls: "s2", pts: b.map((p) => [p.day, +((p.hip_lo + p.hip_hi) / 2).toFixed(2), ext(p)]), band: b.map((p) => [p.day, p.hip_lo, p.hip_hi]) }],
        marker: SIM.phase === "flight" ? (() => { const p = b.reduce((a, q) => (Math.abs(q.day - SIM.day) < Math.abs(a.day - SIM.day) ? q : a)); return { x: p.day, y: p.spine, label: `${AR() ? "اليوم" : "day"} ${p.day}` }; })() : null,
        legendExtra: `<span>┄ ${AR() ? "خط متقطع = استقراء بعد 6 أشهر (خارج مدة الدراسات)" : "dashed = extrapolation beyond 6 months"}</span>` }) +
        `<p class="small muted">${AR() ? "معدل خطي من متوسطات منشورة (0.9%/شهر للعمود الفقري، 1.4–1.5%/شهر للورك) دون تمارين مضادة إضافية. ليس تنبؤًا فرديًا." : "Linear published group rates; not an individual prediction."}</p>` + srcLine(["E-BONE-01", "E-BONE-02"]);
    };
    const num = (id, k, fn) => $(id) && $(id).addEventListener("change", (e) => { SIM[k] = +e.target.value; fn(); });
    if ($("#smDay")) {
      $("#smPhase").addEventListener("change", (e) => { SIM.phase = e.target.value; grav(); });
      $("#smGrav").addEventListener("change", (e) => { SIM.gravity = e.target.value; grav(); });
      num("#smMission", "mission", grav);
      let tm; $("#smDay").addEventListener("input", (e) => { SIM.day = +e.target.value; $("#smDayV").textContent = SIM.day; clearTimeout(tm); tm = setTimeout(grav, 120); });
    }
    document.querySelectorAll("input[name=smMode]").forEach((r) => r.addEventListener("change", (e) => { SIM.mode = e.target.value; atmo(); }));
    $("#smCabin").addEventListener("change", (e) => { SIM.cabin = e.target.value; atmo(); });
    num("#smAlt", "alt", atmo); num("#smFio2", "fio2", atmo); num("#smPaco2", "paco2", atmo); num("#smCo2", "co2", atmo);
    await Promise.all([atmo(), grav()]);
    if (!$("#smGravOut")) { try { const r = await get("/api/physio/atmosphere?cabin=iss"); void r; } catch (e) { /* */ } $("#smPhases").innerHTML = `<p class="muted">${AR() ? "اختر رائد فضاء." : "Select an astronaut."}</p>`; $("#smBone").innerHTML = $("#smPhases").innerHTML; }
  };
  ACTIONS.smApplyCabin = async () => { const r = await post("/api/cabin", { preset: SIM.cabin }); S.meta.cabin_preset = r.cabin_preset; toast("✔ " + r.cabin_preset); };

  // ============================================================ measurement history
  VIEWS.history = async (o = {}) => {
    const ind = S.histInd || "";
    const r = await get(withAid(`/api/history?limit=400${ind ? "&indicator=" + ind : ""}`));
    const inds = S.meta.indicators;
    return `<div class="pagehead"><h2>${ic("history")} ${esc(t("history"))}</h2><div class="actions"><button class="small" data-act="histCsv">${AR() ? "تصدير CSV" : "Export CSV"}</button></div></div>
    <div class="card"><div class="row"><select id="hInd" aria-label="indicator"><option value="">${AR() ? "كل المؤشرات" : "All indicators"}</option>${Object.entries(inds).map(([k, v]) => `<option value="${k}" ${k === ind ? "selected" : ""}>${esc(L(v, "label"))}</option>`).join("")}</select>
      <select id="hProv" aria-label="provenance"><option value="">${AR() ? "كل المصادر" : "All provenance"}</option><option>USER-ENTERED</option><option>SYNTHETIC</option><option>REAL</option></select>
      <span class="muted small">${AR() ? "المجموع" : "Total"}: ${r.total}</span></div>
      <p class="small muted">${AR() ? "هذا السجل يعرض القيم <b>المقيسة أو المُدخلة</b> فقط (مع شارة المصدر). نتائج المحاكاة لا تُحفظ هنا." : "Measured/entered values only; simulations are never stored here."}</p>
      <div class="table-wrap"><table id="hTab"><thead><tr><th>${AR() ? "الوقت (UTC)" : "Time (UTC)"}</th><th>${AR() ? "المؤشر" : "Indicator"}</th><th>${t("value")}</th><th>${AR() ? "سياق الجاذبية" : "Gravity"}</th><th>${AR() ? "المصدر" : "Provenance"}</th><th></th></tr></thead>
      <tbody>${r.rows.map((x) => `<tr data-prov="${esc(x.prov.type)}"><td>${esc(x.t.slice(0, 16).replace("T", " "))}</td><td>${esc(inds[x.indicator] ? L(inds[x.indicator], "label") : x.indicator)}</td><td><b>${x.value}</b> ${esc(x.unit)}</td><td>${esc(x.ctx)}</td><td>${prov(x.prov)}</td><td><button class="small ghost" data-act="trend" data-i="${esc(x.indicator)}" aria-label="chart">${ic("charts")}</button></td></tr>`).join("") || `<tr><td colspan="6"><div class="empty">${AR() ? "لا توجد قياسات بعد" : "No measurements yet"}</div></td></tr>`}</tbody></table></div></div>`;
  };
  MOUNT.history = () => {
    $("#hInd").addEventListener("change", (e) => { S.histInd = e.target.value; go("history"); });
    $("#hProv").addEventListener("change", (e) => document.querySelectorAll("#hTab tbody tr[data-prov]").forEach((tr) => (tr.hidden = !!e.target.value && tr.dataset.prov !== e.target.value)));
  };
  ACTIONS.histCsv = () => {
    const rows = [...document.querySelectorAll("#hTab tr")].filter((tr) => !tr.hidden).map((tr) => [...tr.children].slice(0, 5).map((td) => `"${td.textContent.trim().replace(/"/g, '""')}"`).join(","));
    const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob(["﻿" + rows.join("\n")], { type: "text/csv" })); a.download = "bovd_history.csv"; a.click();
  };

  // ============================================================ help
  VIEWS.help = async () => `<div class="pagehead"><h2>${ic("help")} ${esc(t("help"))}</h2></div>
    <div class="grid2"><div class="card"><h3>${ic("play")} ${AR() ? "الجولة التعريفية" : "Guided tour"}</h3><p>${AR() ? "جولة من 11 مرحلة تعرّفك على الواجهة والنموذج ثلاثي الأبعاد والفحوصات والكاميرا والمصادر، وتنتهي بفحص تجريبي موجَّه." : "11-stage tour ending in a guided practice exam."}</p>
      <div class="mkpad" style="margin-bottom:10px" id="helpPad"><span>${AR() ? "حرّك المؤشر أو اسحب بإصبعك" : "Move the pointer"}</span></div>
      <div class="row"><button class="primary" data-act="tourStart">${ic("play")} ${AR() ? "ابدأ الجولة" : "Start tour"}</button><button data-act="practice">${ic("posecheck")} ${AR() ? "فحص تجريبي موجَّه (ضغط الدم)" : "Guided practice exam (BP)"}</button></div></div>
    <div class="card"><h3>${ic("about")} ${AR() ? "أسئلة شائعة" : "FAQ"}</h3>
      <details><summary><b>${AR() ? "هل تقيس الكاميرا ضغط الدم أو الأكسجين؟" : "Does the camera measure BP or SpO2?"}</b></summary><p>${AR() ? "لا. الكاميرا تتحقق من الوضعية والخطوات فقط. القيم تأتي من جهازك المعتمد." : "No. Posture/procedure only."}</p></details>
      <details><summary><b>${AR() ? "ما معنى «محاكاة»؟" : "What does SIMULATED mean?"}</b></summary><p>${AR() ? "قيمة محسوبة من معادلة أو متوسط منشور (مع رابط المصدر)، وليست قياسًا لك." : "Computed from published equations/means; not your measurement."}</p></details>
      <details><summary><b>${AR() ? "ماذا لو لم يعمل العرض ثلاثي الأبعاد؟" : "3D not working?"}</b></summary><p>${AR() ? "يعرض التطبيق تلقائيًا المخطط ثنائي الأبعاد، وتبقى التعليمات النصية متاحة." : "The app falls back to the 2-D map automatically."}</p></details>
      <details><summary><b>${AR() ? "أين تُحفظ بياناتي؟" : "Where is my data stored?"}</b></summary><p>${AR() ? "على هذا الجهاز فقط في قاعدة بيانات مشفرة. لا توجد سحابة. صور الكاميرا لا تُحفظ أبدًا." : "Locally, encrypted. Camera frames are never stored."}</p></details>
      <details><summary><b>${AR() ? "اختصارات لوحة المفاتيح" : "Keyboard"}</b></summary><p>${AR() ? "Tab للتنقل، Enter للتفعيل، Esc لإغلاق القائمة أو الجولة. في النموذج ثلاثي الأبعاد: الأسهم للتدوير، + و − للتكبير، 0 للعودة." : "Tab/Enter/Esc; in 3D: arrows rotate, +/− zoom, 0 resets."}</p></details></div></div>`;
  MOUNT.help = () => Motion.pad($("#helpPad"));
  ACTIONS.tourStart = () => window.Tour && Tour.start(true);
  ACTIONS.practice = () => window.Tour && Tour.practice();
})();
