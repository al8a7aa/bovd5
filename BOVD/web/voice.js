/* =====================================================================
   BÖVD · on-device signal processing (EXPERIMENTAL)
   F1 voice: Web Audio API → prosodic features. RAW AUDIO IS NEVER STORED OR
   SENT: samples are processed frame by frame in memory and dropped; only the
   7 numbers below leave this function.
   F2 webcam blink: crude luminance-change method in a guide box over the
   eyes. Numbers only. MediaPipe is not bundled (offline); if it is added
   later under web/vendor/, this function is the place to swap it in.
   ===================================================================== */
"use strict";
window.ASTRA_DSP = {
  /** Record `seconds` of audio and return prosodic features. */
  async voiceFeatures(seconds, onTick) {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
    const ac = new (window.AudioContext || window.webkitAudioContext)();
    const src = ac.createMediaStreamSource(stream);
    const an = ac.createAnalyser(); an.fftSize = 2048; src.connect(an);
    const buf = new Float32Array(an.fftSize); const sr = ac.sampleRate;
    const f0s = [], energies = [], periods = [], amps = []; let frames = 0, voiced = 0, peaks = 0, prevE = 0, rising = false;
    const t0 = performance.now();
    await new Promise((resolve) => {
      const step = () => {
        const el = (performance.now() - t0) / 1000; if (onTick) onTick(el);
        if (el >= seconds) return resolve();
        an.getFloatTimeDomainData(buf); frames++;
        let e = 0; for (let i = 0; i < buf.length; i++) e += buf[i] * buf[i]; e = Math.sqrt(e / buf.length);
        energies.push(e);
        if (e > 0.012) { // voiced frame → autocorrelation pitch 70–400 Hz
          voiced++;
          let best = 0, bestLag = 0; const minL = Math.floor(sr / 400), maxL = Math.floor(sr / 70);
          for (let lag = minL; lag <= maxL; lag++) { let s = 0; for (let i = 0; i < buf.length - lag; i++) s += buf[i] * buf[i + lag]; if (s > best) { best = s; bestLag = lag; } }
          if (bestLag) { f0s.push(sr / bestLag); periods.push(bestLag / sr); let pk = 0; for (let i = 0; i < buf.length; i++) pk = Math.max(pk, Math.abs(buf[i])); amps.push(pk); }
          if (e > prevE) rising = true; else if (rising && e < prevE * 0.8) { peaks++; rising = false; } // syllable nuclei ≈ energy peaks
        }
        prevE = e; buf.fill(0); // drop samples immediately
        requestAnimationFrame(step);
      };
      step();
    });
    stream.getTracks().forEach((tr) => tr.stop()); await ac.close();
    const mean = (a) => a.reduce((x, y) => x + y, 0) / Math.max(1, a.length);
    const sd = (a) => { const m = mean(a); return Math.sqrt(mean(a.map((x) => (x - m) ** 2))); };
    const pert = (a) => { if (a.length < 3) return 0; let s = 0; for (let i = 1; i < a.length; i++) s += Math.abs(a[i] - a[i - 1]); return s / (a.length - 1) / Math.max(1e-9, mean(a)); };
    const voicedSec = (voiced / Math.max(1, frames)) * seconds;
    return { f0_mean: +mean(f0s).toFixed(2), f0_sd: +sd(f0s).toFixed(2), energy: +mean(energies).toFixed(4),
      speech_rate: +(peaks / Math.max(1, voicedSec)).toFixed(2), pause_ratio: +(1 - voiced / Math.max(1, frames)).toFixed(3),
      jitter: +pert(periods).toFixed(4), shimmer: +pert(amps).toFixed(4), duration_s: seconds };
  },

  /** EXPERIMENTAL blink estimate from webcam luminance in an eye guide box. */
  async blink(video, seconds, onTick) {
    const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 320, height: 240 } });
    video.srcObject = stream; await video.play();
    const c = document.createElement("canvas"); c.width = 160; c.height = 40; const g = c.getContext("2d", { willReadFrequently: true });
    const series = []; const t0 = performance.now();
    await new Promise((resolve) => {
      const step = () => {
        const el = (performance.now() - t0) / 1000; if (onTick) onTick(el); if (el >= seconds) return resolve();
        g.drawImage(video, 80, 80, 160, 40, 0, 0, 160, 40); // guide box = upper-middle band
        const d = g.getImageData(0, 0, 160, 40).data; let s = 0; for (let i = 0; i < d.length; i += 4) s += d[i] + d[i + 1] + d[i + 2];
        series.push(s / (d.length / 4)); requestAnimationFrame(step);
      };
      step();
    });
    stream.getTracks().forEach((tr) => tr.stop()); video.srcObject = null;
    const m = series.reduce((a, b) => a + b, 0) / series.length; const sd = Math.sqrt(series.reduce((a, b) => a + (b - m) ** 2, 0) / series.length) || 1;
    let blinks = 0, closed = 0, inB = false;
    for (const v of series) { const z = (v - m) / sd; if (Math.abs(z) > 1.8) { closed++; if (!inB) { blinks++; inB = true; } } else inB = false; }
    return { blinks_per_min: +(blinks * 60 / seconds).toFixed(1), closure_ratio: +(closed / series.length).toFixed(3) };
  },
};
