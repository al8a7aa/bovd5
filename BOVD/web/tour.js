/* =====================================================================
   BÖVD · first-run interactive tour (11 stages) + guided practice exam
   Spotlight + tooltip, next / previous / skip / restart, progress %, keyboard (←/→/Esc),
   replay from Help or Settings. Steps whose page the role cannot open are skipped.
   ===================================================================== */
"use strict";
(function () {
  const AR = () => S.lang === "ar";
  const vis = (el) => el && el.offsetParent !== null && el.getBoundingClientRect().width > 0;
  const navTarget = (v) => () => { const a = document.querySelector(`#nav [data-v="${v}"]`); if (vis(a)) return a; return document.querySelector(`#bottomnav [data-v="${v}"]`) || document.querySelector("#bottomnav"); };
  const STEPS = [
    { id: "welcome", view: null, target: null, ar: ["مرحبًا بك في BÖVD", "منصة لمساعدة رواد الفضاء على إجراء فحوصاتهم بالطريقة الصحيحة ومتابعة حالتهم، مع ربط كل قيمة علمية بمصدرها. هذه الجولة تستغرق دقيقتين وتنتهي بفحص تجريبي."], en: ["Welcome to BÖVD", "A two-minute tour ending in a practice exam."] },
    { id: "ui", view: "dashboard", target: () => document.querySelector(".topbar"), ar: ["الواجهة الرئيسية", "في الأعلى: سياق الجاذبية وتأخير الاتصال، وأزرار اللغة والوضع الليلي والتباين العالي ووضع القفازات (أزرار أكبر)."], en: ["Main interface", "Gravity context, comm delay, language, dark mode, high contrast, glove mode."] },
    { id: "sections", view: "dashboard", target: () => (vis($("#sidebar")) ? $("#nav") : $("#bottomnav")), ar: ["الأقسام", "الأقسام مجمّعة: الرئيسية، المتابعة، الميزات الصحية، العلم، النظام. على الهاتف تظهر في الشريط السفلي وزر «المزيد»."], en: ["Sections", "Grouped navigation; on phones use the bottom bar and More."] },
    { id: "body", view: "dashboard", target: () => document.querySelector('[data-tour="body"]'), ar: ["النموذج ثلاثي الأبعاد", "اسحب لتدوير الجسم 360°، واستخدم العجلة أو إصبعين للتكبير. اضغط على عضو لتطير الكاميرا إليه وتظهر حالته ومصادره. ألوان الأعضاء = حالة القراءات (مع أيقونة ونص دائمًا)."], en: ["3D body", "Drag to rotate, zoom, tap an organ."] },
    { id: "exams", view: "measure", target: () => document.querySelector("#main .steps") || $("#main"), ar: ["الفحوصات", "معالج القياس يقودك خطوة بخطوة: العلامات الحيوية، النوم، الكتلة، والمزاج. لكل خطوة لوحة «كيف تفعلها في انعدام الجاذبية» مع زر العرض ثلاثي الأبعاد والتحقق بالكاميرا."], en: ["Exams", "Step-by-step measurement wizard."] },
    { id: "devices", view: "measure", target: () => document.querySelector("#main .panel-micro") || $("#main"), ar: ["الأجهزة", "القيم تأتي من أجهزتك المعتمدة (جهاز الضغط، مقياس الأكسجين، مقياس الحرارة، جهاز قياس الكتلة في المحطة). التطبيق لا يقيس المؤشرات الحيوية بنفسه؛ أنت تُدخل القراءة أو تستوردها."], en: ["Devices", "Values come from your certified devices."] },
    { id: "camera", view: "posecheck", target: () => document.querySelector("#main .honesty"), ar: ["إذن الكاميرا", "الكاميرا اختيارية وتحتاج موافقتك. تُستخدم للتحقق من الوضعية فقط، وتُعالج الصور على هذا الجهاز ولا تُحفظ. بدونها يعمل الوضع اليدوي بنفس الخطوات."], en: ["Camera permission", "Optional, consent-based, posture only, frames never stored."] },
    { id: "method", view: "body3d", target: () => $("#animList"), ar: ["الطريقة الصحيحة للفحص", "اختر فحصًا لمشاهدة رسوم متحركة ثلاثية الأبعاد: وضعية الجسم، الذراع، الكفة، مكان الجهاز، والأدوات. تحكّم بالتشغيل والإيقاف والإعادة والانتقال بين الخطوات."], en: ["Correct method", "3D animations with play/pause/steps."] },
    { id: "trial", view: "posecheck", target: () => $("#pePanel"), ar: ["فحص تجريبي موجَّه", "هنا تجري الفحص مع التحقق: تظهر الخطوات، ونتائج كل فحص (✔/✖)، وتنبيهات فورية للتصحيح، وشريط ثبات الوضعية. في نهاية الجولة يمكنك تجربة فحص ضغط الدم."], en: ["Guided trial exam", "Live checks, corrections and hold bar."] },
    { id: "results", view: "dashboard", target: () => document.querySelector("#main table") || $("#main"), ar: ["قراءة النتائج", "كل قراءة لها حالة (✔ جيد، ⚠ انتباه، ⛔ تصرّف الآن)، ومقارنة بخط أساسك الشخصي، وزر «لماذا؟» يشرح السبب والخطوة التالية ومن تتواصل معه. التطبيق لا يشخّص."], en: ["Reading results", "Status, baseline, WHY explanation; no diagnosis."] },
    { id: "sources", view: "science", target: () => $("#evList"), ar: ["المصادر العلمية", "كل قيمة مربوطة بمصدرها: الجهة، التاريخ، الرابط، موضعها في المصدر، والقيود. «افتراضي» يعني ليس من ناسا، و«دليل غير كافٍ» يعني لا رقم. انتهت الجولة!"], en: ["Scientific sources", "Every value links to its source. Tour complete!"] },
  ];
  const T = { i: 0, steps: [], el: null };
  function allowed(s) { return !s.view || (S.user && NAV[S.user.role].includes(s.view)); }
  function ui() {
    if (T.el) return;
    T.el = document.createElement("div");
    T.el.innerHTML = `<div class="tour-hole" id="tHole"></div><div class="tour-tip" id="tTip" role="dialog" aria-modal="true" aria-labelledby="tTitle">
      <div class="progress" aria-hidden="true"><i id="tBar"></i></div><p class="small muted" id="tPct" style="margin:6px 0"></p>
      <h3 id="tTitle"></h3><p id="tBody"></p>
      <div class="row"><button class="small" id="tPrev">${ic("next")} ${AR() ? "السابق" : "Back"}</button><button class="primary small" id="tNext"></button>
        <button class="small ghost" id="tRestart">${ic("restart")}</button><button class="small ghost" id="tSkip">${AR() ? "تخطي الجولة" : "Skip tour"}</button></div></div>`;
    document.body.appendChild(T.el);
    $("#tPrev").addEventListener("click", () => show(T.i - 1));
    $("#tNext").addEventListener("click", () => (T.i >= T.steps.length - 1 ? end(true) : show(T.i + 1)));
    $("#tSkip").addEventListener("click", () => end(false));
    $("#tRestart").addEventListener("click", () => show(0));
    document.addEventListener("keydown", key);
  }
  function key(e) {
    if (!T.el) return;
    if (e.key === "Escape") end(false);
    else if (e.key === (AR() ? "ArrowLeft" : "ArrowRight")) $("#tNext").click();
    else if (e.key === (AR() ? "ArrowRight" : "ArrowLeft") && T.i > 0) show(T.i - 1);
  }
  async function show(i) {
    T.i = Math.max(0, Math.min(T.steps.length - 1, i)); const s = T.steps[T.i];
    if (s.view && S.view !== s.view) await go(s.view);
    const [title, body] = AR() ? s.ar : s.en;
    $("#tTitle").textContent = title; $("#tBody").textContent = body;
    const pct = Math.round(((T.i + 1) / T.steps.length) * 100);
    $("#tBar").style.width = pct + "%"; $("#tPct").textContent = `${AR() ? "المرحلة" : "Stage"} ${T.i + 1} / ${T.steps.length} · ${pct}%`;
    $("#tPrev").disabled = T.i === 0;
    $("#tNext").textContent = T.i === T.steps.length - 1 ? (AR() ? "ابدأ الفحص التجريبي" : "Start practice exam") : AR() ? "التالي" : "Next";
    const tg = s.target && s.target(); const hole = $("#tHole"), tip = $("#tTip");
    if (tg && vis(tg)) {
      tg.scrollIntoView({ block: "center", behavior: "auto" });
      await new Promise((r) => requestAnimationFrame(r));
      const b = tg.getBoundingClientRect(), pad = 6;
      Object.assign(hole.style, { display: "block", left: b.left - pad + "px", top: Math.max(4, b.top - pad) + "px", width: b.width + 2 * pad + "px", height: Math.min(innerHeight - 8, b.height + 2 * pad) + "px" });
      const tw = Math.min(420, innerWidth - 24); const below = b.bottom + 14 + 220 < innerHeight;
      tip.style.left = Math.max(12, Math.min(innerWidth - tw - 12, b.left + b.width / 2 - tw / 2)) + "px";
      tip.style.top = (below ? Math.min(innerHeight - 230, b.bottom + 14) : Math.max(12, b.top - 14 - tip.offsetHeight)) + "px";
    } else {
      Object.assign(hole.style, { display: "block", left: innerWidth / 2 + "px", top: innerHeight / 2 + "px", width: "0px", height: "0px" });
      tip.style.left = Math.max(12, innerWidth / 2 - Math.min(420, innerWidth - 24) / 2) + "px"; tip.style.top = Math.max(12, innerHeight / 2 - 120) + "px";
    }
    $("#tNext").focus();
  }
  function end(completed) {
    if (T.el) { T.el.remove(); T.el = null; document.removeEventListener("keydown", key); }
    if (S.user) localStorage.setItem("astra.tour." + S.user.username, completed ? "done" : "skipped");
    if (completed && NAV[S.user.role].includes("posecheck")) practice();
  }
  function start() { if (!S.user) return; T.steps = STEPS.filter(allowed); ui(); show(0); }

  // ---------------- guided practice exam (BP): demo → device → camera/manual verification → feedback → compliance
  async function practice() {
    if (!S.user || !NAV[S.user.role].includes("posecheck")) return toast(AR() ? "الفحص التجريبي غير متاح لهذا الدور" : "Not available for this role");
    S.practice = true; S.poseExam = "blood_pressure"; await go("posecheck");
    const panel = document.createElement("div"); panel.className = "why"; panel.id = "practiceBox";
    panel.innerHTML = `<h3>${ic("posecheck")} ${AR() ? "فحص تجريبي موجَّه: ضغط الدم" : "Guided practice: blood pressure"}</h3>
      <ol><li>${AR() ? "شاهد العرض ثلاثي الأبعاد للطريقة الصحيحة." : "Watch the 3D demo."}</li><li>${AR() ? "جهّز جهاز الضغط (الكفة على العضد الأيسر، الأنبوب للأسفل)." : "Prepare the BP device."}</li>
      <li>${AR() ? "ابدأ بالكاميرا (أو الوضع اليدوي) واتبع التنبيهات حتى تكتمل كل خطوة." : "Start with camera (or manual) and follow the prompts."}</li><li>${AR() ? "اقرأ نتيجة الالتزام، ثم أدخل قراءة جهازك في صفحة القياس." : "Read your compliance result, then enter your device reading."}</li></ol>
      <div class="row"><button class="small" data-act="peDemo">${ic("play")} ${AR() ? "1. شاهد العرض" : "1. Watch demo"}</button><button class="small ghost" id="prClose">${AR() ? "إغلاق" : "Close"}</button></div>`;
    $("#main").prepend(panel); $("#prClose").addEventListener("click", () => { panel.remove(); S.practice = false; });
  }
  function onPracticeDone(sc) {
    if (!S.practice) return; S.practice = false;
    toast((AR() ? "انتهى الفحص التجريبي – الالتزام " : "Practice complete – compliance ") + sc.completed_pct + "%", 5000);
    if (S.user) localStorage.setItem("astra.practice." + S.user.username, String(sc.completed_pct));
  }
  window.Tour = { start, practice, onPracticeDone, STEPS };
})();
