/* =====================================================================
   BÖVD · 3D exam guide + camera posture verification (OpenCV + MediaPipe on the local server)
   - The camera checks POSTURE / PROCEDURE only. It never measures blood pressure, SpO2,
     temperature or any other vital sign – those come from the user's certified device.
   - Frames go only to 127.0.0.1, are processed in memory and dropped (never stored).
   - Without a camera, without consent or without MediaPipe → manual mode (same steps, self-confirmed).
   ===================================================================== */
"use strict";
(function () {
  const AR = () => S.lang === "ar";
  const EXAM_OF_ANIM = { bp: "blood_pressure", spo2: "spo2", temp: "temperature", vision: "vision", stand: "stand_test", micro: null };
  const ANIM_LABEL = { bp: ["ضغط الدم", "Blood pressure"], spo2: ["تشبع الأكسجين", "SpO2"], temp: ["الحرارة", "Temperature"], vision: ["حدة البصر", "Visual acuity"], stand: ["اختبار الوقوف", "Stand test"], micro: ["التثبيت في انعدام الجاذبية", "Restraint in 0 g"] };
  const REG_INFO = {
    brain: ["الدماغ والجهاز العصبي", "النوم واليقظة والضغط النفسي؛ تُتابع بسجلات النوم والمزاج."],
    eyes: ["العينان", "تغيّرات الرؤية المرتبطة بالرحلات الطويلة (SANS) تُتابع بفحص حدة البصر وشبكة أمسلر."],
    heart: ["القلب والأوعية", "انتقال السوائل نحو الرأس يغيّر الضغط والنبض؛ تُقارن القراءات بخط الأساس أثناء الرحلة."],
    lungs: ["الرئتان", "تشبع الأكسجين وجودة هواء المقصورة (CO₂ وضغط المقصورة)."],
    bones: ["العظام والعضلات", "فقدان كثافة العظام في انعدام الجاذبية؛ تُعرض القيم المنشورة في صفحة المحاكاة."],
    kidneys: ["الكليتان", "خطر حصى الكلى يرتفع مع ارتشاف الكالسيوم من العظام؛ يُتابع بفحص البول وشرب السوائل."],
    blood: ["الدم والسوائل", "حجم البلازما ينخفض في الأيام الأولى؛ يؤثر في تحمّل الوقوف عند العودة."],
    skin: ["الجلد والجسم", "الحرارة والإشعاع التراكمي."],
  };
  const EV_OF_REG = { heart: ["E-CV-01", "E-CV-02"], bones: ["E-BONE-01", "E-BONE-02"], blood: ["E-CV-03"], lungs: ["E-CO2-01", "E-ATM-01"], kidneys: ["E-CA-01"], brain: ["E-SLEEP-01"], skin: ["E-RAD-01"], eyes: ["E-GAP-01"] };

  // ============================================================ 3D body & exam animations page
  VIEWS.body3d = async () => {
    const anims = Object.keys(ANIM_LABEL);
    return `<div class="pagehead"><h2>${ic("body3d")} ${esc(t("body3d"))}</h2></div>
    <div class="grid2"><div class="card" data-tour="b3dpage">${bodyViewer("page", true)}</div>
      <div class="stack">
        <div class="card"><h3>${ic("measure")} ${AR() ? "الطريقة الصحيحة لكل فحص" : "How to perform each exam"}</h3>
          <div class="regionlist" id="animList">${anims.map((a) => `<button data-act="b3dAnim" data-a="${a}">${ic("play")} ${esc(ANIM_LABEL[a][AR() ? 0 : 1])}</button>`).join("")}</div>
          <div id="player" style="margin-top:12px" hidden>
            <div class="progress" aria-hidden="true"><i id="plBar" style="width:0"></i></div>
            <p class="caption" id="plCap" aria-live="polite"></p>
            <div class="player">
              <button class="small" data-act="plPrev" aria-label="${AR() ? "الخطوة السابقة" : "Previous"}">${ic("prev")}</button>
              <button class="small" data-act="plToggle" id="plToggle" aria-label="${AR() ? "إيقاف مؤقت" : "Pause"}">${ic("pause")}</button>
              <button class="small" data-act="plNext" aria-label="${AR() ? "الخطوة التالية" : "Next"}">${ic("next")}</button>
              <button class="small" data-act="plRestart" aria-label="${AR() ? "إعادة" : "Restart"}">${ic("restart")}</button>
              <button class="small" data-act="plStop">${AR() ? "إنهاء العرض" : "Stop"}</button>
              <span class="muted small" id="plStep"></span>
            </div>
            <div id="plExam" style="margin-top:10px"></div>
          </div>
        </div>
        <div class="card"><h3>${ic("about")} ${AR() ? "أعضاء الجسم" : "Body regions"}</h3>
          <div class="regionlist" id="regionList">${Object.keys(REG_INFO).map((r) => `<button data-act="b3dRegion" data-r="${r}">${esc(REG_INFO[r][0])}</button>`).join("")}</div>
          <div id="regInfo" class="muted" style="margin-top:10px">${AR() ? "اختر عضوًا لتطير الكاميرا إليه وتظهر معلوماته." : "Pick a region – the camera flies to it."}</div></div>
      </div></div>`;
  };
  function regionInfo(r) {
    const box = $("#regInfo"); if (!box) return;
    document.querySelectorAll("#regionList button").forEach((b) => b.classList.toggle("on", b.dataset.r === r));
    if (!r) { box.innerHTML = ""; return; }
    const st = S.dash && S.dash.regions && S.dash.regions[r];
    box.innerHTML = `<div class="card flat"><h3>${esc(REG_INFO[r][0])} ${st ? lvl(st.level) : ""}</h3><p>${esc(REG_INFO[r][1])}</p>
      ${st && st.items && st.items.length ? `<ul>${st.items.map((a) => `<li>${esc(L(a, "label"))}: <b>${a.value} ${esc(a.unit)}</b> ${lvl(a.level)}</li>`).join("")}</ul>` : ""}
      <div class="row small"><b>${AR() ? "المصادر" : "Sources"}:</b> ${evChips(EV_OF_REG[r])}</div></div>`;
  }
  MOUNT.body3d = async () => {
    if (!S.dash && S.aid) { try { S.dash = await get(withAid("/api/dashboard")); } catch (e) { /* researcher etc. */ } }
    const st = {}; if (S.dash) Object.entries(S.dash.regions).forEach(([k, v]) => { if (v.level !== "none") st[k] = v.level; });
    mountBody("page", st, regionInfo);
    if (S.body3dAnim) { const a = S.body3dAnim; S.body3dAnim = null; startAnim(a); }
  };
  UNMOUNT.body3d = () => { if (S.b3d) { S.b3d.destroy(); S.b3d = null; } };
  function startAnim(name) {
    if (!S.b3d) return toast(AR() ? "العرض ثلاثي الأبعاد غير متاح" : "3D unavailable");
    document.querySelectorAll("#animList button").forEach((b) => b.classList.toggle("on", b.dataset.a === name));
    $("#player").hidden = false;
    S.b3d.play(name, { onStep: (i, st, A) => {
      $("#plCap").textContent = st.ar; $("#plStep").textContent = `${i + 1} / ${A.steps.length}`;
      $("#plBar").style.width = ((i + 1) / A.steps.length) * 100 + "%";
    } });
    $("#plToggle").innerHTML = ic("pause");
    const exam = EXAM_OF_ANIM[name];
    $("#plExam").innerHTML = exam ? `<button class="primary small" data-act="openPose" data-e="${exam}">${ic("camera")} ${AR() ? "جرّب الآن مع التحقق بالكاميرا" : "Try it now with camera check"}</button>` : "";
  }
  ACTIONS.b3dAnim = (el) => startAnim(el.dataset.a);
  ACTIONS.b3dRegion = (el) => { if (S.b3d) S.b3d.select(el.dataset.r); regionInfo(el.dataset.r); };
  ACTIONS.plPrev = () => S.b3d && S.b3d.controls.prev();
  ACTIONS.plNext = () => S.b3d && S.b3d.controls.next();
  ACTIONS.plRestart = () => S.b3d && S.b3d.controls.restart();
  ACTIONS.plStop = () => { if (S.b3d) S.b3d.controls.stop(); $("#player").hidden = true; document.querySelectorAll("#animList button").forEach((b) => b.classList.remove("on")); };
  ACTIONS.plToggle = (el) => { if (!S.b3d) return; const s = S.b3d.controls.state(); if (!s) return;
    if (s.paused) { S.b3d.controls.resume(); el.innerHTML = ic("pause"); } else { S.b3d.controls.pause(); el.innerHTML = ic("play"); } };

  // ============================================================ posture verification page
  const P = { stream: null, sid: null, timer: null, busy: false, sess: null, cap: null, exams: [], last: null, fps: 0, lat: [] };
  VIEWS.posecheck = async (opts = {}) => {
    P.cap = await get("/api/pose/status"); P.exams = (await get("/api/pose/exams")).exams;
    const sel = S.poseExam || opts.exam || "blood_pressure";
    let consent = null; if (S.aid && S.user.role === "astronaut") { try { consent = (await get(withAid("/api/consent"))).consents.pose_camera; } catch (e) { /* */ } }
    const canWrite = ["astronaut", "cmo"].includes(S.user.role);
    return `<div class="pagehead"><h2>${ic("posecheck")} ${esc(t("posecheck"))}</h2></div>
    <div class="honesty small">${AR() ? "الكاميرا تتحقق من <b>الوضعية وخطوات الإجراء فقط</b> (الجلوس، وضع الذراع، الثبات، تغطية العين…). لا تقيس الضغط أو الأكسجين أو الحرارة أو أي مؤشر حيوي؛ القيم تُؤخذ من جهازك المعتمد وتُدخل في صفحة القياس. الصور تُعالج على هذا الجهاز فقط ولا تُحفظ." : "The camera verifies <b>posture and procedure steps only</b>. It does NOT measure BP, SpO2, temperature or any vital sign. Frames are processed locally and never stored."}</div>
    <div class="grid2" style="margin-top:14px">
      <div class="card stack">
        <div class="row"><label for="peExam" style="margin:0">${AR() ? "الفحص" : "Exam"}</label>
          <select id="peExam">${P.exams.map((e) => `<option value="${e.id}" ${e.id === sel ? "selected" : ""}>${esc(AR() ? e.title_ar : e.title_en)}</option>`).join("")}</select>
          <select id="peSide" aria-label="side"><option value="left">${AR() ? "الذراع اليسرى" : "Left arm"}</option><option value="right">${AR() ? "الذراع اليمنى" : "Right arm"}</option></select></div>
        <div class="row"><span class="lvl ${P.cap.tier === "full" ? "green" : P.cap.tier === "opencv_only" ? "yellow" : "none"}">${ic("camera")} ${esc(P.cap.tier)}</span><span class="small muted">${esc(P.cap.note_ar)}</span></div>
        ${consent === false ? `<div class="why yellow small">${AR() ? "وضع الكاميرا يتطلب موافقتك على فئة «الكاميرا للتحقق من الوضعية»." : "Camera mode needs the pose_camera consent."} <button class="small primary" data-act="consent" data-c="pose_camera" data-g="1">${t("grant")}</button></div>` : ""}
        <div class="row">${canWrite ? `<button class="primary" data-act="peStart" data-m="camera" ${P.cap.tier === "manual" || consent === false ? "disabled" : ""}>${ic("camera")} ${AR() ? "ابدأ بالكاميرا" : "Start with camera"}</button>
          <button data-act="peStart" data-m="manual">${AR() ? "الوضع اليدوي (بدون كاميرا)" : "Manual mode (no camera)"}</button>` : `<span class="muted">${AR() ? "للعرض فقط لهذا الدور." : "View only for this role."}</span>`}
          <button class="ghost" data-act="peDemo">${ic("play")} ${AR() ? "شاهد العرض ثلاثي الأبعاد" : "Watch 3D demo"}</button></div>
        <div class="cam" id="peCam" hidden><video id="peVid" playsinline muted></video><canvas id="peOv"></canvas><div class="hud" id="peHud" aria-live="polite"></div></div>
        <div id="peManual"></div>
      </div>
      <div class="card stack" id="pePanel" aria-live="polite">
        <h3>${AR() ? "الخطوات" : "Steps"}</h3><div id="peSteps">${stepsHtml(P.exams.find((e) => e.id === sel), -1)}</div>
        <div id="peChecks"></div><div id="peResult"></div>
        <details class="small"><summary><b>${AR() ? "كيف يعمل؟" : "How it works"}</b></summary><p class="muted">${AR()
          ? "يرسل المتصفح نحو 6 إطارات في الثانية بدقة منخفضة إلى الخادم المحلي. OpenCV يقيس الإضاءة والوضوح والحركة ويحسّن الإضاءة المنخفضة (CLAHE)، ثم MediaPipe Pose يحدد 33 معلمًا للجسم، ثم قواعد هندسية بسيطة تتحقق من كل خطوة (مثل: منتصف العضد بمستوى القلب تقديريًا). تنتقل الخطوة تلقائيًا بعد ثبات الوضعية الصحيحة لعدة إطارات متتالية. الخطوات التي لا يمكن رؤيتها (مثل لف الكفة) تُؤكَّد يدويًا."
          : "~6 low-res frames/s go to the local server: OpenCV checks light/blur/motion (CLAHE for low light), MediaPipe Pose finds 33 landmarks, simple geometric rules verify each step; a step advances after the correct posture is held for several frames. Non-visible steps are confirmed manually."}</p></details>
        <div id="peHist"></div>
      </div></div>`;
  };
  function stepsHtml(exam, cur, log) {
    if (!exam) return "";
    return `<ol class="checklist" style="padding:0">${exam.steps.map((s, i) => { const lg = log && log[i]; const st = lg && lg.passed ? "done" : i === cur ? "on" : "";
      return `<li class="${st}" style="padding:6px 8px;border-radius:8px;${i === cur ? "background:var(--info-bg)" : ""}"><span>${lg && lg.passed ? `<span class="ok">✔</span>` : i === cur ? "▶" : `${i + 1}.`}</span>
        <span>${esc(s.ar)} ${s.manual ? `<span class="badge USER-ENTERED">${AR() ? "تأكيد يدوي" : "manual"}</span>` : ""} ${lg && lg.how ? `<span class="muted small">(${lg.how === "auto" ? (AR() ? "تحقق تلقائي" : "auto") : AR() ? "يدوي" : "manual"})</span>` : ""}</span></li>`; }).join("")}</ol>`;
  }
  MOUNT.posecheck = async () => {
    S.poseExam = null;
    $("#peExam").addEventListener("change", () => { $("#peSteps").innerHTML = stepsHtml(P.exams.find((e) => e.id === $("#peExam").value), -1); });
    try { const h = await get(withAid("/api/pose/sessions")); renderHist(h.sessions); } catch (e) { /* */ }
  };
  function renderHist(list) {
    if (!list || !list.length) return;
    $("#peHist").innerHTML = `<h3>${AR() ? "آخر جلسات التحقق" : "Recent sessions"}</h3><div class="table-wrap"><table><tr><th>${AR() ? "الوقت" : "Time"}</th><th>${AR() ? "الفحص" : "Exam"}</th><th>${AR() ? "الالتزام" : "Compliance"}</th><th>${AR() ? "الوضع" : "Mode"}</th></tr>
      ${list.slice().reverse().map((r) => { const p = r.payload || r; return `<tr><td>${esc((r.ts || "").slice(0, 16).replace("T", " "))}</td><td>${esc(p.exam)}</td><td>${p.score ? p.score.completed_pct + "%" : "—"}</td><td>${esc(p.mode)}</td></tr>`; }).join("")}</table></div>`;
  }
  UNMOUNT.posecheck = () => stopCam();
  ACTIONS.peDemo = () => { const e = P.exams.find((x) => x.id === $("#peExam").value); S.body3dAnim = e ? e.anim : "bp"; go("body3d"); };

  async function stopCam() {
    clearInterval(P.timer); P.timer = null;
    if (P.stream) { P.stream.getTracks().forEach((tr) => tr.stop()); P.stream = null; }
  }
  ACTIONS.peStart = async (el) => {
    const mode = el.dataset.m, exam = $("#peExam").value;
    await stopCam(); $("#peResult").innerHTML = ""; $("#peChecks").innerHTML = "";
    if (mode === "camera") {
      try {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) throw new Error("unsupported");
        P.stream = await navigator.mediaDevices.getUserMedia({ video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" }, audio: false });
      } catch (e) {
        toast(AR() ? "تعذّر الوصول إلى الكاميرا – تم التحويل إلى الوضع اليدوي" : "Camera unavailable – switched to manual", 4000);
        return ACTIONS.peStart({ dataset: { m: "manual" } });
      }
    }
    $("#peChecks").innerHTML = Motion.loader("dots", AR() ? "جارٍ تجهيز التحقق…" : "Preparing…");
    P.sess = await post("/api/pose/start", { aid: S.aid, exam, side: $("#peSide").value, mode });
    P.sid = P.sess.session; P.mode = mode; render(P.sess);
    if (mode === "camera") {
      $("#peCam").hidden = false; const v = $("#peVid"); v.srcObject = P.stream; await v.play().catch(() => {});
      P.stream.getVideoTracks()[0].addEventListener("ended", () => { toast(AR() ? "انقطعت الكاميرا – أكمل يدويًا" : "Camera disconnected – continue manually", 4000); stopCam(); P.mode = "manual"; render(P.sess); });
      const off = document.createElement("canvas");
      P.timer = setInterval(async () => {
        if (P.busy || !P.sid || !v.videoWidth) return; P.busy = true;
        const w = 384, h = Math.round((v.videoHeight / v.videoWidth) * w); off.width = w; off.height = h;
        off.getContext("2d").drawImage(v, 0, 0, w, h);
        const t0 = performance.now();
        try { const r = await post("/api/pose/frame", { session: P.sid, image: off.toDataURL("image/jpeg", 0.7) }); P.lat.push(performance.now() - t0); if (P.lat.length > 20) P.lat.shift(); P.sess = r; render(r); }
        catch (e) { $("#peHud").textContent = "⚠ " + e.message; }
        finally { P.busy = false; }
      }, 160);
    } else $("#peCam").hidden = true;
  };
  function render(v) {
    const exam = P.exams.find((e) => e.id === v.exam);
    $("#peSteps").innerHTML = stepsHtml(exam, v.done ? -1 : v.step_index, v.log);
    if (v.done) return finish();
    const r = v.result; const stepManual = v.step.manual || P.mode !== "camera";
    $("#peManual").innerHTML = stepManual ? `<div class="why"><b>${AR() ? "الخطوة" : "Step"} ${v.step_index + 1}/${v.steps_total}:</b> ${esc(v.step.ar)}
      <div class="row" style="margin-top:8px"><button class="primary" data-act="peConfirm">✔ ${AR() ? "أكّدت تنفيذ هذه الخطوة" : "I did this step"}</button>
      <button class="small" data-act="peDemo">${ic("play")} ${AR() ? "اعرض الطريقة" : "Show me"}</button></div></div>` : "";
    if (r) {
      $("#peChecks").innerHTML = `<ul class="checklist">${r.checks.map((c) => `<li><span class="${c.ok === true ? "ok" : c.ok === false ? "bad" : "unk"}">${c.ok === true ? "✔" : c.ok === false ? "✖" : "?"}</span><span>${esc(AR() ? c.ar : c.en)}</span></li>`).join("")}</ul>
        <div class="progress" title="hold"><i style="width:${Math.min(100, (v.hold.have / v.hold.need) * 100)}%"></i></div>
        <p class="small muted">${AR() ? "ثبات الوضعية" : "Hold"} ${v.hold.have}/${v.hold.need} · ${r.ms} ms · ${P.lat.length ? Math.round(P.lat.reduce((a, b) => a + b, 0) / P.lat.length) : "—"} ms ${AR() ? "ذهابًا وإيابًا" : "round-trip"} · ${esc(r.detector)}</p>`;
      const bad = r.checks.find((c) => c.ok === false);
      $("#peHud").textContent = bad ? "✖ " + (AR() ? bad.ar : bad.en) : "✔ " + (AR() ? "وضعية صحيحة – حافظ عليها" : "Correct – hold it");
      draw(r);
    } else if ($("#peHud")) $("#peHud").textContent = v.step.ar;
  }
  const EDGES = [[11, 12], [11, 13], [13, 15], [12, 14], [14, 16], [11, 23], [12, 24], [23, 24], [23, 25], [25, 27], [24, 26], [26, 28], [0, 11], [0, 12]];
  function draw(r) {
    const c = $("#peOv"), v = $("#peVid"); if (!c || !v) return;
    const W = (c.width = c.clientWidth), H = (c.height = c.clientHeight); const g = c.getContext("2d"); g.clearRect(0, 0, W, H);
    const X = (x) => (1 - x) * W, Y = (y) => y * H; // mirrored preview
    const col = { ok: "#3ccf7d", bad: "#ff6f78", hint: "#6fdcf9" };
    r.checks.forEach((ch) => (ch.guides || []).forEach((gd) => {
      g.strokeStyle = g.fillStyle = col[gd.state] || col.hint; g.lineWidth = 3; g.setLineDash(gd.state === "hint" ? [8, 6] : []);
      if (gd.type === "box") g.strokeRect(X(gd.x + gd.w), Y(gd.y), gd.w * W, gd.h * H);
      if (gd.type === "line") { g.beginPath(); g.moveTo(X(gd.a[0]), Y(gd.a[1])); g.lineTo(X(gd.b[0]), Y(gd.b[1])); g.stroke(); }
      if (gd.type === "band") { g.globalAlpha = 0.18; g.fillRect(0, Y(gd.y - gd.h / 2), W, gd.h * H); g.globalAlpha = 1; g.strokeRect(0, Y(gd.y - gd.h / 2), W, gd.h * H);
        if (gd.label) { g.font = "bold 14px sans-serif"; g.fillText(gd.label, 10, Y(gd.y - gd.h / 2) - 4); } }
      if (gd.type === "arrow") { const [x1, y1] = [X(gd.from[0]), Y(gd.from[1])], [x2, y2] = [X(gd.to[0]), Y(gd.to[1])]; g.beginPath(); g.moveTo(x1, y1); g.lineTo(x2, y2); g.stroke();
        const a = Math.atan2(y2 - y1, x2 - x1); g.beginPath(); g.moveTo(x2, y2); g.lineTo(x2 - 14 * Math.cos(a - 0.5), y2 - 14 * Math.sin(a - 0.5)); g.lineTo(x2 - 14 * Math.cos(a + 0.5), y2 - 14 * Math.sin(a + 0.5)); g.fill(); }
    }));
    g.setLineDash([]);
    if (r.landmarks) {
      g.strokeStyle = "rgba(166,236,255,.9)"; g.lineWidth = 2;
      EDGES.forEach(([a, b]) => { const p = r.landmarks[a], q = r.landmarks[b]; if (p && q && p.v > 0.4 && q.v > 0.4) { g.beginPath(); g.moveTo(X(p.x), Y(p.y)); g.lineTo(X(q.x), Y(q.y)); g.stroke(); } });
      g.fillStyle = "#1ba6cf"; r.landmarks.forEach((p) => { if (p.v > 0.4) { g.beginPath(); g.arc(X(p.x), Y(p.y), 3.5, 0, 7); g.fill(); } });
    }
  }
  ACTIONS.peConfirm = async () => { if (!P.sid) return; P.sess = await post("/api/pose/manual", { session: P.sid, confirmed: true }); render(P.sess); };
  async function finish() {
    if (!P.sid) return; const sid = P.sid; P.sid = null; await stopCam();
    $("#peCam").hidden = true; $("#peManual").innerHTML = ""; $("#peChecks").innerHTML = "";
    const r = await post("/api/pose/finish", { session: sid, aid: S.aid }); const sc = r.score;
    $("#peResult").innerHTML = `<div class="why green"><h3>✔ ${AR() ? "اكتمل الإجراء" : "Procedure complete"}</h3>
      <div class="grid3"><div class="kpi"><span class="muted small">${AR() ? "الالتزام بالخطوات" : "Compliance"}</span><span class="v">${sc.completed_pct}%</span></div>
      <div class="kpi"><span class="muted small">${AR() ? "تحقق تلقائي" : "Auto-verified"}</span><span class="v">${sc.auto_verified}/${sc.steps}</span></div>
      <div class="kpi"><span class="muted small">${AR() ? "تأكيد يدوي" : "Manual"}</span><span class="v">${sc.manual_confirmed}</span></div>
      <div class="kpi"><span class="muted small">${AR() ? "تصحيحات" : "Corrections"}</span><span class="v">${sc.corrections}</span></div></div>
      <p class="small">${esc(sc.note_ar)}</p>
      <div class="row"><button class="primary" data-act="go" data-v="measure">${ic("measure")} ${AR() ? "أدخل قراءة جهازك الآن" : "Enter your device reading"}</button></div></div>`;
    if (window.Tour && Tour.onPracticeDone) Tour.onPracticeDone(sc);
    try { const h = await get(withAid("/api/pose/sessions")); renderHist(h.sessions); } catch (e) { /* */ }
  }
  window.PoseUI = { stopCam, P };
})();
