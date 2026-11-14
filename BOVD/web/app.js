/* =====================================================================
   BÖVD · core UI (vanilla JavaScript, no build step, offline)
   - talks only to the local Python server on 127.0.0.1
   - Arabic/English with RTL, high-contrast and glove mode (rule 8)
   - status always = colour + icon + text (WCAG / ISO 9241-125)
   - CSP-friendly: no inline handlers; one delegated click listener
   ===================================================================== */
"use strict";
const S = { token: localStorage.getItem("astra.token"), user: JSON.parse(localStorage.getItem("astra.user") || "null"),
  lang: localStorage.getItem("astra.lang") || "ar", meta: null, aid: null, crew: [], view: "dashboard",
  lastBeep: 0, sound: localStorage.getItem("astra.sound") !== "0", wiz: null };
const $ = (s, r = document) => r.querySelector(s);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const t = (k) => (I18N[S.lang] && I18N[S.lang][k]) || I18N.en[k] || k;
const L = (o, base) => (o ? (o[`${base}_${S.lang}`] ?? o[`${base}_en`] ?? o[base] ?? "") : "");
const ICON = { green: "✔", yellow: "⚠", red: "⛔", none: "○", info: "ℹ" };
const VIEWS = {}; const ACTIONS = {}; const MOUNT = {}; const UNMOUNT = {};
const ic = (n, c) => (window.Brand ? Brand.icon(n, c) : "");
const reduceMotion = () => document.body.classList.contains("reduce-motion") || matchMedia("(prefers-reduced-motion: reduce)").matches;
/** Evidence chips: every scientific value links to its source entry (science page). */
function evChips(ids) {
  if (!ids || !ids.length || !S.evidence) return "";
  return `<span class="row" style="gap:4px">${ids.map((id) => { const e = S.evidence.find((x) => x.id === id); return e ? `<a href="#" class="badge ev" data-act="ev" data-id="${esc(id)}" title="${esc(e.indicator_ar)}">📚 ${esc(id)}</a>` : ""; }).join("")}</span>`;
}

// ------------------------------------------------------------------ API
async function api(method, path, body) {
  const res = await fetch(path, { method, headers: { "Content-Type": "application/json", ...(S.token ? { Authorization: "Bearer " + S.token } : {}) },
    body: body ? JSON.stringify(body) : undefined });
  if (res.status === 401 && S.token) { logout(); throw new Error("login required"); }
  const ct = res.headers.get("Content-Type") || "";
  const data = ct.includes("json") ? await res.json() : await res.blob();
  if (!res.ok) throw new Error((data && data.error) || res.statusText);
  return data;
}
const get = (p) => api("GET", p); const post = (p, b) => api("POST", p, b || {});
const withAid = (p) => p + (p.includes("?") ? "&" : "?") + "aid=" + encodeURIComponent(S.aid || "");
function toast(msg, ms = 2600) { const el = $("#toast"); el.textContent = msg; el.style.display = "block"; clearTimeout(el._t); el._t = setTimeout(() => (el.style.display = "none"), ms); }

// ------------------------------------------------------------ components
const lvl = (l) => `<span class="lvl ${esc(l)}">${ICON[l] || ""} ${esc(t("level_" + l))}</span>`;
const prov = (p) => p ? `<span class="badge ${esc(p.type)}" title="${esc(p.ref)}">${esc(p.type)}${p.ref ? " · " + esc(p.ref) : ""}</span>` : "";
const expBadge = () => `<span class="badge exp">${esc(t("experimental"))}</span>`;
function cites(list) {
  if (!list || !list.length) return "";
  return `<div class="cite" dir="ltr" style="text-align:left"><b>${t("citations")}:</b><ul>${list.map((c) => `<li>${esc(c.apa)} ${c.url ? `<a href="${esc(c.url)}" target="_blank" rel="noopener">${esc(c.url)}</a>` : ""}</li>`).join("")}</ul></div>`;
}
function whyBox(a) {
  if (!a || !a.why) return "";
  const w = a.why;
  return `<div class="why ${esc(a.level)}"><b>${t("why")}</b> · ${t("hazard")}: ${esc(L(w.hazard, "") || w.hazard[S.lang] || w.hazard.en)}<br>
   ${esc(S.lang === "ar" ? w.explanation_ar : w.explanation_en)}
   ${S.lang === "ar" && a.notes && a.notes.length ? `<div class="muted">${a.notes.map(esc).join(" · ")}</div>` : ""}
   <div><b>${t("actions")}:</b><ol>${(S.lang === "ar" ? w.actions_ar : w.actions_en).map((x) => `<li>${esc(x)}</li>`).join("")}</ol></div>
   <div><b>${t("contact")}:</b> ${esc(w.contact)} ${w.protocol ? `<button class="small" data-act="openProtocol" data-p="${esc(w.protocol)}">🤖 ${esc(protoTitle(w.protocol))}</button>` : ""}</div>
   ${cites(w.citations)}<div class="row small"><b>${S.lang === "ar" ? "الأدلة" : "Evidence"}:</b> ${evChips(((S.meta.indicators[a.indicator] || {}).evidence) || [])}</div><div class="cite">${esc(w.disclaimer)}</div></div>`;
}
const protoTitle = (id) => { const p = (S.meta.protocols || []).find((x) => x.id === id); return p ? L(p, "title") : id; };
function ring(score, band) {
  const pct = Math.min(1, score / 20), r = 70, c = 2 * Math.PI * r;
  const col = { green: "var(--green)", yellow: "var(--amber)", red: "var(--red)" }[band] || "var(--muted)";
  return `<svg class="ring" viewBox="0 0 170 170" role="img" aria-label="${t("composite")} ${score}/20">
    <circle cx="85" cy="85" r="${r}" fill="none" stroke="var(--line)" stroke-width="16"/>
    <circle cx="85" cy="85" r="${r}" fill="none" stroke="${col}" stroke-width="16" stroke-linecap="round"
      stroke-dasharray="${(c * pct).toFixed(1)} ${c.toFixed(1)}" transform="rotate(-90 85 85)"/>
    <text x="85" y="80" text-anchor="middle" font-size="36" font-weight="800" fill="currentColor">${score}</text>
    <text x="85" y="104" text-anchor="middle" font-size="14" fill="currentColor">/ 20 ${ICON[band] || ""}</text></svg>`;
}
const MICRO = {
  vitals: { en: ["Same time of day (crew schedule).", "Body restrained: foot loops or seat strap – do not float.", "Rest 5 minutes before measuring.", "Note arm position (same arm, at heart level).", "Expect ~2 L headward fluid shift: puffy face and lower leg volume are normal in 0 g – your in-flight baseline accounts for this."],
    ar: ["نفس الوقت يوميًا (حسب جدول الطاقم).", "ثبّت جسمك: حلقات القدم أو حزام المقعد – لا تطفُ.", "استرح 5 دقائق قبل القياس.", "سجّل وضعية الذراع (نفس الذراع، بمستوى القلب).", "انتقال نحو 2 لتر من السوائل نحو الرأس طبيعي في انعدام الجاذبية – خط أساسك أثناء الرحلة يأخذ ذلك بالحسبان."] },
  sleep: { en: ["Use the crew schedule, not sunrise (≈16 sunrises/day on ISS).", "Log time in the secured sleeping bag, not time 'in quarters'.", "Note light/noise disturbances and any sleep aid used per protocol."],
    ar: ["استخدم جدول الطاقم وليس الشروق (نحو 16 شروقًا يوميًا).", "سجّل الوقت داخل كيس النوم المثبت.", "سجّل الإزعاج الضوئي/الصوتي وأي مساعد نوم حسب البروتوكول."] },
  mass: { en: ["No bathroom scale in 0 g: enter the value from the station's mass-measurement device (e.g. SLAMMD).", "Same clothing, before breakfast."], ar: ["لا يوجد ميزان عادي في انعدام الجاذبية: أدخل القيمة من جهاز قياس الكتلة في المحطة.", "نفس الملابس، قبل الإفطار."] },
  stand: { en: ["Only after a gravity transition (Moon/Mars landing, return to Earth).", "Seated 5 min → record HR/BP → stand with a spotter → record at 1 and 3 min.", "Stop and sit if dizzy."], ar: ["فقط بعد انتقال الجاذبية (الهبوط على القمر/المريخ أو العودة للأرض).", "اجلس 5 دقائق ← سجّل النبض/الضغط ← قف بوجود مرافق ← سجّل عند الدقيقة 1 و 3.", "توقف واجلس إذا شعرت بدوار."] },
};
const MICRO_LINK = { vitals: ["bp", "blood_pressure"], sleep: ["micro", null], mass: ["micro", null], stand: ["stand", "stand_test"] };
const micro = (k) => { const [anim, exam] = MICRO_LINK[k] || [];
  return `<details class="panel-micro" open><summary>🪐 ${t("micro")}</summary><ul>${(MICRO[k][S.lang] || MICRO[k].en).map((x) => `<li>${esc(x)}</li>`).join("")}</ul>
  <div class="row">${anim ? `<button class="small" data-act="openAnim" data-a="${anim}">${ic("play")} ${S.lang === "ar" ? "شاهد الطريقة الصحيحة (ثلاثي الأبعاد)" : "Watch how (3D)"}</button>` : ""}
  ${exam ? `<button class="small" data-act="openPose" data-e="${exam}">${ic("camera")} ${S.lang === "ar" ? "تحقق من وضعيتك بالكاميرا" : "Check posture with camera"}</button>` : ""}</div></details>`; };
ACTIONS.openAnim = (el) => { S.body3dAnim = el.dataset.a; navTo("body3d"); };
ACTIONS.openPose = (el) => { S.poseExam = el.dataset.e; navTo("posecheck"); };
ACTIONS.ev = (el) => { S.evFocus = el.dataset.id; navTo("science"); };

// ------------------------------------------------------------------ body figure
function bodySvg(regions) {
  const R = regions, f = (id) => "region fill-" + ((R[id] && R[id].level) || "none");
  const lab = (id, x, y, end) => `<text x="${x}" y="${y}" text-anchor="${end ? "end" : "start"}">${(R[id] && R[id].icon) || ""} ${esc(L(R[id], "") || R[id][S.lang] || R[id].en)} ${ICON[R[id].level] || "○"}</text>`;
  const g = (id, shape) => `<g tabindex="0" role="button" aria-label="${esc(R[id].en)} – ${esc(R[id].level)}" data-act="region" data-r="${id}">${shape}</g>`;
  return `<svg class="body-svg" viewBox="-60 0 560 470" role="img" aria-label="Body status figure" style="max-width:560px;width:100%;direction:ltr">
   ${g("skin", `<path class="${f("skin")}" opacity=".35" d="M210 20c28 0 42 20 42 44s-14 46-42 46-42-22-42-46 14-44 42-44zM150 118h120l30 150-26 6-14-80v266h-38V312h-24v148h-38V194l-14 80-26-6z"/>`)}
   ${g("brain", `<ellipse class="${f("brain")}" cx="210" cy="50" rx="34" ry="24"/>`)}
   ${g("eyes", `<circle class="${f("eyes")}" cx="196" cy="80" r="8"/><circle class="${f("eyes")}" cx="224" cy="80" r="8"/>`)}
   ${g("lungs", `<ellipse class="${f("lungs")}" cx="185" cy="170" rx="20" ry="34"/><ellipse class="${f("lungs")}" cx="235" cy="170" rx="20" ry="34"/>`)}
   ${g("heart", `<path class="${f("heart")}" d="M210 205c-18-14-28-22-28-34 0-8 6-14 14-14 6 0 10 3 14 8 4-5 8-8 14-8 8 0 14 6 14 14 0 12-10 20-28 34z"/>`)}
   ${g("kidneys", `<ellipse class="${f("kidneys")}" cx="188" cy="240" rx="11" ry="17"/><ellipse class="${f("kidneys")}" cx="232" cy="240" rx="11" ry="17"/>`)}
   ${g("blood", `<rect class="${f("blood")}" x="140" y="200" width="14" height="70" rx="7"/><rect class="${f("blood")}" x="266" y="200" width="14" height="70" rx="7"/>`)}
   ${g("bones", `<rect class="${f("bones")}" x="178" y="320" width="20" height="130" rx="9"/><rect class="${f("bones")}" x="222" y="320" width="20" height="130" rx="9"/>`)}
   ${lab("brain", 300, 46)}${lab("eyes", 300, 86)}${lab("lungs", 310, 160)}${lab("heart", 310, 200)}${lab("kidneys", 310, 246)}
   ${lab("blood", 132, 230, 1)}${lab("bones", 300, 390)}${lab("skin", 132, 330, 1)}</svg>`;
}

// ------------------------------------------------------------------ chart
function chartSvg(series, opts = {}) {
  const pts = series.points || []; const W = 720, H = 260, P = 40;
  if (!pts.length) return `<p class="muted">${t("level_none")}</p>`;
  const ts = pts.map((p) => Date.parse(p.t)); const vs = pts.map((p) => p.v);
  const b = series.baseline; let lo = Math.min(...vs, b ? b.low : Infinity), hi = Math.max(...vs, b ? b.high : -Infinity);
  if (lo === hi) { lo -= 1; hi += 1; } const pad = (hi - lo) * 0.1; lo -= pad; hi += pad;
  const t0 = Math.min(...ts), t1 = Math.max(...ts) || t0 + 1;
  const X = (x) => P + ((x - t0) / Math.max(1, t1 - t0)) * (W - 2 * P), Y = (v) => H - P - ((v - lo) / (hi - lo)) * (H - 2 * P);
  const path = pts.map((p, i) => `${i ? "L" : "M"}${X(Date.parse(p.t)).toFixed(1)},${Y(p.v).toFixed(1)}`).join(" ");
  const band = b ? `<rect x="${P}" y="${Y(b.high)}" width="${W - 2 * P}" height="${Math.max(1, Y(b.low) - Y(b.high))}" fill="rgba(0,180,216,.15)"/><text x="${P + 4}" y="${Y(b.high) - 4}" font-size="11" fill="var(--cyan)">${t("baseline")} ${b.low}–${b.high} (${esc(b.source)})</text>` : "";
  const marks = (series.markers || []).filter((m) => Date.parse(m.ts) >= t0 && Date.parse(m.ts) <= t1).map((m) => `<line x1="${X(Date.parse(m.ts))}" x2="${X(Date.parse(m.ts))}" y1="${P}" y2="${H - P}" stroke="var(--amber)" stroke-dasharray="4 4"/><text x="${X(Date.parse(m.ts)) + 3}" y="${P + 10}" font-size="11" fill="var(--amber)">${esc(m.type)}</text>`).join("");
  const dots = pts.map((p) => `<circle cx="${X(Date.parse(p.t))}" cy="${Y(p.v)}" r="${p.ctx === "earth_preflight" ? 3 : 4}" fill="${p.prov.type === "SYNTHETIC" ? "#d2a8ff" : p.prov.type === "REAL" ? "#7ee787" : "#79c0ff"}"><title>${esc(p.t)} · ${p.v} ${esc(series.unit)} · ${esc(p.prov.type)} · ${esc(p.ctx)}</title></circle>`).join("");
  const yt = [lo, (lo + hi) / 2, hi].map((v) => `<text x="4" y="${Y(v) + 4}" font-size="11" fill="var(--muted)">${v.toFixed(1)}</text>`).join("");
  const xt = [t0, (t0 + t1) / 2, t1].map((v) => `<text x="${X(v) - 30}" y="${H - 12}" font-size="11" fill="var(--muted)">${new Date(v).toISOString().slice(5, 16).replace("T", " ")}</text>`).join("");
  return `<svg viewBox="0 0 ${W} ${H}" style="width:100%;direction:ltr" role="img" aria-label="${esc(opts.label || series.indicator)} chart">${band}${marks}<path d="${path}" fill="none" stroke="var(--cyan)" stroke-width="2"/>${dots}${yt}${xt}</svg>
   <div class="muted cite">● <span style="color:#d2a8ff">SYNTHETIC</span> ● <span style="color:#79c0ff">USER-ENTERED</span> ● <span style="color:#7ee787">REAL</span> · ┆ <span style="color:var(--amber)">gravity transition / mission event</span></div>`;
}

// ------------------------------------------------------------------ navigation
const NAV = {
  astronaut: ["dashboard", "body3d", "measure", "posecheck", "charts", "history", "alerts", "schedule", "cdss", "radiation", "vision", "urine", "coach", "voice", "crew", "connection", "science", "simulate", "help", "status", "settings", "about"],
  cmo: ["dashboard", "body3d", "measure", "posecheck", "charts", "history", "alerts", "schedule", "cdss", "radiation", "vision", "urine", "coach", "crew", "blackbox", "science", "simulate", "help", "status", "settings", "about"],
  bhs: ["crew", "voice", "connection", "science", "simulate", "help", "status", "settings", "about"],
  flight_surgeon: ["surgeon", "dashboard", "body3d", "charts", "history", "alerts", "schedule", "radiation", "vision", "urine", "coach", "crew", "blackbox", "science", "simulate", "help", "status", "settings", "about"],
  researcher: ["blackbox", "science", "simulate", "help", "status", "about"],
};
const GROUPS = [
  ["g_main", ["surgeon", "dashboard", "body3d", "measure", "posecheck"]],
  ["g_monitor", ["charts", "history", "alerts", "schedule"]],
  ["g_features", ["cdss", "radiation", "vision", "urine", "coach", "voice", "crew", "connection", "blackbox"]],
  ["g_science", ["science", "simulate"]],
  ["g_system", ["help", "status", "settings", "about"]],
];
const BOTTOM = { astronaut: ["dashboard", "measure", "body3d", "alerts"], cmo: ["dashboard", "measure", "alerts", "body3d"], bhs: ["crew", "voice", "science", "help"],
  flight_surgeon: ["surgeon", "dashboard", "alerts", "science"], researcher: ["blackbox", "science", "simulate", "help"] };
function renderNav() {
  const items = S.user ? NAV[S.user.role] : [];
  $("#nav").innerHTML = GROUPS.map(([g, list]) => { const vs = list.filter((v) => items.includes(v)); return vs.length ? `<div class="navgroup"><h4>${esc(t(g))}</h4>${vs.map((v) =>
    `<button class="navbtn ${S.view === v ? "on" : ""}" data-act="go" data-v="${v}" ${S.view === v ? 'aria-current="page"' : ""} data-tour="nav-${v}">${ic(v)}<span>${esc(t(v))}</span></button>`).join("")}</div>` : ""; }).join("");
  const bn = S.user ? BOTTOM[S.user.role] : [];
  $("#bottomnav").innerHTML = bn.map((v) => `<button class="${S.view === v ? "on" : ""}" data-act="go" data-v="${v}" aria-label="${esc(t(v))}">${ic(v)}<span>${esc(I18N[S.lang][v + "_short"] || t(v))}</span></button>`).join("") +
    (S.user ? `<button data-act="menu">${ic("more")}<span>${esc(t("more"))}</span></button>` : "");
}
ACTIONS.menu = () => { const o = document.body.classList.toggle("nav-open"); $("#menuBtn").setAttribute("aria-expanded", o); };
let currentView = null;
async function go(v, opts = {}) {
  if (UNMOUNT[currentView]) { try { UNMOUNT[currentView](); } catch (e) { /* ignore */ } }
  currentView = v; S.view = v; renderNav(); document.body.classList.remove("nav-open");
  $("#pageTitle").innerHTML = `${ic(v)} ${esc(t(v))}`;
  const m = $("#main");
  m.innerHTML = window.Motion ? Motion.loader("orbit") : "";
  try {
    m.innerHTML = await VIEWS[v](opts);
    const h = m.querySelector("h2"); if (h && !h.nextElementSibling?.classList.contains("crenel")) h.insertAdjacentHTML("afterend", '<div class="crenel" aria-hidden="true"></div>');
    m.classList.remove("page-enter"); void m.offsetWidth; if (!reduceMotion()) m.classList.add("page-enter");
    if (MOUNT[v]) await MOUNT[v](opts);
  } catch (e) { m.innerHTML = `<div class="card"><h3>⚠ ${esc(t(v))}</h3><p>${esc(e.message)}</p><button data-act="go" data-v="${esc(v)}">${ic("restart")} ${S.lang === "ar" ? "إعادة المحاولة" : "Retry"}</button></div>`; }
  if (!opts.keepScroll) window.scrollTo(0, 0);
  m.focus({ preventScroll: true });
}
document.addEventListener("click", (ev) => {
  const el = ev.target.closest("[data-act]"); if (!el) return;
  const fn = ACTIONS[el.dataset.act]; if (fn) { if (el.type !== "checkbox") ev.preventDefault(); Promise.resolve(fn(el, ev)).catch((e) => toast("⚠ " + e.message, 4000)); }
});
document.addEventListener("keydown", (ev) => { if ((ev.key === "Enter" || ev.key === " ") && ev.target.matches("g[data-act]")) { ev.preventDefault(); ev.target.dispatchEvent(new MouseEvent("click", { bubbles: true })); } });
ACTIONS.go = (el) => navTo(el.dataset.v);
/** User-initiated navigation runs through the chosen Motion-Kit transition (planet / pulse / satellite / none). */
function navTo(v, opts) { if (v === S.view && !opts) return go(v); return window.Motion ? Motion.transition(() => go(v, opts)) : go(v, opts); }

// ------------------------------------------------------------------ chrome
function applyLang() {
  document.documentElement.lang = S.lang; document.documentElement.dir = S.lang === "ar" ? "rtl" : "ltr";
  $("#langBtn").innerHTML = `${ic("lang")}<span>${S.lang === "ar" ? "EN" : "ع"}</span>`; $("#tagline").textContent = t("tagline");
  $("#sideFoot").textContent = t("footer");
}
function applyTheme() { document.documentElement.dataset.theme = S.theme; $("#themeBtn").innerHTML = ic(S.theme === "dark" ? "sun" : "moon"); }
S.theme = localStorage.getItem("astra.theme") || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
$("#langBtn").addEventListener("click", () => { S.lang = S.lang === "ar" ? "en" : "ar"; localStorage.setItem("astra.lang", S.lang); applyLang(); if (S.user) go(S.view); else VIEWS.login().then((h) => ($("#main").innerHTML = h)); });
$("#themeBtn").addEventListener("click", () => { S.theme = S.theme === "dark" ? "light" : "dark"; localStorage.setItem("astra.theme", S.theme); applyTheme(); });
$("#hcBtn").innerHTML = ic("contrast"); $("#bigBtn").innerHTML = ic("glove"); $("#logoutBtn").innerHTML = ic("logout"); $("#menuBtn").innerHTML = ic("menu");
$("#brandMark").innerHTML = Brand.mark(42);
$("#hcBtn").addEventListener("click", () => { document.body.classList.toggle("hc"); localStorage.setItem("astra.hc", document.body.classList.contains("hc") ? "1" : "0"); });
$("#bigBtn").addEventListener("click", () => { document.body.classList.toggle("big"); localStorage.setItem("astra.big", document.body.classList.contains("big") ? "1" : "0"); });
$("#menuBtn").addEventListener("click", () => ACTIONS.menu());
$("#logoutBtn").addEventListener("click", () => logout());
$("#crewSel").addEventListener("change", (e) => { S.aid = e.target.value; go(S.view); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") document.body.classList.remove("nav-open"); });
if (localStorage.getItem("astra.hc") === "1") document.body.classList.add("hc");
if (localStorage.getItem("astra.big") === "1") document.body.classList.add("big");
if (localStorage.getItem("astra.reduce") === "1") document.body.classList.add("reduce-motion");
applyTheme();

function logout() { S.token = null; S.user = null; localStorage.removeItem("astra.token"); localStorage.removeItem("astra.user"); location.reload(); }

// ------------------------------------------------------------------ login
VIEWS.login = async () => {
  let demo = { users: [], password: "" }; try { demo = await get("/api/demo-users"); } catch (e) { /* offline */ }
  return `<div class="login card"><h2>🛰️ ${t("login")}</h2><div class="honesty">${esc(t("honesty"))}</div>
   <form id="loginForm"><label for="u">${t("username")}</label><input id="u" autocomplete="username" required style="width:100%">
   <label for="p">${t("password")}</label><input id="p" type="password" autocomplete="current-password" required style="width:100%">
   <p><button class="primary" type="submit" style="width:100%">${t("login")}</button></p></form>
   <h3>${t("demo")}</h3><div class="row">${demo.users.map((u) => `<button class="small" data-act="demoLogin" data-u="${esc(u.username)}" data-p="${esc(demo.password)}">${esc(u.display)}<br><small>${esc(u.username)}</small></button>`).join("")}</div>
   <p class="muted">password: <code>${esc(demo.password)}</code></p>
   <div class="mkpad" id="loginPad"><span>${S.lang === "ar" ? "حرّك المؤشر أو اسحب بإصبعك" : "Move the pointer or drag"}</span></div></div>`;
};
ACTIONS.demoLogin = (el) => doLogin(el.dataset.u, el.dataset.p);
document.addEventListener("submit", (ev) => { if (ev.target.id === "loginForm") { ev.preventDefault(); doLogin($("#u").value, $("#p").value).catch((e) => toast("⚠ " + e.message)); } });
async function doLogin(u, p) {
  const r = await post("/api/login", { username: u, password: p });
  S.token = r.token; S.user = r.user; S.justLoggedIn = true; localStorage.setItem("astra.token", r.token); localStorage.setItem("astra.user", JSON.stringify(r.user));
  await boot();
}

// ------------------------------------------------------------------ poll (replaces WebSocket)
async function poll() {
  if (!S.token) return;
  try {
    const p = await get("/api/poll"); $("#offline").classList.remove("on"); flushOutbox();
    const ctx = S.meta.gravity.contexts[p.gravity];
    $("#ctxChip").textContent = "🪐 " + L(ctx, "label") + " · " + ctx.g + " g";
    $("#delayChip").textContent = "📡 " + t("delay") + ": " + fmtDelay(p.delay_s);
    const a = $("#alarm");
    if (p.spe && p.spe.active) {
      const left = Math.max(0, (Date.parse(p.spe.arrival) - Date.now()) / 60000);
      a.className = "alarm spe"; a.innerHTML = `☢️ SPE – ${S.lang === "ar" ? "اذهب إلى الملجأ" : "GO TO SHELTER"}: ${esc(L(p.spe.shelter, "name"))} · ${left.toFixed(1)} min <button class="small" data-act="go" data-v="radiation">☢️</button>`;
    } else if (p.high) { a.className = "alarm high"; a.innerHTML = `⛔ ${p.high} HIGH-priority alert(s) – ${t("level_red")} <button class="small" data-act="go" data-v="alerts">${t("alerts")}</button>`; }
    else if (p.medium) { a.className = "alarm medium"; a.innerHTML = `⚠ ${p.medium} ${t("alerts")} <button class="small" data-act="go" data-v="alerts">${t("alerts")}</button>`; }
    else { a.className = "alarm"; a.innerHTML = ""; }
    if ((p.high || (p.spe && p.spe.active)) && S.sound && Date.now() - S.lastBeep > 30000) { beep(); S.lastBeep = Date.now(); }
  } catch (e) { if (S.token) { $("#offline").textContent = t("offline"); $("#offline").classList.add("on"); } }
}
const fmtDelay = (s) => (s < 60 ? `${(+s).toFixed(1)} s` : `${(s / 60).toFixed(1)} min`);
function beep() { // IEC 60601-1-8-inspired high-priority burst (visual banner is the voice-free fallback)
  try { const ac = new (window.AudioContext || window.webkitAudioContext)(); [0, 0.25, 0.5].forEach((d) => { const o = ac.createOscillator(), g = ac.createGain(); o.frequency.value = 880; g.gain.value = 0.15; o.connect(g); g.connect(ac.destination); o.start(ac.currentTime + d); o.stop(ac.currentTime + d + 0.15); }); } catch (e) { /* no audio */ }
}

// ------------------------------------------------------------------ offline outbox (IndexedDB)
function idb() { return new Promise((res, rej) => { const r = indexedDB.open("astra", 1); r.onupgradeneeded = () => r.result.createObjectStore("outbox", { autoIncrement: true }); r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error); }); }
async function outboxAdd(item) { const db = await idb(); return new Promise((res) => { const tx = db.transaction("outbox", "readwrite"); tx.objectStore("outbox").add(item); tx.oncomplete = res; }); }
async function flushOutbox() {
  try {
    const db = await idb(); const items = await new Promise((res) => { const out = []; const tx = db.transaction("outbox", "readonly"); tx.objectStore("outbox").openCursor().onsuccess = (e) => { const c = e.target.result; if (c) { out.push([c.key, c.value]); c.continue(); } else res(out); }; });
    for (const [k, v] of items) { await post("/api/readings", v); await new Promise((res) => { const tx = db.transaction("outbox", "readwrite"); tx.objectStore("outbox").delete(k); tx.oncomplete = res; }); toast("✔ outbox synced"); }
  } catch (e) { /* still offline */ }
}

// ------------------------------------------------------------------ splash (intro)
function splash() {
  return new Promise((resolve) => {
    const el = $("#splash");
    if (!el) return resolve();
    if (localStorage.getItem("astra.intro") === "0" || sessionStorage.getItem("astra.introShown")) { el.remove(); return resolve(); }
    sessionStorage.setItem("astra.introShown", "1");
    $("#splashTag").textContent = t("tagline");
    let done = false; const finish = () => { if (done) return; done = true; run.stop(); el.classList.add("out"); setTimeout(() => el.remove(), 520); resolve(); };
    const run = Brand.intro($("#splashStage"), finish, { reduced: reduceMotion() });
    $("#splashSkip").addEventListener("click", finish);
    el.addEventListener("keydown", (e) => { if (e.key === "Escape" || e.key === "Enter") finish(); });
    $("#splashSkip").focus();
  });
}

// ------------------------------------------------------------------ boot
async function boot() {
  applyLang();
  const intro = splash();
  S.meta = await get("/api/meta");
  try { S.evidence = (await get("/api/evidence")).entries; } catch (e) { S.evidence = []; }
  await intro;
  if (!S.token) { renderNav(); $("#main").innerHTML = await VIEWS.login(); $("#pageTitle").textContent = t("login"); if (window.Motion) Motion.pad($("#loginPad")); return; }
  try { S.crew = (await get("/api/crew")).crew; } catch (e) { return; }
  S.aid = S.user.astronaut_id || (S.crew[0] && S.crew[0].id) || null;
  const sel = $("#crewSel");
  if (["cmo", "flight_surgeon", "bhs"].includes(S.user.role)) {
    sel.style.display = ""; sel.innerHTML = S.crew.map((a) => `<option value="${esc(a.id)}" ${a.id === S.aid ? "selected" : ""}>${esc(a.id)} · ${esc(a.name)}</option>`).join("");
  }
  $("#userChip").innerHTML = `${esc(S.user.display)}`; $("#logoutBtn").style.display = "";
  S.view = NAV[S.user.role][0]; await (window.Motion && S.justLoggedIn ? Motion.transition(() => go(S.view)) : go(S.view)); S.justLoggedIn = false; poll(); setInterval(poll, 3000);
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});
  if (window.Tour && !localStorage.getItem("astra.tour." + S.user.username)) setTimeout(() => Tour.start(), 1900);
}

// ================================================================== VIEWS
VIEWS.dashboard = async () => {
  const d = await get(withAid("/api/dashboard")); S.dash = d;
  const reg = d.regions; const c = d.composite;
  const rows = d.latest.map((a) => `<tr><td>${esc(L(a, "label"))}</td><td><b>${a.value}</b> ${esc(a.unit)}</td><td>${lvl(a.level)}</td>
     <td class="muted">${a.baseline ? `${a.baseline.low}–${a.baseline.high}` : "—"}</td><td>${prov(a.provenance)}</td>
     <td><button class="small" data-act="showWhy" data-i="${esc(a.indicator)}">${t("why")}</button></td></tr>`).join("");
  const gtp = d.gtp && d.gtp.active ? `<div class="card" style="border-color:var(--amber)"><h3>🪂 Gravity Transition Protocol – ${esc(d.gtp.context)}</h3><ol>${(S.lang === "ar" ? d.gtp.steps_ar : d.gtp.steps_en).map((s, i) => `<li><label class="row"><input type="checkbox" data-act="gtpStep" data-i="${i}" ${d.gtp.done[i] ? "checked" : ""}> ${esc(s)}</label></li>`).join("")}</ol><p class="muted">Stand tests due: ${d.gtp.stand_tests_due.map(esc).join(" · ")}</p><button data-act="go" data-v="schedule">→ ${t("schedule")}</button>${cites(d.gtp.citation)}</div>` : "";
  return `<h2>${t("dashboard")} – ${esc(d.astronaut_id)}</h2>${gtp}
  <div class="grid2"><div class="card"><div class="row" style="justify-content:space-between"><div>${ring(c.score, c.band)}</div>
      <div><div class="big-num">${lvl(c.band)}</div><p>${t("composite")}: <b>${c.score}/20</b></p>
      <p class="muted">${t("gravity")}: ${esc(L(d.gravity, "label"))} (${d.gravity.g} g) · 📡 ${fmtDelay(d.delay_s)}</p>
      <p class="muted" style="max-width:340px">${esc(L(d.gravity, "advice"))}</p>
      <button class="primary" data-act="go" data-v="measure">➕ ${t("measure")}</button></div></div></div>
    <div class="card" data-tour="body"><h3>${ic("body3d")} ${S.lang === "ar" ? "النموذج ثلاثي الأبعاد" : "3D body"}</h3>${bodyViewer("dash")}
      <div class="regionlist" id="regionList" style="margin-top:10px">${Object.keys(reg).map((r) => `<button data-act="region" data-r="${r}">${reg[r].icon} ${esc(reg[r][S.lang] || reg[r].en)} ${ICON[reg[r].level] || "○"}</button>`).join("")}</div>
      <div id="regionPanel" class="muted" style="margin-top:10px">${S.lang === "ar" ? "اسحب للتدوير، واضغط على عضو أو اختره من القائمة لعرض تفاصيله." : "Drag to rotate; tap an organ or pick it from the list."}</div></div></div>
  <div class="card" style="margin-top:14px"><h3>${S.lang === "ar" ? "أحدث القراءات" : "Latest readings"}</h3><div style="overflow-x:auto"><table><tr><th>${S.lang === "ar" ? "المؤشر" : "Indicator"}</th><th>${t("value")}</th><th>Status</th><th>${t("baseline")}</th><th>Provenance</th><th></th></tr>${rows}</table></div><div id="whyPanel"></div></div>`;
};
ACTIONS.showWhy = (el) => { const a = S.dash.latest.find((x) => x.indicator === el.dataset.i); $("#whyPanel").innerHTML = whyBox(a); $("#whyPanel").scrollIntoView({ behavior: "smooth" }); };
ACTIONS.gtpStep = async (el) => { await post("/api/gtp/step", { index: +el.dataset.i, done: el.checked }); };
ACTIONS.region = (el) => showRegion(el.dataset.r, true);
function showRegion(id, fromList) {
  if (!id) { $("#regionPanel").innerHTML = ""; return; }
  const r = S.dash.regions[id]; if (!r) return;
  document.querySelectorAll("#regionList button").forEach((b) => b.classList.toggle("on", b.dataset.r === id));
  if (fromList && S.b3d) S.b3d.select(id);
  $("#regionPanel").innerHTML = `<div class="card"><h3>${r.icon} ${esc(r[S.lang] || r.en)} ${lvl(r.level)}</h3>
   <p><b>${S.lang === "ar" ? "الوظيفة" : "Function"}:</b> ${esc(L(r, "function"))}</p><p><b>${S.lang === "ar" ? "تأثير انعدام الجاذبية" : "Microgravity effects"}:</b> ${esc(L(r, "micro"))}</p>
   ${r.items.map((a) => `<div><b>${esc(L(a, "label"))}</b>: ${a.value} ${esc(a.unit)} ${lvl(a.level)} ${prov(a.provenance)} <button class="small" data-act="trend" data-i="${esc(a.indicator)}">📈</button>${whyBox(a)}</div>`).join("") || `<p class="muted">${t("level_none")}</p>`}
   ${r.vision ? `<p>👁️ ${esc((r.vision.payload.reasons || []).join("; ") || "no change")}</p><button class="small" data-act="go" data-v="vision">${t("vision")}</button>` : ""}
   ${cites(r.citations)}</div>`;
}
/** 3D viewer container (arched window) + controls; falls back to SVG map if WebGL is unavailable. */
function bodyViewer(id, tall) {
  return `<div class="b3d ${tall ? "tall" : ""}" id="b3d_${id}"><div class="tools">
    <button class="small" data-act="b3dZoom" data-f="0.8" aria-label="تكبير">${ic("plus")}</button><button class="small" data-act="b3dZoom" data-f="1.25" aria-label="تصغير">${ic("minus")}</button>
    <button class="small" data-act="b3dReset" aria-label="العرض الكامل">${ic("reset")}</button></div><div class="hint">${S.lang === "ar" ? "اسحب للتدوير · العجلة أو إصبعان للتكبير · نقرتان للعودة" : "Drag to rotate · wheel/pinch to zoom · double-click to reset"}</div></div>`;
}
function mountBody(id, statusMap, onSelect) {
  const host = document.getElementById("b3d_" + id); if (!host) return null;
  if (S.b3d) { try { S.b3d.destroy(); } catch (e) { /* ignore */ } S.b3d = null; }
  try {
    if (!window.Body3D || !Body3D.supported()) throw new Error("webgl");
    S.b3d = Body3D.mount(host, { onSelect }); S.b3d.setStatus(statusMap || {}); return S.b3d;
  } catch (e) { // graceful fallback: the original 2-D SVG body map
    host.classList.remove("b3d"); host.innerHTML = `<p class="muted small">${S.lang === "ar" ? "تعذّر تشغيل العرض ثلاثي الأبعاد على هذا الجهاز؛ يُعرض المخطط ثنائي الأبعاد." : "3D unavailable on this device – showing the 2D map."}</p>` + (S.dash ? bodySvg(S.dash.regions) : ""); return null;
  }
}
ACTIONS.b3dZoom = (el) => S.b3d && S.b3d.zoom(+el.dataset.f);
ACTIONS.b3dReset = () => S.b3d && S.b3d.reset();
UNMOUNT.dashboard = () => { if (S.b3d) { S.b3d.destroy(); S.b3d = null; } };
MOUNT.dashboard = () => { const st = {}; Object.entries(S.dash.regions).forEach(([k, v]) => { if (v.level !== "none") st[k] = v.level; });
  mountBody("dash", st, (r) => showRegion(r, false)); };
ACTIONS.trend = (el) => { S.chartInd = el.dataset.i; go("charts"); };

// ---------------- measurement wizard: input → validation → assessment → explanation → action → escalation → follow-up
const WIZ = [
  { k: "conditions", en: "Conditions", ar: "الظروف" },
  { k: "cv", en: "Cardiovascular", ar: "القلب والدورة", inds: ["heart_rate", "systolic", "diastolic", "spo2"], micro: "vitals" },
  { k: "sleep", en: "Sleep & behaviour", ar: "النوم والسلوك", inds: ["sleep_hours", "sleep_quality", "mood", "stress", "workload"], micro: "sleep" },
  { k: "sec", en: "Secondary", ar: "ثانوي", inds: ["body_temp", "glucose", "body_mass", "cabin_co2"], micro: "mass" },
  { k: "review", en: "Review & submit", ar: "مراجعة وإرسال" },
];
const SYMPT = { en: ["Facial puffiness", "Nasal congestion", "Head fullness / headache", "Dizziness", "Palpitations", "Leg cramps"], ar: ["انتفاخ الوجه", "احتقان الأنف", "امتلاء الرأس / صداع", "دوار", "خفقان", "تشنج الساقين"] };
VIEWS.measure = async () => {
  if (!S.wiz) S.wiz = { step: 0, vals: {}, cond: { time_of_day: new Date().toISOString().slice(11, 16), restrained: true, arm_position: "left, heart level", rested_5min: true }, sym: [] };
  const w = S.wiz, st = WIZ[w.step];
  const steps = `<div class="steps">${WIZ.map((s, i) => `<span class="${i === w.step ? "on" : ""}">${i + 1}. ${esc(s[S.lang])}</span>`).join("")}</div>`;
  let body = "";
  if (st.k === "conditions") {
    body = `${micro("vitals")}<div class="grid"><div><label>${S.lang === "ar" ? "الوقت (جدول الطاقم)" : "Time (crew schedule)"}</label><input id="c_time" value="${esc(w.cond.time_of_day)}"></div>
     <div><label>${S.lang === "ar" ? "وضعية الذراع" : "Arm position"}</label><select id="c_arm">${["left, heart level", "right, heart level", "left, raised", "other"].map((x) => `<option ${x === w.cond.arm_position ? "selected" : ""}>${x}</option>`).join("")}</select></div>
     <div><label class="row"><input type="checkbox" id="c_restr" ${w.cond.restrained ? "checked" : ""}> ${S.lang === "ar" ? "الجسم مثبت (حلقات القدم/المقعد)" : "Body restrained (foot loops / seat)"}</label>
     <label class="row"><input type="checkbox" id="c_rest" ${w.cond.rested_5min ? "checked" : ""}> ${S.lang === "ar" ? "راحة 5 دقائق" : "Rested 5 minutes"}</label></div></div>
     <h3>${S.lang === "ar" ? "أعراض انتقال السوائل" : "Fluid-shift symptoms"}</h3><div class="row">${SYMPT[S.lang].map((s, i) => `<label class="row chip"><input type="checkbox" class="sym" value="${SYMPT.en[i]}" ${w.sym.includes(SYMPT.en[i]) ? "checked" : ""}> ${esc(s)}</label>`).join("")}</div>`;
  } else if (st.inds) {
    body = `${micro(st.micro)}<div class="grid">${st.inds.map((k) => { const m = S.meta.indicators[k]; return `<div class="card"><label for="v_${k}"><b>${esc(L(m, "label"))}</b> (${esc(m.unit)})</label>
      <input id="v_${k}" inputmode="decimal" data-ind="${k}" value="${esc(w.vals[k] ?? "")}" style="width:100%;font-size:1.4em"><div class="row">${quick(k)}</div><div id="vv_${k}" class="cite"></div></div>`; }).join("")}</div>`;
  } else {
    const list = Object.entries(w.vals).filter(([, v]) => v !== "" && v != null);
    body = `<table>${list.map(([k, v]) => `<tr><td>${esc(L(S.meta.indicators[k], "label"))}</td><td><b>${esc(v)}</b> ${esc(S.meta.indicators[k].unit)}</td></tr>`).join("") || `<tr><td>${t("none")}</td></tr>`}</table>
      <p class="muted">${esc(JSON.stringify(w.cond))} ${w.sym.length ? "· " + esc(w.sym.join(", ")) : ""}</p><button class="primary" data-act="wizSubmit" ${list.length ? "" : "disabled"}>✔ ${t("submit")}</button><div id="wizResult"></div>`;
  }
  return `<h2>${t("measure")}</h2>${steps}<div class="card">${body}</div><div class="row" style="margin-top:10px"><button data-act="wizBack" ${w.step ? "" : "disabled"}>◀ ${t("back")}</button><button class="primary" data-act="wizNext" ${w.step < WIZ.length - 1 ? "" : "disabled"}>${t("next")} ▶</button><button data-act="wizReset">↺</button></div>`;
};
function quick(k) { // big one-tap buttons for scored items (glove friendly)
  if (["sleep_quality", "mood", "stress", "workload"].includes(k)) return [1, 2, 3, 4, 5].map((n) => `<button class="small" data-act="qset" data-k="${k}" data-v="${n}">${n}</button>`).join("");
  return "";
}
ACTIONS.qset = (el) => { $("#v_" + el.dataset.k).value = el.dataset.v; S.wiz.vals[el.dataset.k] = el.dataset.v; };
function wizCollect() {
  const w = S.wiz, st = WIZ[w.step];
  if (st.k === "conditions") { w.cond = { time_of_day: $("#c_time").value, arm_position: $("#c_arm").value, restrained: $("#c_restr").checked, rested_5min: $("#c_rest").checked }; w.sym = [...document.querySelectorAll(".sym:checked")].map((x) => x.value); }
  if (st.inds) st.inds.forEach((k) => { w.vals[k] = $("#v_" + k).value.trim(); });
}
ACTIONS.wizNext = async () => {
  wizCollect(); const st = WIZ[S.wiz.step];
  if (st.inds) { // live validation before moving on
    let bad = false;
    for (const k of st.inds) { const v = S.wiz.vals[k]; if (v === "") continue; const r = await post("/api/validate", { indicator: k, value: v, conditions: S.wiz.cond }); $("#vv_" + k).textContent = r.ok ? (r.warnings.join("; ") || "✔") : "⛔ " + r.errors.join("; "); if (!r.ok) bad = true; }
    if (bad) return toast("⛔ " + (S.lang === "ar" ? "صحّح القيم المرفوضة" : "Fix rejected values"));
  }
  S.wiz.step++; go("measure");
};
ACTIONS.wizBack = () => { wizCollect(); S.wiz.step--; go("measure"); };
ACTIONS.wizReset = () => { S.wiz = null; go("measure"); };
ACTIONS.wizSubmit = async () => {
  const w = S.wiz; const readings = Object.entries(w.vals).filter(([, v]) => v !== "").map(([indicator, value]) => ({ indicator, value }));
  const body = { aid: S.aid, readings, conditions: { ...w.cond, fluid_shift_symptoms: w.sym } };
  let r; try { r = await post("/api/readings", body); } catch (e) { if (/fetch|network/i.test(e.message)) { await outboxAdd(body); return toast("📦 " + t("offline")); } throw e; }
  const html = r.results.map((x) => x.ok ? `<div class="card" style="margin-top:8px"><b>${esc(L(x.assessment, "label"))}</b>: ${x.assessment.value} ${esc(x.assessment.unit)} ${lvl(x.assessment.level)}
     ${x.validation.warnings.length ? `<div class="cite">⚠ ${esc(x.validation.warnings.join("; "))}</div>` : ""}${whyBox(x.assessment)}
     ${x.alert_id ? `<p>📣 ${t("escalation")}: crew → CMO → flight surgeon · <button class="small" data-act="go" data-v="alerts">${t("alerts")}</button></p>` : ""}</div>`
    : `<div class="card">⛔ ${esc(x.validation.indicator)}: ${esc(x.validation.errors.join("; "))}</div>`).join("");
  $("#wizResult").innerHTML = html + `<p class="muted">🔁 ${S.lang === "ar" ? "المتابعة: أعد القياس في الظروف القياسية غدًا في نفس الوقت، أو خلال 30 دقيقة لأي نتيجة صفراء/حمراء." : "Follow-up: repeat tomorrow at the same time, or within 30 min for any yellow/red result."}</p>`;
  S.wiz = { ...w, vals: {} };
};

// ---------------- charts
VIEWS.charts = async () => {
  const ind = S.chartInd || "heart_rate"; const days = S.chartDays ?? 7;
  const s = await get(withAid(`/api/series?indicator=${ind}${days ? "&days=" + days : ""}`));
  return `<h2>${t("charts")}</h2><div class="row"><select id="chInd">${Object.entries(S.meta.indicators).map(([k, m]) => `<option value="${k}" ${k === ind ? "selected" : ""}>${esc(L(m, "label"))}</option>`).join("")}</select>
   ${[[1, t("today")], [7, t("week")], [0, t("mission")]].map(([d, l]) => `<button class="${d === days ? "primary" : ""}" data-act="chDays" data-d="${d}">${l}</button>`).join("")}</div>
   <div class="card" style="margin-top:10px">${chartSvg(s, { label: L(S.meta.indicators[ind], "label") })}</div>
   <p class="muted">${t("baseline")}: ${s.baseline ? `${s.baseline.mean} ± ${s.baseline.k}·${s.baseline.sd} (${esc(s.baseline.source)}, n=${s.baseline.n})` : "—"} · ${S.lang === "ar" ? "الوحدة" : "unit"}: <b>${esc(s.unit)}</b></p>
   <div class="card flat"><b>${S.lang === "ar" ? "المصادر العلمية لهذا المؤشر" : "Scientific sources for this indicator"}:</b> ${evChips(S.meta.indicators[ind].evidence)}
   <p class="small muted">${S.lang === "ar" ? "العتبات المعروضة قيم قابلة للتعديل؛ القيم الموسومة «افتراضية» ليست صادرة عن ناسا." : "Thresholds are configurable; values marked default are not NASA values."} <a href="#" data-act="go" data-v="simulate">${S.lang === "ar" ? "← قارن الأرض بالفضاء في المحاكاة" : "→ compare Earth vs space in the simulation"}</a></p></div>`;
};
MOUNT.charts = () => $("#chInd").addEventListener("change", (e) => { S.chartInd = e.target.value; go("charts"); });
ACTIONS.chDays = (el) => { S.chartDays = +el.dataset.d; go("charts"); };

// ---------------- alerts
VIEWS.alerts = async () => {
  const r = await get("/api/alerts");
  const card = (a) => `<div class="card" style="border-inline-start:6px solid ${a.priority === "high" ? "var(--red)" : a.priority === "medium" ? "var(--amber)" : "var(--cyan)"}">
    <div class="row" style="justify-content:space-between"><b>${a.priority.toUpperCase()} · ${esc(a.astronaut_id)} · ${esc(L(a.body, "label"))}</b>${lvl(a.body.level)}</div>
    <p class="muted">${esc(a.created)} · ${t("tier")}: ${a.tier} (${esc(r.tiers[a.tier])}) · repeats: ${a.repeats} · ${esc(a.status)} ${a.acked_by ? "· ✔ " + esc(a.acked_by) : ""}</p>
    ${a.status === "active" ? `<button class="primary" data-act="ack" data-id="${esc(a.id)}">✔ ${t("ack")}</button>` : ""}${whyBox(a.body)}</div>`;
  const act = r.alerts.filter((a) => a.status === "active"), old = r.alerts.filter((a) => a.status !== "active").slice(0, 15);
  return `<h2>${t("alerts")}</h2><div class="card muted">IEC 60601-1-8 style: HIGH = red flashing, repeats every ${r.policy.high.repeat_s} s, escalates every ${r.policy.high.escalate_s / 60} min · MEDIUM = amber, repeats every ${r.policy.medium.repeat_s / 60} min, escalates every ${r.policy.medium.escalate_s / 60} min · LOW = info, no repeat. ${t("escalation")}: ${r.tiers.join(" → ")}.
   <label class="row"><input type="checkbox" id="snd" ${S.sound ? "checked" : ""}> 🔊 sound (visual banner always on)</label></div>
   <div class="grid" style="margin-top:10px">${act.map(card).join("") || `<p>✔ ${t("none")}</p>`}</div><h3>History</h3><div class="grid">${old.map(card).join("")}</div>`;
};
MOUNT.alerts = () => $("#snd").addEventListener("change", (e) => { S.sound = e.target.checked; localStorage.setItem("astra.sound", S.sound ? "1" : "0"); });
ACTIONS.ack = async (el) => { const r = await post(`/api/alerts/${el.dataset.id}/ack`); toast(r.status === "acknowledged" ? "✔" : `📡 ${r.status} – ${fmtDelay(r.delay_s)}`); go(S.view); };

// ---------------- flight surgeon (ground) view
VIEWS.surgeon = async () => {
  const [q, al] = await Promise.all([get("/api/queue"), get("/api/alerts")]);
  const crewRows = await Promise.all(S.crew.map(async (c) => { const d = await get(`/api/dashboard?aid=${c.id}`); return `<tr><td>${esc(c.id)} · ${esc(c.name)}</td><td>${ring(d.composite.score, d.composite.band).replace('class="ring"', 'class="ring" style="width:60px;height:60px"')}</td><td>${lvl(d.composite.band)}</td><td>${d.alerts.length}</td><td><button class="small" data-act="pickAid" data-a="${esc(c.id)}">${t("dashboard")}</button></td></tr>`; }));
  const inbox = q.queue.filter((m) => m.direction === "down").map((m) => `<tr><td>${esc(m.body.kind)}</td><td>${esc(m.body.astronaut_id)}</td><td>${esc((m.body.payload && (m.body.payload.label_en || m.body.payload.outcome_en)) || "")}</td><td>${esc(m.deliver_at)}</td><td>${fmtDelay(m.body.delay_s)}</td></tr>`).join("");
  const up = q.queue.filter((m) => m.direction === "up").map((m) => `<li>${esc(m.body.kind)} → ${m.delivered ? t("delivered") : t("in_transit") + " (ETA " + esc(m.deliver_at) + ")"}</li>`).join("");
  return `<h2>🌍 ${t("surgeon")}</h2><div class="card muted">${S.lang === "ar" ? "يرى الأرض فقط ما وصل عبر الوصلة المتأخرة. الإقرارات تعود بنفس التأخير." : "The ground sees only what has ARRIVED over the delayed link. Acknowledgements travel back with the same delay."} 📡 ${fmtDelay(q.delay_s)}</div>
   <div class="card"><h3>Crew overview</h3><table><tr><th>Crew</th><th></th><th>Status</th><th>Active alerts</th><th></th></tr>${crewRows.join("")}</table></div>
   <div class="grid2" style="margin-top:14px"><div class="card"><h3>📥 Delivered inbox</h3><div style="overflow-x:auto"><table><tr><th>Kind</th><th>Crew</th><th>Item</th><th>Arrived</th><th>Delay</th></tr>${inbox || `<tr><td>${t("none")}</td></tr>`}</table></div></div>
   <div class="card"><h3>✔ Arrived alerts</h3>${al.alerts.filter((a) => a.status === "active").map((a) => `<p>${esc(a.priority)} · ${esc(a.astronaut_id)} · ${esc(a.body.label_en)} <button class="small" data-act="ack" data-id="${esc(a.id)}">${t("ack")} 📡</button></p>`).join("") || t("none")}<h3>📤 Uplink</h3><ul>${up || "<li>—</li>"}</ul></div></div>`;
};
ACTIONS.pickAid = (el) => { S.aid = el.dataset.a; $("#crewSel").value = S.aid; go("dashboard"); };

// ---------------- mission timeline, routine, GTP, stand test
VIEWS.schedule = async () => {
  const [ev, dash] = await Promise.all([get("/api/events"), get(withAid("/api/dashboard"))]);
  const ctxs = S.meta.gravity.contexts; const standOk = ctxs[dash.gravity_context].standing_tests;
  return `<h2>${t("schedule")}</h2><div class="grid2"><div class="card"><h3>🗓️ ${S.lang === "ar" ? "الروتين اليومي (جدول الطاقم)" : "Daily routine (crew schedule)"}</h3><table>${S.meta.routine.map((r) => `<tr><td><b>${esc(r.time)}</b></td><td>${esc(L(r, "task"))}</td></tr>`).join("")}</table>${micro("sleep")}</div>
   <div class="card"><h3>🪐 ${t("gravity")}</h3><select id="ctxSel">${Object.entries(ctxs).map(([k, v]) => `<option value="${k}" ${k === dash.gravity_context ? "selected" : ""}>${esc(L(v, "label"))} – ${v.g} g – 📡 ${v.delay_s.join("–")} s</option>`).join("")}</select> <button data-act="setCtx">${t("save")}</button>
     <h3>➕ Mission event</h3><div class="row"><select id="evType">${["launch", "docking", "landing", "return", "critical_task"].map((x) => `<option>${x}</option>`).join("")}</select><select id="evCtx">${Object.keys(ctxs).map((k) => `<option>${k}</option>`).join("")}</select><input id="evNote" placeholder="note / critical-task hours"><button data-act="addEvent">${t("save")}</button></div>
     <p class="muted">landing/return from 0 g → Gravity Transition Protocol starts automatically (rule 3).</p>
     <label>📡 delay override (s, demo)</label><div class="row"><input id="delayOv" type="number" placeholder="auto"><button data-act="setDelay">${t("save")}</button></div>
     <h3>Timeline</h3><ul>${ev.events.map((e) => `<li>${esc(e.ts)} · <b>${esc(e.type)}</b> · ${esc(e.context)} · ${esc(e.note || "")}</li>`).join("") || "<li>—</li>"}</ul></div></div>
   <div class="card" style="margin-top:14px"><h3>🧍‍♂️ ${S.lang === "ar" ? "اختبار الجلوس ← الوقوف بعد الهبوط" : "Post-landing seated → stand test"}</h3>${micro("stand")}
     ${standOk ? `<div class="grid">${[["seated_hr", "Seated HR"], ["seated_sys", "Seated systolic"], ["stand_hr", "Standing HR (3 min)"], ["stand_sys", "Standing systolic (3 min)"]].map(([k, l]) => `<div><label>${l}</label><input id="st_${k}" inputmode="decimal"></div>`).join("")}</div><button class="primary" data-act="standTest">✔ ${t("submit")}</button><div id="stRes"></div>`
      : `<p>⛔ ${S.lang === "ar" ? "غير متاح في انعدام الجاذبية – لا توجد وضعية وقوف (القاعدة 3)." : "Not available in 0 g – there is no standing posture (rule 3)."}</p>`}</div>`;
};
ACTIONS.setCtx = async () => { const r = await post("/api/gravity", { context: $("#ctxSel").value }); toast(r.transition ? "🪂 Gravity Transition Protocol started" : "✔"); go("schedule"); };
ACTIONS.addEvent = async () => { await post("/api/events", { type: $("#evType").value, context: $("#evCtx").value, note: $("#evNote").value }); go("schedule"); };
ACTIONS.setDelay = async () => { const v = $("#delayOv").value; const r = await post("/api/delay", { seconds: v === "" ? null : +v }); toast("📡 " + fmtDelay(r.delay_s)); poll(); };
ACTIONS.standTest = async () => { const b = { aid: S.aid }; ["seated_hr", "seated_sys", "stand_hr", "stand_sys"].forEach((k) => (b[k] = $("#st_" + k).value)); const r = await post("/api/stand_test", b); $("#stRes").innerHTML = r.ok ? `<p>${lvl(r.assessment.level)} HR +${r.assessment.hr_rise} · SBP −${r.assessment.systolic_drop}</p>${whyBox(r.assessment)}` : `<p>⛔ ${esc(r.error)}</p>`; };

// ---------------- project status
VIEWS.status = async () => { const s = S.meta.status; const lab = { done: ["done", "أُنجز"], partial: ["partial", "جزئي"], next: ["next", "التالي"] };
  const col = (k, i) => `<div class="card"><h3>${i} ${lab[k][S.lang === "ar" ? 1 : 0]}</h3><ul>${(S.lang === "ar" && s[k + "_ar"] ? s[k + "_ar"] : s[k]).map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>`; return `<h2>${t("status")}</h2><div class="grid">${col("done", "✅")}${col("partial", "🟡")}${col("next", "➡️")}</div>`; };
// ---------------- about
VIEWS.about = async () => `<h2>${t("about")}</h2><div class="honesty">${esc(t("honesty"))}</div><div class="card" style="margin-top:12px"><p>BÖVD ${esc(S.meta.version)} · crypto: ${esc(S.meta.crypto)} · local server 127.0.0.1 · no cloud.</p><p>Intended use: decision support and training for crew self-monitoring in analog / hackathon settings. Not intended for diagnosis, treatment, or operational flight use.</p><p><a href="/api/openapi.json" target="_blank">OpenAPI</a></p></div>`;

boot().catch((e) => { $("#main").innerHTML = `<div class="card">⚠ ${esc(e.message)} – is the local server running? (start.bat)</div>`; });
