/* =====================================================================
   BÖVD · Body3D – interactive 3D human model (WebGL 1, no external library)
   - procedural articulated human (skeleton + ellipsoid parts) with internal organs
   - orbit (drag), zoom (wheel / pinch), touch, keyboard, double-click reset
   - colour-ID picking of organs/regions, camera fly-to, highlight + x-ray skin
   - keyframed instructional animations for each exam with props
   Three.js could not be bundled offline, so this small engine is self-contained.
   If WebGL is unavailable the caller falls back to the 2-D SVG body map.
   ===================================================================== */
"use strict";
(function () {
  // ------------------------------------------------------------ math
  const M = {
    ident: () => [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
    mul(a, b) { const o = new Array(16); for (let c = 0; c < 4; c++) for (let r = 0; r < 4; r++) { let s = 0; for (let k = 0; k < 4; k++) s += a[k * 4 + r] * b[c * 4 + k]; o[c * 4 + r] = s; } return o; },
    trans: (x, y, z) => [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, x, y, z, 1],
    scale: (x, y, z) => [x, 0, 0, 0, 0, y, 0, 0, 0, 0, z, 0, 0, 0, 0, 1],
    rx(d) { const r = d * Math.PI / 180, c = Math.cos(r), s = Math.sin(r); return [1, 0, 0, 0, 0, c, s, 0, 0, -s, c, 0, 0, 0, 0, 1]; },
    ry(d) { const r = d * Math.PI / 180, c = Math.cos(r), s = Math.sin(r); return [c, 0, -s, 0, 0, 1, 0, 0, s, 0, c, 0, 0, 0, 0, 1]; },
    rz(d) { const r = d * Math.PI / 180, c = Math.cos(r), s = Math.sin(r); return [c, s, 0, 0, -s, c, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]; },
    persp(fov, asp, n, f) { const t = 1 / Math.tan(fov / 2); return [t / asp, 0, 0, 0, 0, t, 0, 0, 0, 0, (f + n) / (n - f), -1, 0, 0, 2 * f * n / (n - f), 0]; },
    lookAt(e, c, u) {
      let z = [e[0] - c[0], e[1] - c[1], e[2] - c[2]]; let l = Math.hypot(...z); z = z.map((v) => v / l);
      let x = [u[1] * z[2] - u[2] * z[1], u[2] * z[0] - u[0] * z[2], u[0] * z[1] - u[1] * z[0]]; l = Math.hypot(...x); x = x.map((v) => v / l);
      const y = [z[1] * x[2] - z[2] * x[1], z[2] * x[0] - z[0] * x[2], z[0] * x[1] - z[1] * x[0]];
      return [x[0], y[0], z[0], 0, x[1], y[1], z[1], 0, x[2], y[2], z[2], 0, -(x[0] * e[0] + x[1] * e[1] + x[2] * e[2]), -(y[0] * e[0] + y[1] * e[1] + y[2] * e[2]), -(z[0] * e[0] + z[1] * e[1] + z[2] * e[2]), 1];
    },
    normal3(m) { // inverse-transpose of upper 3x3
      const a = m[0], b = m[4], c = m[8], d = m[1], e = m[5], f = m[9], g = m[2], h = m[6], i = m[10];
      const A = e * i - f * h, B = -(d * i - f * g), C = d * h - e * g, det = a * A + b * B + c * C || 1e-9;
      const inv = [A, -(b * i - c * h), b * f - c * e, B, a * i - c * g, -(a * f - c * d), C, -(a * h - b * g), a * e - b * d].map((v) => v / det);
      return [inv[0], inv[3], inv[6], inv[1], inv[4], inv[7], inv[2], inv[5], inv[8]];
    },
    apply(m, p) { return [m[0] * p[0] + m[4] * p[1] + m[8] * p[2] + m[12], m[1] * p[0] + m[5] * p[1] + m[9] * p[2] + m[13], m[2] * p[0] + m[6] * p[1] + m[10] * p[2] + m[14]]; },
  };
  const lerp = (a, b, t) => a + (b - a) * t;
  const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

  // ------------------------------------------------------------ meshes
  function sphere(seg = 24, ring = 16) {
    const p = [], n = [], idx = [];
    for (let r = 0; r <= ring; r++) { const v = r / ring, th = v * Math.PI; for (let s = 0; s <= seg; s++) { const u = s / seg, ph = u * 2 * Math.PI; const x = Math.sin(th) * Math.cos(ph), y = Math.cos(th), z = Math.sin(th) * Math.sin(ph); p.push(x, y, z); n.push(x, y, z); } }
    for (let r = 0; r < ring; r++) for (let s = 0; s < seg; s++) { const a = r * (seg + 1) + s, b = a + seg + 1; idx.push(a, b, a + 1, b, b + 1, a + 1); }
    return { p, n, idx };
  }
  function cylinder(seg = 24) { // radius 1, y from -1 to 1, with caps
    const p = [], n = [], idx = [];
    for (let s = 0; s <= seg; s++) { const a = s / seg * 2 * Math.PI, x = Math.cos(a), z = Math.sin(a); p.push(x, -1, z, x, 1, z); n.push(x, 0, z, x, 0, z); }
    for (let s = 0; s < seg; s++) { const a = s * 2; idx.push(a, a + 2, a + 1, a + 1, a + 2, a + 3); }
    for (const y of [-1, 1]) { const c = p.length / 3; p.push(0, y, 0); n.push(0, y, 0); for (let s = 0; s <= seg; s++) { const a = s / seg * 2 * Math.PI; p.push(Math.cos(a), y, Math.sin(a)); n.push(0, y, 0); } for (let s = 0; s < seg; s++) idx.push(c, c + 1 + s, c + 2 + s); }
    return { p, n, idx };
  }
  function box() {
    const p = [], n = [], idx = [];
    const faces = [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]];
    faces.forEach((f) => { const [a, b] = f[0] ? [[0, 1, 0], [0, 0, 1]] : f[1] ? [[1, 0, 0], [0, 0, 1]] : [[1, 0, 0], [0, 1, 0]]; const c = p.length / 3;
      for (const [s, t] of [[-1, -1], [1, -1], [1, 1], [-1, 1]]) { p.push(f[0] + s * a[0] + t * b[0], f[1] + s * a[1] + t * b[1], f[2] + s * a[2] + t * b[2]); n.push(...f); }
      idx.push(c, c + 1, c + 2, c, c + 2, c + 3); });
    return { p, n, idx };
  }

  // ------------------------------------------------------------ skeleton
  const J = { // name: [parent, offset]
    root: [null, [0, 0.95, 0]], spine: ["root", [0, 0.1, 0]], chest: ["spine", [0, 0.25, 0]], neck: ["chest", [0, 0.22, 0]], head: ["neck", [0, 0.1, 0]],
    shL: ["chest", [0.19, 0.17, 0]], elL: ["shL", [0, -0.29, 0]], wrL: ["elL", [0, -0.26, 0]],
    shR: ["chest", [-0.19, 0.17, 0]], elR: ["shR", [0, -0.29, 0]], wrR: ["elR", [0, -0.26, 0]],
    hipL: ["root", [0.1, -0.05, 0]], knL: ["hipL", [0, -0.42, 0]], anL: ["knL", [0, -0.42, 0]],
    hipR: ["root", [-0.1, -0.05, 0]], knR: ["hipR", [0, -0.42, 0]], anR: ["knR", [0, -0.42, 0]],
  };
  const ORDER = Object.keys(J);
  const SKIN = [ // [joint, centre offset, radii, pick-region]
    ["root", [0, 0, 0], [0.17, 0.12, 0.11], "skin"], ["spine", [0, 0.1, 0], [0.15, 0.15, 0.1], "skin"], ["chest", [0, 0.08, 0], [0.19, 0.21, 0.12], "skin"],
    ["neck", [0, 0.03, 0], [0.05, 0.07, 0.05], "skin"], ["head", [0, 0.1, 0], [0.095, 0.12, 0.105], "skin"],
    ["shL", [0, -0.145, 0], [0.055, 0.165, 0.055], "bones"], ["elL", [0, -0.13, 0], [0.045, 0.145, 0.045], "bones"], ["wrL", [0, -0.07, 0.01], [0.04, 0.075, 0.025], "bones"],
    ["shR", [0, -0.145, 0], [0.055, 0.165, 0.055], "bones"], ["elR", [0, -0.13, 0], [0.045, 0.145, 0.045], "bones"], ["wrR", [0, -0.07, 0.01], [0.04, 0.075, 0.025], "bones"],
    ["hipL", [0, -0.21, 0], [0.075, 0.235, 0.075], "bones"], ["knL", [0, -0.21, 0], [0.055, 0.225, 0.055], "bones"], ["anL", [0, -0.04, 0.06], [0.045, 0.035, 0.11], "bones"],
    ["hipR", [0, -0.21, 0], [0.075, 0.235, 0.075], "bones"], ["knR", [0, -0.21, 0], [0.055, 0.225, 0.055], "bones"], ["anR", [0, -0.04, 0.06], [0.045, 0.035, 0.11], "bones"],
  ];
  const ORGANS = [ // [region, joint, centre, radii, mesh]
    ["brain", "head", [0, 0.13, -0.005], [0.075, 0.06, 0.085]],
    ["eyes", "head", [0.035, 0.11, 0.088], [0.018, 0.018, 0.018]], ["eyes", "head", [-0.035, 0.11, 0.088], [0.018, 0.018, 0.018]],
    ["lungs", "chest", [0.08, 0.07, 0], [0.07, 0.13, 0.07]], ["lungs", "chest", [-0.08, 0.07, 0], [0.07, 0.13, 0.07]],
    ["heart", "chest", [0.03, 0.02, 0.035], [0.05, 0.06, 0.045]],
    ["kidneys", "spine", [0.06, 0.02, -0.05], [0.03, 0.05, 0.025]], ["kidneys", "spine", [-0.06, 0.02, -0.05], [0.03, 0.05, 0.025]],
    ["bones", "hipL", [0, -0.21, 0], [0.022, 0.2, 0.022]], ["bones", "knL", [0, -0.21, 0], [0.018, 0.2, 0.018]],
    ["bones", "hipR", [0, -0.21, 0], [0.022, 0.2, 0.022]], ["bones", "knR", [0, -0.21, 0], [0.018, 0.2, 0.018]],
    ["bones", "shL", [0, -0.145, 0], [0.018, 0.14, 0.018]], ["bones", "shR", [0, -0.145, 0], [0.018, 0.14, 0.018]],
    ["bones", "spine", [0, 0.1, -0.06], [0.02, 0.2, 0.02]],
    ["blood", "elL", [0.015, -0.13, 0.025], [0.009, 0.13, 0.009]], ["blood", "elR", [-0.015, -0.13, 0.025], [0.009, 0.13, 0.009]],
    ["blood", "shL", [0.02, -0.145, 0.03], [0.01, 0.15, 0.01]], ["blood", "shR", [-0.02, -0.145, 0.03], [0.01, 0.15, 0.01]],
  ];
  const REGIONS = ["brain", "eyes", "heart", "lungs", "bones", "kidneys", "blood", "skin"];
  const FOCUS = { brain: ["head", [0, 0.12, 0], 0.7], eyes: ["head", [0, 0.11, 0.08], 0.55], heart: ["chest", [0.03, 0.02, 0.03], 0.8],
    lungs: ["chest", [0, 0.06, 0], 0.95], kidneys: ["spine", [0, 0.02, -0.05], 0.9], bones: ["root", [0, -0.3, 0], 2.4],
    blood: ["shL", [0, -0.3, 0], 1.2], skin: ["root", [0, 0.1, 0], 2.6], body: ["root", [0, -0.05, 0], 3.1] };
  const BASE = { brain: [0.93, 0.75, 0.82], eyes: [0.98, 0.98, 1], heart: [0.85, 0.3, 0.35], lungs: [0.95, 0.62, 0.66], kidneys: [0.6, 0.32, 0.3],
    bones: [0.95, 0.93, 0.86], blood: [0.75, 0.15, 0.2] };
  const STATUS = { green: [0.12, 0.62, 0.36], yellow: [0.92, 0.62, 0.05], red: [0.86, 0.22, 0.25] };

  // ------------------------------------------------------------ poses & animations
  const rest = () => ({ pos: [0, 0, 0], rot: {} });
  const seated = (extra = {}) => ({ pos: [0, -0.45, 0], rot: { hipL: [-88, 0, 0], hipR: [-88, 0, 0], knL: [88, 0, 0], knR: [88, 0, 0], ...extra } });
  const ARM_ON_REST = { shL: [-10, 0, 15], elL: [-80, 0, 0] }; // solved by FK search: mid upper arm ≈ heart level, forearm on rest
  const ANIMS = {
    bp: { title: "ضغط الدم", steps: [
      { ar: "اجلس على كرسي بظهر مستقيم ومسنود، والقدمان على الأرض (أو مثبتتان بحلقات القدم في انعدام الجاذبية).", pose: seated(), props: ["chair", "loops"], cam: [35, 8, "body", 3.2] },
      { ar: "ضع الساعد الأيسر على المسند بحيث يكون منتصف العضد بمستوى القلب، والكف للأعلى.", pose: seated(ARM_ON_REST), props: ["chair", "rest"], cam: [60, 5, "heart", 1.4] },
      { ar: "لُفّ الكفة على العضد العاري كما في تعليمات الجهاز، بإحكام مناسب.", pose: seated(ARM_ON_REST), props: ["chair", "rest", "cuff"], cam: [70, 10, "shL", 0.9], cuffIn: true },
      { ar: "ابدأ القياس وابقَ ساكنًا دون كلام، والساقان غير متقاطعتين، حتى تنتهي القراءة.", pose: seated(ARM_ON_REST), props: ["chair", "rest", "cuff"], cam: [40, 12, "body", 2.6], pulse: true },
    ] },
    spo2: { title: "تشبع الأكسجين", steps: [
      { ar: "اجلس مستقيمًا واجعل اليد دافئة ومسنودة على المسند قرب مستوى القلب.", pose: seated(ARM_ON_REST), props: ["chair", "rest"], cam: [45, 8, "body", 2.8] },
      { ar: "ضع جهاز الإصبع على السبابة، والظفر بلا طلاء.", pose: seated(ARM_ON_REST), props: ["chair", "rest", "oxi"], cam: [80, 15, "wrL", 0.7] },
      { ar: "ابقَ ساكنًا حتى تستقر القراءة ثم سجّلها.", pose: seated(ARM_ON_REST), props: ["chair", "rest", "oxi"], cam: [45, 8, "body", 2.6], pulse: true },
    ] },
    temp: { title: "الحرارة", steps: [
      { ar: "اجلس مستقيمًا واسترح قبل القياس.", pose: seated(), props: ["chair"], cam: [30, 6, "body", 3] },
      { ar: "ضع مقياس الحرارة حسب نوعه وتعليماته (مثل تحت اللسان مع إغلاق الفم).", pose: seated({ shR: [-55, 60, -40], elR: [-125, 0, 0] }), props: ["chair", "thermo"], cam: [-35, 6, "head", 1.3] },
      { ar: "ابقَ ساكنًا حتى ينتهي القياس.", pose: seated({ shR: [-55, 60, -40], elR: [-125, 0, 0] }), props: ["chair", "thermo"], cam: [35, 6, "body", 2.6] },
    ] },
    vision: { title: "حدة البصر", steps: [
      { ar: "اجلس على مسافة الاختبار المعايرة أمام الشاشة، والرأس مستقيم.", pose: seated(), props: ["chair", "chart"], cam: [140, 10, "body", 3.6] },
      { ar: "غطِّ العين اليسرى براحة اليد دون ضغط، واقرأ الأسطر من الأعلى.", pose: seated({ shL: [-120, 60, -60], elL: [-110, 0, 0] }), props: ["chair", "chart"], cam: [25, 4, "head", 1.3] },
      { ar: "ثم غطِّ العين اليمنى وكرّر القراءة.", pose: seated({ shR: [-120, -60, 60], elR: [-110, 0, 0] }), props: ["chair", "chart"], cam: [-25, 4, "head", 1.3] },
    ] },
    stand: { title: "اختبار الوقوف بعد الهبوط", steps: [
      { ar: "بعد الهبوط: اجلس 5 دقائق وسجّل النبض والضغط.", pose: seated(), props: ["chair"], cam: [45, 8, "body", 3.2] },
      { ar: "تأكد من وجود مرافق، ثم قف ببطء.", pose: { pos: [0, -0.2, 0], rot: { hipL: [-40, 0, 0], hipR: [-40, 0, 0], knL: [55, 0, 0], knR: [55, 0, 0], spine: [-15, 0, 0] } }, props: ["chair"], cam: [70, 8, "body", 3.2] },
      { ar: "قف ساكنًا وسجّل عند الدقيقة 1 و3. اجلس فورًا إن شعرت بدوار.", pose: rest(), props: ["chair"], cam: [40, 8, "body", 3.4], pulse: true },
    ] },
    micro: { title: "التثبيت في انعدام الجاذبية", steps: [
      { ar: "في انعدام الجاذبية لا توجد وضعية وقوف: ثبّت قدميك بحلقات القدم أو الحزام قبل أي قياس.", pose: { pos: [0, 0.05, 0], rot: { hipL: [-20, 0, 0], hipR: [-20, 0, 0], knL: [35, 0, 0], knR: [35, 0, 0], shL: [-35, 0, 25], shR: [-35, 0, -25], elL: [-30, 0, 0], elR: [-30, 0, 0] } }, props: ["loops"], cam: [30, 5, "body", 3.4], float: true },
      { ar: "انتقال السوائل نحو الرأس (≈ 2 لتر) يجعل الوجه منتفخًا قليلًا؛ لذلك نقارن قراءاتك بخط أساسك أثناء الرحلة.", pose: { pos: [0, 0.05, 0], rot: { hipL: [-20, 0, 0], hipR: [-20, 0, 0], knL: [35, 0, 0], knR: [35, 0, 0] } }, props: ["loops"], cam: [10, 4, "head", 1.0], float: true, fluid: true },
    ] },
  };
  const PROPS = { // [joint|null, centre, radii/size, mesh, colour, alpha]
    chair: [[null, [0, 0.355, -0.05], [0.24, 0.025, 0.24], "box", [0.36, 0.42, 0.55]], [null, [0, 0.66, -0.27], [0.24, 0.3, 0.025], "box", [0.36, 0.42, 0.55]],
      [null, [0.2, 0.17, 0.15], [0.02, 0.17, 0.02], "box", [0.3, 0.34, 0.45]], [null, [-0.2, 0.17, 0.15], [0.02, 0.17, 0.02], "box", [0.3, 0.34, 0.45]],
      [null, [0.2, 0.17, -0.25], [0.02, 0.17, 0.02], "box", [0.3, 0.34, 0.45]], [null, [-0.2, 0.17, -0.25], [0.02, 0.17, 0.02], "box", [0.3, 0.34, 0.45]]],
    rest: [[null, [0.29, 0.7, 0.22], [0.075, 0.018, 0.2], "box", [0.78, 0.66, 0.42]], [null, [0.29, 0.35, 0.22], [0.025, 0.35, 0.025], "box", [0.62, 0.52, 0.34]]],
    cuff: [["shL", [0, -0.17, 0], [0.068, 0.07, 0.068], "cyl", [0.11, 0.65, 0.81]]],
    oxi: [["wrL", [0, -0.14, 0.02], [0.022, 0.03, 0.026], "box", [0.11, 0.65, 0.81]]],
    thermo: [["head", [0, 0.03, 0.12], [0.006, 0.006, 0.07], "box", [0.9, 0.9, 0.95]]],
    chart: [[null, [0, 1.05, 2.3], [0.4, 0.5, 0.02], "box", [0.98, 0.98, 0.98]], [null, [0, 1.25, 2.27], [0.12, 0.05, 0.005], "box", [0.05, 0.09, 0.2]], [null, [0, 1.08, 2.27], [0.08, 0.035, 0.005], "box", [0.05, 0.09, 0.2]], [null, [0, 0.94, 2.27], [0.05, 0.022, 0.005], "box", [0.05, 0.09, 0.2]]],
    loops: [[null, [0.1, 0.03, 0.1], [0.07, 0.015, 0.12], "box", [0.85, 0.66, 0.36]], [null, [-0.1, 0.03, 0.1], [0.07, 0.015, 0.12], "box", [0.85, 0.66, 0.36]]],
  };

  // ------------------------------------------------------------ GL helpers
  const VS = `attribute vec3 p;attribute vec3 n;uniform mat4 P,V,Mo;uniform mat3 N;varying vec3 vn;varying vec3 vw;
    void main(){vec4 w=Mo*vec4(p,1.);vw=w.xyz;vn=normalize(N*n);gl_Position=P*V*w;}`;
  const FS = `precision mediump float;varying vec3 vn;varying vec3 vw;uniform vec3 col;uniform float a,glow,flat_;uniform vec3 eye;
    void main(){vec3 n=normalize(vn);vec3 L=normalize(vec3(.45,.8,.55));float d=max(dot(n,L),0.);
    float q=flat_>0.5?floor(d*3.+.5)/3.:d; float rim=pow(1.-max(dot(n,normalize(eye-vw)),0.),3.);
    vec3 c=col*(.42+.58*q)+vec3(.11,.65,.81)*rim*.35+col*glow; gl_FragColor=vec4(c,a);}`;
  const FS_ID = `precision mediump float;uniform vec3 col;void main(){gl_FragColor=vec4(col,1.);}`;

  function prog(gl, fs) {
    const mk = (t, s) => { const o = gl.createShader(t); gl.shaderSource(o, s); gl.compileShader(o); if (!gl.getShaderParameter(o, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(o)); return o; };
    const p = gl.createProgram(); gl.attachShader(p, mk(gl.VERTEX_SHADER, VS)); gl.attachShader(p, mk(gl.FRAGMENT_SHADER, fs)); gl.linkProgram(p);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));
    const u = {}; ["P", "V", "Mo", "N", "col", "a", "glow", "flat_", "eye"].forEach((k) => (u[k] = gl.getUniformLocation(p, k)));
    return { p, u, ap: gl.getAttribLocation(p, "p"), an: gl.getAttribLocation(p, "n") };
  }
  function upload(gl, m) {
    const b = (d, t, T) => { const o = gl.createBuffer(); gl.bindBuffer(t, o); gl.bufferData(t, new T(d), gl.STATIC_DRAW); return o; };
    return { p: b(m.p, gl.ARRAY_BUFFER, Float32Array), n: b(m.n, gl.ARRAY_BUFFER, Float32Array), i: b(m.idx, gl.ELEMENT_ARRAY_BUFFER, Uint16Array), c: m.idx.length };
  }

  // ------------------------------------------------------------ public component
  function supported() { try { const c = document.createElement("canvas"); return !!(c.getContext("webgl") || c.getContext("experimental-webgl")); } catch (e) { return false; } }

  function mount(host, opts = {}) {
    const canvas = document.createElement("canvas");
    canvas.className = "b3d-canvas"; canvas.tabIndex = 0;
    canvas.setAttribute("role", "img"); canvas.setAttribute("aria-label", opts.label || "نموذج ثلاثي الأبعاد لجسم الإنسان – اسحب للتدوير، عجلة الفأرة للتكبير");
    host.appendChild(canvas);
    const gl = canvas.getContext("webgl", { antialias: true, preserveDrawingBuffer: true, alpha: true });
    if (!gl) throw new Error("WebGL unavailable");
    const pr = prog(gl, FS), pid = prog(gl, FS_ID);
    const mesh = { sph: upload(gl, sphere()), cyl: upload(gl, cylinder()), box: upload(gl, box()) };
    const reduce = () => document.body.classList.contains("reduce-motion") || matchMedia("(prefers-reduced-motion: reduce)").matches;
    const S = { yaw: 25, pitch: 6, dist: 3.1, target: [0, 0.9, 0], status: {}, selected: null, pose: rest(), props: [], anim: null,
      fly: null, xray: 0.0, dpr: Math.min(2, devicePixelRatio || 1), dirty: true, t0: performance.now(), frameMs: [], destroyed: false, extras: {} };

    function world(pose) { // joint world matrices
      const W = {};
      for (const j of ORDER) {
        const [par, off] = J[j]; const r = pose.rot[j] || [0, 0, 0];
        let local = M.trans(...off); if (j === "root") local = M.trans(off[0] + pose.pos[0], off[1] + pose.pos[1], off[2] + pose.pos[2]);
        local = M.mul(local, M.mul(M.ry(r[1]), M.mul(M.rx(r[0]), M.rz(r[2]))));
        W[j] = par ? M.mul(W[par], local) : local;
      }
      return W;
    }
    function jointPos(j, off = [0, 0, 0]) { if (!j) return off; return M.apply(world(S.pose)[j], off); }

    function draws(W) {
      const out = [];
      const sel = S.selected, has = (r) => (S.status[r] && STATUS[S.status[r]]) || null;
      if (!S.anim) ORGANS.forEach(([reg, j, c, r]) => {
        const m = M.mul(W[j], M.mul(M.trans(...c), M.scale(...r)));
        let col = has(reg) || BASE[reg]; if (has(reg)) col = col.map((v, i) => v * 0.75 + BASE[reg][i] * 0.25);
        const dim = sel && sel !== reg && sel !== "skin" && sel !== "body" ? 0.45 : 1;
        out.push({ m, mesh: "sph", col: col.map((v) => v * dim), a: 1, glow: sel === reg ? 0.25 + 0.2 * Math.sin(performance.now() / 260) : 0, id: REGIONS.indexOf(reg) + 1, organ: true });
      });
      const skinCol = S.anim ? [0.58, 0.74, 0.86] : has("skin") ? has("skin").map((v) => v * 0.35 + 0.45) : [0.5, 0.7, 0.84];
      const skinA = S.anim ? 0.94 : sel && sel !== "skin" && sel !== "body" ? 0.16 : 0.42;
      SKIN.forEach(([j, c, r, reg]) => out.push({ m: M.mul(W[j], M.mul(M.trans(...c), M.scale(...r))), mesh: "sph", col: skinCol, a: skinA, glow: sel === "skin" ? 0.15 : 0, id: REGIONS.indexOf(reg) + 1, skin: true }));
      S.props.forEach((name) => (PROPS[name] || []).forEach(([j, c, r, kind, col]) => {
        let sc = r; if (name === "cuff" && S.extras.cuffScale != null) sc = r.map((v, i) => (i === 1 ? v : v * S.extras.cuffScale));
        const base = j ? W[j] : M.ident(); const rot = kind === "cyl" ? M.ident() : M.ident();
        out.push({ m: M.mul(base, M.mul(M.trans(...c), M.mul(rot, M.scale(...sc)))), mesh: kind === "cyl" ? "cyl" : "box", col, a: 1, glow: 0, prop: true });
      }));
      return out;
    }
    function cam() {
      const y = S.yaw * Math.PI / 180, p = S.pitch * Math.PI / 180;
      const e = [S.target[0] + S.dist * Math.sin(y) * Math.cos(p), S.target[1] + S.dist * Math.sin(p), S.target[2] + S.dist * Math.cos(y) * Math.cos(p)];
      return { e, V: M.lookAt(e, S.target, [0, 1, 0]), P: M.persp(0.62, canvas.width / canvas.height, 0.05, 30) };
    }
    function drawList(list, P, V, e, idPass) {
      const g = idPass ? pid : pr; gl.useProgram(g.p);
      gl.uniformMatrix4fv(g.u.P, false, P); gl.uniformMatrix4fv(g.u.V, false, V);
      if (!idPass) { gl.uniform3fv(g.u.eye, e); gl.uniform1f(g.u.flat_, 1); }
      for (const d of list) {
        const ms = mesh[d.mesh];
        gl.bindBuffer(gl.ARRAY_BUFFER, ms.p); gl.enableVertexAttribArray(g.ap); gl.vertexAttribPointer(g.ap, 3, gl.FLOAT, false, 0, 0);
        if (g.an >= 0) { gl.bindBuffer(gl.ARRAY_BUFFER, ms.n); gl.enableVertexAttribArray(g.an); gl.vertexAttribPointer(g.an, 3, gl.FLOAT, false, 0, 0); }
        gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ms.i);
        gl.uniformMatrix4fv(g.u.Mo, false, d.m);
        if (g.u.N) gl.uniformMatrix3fv(g.u.N, false, M.normal3(d.m));
        if (idPass) gl.uniform3f(g.u.col, d.id / 255, 0, 0);
        else { gl.uniform3fv(g.u.col, d.col); gl.uniform1f(g.u.a, d.a); gl.uniform1f(g.u.glow, d.glow); }
        gl.drawElements(gl.TRIANGLES, ms.c, gl.UNSIGNED_SHORT, 0);
      }
    }
    function resize() {
      const w = host.clientWidth || 300, h = host.clientHeight || 300;
      const W2 = Math.round(w * S.dpr), H2 = Math.round(h * S.dpr);
      if (canvas.width !== W2 || canvas.height !== H2) { canvas.width = W2; canvas.height = H2; }
    }
    function render() {
      const t0 = performance.now();
      resize(); gl.viewport(0, 0, canvas.width, canvas.height);
      gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
      gl.enable(gl.DEPTH_TEST); gl.enable(gl.CULL_FACE);
      const W = world(S.pose), list = draws(W), { e, V, P } = cam();
      gl.disable(gl.BLEND); gl.depthMask(true);
      drawList(list.filter((d) => !d.skin), P, V, e, false);
      gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA); gl.depthMask(false);
      drawList(list.filter((d) => d.skin), P, V, e, false);
      gl.depthMask(true); gl.disable(gl.BLEND);
      S.frameMs.push(performance.now() - t0); if (S.frameMs.length > 120) S.frameMs.shift();
    }
    function pick(cx, cy) {
      const rect = canvas.getBoundingClientRect(); const x = Math.round((cx - rect.left) * S.dpr), y = Math.round((rect.bottom - cy) * S.dpr);
      const W = world(S.pose), list = draws(W), { e, V, P } = cam(); const px = new Uint8Array(4);
      gl.viewport(0, 0, canvas.width, canvas.height); gl.disable(gl.BLEND); gl.enable(gl.DEPTH_TEST);
      for (const pass of [list.filter((d) => d.organ), list.filter((d) => d.skin)]) {
        gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
        drawList(pass, P, V, e, true); gl.readPixels(x, y, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px);
        if (px[0]) { S.dirty = true; return REGIONS[px[0] - 1]; }
      }
      S.dirty = true; return null;
    }

    // -------------------------------------------------------- camera control
    function focusRegion(reg, instant) {
      const f = FOCUS[reg] || FOCUS.body; const tgt = jointPos(f[0], f[1]);
      const to = { target: tgt, dist: f[2], yaw: S.yaw, pitch: Math.min(25, Math.max(-10, S.pitch)) };
      setView(to, instant);
    }
    function setView(to, instant) {
      if (instant || reduce()) { Object.assign(S, to); S.fly = null; S.dirty = true; return; }
      S.fly = { from: { target: [...S.target], dist: S.dist, yaw: S.yaw, pitch: S.pitch }, to, t0: performance.now(), dur: 650 };
    }
    // Pointer Events for mouse, pen and touch: 1 pointer = rotate / tap-to-pick, 2 pointers = pinch zoom
    let drag = null, pinch = null; const ptrs = new Map();
    const spread = () => { const p = [...ptrs.values()]; return Math.hypot(p[0].x - p[1].x, p[0].y - p[1].y); };
    canvas.addEventListener("pointerdown", (e) => {
      try { canvas.setPointerCapture(e.pointerId); } catch (err) { /* synthetic or already released pointer */ }
      ptrs.set(e.pointerId, { x: e.clientX, y: e.clientY });
      if (ptrs.size === 2) { pinch = spread(); drag = null; } else if (ptrs.size === 1) drag = { x: e.clientX, y: e.clientY, moved: 0, id: e.pointerId };
    });
    canvas.addEventListener("pointermove", (e) => {
      if (ptrs.has(e.pointerId)) ptrs.set(e.pointerId, { x: e.clientX, y: e.clientY });
      if (pinch && ptrs.size === 2) { const d = spread(); if (d > 0) zoom(pinch / d); pinch = d; return; }
      if (!drag || pinch) return; const dx = e.clientX - drag.x, dy = e.clientY - drag.y; drag.moved += Math.abs(dx) + Math.abs(dy);
      S.yaw -= dx * 0.45; S.pitch = Math.max(-60, Math.min(70, S.pitch + dy * 0.35)); drag.x = e.clientX; drag.y = e.clientY; S.fly = null; S.dirty = true;
    });
    const up = (e) => {
      if (drag && drag.moved < 6 && !pinch && e.type === "pointerup") { const r = pick(e.clientX, e.clientY); select(r); }
      ptrs.delete(e.pointerId); if (ptrs.size < 2) pinch = null; drag = null;
    };
    canvas.addEventListener("pointerup", up); canvas.addEventListener("pointercancel", up);
    canvas.addEventListener("wheel", (e) => { e.preventDefault(); zoom(e.deltaY > 0 ? 1.1 : 0.9); }, { passive: false });
    canvas.addEventListener("dblclick", () => { select(null); });
    canvas.addEventListener("keydown", (e) => {
      const k = e.key; if (k === "ArrowLeft") S.yaw += 10; else if (k === "ArrowRight") S.yaw -= 10; else if (k === "ArrowUp") S.pitch = Math.min(70, S.pitch + 8);
      else if (k === "ArrowDown") S.pitch = Math.max(-60, S.pitch - 8); else if (k === "+" || k === "=") zoom(0.85); else if (k === "-") zoom(1.15);
      else if (k === "Escape" || k === "0") select(null); else return; e.preventDefault(); S.dirty = true;
    });
    function zoom(f) { S.dist = Math.max(0.35, Math.min(6, S.dist * f)); S.fly = null; S.dirty = true; }
    function select(reg) {
      S.selected = reg; S.dirty = true;
      if (reg) focusRegion(reg); else setView({ target: [0, 0.9, 0], dist: 3.1, yaw: 25, pitch: 6 });
      if (opts.onSelect) opts.onSelect(reg);
    }

    // -------------------------------------------------------- animation player
    function play(name, cb = {}) {
      const A = ANIMS[name]; if (!A) throw new Error("unknown animation " + name);
      S.anim = { name, A, step: 0, t0: performance.now(), paused: false, from: clonePose(S.pose), cb };
      S.selected = null; applyStepView(); if (cb.onStep) cb.onStep(0, A.steps[0], A); S.dirty = true;
      return controls;
    }
    function clonePose(p) { return { pos: [...p.pos], rot: JSON.parse(JSON.stringify(p.rot)) }; }
    function applyStepView() {
      const st = S.anim.A.steps[S.anim.step]; S.props = st.props || [];
      const [yaw, pitch, tgt, dist] = st.cam; const f = FOCUS[tgt];
      const target = f ? jointPosAfter(st.pose, f[0], f[1]) : jointPosAfter(st.pose, tgt, [0, 0, 0]);
      setView({ target, dist, yaw, pitch });
    }
    function jointPosAfter(pose, j, off) { const W = world(pose); return M.apply(W[j], off); }
    const controls = {
      pause() { if (S.anim) { S.anim.paused = true; S.anim.pausedAt = performance.now(); } },
      resume() { if (S.anim && S.anim.paused) { S.anim.t0 += performance.now() - S.anim.pausedAt; S.anim.paused = false; } },
      restart() { if (S.anim) play(S.anim.name, S.anim.cb); },
      go(i) { if (!S.anim) return; const n = S.anim.A.steps.length; S.anim.step = Math.max(0, Math.min(n - 1, i)); S.anim.from = clonePose(S.pose); S.anim.t0 = performance.now(); applyStepView(); if (S.anim.cb.onStep) S.anim.cb.onStep(S.anim.step, S.anim.A.steps[S.anim.step], S.anim.A); S.dirty = true; },
      next() { if (S.anim) controls.go(S.anim.step + 1); },
      prev() { if (S.anim) controls.go(S.anim.step - 1); },
      stop() { S.anim = null; S.props = []; S.pose = rest(); select(null); },
      state() { return S.anim ? { name: S.anim.name, step: S.anim.step, steps: S.anim.A.steps.length, paused: S.anim.paused } : null; },
    };
    function tickAnim(now) {
      const a = S.anim; if (!a || a.paused) return;
      const st = a.A.steps[a.step]; const dur = reduce() ? 1 : 1100; const t = ease(Math.min(1, (now - a.t0) / dur));
      const to = st.pose; const p = { pos: a.from.pos.map((v, i) => lerp(v, to.pos[i], t)), rot: {} };
      const keys = new Set([...Object.keys(a.from.rot), ...Object.keys(to.rot)]);
      keys.forEach((k) => { const f = a.from.rot[k] || [0, 0, 0], g = to.rot[k] || [0, 0, 0]; p.rot[k] = f.map((v, i) => lerp(v, g[i], t)); });
      if (st.float && !reduce()) p.pos[1] += 0.02 * Math.sin(now / 700);
      if (!reduce()) p.rot.chest = [(p.rot.chest ? p.rot.chest[0] : 0) + 0.8 * Math.sin(now / 900), 0, 0]; // breathing
      S.pose = p;
      S.extras.cuffScale = st.cuffIn ? lerp(1.6, 1, t) : st.pulse && !reduce() && (st.props || []).includes("cuff") ? 1 + 0.06 * (0.5 + 0.5 * Math.sin(now / 300)) : 1;
      S.dirty = true;
      const stepTime = reduce() ? 4000 : 5200;
      if (a.cb.autoAdvance !== false && now - a.t0 > stepTime && a.step < a.A.steps.length - 1) controls.next();
    }

    // -------------------------------------------------------- loop
    function loop(now) {
      if (S.destroyed) return;
      if (S.fly) { const k = ease(Math.min(1, (now - S.fly.t0) / S.fly.dur)); const f = S.fly.from, t = S.fly.to;
        S.target = f.target.map((v, i) => lerp(v, t.target[i], k)); S.dist = lerp(f.dist, t.dist, k); S.yaw = lerp(f.yaw, t.yaw, k); S.pitch = lerp(f.pitch, t.pitch, k);
        if (k >= 1) S.fly = null; S.dirty = true; }
      tickAnim(now);
      if (S.selected || S.dirty) { render(); S.dirty = false; }
      requestAnimationFrame(loop);
    }
    requestAnimationFrame(loop);
    const ro = new ResizeObserver(() => (S.dirty = true)); ro.observe(host);

    return {
      setStatus(map) { S.status = map || {}; S.dirty = true; }, select, focus: focusRegion, play, controls,
      zoom, reset() { select(null); }, rotate(d) { S.yaw += d; S.dirty = true; },
      perf() { const a = S.frameMs; return { frames: a.length, avg_ms: a.length ? +(a.reduce((x, y) => x + y, 0) / a.length).toFixed(2) : null }; },
      view() { return { yaw: S.yaw, pitch: S.pitch, dist: S.dist, selected: S.selected, anim: controls.state() }; },
      pickAt(x, y) { return pick(x, y); }, joint(j, off) { return jointPos(j, off || [0, 0, 0]); }, canvas,
      destroy() { S.destroyed = true; ro.disconnect(); canvas.remove(); },
    };
  }
  window.Body3D = { supported, mount, ANIMS, REGIONS };
})();
