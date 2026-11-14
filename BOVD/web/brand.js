/* =====================================================================
   BÖVD brand kit: logo (static), intro animation (from BOVD_Intro v2),
   Omani geometric ornaments (CSS variables) and the geometric icon set.
   ===================================================================== */
"use strict";
(function () {
  const C = "#1ba6cf";
  const TRAIL = "M333,572C270,580 224,565 226,535C228,505 275,488 316,480H486L493,468L500,492L540,398L566,543L598,457L610,479C720,480 860,470 938,444C955,438 970,435 986,433C1030,428 1056,404 1044,388C1030,368 975,366 920,370";
  const WORDMARK = `<path d="M260,910H368Q396,910 396,933Q396,956 368,956H260ZM260,956H372Q396,956 396,980Q396,1003 372,1003H260Z"/>
    <rect x="477" y="910" width="114" height="93" rx="40"/><path d="M860,910H948Q998,910 998,956Q998,1003 948,1003H860Z"/>
    <polygon points="612,898 656,898 713,978 770,898 814,898 724,1015 702,1015" fill="currentColor" stroke="none"/>`;
  const sp = (r) => `M0 ${-r}Q${r * 0.12} ${-r * 0.12} ${r} 0Q${r * 0.12} ${r * 0.12} 0 ${r}Q${-r * 0.12} ${r * 0.12} ${-r} 0Q${-r * 0.12} ${-r * 0.12} 0 ${-r}Z`;

  /** Static logo mark (planet + heartbeat orbit). */
  function mark(size = 40) {
    return `<svg viewBox="200 150 860 700" width="${size}" height="${size}" aria-hidden="true"><circle cx="627" cy="477" r="312" fill="#060a1b"/>
      <path d="${TRAIL}" fill="none" stroke="${C}" stroke-width="30" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="${sp(40)}" transform="translate(475 252)" fill="${C}"/><path d="${sp(30)}" transform="translate(783 236)" fill="#fff"/></svg>`;
  }
  /** Full logo with wordmark. */
  function logo(width = 180) {
    return `<svg viewBox="150 100 960 960" width="${width}" aria-label="BÖVD"><circle cx="627" cy="477" r="312" fill="#060a1b"/>
      <path d="${TRAIL}" fill="none" stroke="${C}" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>
      <g fill="none" stroke="currentColor" stroke-width="24" style="color:var(--ink)">${WORDMARK}</g>
      <path d="${sp(20)}" transform="translate(492 863)" fill="${C}"/><path d="${sp(20)}" transform="translate(560 863)" fill="${C}"/></svg>`;
  }

  /* ---------------- Omani ornaments as CSS variables ---------------- */
  function ornaments() {
    const enc = (s) => `url("data:image/svg+xml,${encodeURIComponent(s)}")`;
    // 8-point star (khatam) lattice inspired by carved Omani doors & window screens
    const star = (col, op) => `<svg xmlns="http://www.w3.org/2000/svg" width="28" height="14" viewBox="0 0 28 14"><g fill="none" stroke="${col}" stroke-opacity="${op}" stroke-width="1">
      <rect x="9" y="2" width="10" height="10"/><rect x="9" y="2" width="10" height="10" transform="rotate(45 14 7)"/><path d="M0 7h4M24 7h4"/></g></svg>`;
    // fort crenellation (merlons) – Nizwa / Bahla battlements
    const merlon = `<svg xmlns="http://www.w3.org/2000/svg" width="40" height="10" viewBox="0 0 40 10"><path d="M0 10V6h4V0h12v6h8V0h12v6h4v4z" fill="#000"/></svg>`;
    const r = document.documentElement.style;
    r.setProperty("--khatam", enc(star("#b8935a", 0.9)));
    r.setProperty("--khatam-faint", enc(star("#1ba6cf", 0.12)));
    r.setProperty("--merlon", enc(merlon));
  }

  /* ---------------- icons (24px, stroke = currentColor) ---------------- */
  const P = {
    dashboard: "M4 4h7v7H4zM13 4h7v4h-7zM13 10h7v10h-7zM4 13h7v7H4z",
    body3d: "M12 4a2 2 0 1 0 0 .1M8 21l2-7-3-4 5-2 5 2-3 4 2 7M12 8v4",
    measure: "M3 12h4l2-6 4 12 2-6h6",
    posecheck: "M4 8h3l2-3h6l2 3h3v11H4zM12 17a4 4 0 1 0 0-8 4 4 0 0 0 0 8z",
    charts: "M4 20V4M4 20h16M8 16l4-5 3 3 5-7",
    history: "M12 7v5l3 2M4 12a8 8 0 1 0 2.3-5.6M4 4v4h4",
    alerts: "M6 17V11a6 6 0 1 1 12 0v6l2 2H4zM10 21h4",
    schedule: "M5 5h14v15H5zM5 10h14M9 3v4M15 3v4",
    cdss: "M7 4v6a5 5 0 0 0 10 0V4M17 14v1a4 4 0 0 1-8 0M19 12a2 2 0 1 0 0 .1",
    radiation: "M12 12m-2 0a2 2 0 1 0 4 0 2 2 0 1 0-4 0M12 10L9 4.8A8 8 0 0 0 4 12h6M14 12h6a8 8 0 0 0-5-7.2L12 10M11 13.7L8 19a8 8 0 0 0 8 0l-3-5.3",
    vision: "M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12zM12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z",
    urine: "M12 3s6 7 6 11a6 6 0 0 1-12 0c0-4 6-11 6-11z",
    coach: "M3 10v4M6 8v8M18 8v8M21 10v4M6 12h12",
    voice: "M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3zM5 11a7 7 0 0 0 14 0M12 18v3",
    crew: "M9 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM3 20a6 6 0 0 1 12 0M16 11a3 3 0 1 0 0-6M21 20a6 6 0 0 0-4-5.6",
    connection: "M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z",
    blackbox: "M4 7l8-4 8 4v10l-8 4-8-4zM4 7l8 4 8-4M12 11v10",
    surgeon: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18",
    science: "M5 4h10l4 4v12H5zM15 4v4h4M8 12h8M8 16h6",
    simulate: "M12 12m-3 0a3 3 0 1 0 6 0 3 3 0 1 0-6 0M3 12c3-6 15-6 18 0M3 12c3 6 15 6 18 0",
    status: "M5 21V4h11l-2 4 2 4H5",
    settings: "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19 12l2-1-1-3-2 .2-1.3-1.3.2-2-3-1-1 2h-1.8l-1-2-3 1 .2 2L5.6 7.2 3.6 7l-1 3 2 1v2l-2 1 1 3 2-.2 1.3 1.3-.2 2 3 1 1-2h1.8l1 2 3-1-.2-2 1.3-1.3 2 .2 1-3-2-1z",
    help: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6V14M12 17h.01",
    about: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 11v6M12 7h.01",
    menu: "M4 6h16M4 12h16M4 18h16", more: "M5 12h.01M12 12h.01M19 12h.01",
    play: "M7 4l12 8-12 8z", pause: "M7 4h3v16H7zM14 4h3v16h-3z", restart: "M4 12a8 8 0 1 0 2.3-5.6M4 4v4h4",
    next: "M15 6l-6 6 6 6", prev: "M9 6l6 6-6 6", plus: "M12 5v14M5 12h14", minus: "M5 12h14", reset: "M3 12h4M17 12h4M12 3v4M12 17v4",
    camera: "M4 8h3l2-3h6l2 3h3v11H4zM12 17a4 4 0 1 0 0-8 4 4 0 0 0 0 8z", sun: "M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10zM12 1v2M12 21v2M1 12h2M21 12h2",
    moon: "M21 13A9 9 0 1 1 11 3a7 7 0 0 0 10 10z", glove: "M7 11V5a1.5 1.5 0 0 1 3 0v5M10 10V4a1.5 1.5 0 0 1 3 0v6M13 10V5a1.5 1.5 0 0 1 3 0v6M16 11V8a1.5 1.5 0 0 1 3 0v6a7 7 0 0 1-14 0v-3a1.5 1.5 0 0 1 3 0",
    contrast: "M12 21a9 9 0 1 0 0-18v18z", logout: "M15 4h4v16h-4M10 8l-4 4 4 4M6 12h10", lang: "M4 5h9M8 3v2M6 5c0 4 3 7 6 8M11 5c0 4-3 7-7 9M14 21l4-10 4 10M15.5 17h5",
    orbit: "M12 12m-3 0a3 3 0 1 0 6 0 3 3 0 1 0-6 0M2 12a10 4 0 1 0 20 0 10 4 0 1 0-20 0", delay: "M2 12h4l3-8 4 16 3-8h6",
  };
  const icon = (name, cls = "") => `<svg viewBox="0 0 24 24" class="${cls}" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${P[name] || P.about}"/></svg>`;

  /* ---------------- intro (adapted from BOVD_Intro v2, user-supplied) ---------------- */
  function intro(stageEl, onDone, opts = {}) {
    const NS = "http://www.w3.org/2000/svg", W = "#ffffff", cx = 627, cy = 477;
    stageEl.innerHTML = `<svg viewBox="150 100 960 960" role="img" aria-label="BÖVD">
<defs><linearGradient id="rim" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#6fdcf9" stop-opacity=".95"/><stop offset=".45" stop-color="${C}" stop-opacity="0"/><stop offset="1" stop-color="${C}" stop-opacity=".4"/></linearGradient><radialGradient id="halo"><stop offset=".78" stop-color="${C}" stop-opacity=".3"/><stop offset="1" stop-color="${C}" stop-opacity="0"/></radialGradient><linearGradient id="gg"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".9"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient><mask id="gm" maskUnits="userSpaceOnUse" x="240" y="880" width="800" height="150" style="mask-type:alpha"><use href="#wm"/></mask><clipPath id="wc"><rect id="wcr" x="240" y="880" width="0" height="150"/></clipPath></defs>
<path id="arc" d="M920,370C800,385 430,545 333,572" fill="none"/><circle id="haloc" cx="627" cy="477" r="400" fill="url(#halo)" opacity="0"/>
<g id="dust"></g><g id="rip"></g><g id="planet"><circle cx="627" cy="477" r="312" fill="#060a1b"/><circle cx="627" cy="477" r="309" fill="none" stroke="url(#rim)" stroke-width="3"/></g>
<g id="stars"></g><path id="cons" fill="none" stroke="${C}" stroke-width="1.4"/>
<path id="trail" style="filter:drop-shadow(0 0 4px rgba(27,166,207,.55))" fill="none" stroke="${C}" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round" d="${TRAIL}"/>
<g id="links"></g><g id="sats"></g>
<g id="wm" clip-path="url(#wc)" fill="none" stroke="currentColor" stroke-width="24" style="color:var(--ink)">${WORDMARK}</g><g id="ws"></g>
<g mask="url(#gm)"><rect id="gl" y="880" width="110" height="150" fill="url(#gg)"/></g></svg>`;
    const $ = (id) => stageEl.querySelector("#" + id);
    const mk = (t, a, p) => { const e = document.createElementNS(NS, t); for (const k in a) e.setAttribute(k, a[k]); p.appendChild(e); return e; };
    const items = [[475, 252, 20, C, 1], [424, 667, 14, C, 1], [783, 236, 15, W, 1], [881, 383, 11, W, 1], [796, 674, 18, W, 1], [384, 617, 8, W, 1],
      [535, 208, 3.5, C], [392, 308, 5.5, C], [428, 291, 2.5, C], [882, 586, 4.5, C], [738, 741, 3.5, C], [849, 636, 2.5, C], [906, 421, 3, C],
      [501, 220, 3, W], [738, 228, 2.5, W], [840, 288, 4.5, W], [840, 320, 3, W], [874, 332, 3, W], [375, 381, 3, W], [355, 421, 3, W], [353, 535, 3, W],
      [905, 564, 3, W], [467, 692, 3, W], [489, 716, 3, W], [693, 752, 4, W], [741, 704, 2.5, W], [782, 716, 3, W], [445, 703, 2, W], [815, 254, 2, W], [913, 481, 2, W]];
    const sg = $("stars");
    items.forEach((it) => { it.e = it[4] ? mk("path", { d: sp(it[2]), fill: it[3] }, sg) : mk("circle", { r: it[2], fill: it[3] }, sg); it.a = Math.atan2(it[1] - cy, it[0] - cx); });
    const order = [...items].sort((a, b) => a.a - b.a); order.forEach((it, i) => (it.d = 900 + i * 55));
    const pts = order.filter((it) => it[4] || it[3] === C);
    const cons = $("cons"); cons.setAttribute("d", "M" + pts.map((p) => p[0] + "," + p[1]).join("L") + "Z");
    const cLen = cons.getTotalLength(); cons.setAttribute("stroke-dasharray", cLen);
    const ws = [492, 560].map((x) => ({ x, e: mk("path", { d: sp(20), fill: C }, $("ws")) }));
    const trail = $("trail"), planet = $("planet"), wcr = $("wcr"), halo = $("haloc"), gl = $("gl");
    const dust = [...Array(18)].map((_, i) => { const a = i * 2.399, r = 330 + (i * 53 % 140); return { x: cx + Math.cos(a) * r * 1.18, y: cy + Math.sin(a) * r * 0.95, ph: i * 1.7, e: mk("circle", { r: 1.4 + (i % 4) * 0.6, fill: i % 3 ? C : "#8fe3fb", opacity: 0 }, $("dust")) }; });
    const LT = trail.getTotalLength(), L4 = $("arc").getTotalLength(), LTOT = LT + L4, TAIL = 230;
    const N = 3, GAP = LTOT / N, SZ = [13, 8.5, 6.5];
    const d0 = TRAIL; const sp0 = mk("path", { d: d0.slice(0, d0.indexOf("L540,398") + 8), fill: "none" }, $("ws"));
    const spikeS = sp0.getTotalLength(); sp0.remove();
    const sats = [...Array(N)].map((_, i) => {
      const R = SZ[i], c = mk("path", { d: TRAIL, fill: "none", stroke: i ? "#7fdcf7" : "#a6ecff", "stroke-width": i ? 4 : 7, "stroke-linecap": "round", "stroke-linejoin": "round", "stroke-dasharray": TAIL * (i ? 0.7 : 1) + " " + LT * 2, opacity: 0 }, $("sats"));
      const g = mk("g", { opacity: 0 }, $("sats")); mk("circle", { r: R * 2, fill: C, opacity: 0.2 }, g);
      const b = mk("g", {}, g); mk("line", { y1: -R * 1.5, y2: R * 1.5, stroke: C, "stroke-width": R * 0.12 }, b);
      [-1, 1].forEach((k) => mk("rect", { x: -R * 0.5, y: k < 0 ? -R * 2.9 : R * 1.5, width: R, height: R * 1.4, rx: R * 0.18, fill: "#8fe3fb", stroke: C, "stroke-width": R * 0.12 }, b));
      mk("circle", { r: R, fill: C }, b); mk("circle", { cx: -R * 0.3, cy: -R * 0.3, r: R * 0.28, fill: "#fff", opacity: 0.7 }, b);
      return { g, c, b };
    });
    const lk = [0, 1, 2].map(() => mk("line", { stroke: C, "stroke-width": 1.6, "stroke-dasharray": "3 7", opacity: 0 }, $("links")));
    const rp = [0, 1, 2].map(() => mk("circle", { cx, cy, r: 312, fill: "none", stroke: C, "stroke-width": 3, opacity: 0 }, $("rip")));
    trail.setAttribute("stroke-dasharray", LT + " " + LT);
    const T0 = 1700, V1 = 300, V2 = 330, D1 = LTOT / V1 * 1000;
    const cl = (v) => Math.min(1, Math.max(0, v)), eo = (x) => 1 - Math.pow(1 - x, 3), eio = (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
    const eb = (x) => { const a = 1.70158, b = a + 1; return 1 + b * Math.pow(x - 1, 3) + a * Math.pow(x - 1, 2); };
    function frame(t) {
      const p = eo(cl(t / 900));
      planet.setAttribute("transform", `translate(${cx} ${cy}) scale(${(0.86 + 0.14 * p) * (1 + 0.005 * p * Math.sin(t / 650))}) translate(${-cx} ${-cy})`);
      planet.setAttribute("opacity", p); halo.setAttribute("opacity", p * (0.8 + 0.2 * Math.sin(t / 650)));
      items.forEach((it) => { const k = t - it.d, sc = eb(cl(k / 420)) * (it[4] ? 1 + 0.1 * Math.sin(t / 380 + it[0]) : 1); it.e.setAttribute("transform", `translate(${it[0]} ${it[1]}) scale(${sc})`); it.e.setAttribute("opacity", cl(k / 150)); });
      cons.setAttribute("stroke-dashoffset", cLen * (1 - eio(cl((t - 1000) / 1300))));
      dust.forEach((d) => { d.e.setAttribute("cx", d.x + Math.sin(t / 2600 + d.ph) * 14); d.e.setAttribute("cy", d.y + Math.cos(t / 3100 + d.ph) * 12); d.e.setAttribute("opacity", cl((t - 600) / 1500) * (0.18 + 0.17 * Math.sin(t / 900 + d.ph))); });
      cons.setAttribute("opacity", (t < 2300 ? 1 : 1 - cl((t - 2300) / 600)) * 0.6);
      let sr = -1; if (t >= T0) { const d = (t - T0) / 1000, d1 = D1 / 1000; sr = d < d1 ? d * V1 : LTOT + (d - d1) * V2; }
      const rev = sr < 0 ? 0 : Math.min(sr, LT); trail.setAttribute("opacity", rev > 1 ? 1 : 0); trail.setAttribute("stroke-dashoffset", LT - rev);
      const Pp = [];
      sats.forEach((o, i) => {
        const raw = sr - i * GAP; if (raw < 0) { o.g.setAttribute("opacity", 0); o.c.setAttribute("opacity", 0); Pp[i] = null; return; }
        const s = raw % LTOT; o.c.setAttribute("opacity", s <= LT + TAIL ? 0.85 : 0); o.c.setAttribute("stroke-dashoffset", TAIL * (i ? 0.7 : 1) - s);
        if (s <= LT) { const q = trail.getPointAtLength(s), q2 = trail.getPointAtLength(Math.min(s + 2, LT)), a = Math.atan2(q2.y - q.y, q2.x - q.x) * 180 / Math.PI;
          o.g.setAttribute("transform", `translate(${q.x} ${q.y})`); o.b.setAttribute("transform", `rotate(${a})`); o.g.setAttribute("opacity", 1); Pp[i] = q; }
        else { o.g.setAttribute("opacity", 0); Pp[i] = null; }
        const age = raw - spikeS; if (age >= 0) { const m = age % LTOT; rp[i].setAttribute("r", 312 + m * 0.22); rp[i].setAttribute("opacity", m < 650 ? (1 - m / 650) * 0.5 : 0); }
      });
      lk.forEach((l, j) => { const a = Pp[j], b = Pp[(j + 1) % N]; if (a && b) { l.setAttribute("x1", a.x); l.setAttribute("y1", a.y); l.setAttribute("x2", b.x); l.setAttribute("y2", b.y); l.setAttribute("opacity", 0.55); l.setAttribute("stroke-dashoffset", -t / 30); } else l.setAttribute("opacity", 0); });
      wcr.setAttribute("width", 780 * eio(cl((t - 3500) / 1200)));
      const gp = t > 6000 ? ((t - 6000) % 4800) / 1300 : 2; gl.setAttribute("transform", `translate(${210 + gp * 820} 955) skewX(-20) translate(0 -955)`);
      ws.forEach((o, i) => { const k = t - 4600 - i * 150, sc = eb(cl(k / 450)) * (1 + 0.1 * Math.sin(t / 330 + i * 2)); o.e.setAttribute("transform", `translate(${o.x} 863) scale(${sc})`); o.e.setAttribute("opacity", cl(k / 150)); });
    }
    const total = opts.reduced ? 1 : opts.duration || 7200;
    if (opts.reduced) { frame(9000); setTimeout(onDone, 1100); return { stop() {} }; }
    let t0 = performance.now(), stopped = false;
    (function loop(n) { if (stopped) return; const t = n - t0; frame(t); if (t >= total) { stopped = true; onDone(); return; } requestAnimationFrame(loop); })(t0);
    return { stop() { stopped = true; } };
  }

  window.Brand = { mark, logo, icon, intro, ornaments, ICONS: P };
  ornaments();
})();
