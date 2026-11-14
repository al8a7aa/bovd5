/* =====================================================================
   BÖVD Motion Kit (adapted from the user-supplied BOVD_Motion_Kit.html)
   - Page transitions: planet (expanding planet), pulse (heartbeat line opens), sat (satellite curtain)
     → chosen in Settings, stored per browser; "none" and prefers-reduced-motion skip them.
   - Loaders: orbiting moon, moving pulse, connecting dots.
   - Interaction: radar-ripple on primary buttons; satellites that follow the pointer (login / help).
   CSP-safe: no inline scripts, no external fonts.
   ===================================================================== */
"use strict";
(function () {
  const ease = (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
  const tween = (ms, fn) => new Promise((r) => { const t0 = performance.now(); (function f(n) { const k = Math.min(1, (n - t0) / ms); fn(ease(k)); k < 1 ? requestAnimationFrame(f) : r(); })(t0); });
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const SPEED = 0.62; // app navigation is frequent → the kit timings, shortened
  const ms = (x) => Math.round(x * SPEED);
  const STYLES = {
    planet: ["كوكب يتمدّد", "Expanding planet", "دائرة الكوكب تتمدد وتغطي الشاشة، يظهر الشعار، ثم تنكمش لتكشف الصفحة الجديدة."],
    pulse: ["نبضة قلب", "Heartbeat", "خط النبض يُرسم عبر الشاشة ثم ينفتح ليغطيها، ويرتد بعد ظهور الشعار."],
    sat: ["قمر عابر", "Passing satellite", "قمر صناعي يسحب ستارة قطرية خلفه، ثم يعود ليكشف الصفحة التالية."],
    none: ["بدون انتقال", "No transition", "تنتقل الصفحات مباشرة مع ظهور خفيف للمحتوى."],
  };
  let el = null;
  function overlay() {
    if (el) return el;
    const d = document.createElement("div"); d.id = "mkov"; d.setAttribute("aria-hidden", "true");
    d.innerHTML = `<div id="mkpn"></div><div id="mked"></div>
      <svg id="mkhb" viewBox="0 0 1200 160" preserveAspectRatio="none"><path id="mkhp" pathLength="1" d="M0 80H470L486 66L500 98L530 24L558 138L584 52L600 80H1200"/></svg>
      <div id="mkst"></div>
      <div id="mkct"><svg width="100" viewBox="-40 -28 80 56"><circle r="20" class="a"/><ellipse rx="36" ry="10" transform="rotate(-10)" class="b"/><path class="b" d="M-20 0H-8L-4 -9L2 10L7 -4L10 0H20"/></svg><b>BÖVD</b></div>`;
    document.body.appendChild(d); el = d; return d;
  }
  const q = (id) => document.getElementById(id);
  const show = (on) => (overlay().style.visibility = on ? "visible" : "hidden");
  const reset = () => { ["mkpn", "mked", "mkhb", "mkhp", "mkst", "mkct"].forEach((i) => (q(i).style.cssText = "")); show(0); };
  const brand = (on) => { const c = q("mkct"); c.style.opacity = on ? 1 : 0; c.style.transform = `translate(-50%,-50%) scale(${on ? 1 : 0.85})`; };
  const edge = (x, k) => { q("mked").style.clipPath = `polygon(${x}% 0,${x + 0.6}% 0,${x + 30.6}% 100%,${x + 30}% 100%)`; const f = 0.5 + 0.42 * Math.sin(k * Math.PI * 3); q("mkst").style.left = x + 30 * f + "%"; q("mkst").style.top = f * 100 + "%"; };
  const T = {
    async planet(go) { overlay(); show(1); const pn = q("mkpn");
      await tween(ms(700), (k) => (pn.style.clipPath = `circle(${k * 80}% at 50% 50%)`));
      brand(1); await Promise.all([go(), wait(ms(700))]); brand(0);
      await tween(ms(700), (k) => (pn.style.clipPath = `circle(${(1 - k) * 80}% at 50% 50%)`)); reset(); },
    async pulse(go) { overlay(); const pn = q("mkpn"), hb = q("mkhb"), hp = q("mkhp"); pn.style.clipPath = "inset(50% 0 50% 0)"; show(1); hb.style.opacity = 1;
      await tween(ms(800), (k) => (hp.style.strokeDashoffset = 1 - k));
      await tween(ms(550), (k) => (pn.style.clipPath = `inset(${50 - 50 * k}% 0 ${50 - 50 * k}% 0)`));
      hb.style.opacity = 0; brand(1); await Promise.all([go(), wait(ms(650))]); brand(0);
      await tween(ms(600), (k) => (pn.style.clipPath = `inset(${50 * k}% 0 ${50 * k}% 0)`)); reset(); },
    async sat(go) { overlay(); const pn = q("mkpn"), ed = q("mked"), st = q("mkst"); show(1); ed.style.opacity = 1; st.style.opacity = 1;
      await tween(ms(900), (k) => { const x = 100 - 135 * k; pn.style.clipPath = `polygon(${x}% 0,100% 0,100% 100%,${x + 30}% 100%)`; edge(x, k); });
      ed.style.opacity = 0; st.style.opacity = 0; brand(1); await Promise.all([go(), wait(ms(650))]); brand(0); ed.style.opacity = 1; st.style.opacity = 1;
      await tween(ms(900), (k) => { const a = 100 - 135 * k; pn.style.clipPath = `polygon(-35% 0,${a}% 0,${a + 30}% 100%,-5% 100%)`; edge(a, k); }); reset(); },
  };
  const reduced = () => document.body.classList.contains("reduce-motion") || matchMedia("(prefers-reduced-motion: reduce)").matches;
  const style = () => localStorage.getItem("astra.trans") || "planet";
  let busy = false;
  /** Run a navigation through the chosen transition. `go` may be async; the page is revealed after it resolves. */
  async function transition(go, force) {
    const s = force || style();
    if (busy) return; // ignore double clicks mid-transition
    if (reduced() || s === "none" || !T[s]) return go();
    busy = true;
    try { await T[s](async () => { await go(); }); } catch (e) { reset(); throw e; } finally { busy = false; }
  }

  // ---------------- loaders
  const LOADERS = {
    orbit: (label) => `<div class="mkload" role="status" aria-label="${label}"><svg viewBox="-70 -45 140 90"><g transform="rotate(-12)"><ellipse rx="52" ry="15" class="rg" opacity=".5"/><circle r="26" class="pl"/><path class="rg" d="M-52 0A52 15 0 0 0 52 0"/><circle r="4.5" fill="#1ba6cf"><animateMotion dur="2.6s" repeatCount="indefinite" path="M-52,0A52,15 0 1 0 52,0A52,15 0 1 0 -52,0"/><animate attributeName="opacity" values="1;1;.15;.15;1" keyTimes="0;.48;.5;.98;1" dur="2.6s" repeatCount="indefinite"/></circle></g></svg><small>${label}</small></div>`,
    pulse: (label) => `<div class="mkload" role="status" aria-label="${label}"><svg viewBox="0 0 240 60"><path class="ecg" pathLength="1" d="M0 30H80L90 22L98 38L112 6L126 54L138 18L146 30H240"/></svg><small>${label}</small></div>`,
    dots: (label) => `<div class="mkload" role="status" aria-label="${label}"><svg viewBox="-50 -50 100 100"><path class="ecg" style="animation-duration:3.6s;stroke-width:1.6" pathLength="1" d="M34 0L17 29.4L-17 29.4L-34 0L-17 -29.4L17 -29.4Z"/>${[[34, 0], [17, 29.4], [-17, 29.4], [-34, 0], [-17, -29.4], [17, -29.4]].map(([x, y], i) => `<circle class="dt" style="--i:${i}" cx="${x}" cy="${y}" r="4"/>`).join("")}</svg><small>${label}</small></div>`,
  };
  const loader = (kind = "orbit", label = "") => (LOADERS[kind] || LOADERS.orbit)(label || (document.documentElement.lang === "ar" ? "جارٍ التحميل…" : "Loading…"));

  // ---------------- radar ripple on primary buttons (kit: "زر بنبضة رادار")
  document.addEventListener("pointerdown", (e) => {
    const b = e.target.closest && e.target.closest("button.primary, .mk-sonar"); if (!b || b.disabled || reduced()) return;
    [0, 180, 360].forEach((d) => setTimeout(() => { const s = document.createElement("span"); s.className = "mkr"; b.appendChild(s); setTimeout(() => s.remove(), 1500); }, d));
  });

  // ---------------- satellites following the pointer (kit: "أقمار تدور حول مؤشرك")
  function pad(host) {
    const cv = document.createElement("canvas"); host.appendChild(cv); const g = cv.getContext("2d");
    let W = 1, H = 1, mx = 0, my = 0, px = 0, py = 0, an = 0, sd = [], alive = true;
    const rs = () => { const r = cv.getBoundingClientRect(), d = devicePixelRatio || 1; if (!r.width) return; W = r.width; H = r.height; cv.width = W * d; cv.height = H * d; g.setTransform(d, 0, 0, d, 0, 0); mx = px = W / 2; my = py = H / 2;
      let seed = 7; const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647); sd = [...Array(46)].map(() => [rnd() * W, rnd() * H, rnd() * 1.3 + 0.3]); };
    cv.addEventListener("pointermove", (e) => { const r = cv.getBoundingClientRect(); mx = e.clientX - r.left; my = e.clientY - r.top; });
    const SA = [[34, 1, "#1ba6cf", 5], [56, -0.7, "#8fe3fb", 3.6], [78, 0.5, "#ffffff", 3]];
    (function lp() { if (!alive || !cv.isConnected) return; requestAnimationFrame(lp);
      g.fillStyle = "rgba(6,10,27,.22)"; g.fillRect(0, 0, W, H); g.fillStyle = "rgba(255,255,255,.5)"; sd.forEach((s) => g.fillRect(s[0], s[1], s[2], s[2]));
      px += (mx - px) * 0.09; py += (my - py) * 0.09; if (!reduced()) an += 0.03;
      const P = SA.map(([r, v, c, z]) => { const a = an * v * 2; return [px + Math.cos(a) * r, py + Math.sin(a) * r * 0.42, c, z]; });
      g.strokeStyle = "rgba(27,166,207,.45)"; g.lineWidth = 1; g.beginPath(); P.forEach((p, i) => (i ? g.lineTo(p[0], p[1]) : g.moveTo(p[0], p[1]))); g.closePath(); g.stroke();
      g.fillStyle = "#0b1a3a"; g.strokeStyle = "#1ba6cf"; g.beginPath(); g.arc(px, py, 12, 0, 7); g.fill(); g.stroke();
      P.forEach((p) => { g.fillStyle = p[2]; g.shadowColor = p[2]; g.shadowBlur = 14; g.beginPath(); g.arc(p[0], p[1], p[3], 0, 7); g.fill(); g.shadowBlur = 0; });
    })();
    rs(); addEventListener("resize", rs);
    return { stop() { alive = false; removeEventListener("resize", rs); } };
  }

  window.Motion = { transition, loader, pad, STYLES, style, T };
})();
