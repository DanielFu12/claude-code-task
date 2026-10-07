// Procedural score for the video. Writes a 48 kHz / 24-bit stereo WAV.
// node audio.js out.wav
const fs = require('fs');
const { TL } = require('./timeline.js');

const SR = 48000;
const N = Math.ceil(TL.DURATION * SR);
const BEAT = TL.BEAT;
const bt = (beat) => beat * BEAT;
const mtof = (m) => 440 * Math.pow(2, (m - 69) / 12);

// buses
const bus = () => [new Float32Array(N), new Float32Array(N)];
const MUSIC = bus();   // ducked by kick, gated by silences
const DRUMS = bus();   // gated by silences
const FX = bus();      // transitions / hits, never gated
const SUB = bus();     // sub drone: gated + dynamics, not ducked
const SEND = bus();    // reverb input

let seed = 1234567;
const rnd = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
const white = () => rnd() * 2 - 1;

class Biquad {
  constructor() { this.x1 = this.x2 = this.y1 = this.y2 = 0; }
  lp(f, q = 0.707) { return this._set(f, q, 'lp'); }
  hp(f, q = 0.707) { return this._set(f, q, 'hp'); }
  bp(f, q = 1) { return this._set(f, q, 'bp'); }
  _set(f, q, type) {
    const w = 2 * Math.PI * Math.min(Math.max(f, 10), SR * 0.45) / SR;
    const c = Math.cos(w), s = Math.sin(w), a = s / (2 * q);
    let b0, b1, b2;
    if (type === 'lp') { b0 = (1 - c) / 2; b1 = 1 - c; b2 = (1 - c) / 2; }
    else if (type === 'hp') { b0 = (1 + c) / 2; b1 = -(1 + c); b2 = (1 + c) / 2; }
    else { b0 = a; b1 = 0; b2 = -a; }
    const a0 = 1 + a;
    this.b0 = b0 / a0; this.b1 = b1 / a0; this.b2 = b2 / a0; this.a1 = -2 * c / a0; this.a2 = (1 - a) / a0;
    return this;
  }
  p(x) {
    const y = this.b0 * x + this.b1 * this.x1 + this.b2 * this.x2 - this.a1 * this.y1 - this.a2 * this.y2;
    this.x2 = this.x1; this.x1 = x; this.y2 = this.y1; this.y1 = y;
    return y;
  }
}

const polyblep = (t, dt) => {
  if (t < dt) { t /= dt; return t + t - t * t - 1; }
  if (t > 1 - dt) { t = (t - 1) / dt; return t * t + t + t + 1; }
  return 0;
};

function add(b, i, l, r) { if (i >= 0 && i < N) { b[0][i] += l; b[1][i] += r; } }
const panLR = (p) => [Math.cos((p + 1) * Math.PI / 4), Math.sin((p + 1) * Math.PI / 4)];

// ------------------------------------------------------------------ instruments
function pad(t0, dur, notes, level, cutoff, rel = 1.4) {
  const att = 0.5;
  const len = Math.floor((dur + rel) * SR);
  const i0 = Math.floor(t0 * SR);
  const fl = new Biquad().lp(cutoff, 0.8), fr = new Biquad().lp(cutoff, 0.8);
  const vs = [];
  notes.forEach((m, ni) => {
    for (const d of [-0.11, -0.04, 0.04, 0.11]) {
      vs.push({ f: mtof(m + d), ph: rnd(), pan: Math.max(-0.9, Math.min(0.9, d * 6 + (ni - 1) * 0.2)) });
    }
  });
  const g = level / Math.sqrt(vs.length);
  for (let k = 0; k < len; k++) {
    const t = k / SR;
    let env = Math.min(1, t / att);
    if (t > dur) env *= Math.exp(-(t - dur) / (rel / 4));
    env = env * env * (3 - 2 * env);
    if ((k & 63) === 0) {
      const c = cutoff * (1 + 0.35 * Math.sin(2 * Math.PI * 0.11 * (t0 + t)));
      fl.lp(c, 0.8); fr.lp(c, 0.8);
    }
    let l = 0, r = 0;
    for (const v of vs) {
      const dt = v.f / SR;
      v.ph += dt; if (v.ph >= 1) v.ph -= 1;
      const s = 2 * v.ph - 1 - polyblep(v.ph, dt);
      l += s * (1 - v.pan) * 0.5; r += s * (1 + v.pan) * 0.5;
    }
    const ol = fl.p(l) * g * env, or = fr.p(r) * g * env;
    add(MUSIC, i0 + k, ol, or);
    add(SEND, i0 + k, ol * 0.6, or * 0.6);
  }
}

function piano(t0, m, vel, dur) {
  const f = mtof(m);
  const B = 0.00035;
  const tauBase = 2.8 * Math.max(0.35, 1.4 - (m - 60) / 40);
  const parts = [];
  for (let k = 1; k <= 9; k++) {
    const fk = k * f * Math.sqrt(1 + B * k * k);
    if (fk > 9000) break;
    parts.push({ fk, a: Math.pow(k, -1.35) * (k === 1 ? 1 : 0.8 * (0.5 + vel * 0.6)), tau: tauBase / (1 + 0.7 * (k - 1)) });
  }
  const len = Math.floor(Math.min(dur + 1.2, tauBase * 3.5) * SR);
  const i0 = Math.floor(t0 * SR);
  const [pl, pr] = panLR(Math.max(-0.6, Math.min(0.6, (m - 66) / 20)));
  const g = vel * 0.22;
  for (let k = 0; k < len; k++) {
    const t = k / SR;
    let s = 0;
    for (const p of parts) s += p.a * Math.exp(-t / p.tau) * (Math.sin(2 * Math.PI * p.fk * t) + 0.6 * Math.sin(2 * Math.PI * p.fk * 1.0012 * t));
    let env = Math.min(1, t / 0.004);
    if (t > dur) env *= Math.exp(-(t - dur) / 0.35);
    const o = s * env * g;
    add(MUSIC, i0 + k, o * pl, o * pr);
    add(SEND, i0 + k, o * 0.9, o * 0.9);
  }
}

function pluck(t0, m, vel, pan) {
  const f = mtof(m);
  const len = Math.floor(0.9 * SR);
  const i0 = Math.floor(t0 * SR);
  const [pl, pr] = panLR(pan);
  const g = vel * 0.1;
  for (let k = 0; k < len; k++) {
    const t = k / SR;
    const s = Math.sin(2 * Math.PI * f * t) * Math.exp(-t / 0.17)
      + 0.45 * Math.sin(4 * Math.PI * f * t) * Math.exp(-t / 0.06)
      + 0.18 * Math.sin(6 * Math.PI * f * t) * Math.exp(-t / 0.05);
    const o = s * Math.min(1, t / 0.003) * g;
    add(MUSIC, i0 + k, o * pl, o * pr);
    add(SEND, i0 + k, o * 0.45, o * 0.45);
  }
}

function strings(t0, m, dur, level) {
  const len = Math.floor((dur + 1.6) * SR);
  const i0 = Math.floor(t0 * SR);
  const vs = [-0.14, -0.07, 0, 0.07, 0.14].map((d, i) => ({ d, ph: rnd(), pan: (i - 2) * 0.35 }));
  const fl = new Biquad().lp(3600, 0.6), fr = new Biquad().lp(3600, 0.6);
  const g = level * 0.07;
  for (let k = 0; k < len; k++) {
    const t = k / SR;
    let env = Math.min(1, t / 0.45);
    if (t > dur) env *= Math.exp(-(t - dur) / 0.5);
    env = env * env;
    const vib = 0.12 * Math.min(1, t / 0.8) * Math.sin(2 * Math.PI * 5.2 * t);
    let l = 0, r = 0;
    for (const v of vs) {
      const fr0 = mtof(m + v.d + vib), dt = fr0 / SR;
      v.ph += dt; if (v.ph >= 1) v.ph -= 1;
      const s = 2 * v.ph - 1 - polyblep(v.ph, dt);
      l += s * (1 - v.pan) * 0.5; r += s * (1 + v.pan) * 0.5;
    }
    const ol = fl.p(l) * g * env, or = fr.p(r) * g * env;
    add(MUSIC, i0 + k, ol, or);
    add(SEND, i0 + k, ol * 1.1, or * 1.1);
  }
}

function bassNote(t0, m, dur, level, pulse) {
  const f = mtof(m);
  const len = Math.floor((dur + 0.3) * SR);
  const i0 = Math.floor(t0 * SR);
  const lp = new Biquad().lp(pulse ? 420 : 260, 0.9);
  let ph = 0;
  for (let k = 0; k < len; k++) {
    const t = k / SR;
    let env = Math.min(1, t / (pulse ? 0.005 : 0.08));
    env *= pulse ? Math.exp(-t / 0.22) : (t > dur ? Math.exp(-(t - dur) / 0.1) : 1);
    ph += f / SR; if (ph >= 1) ph -= 1;
    const saw = 2 * ph - 1 - polyblep(ph, f / SR);
    const s = Math.sin(2 * Math.PI * ph) + 0.35 * lp.p(saw);
    const o = Math.tanh(s * 1.3) * env * level * 0.21;
    add(MUSIC, i0 + k, o, o);
  }
}

function subNote(t0, m, dur, level) {
  const f = mtof(m);
  const len = Math.floor((dur + 0.4) * SR);
  const i0 = Math.floor(t0 * SR);
  for (let k = 0; k < len; k++) {
    const t = k / SR;
    let env = Math.min(1, t / 0.3);
    if (t > dur) env *= Math.exp(-(t - dur) / 0.15);
    const o = Math.sin(2 * Math.PI * f * t) * env * level * 0.14;
    add(SUB, i0 + k, o, o);
  }
}

function kick(t0, level) {
  const len = Math.floor(0.7 * SR);
  const i0 = Math.floor(t0 * SR);
  const lp = new Biquad().lp(2500, 0.7);
  let ph = 0;
  for (let k = 0; k < len; k++) {
    const t = k / SR;
    const f = 44 + 120 * Math.exp(-t * 28);
    ph += f / SR;
    const body = Math.sin(2 * Math.PI * ph) * Math.exp(-t / 0.32);
    const click = lp.p(white()) * Math.exp(-t / 0.004) * 0.25;
    const o = Math.tanh((body + click) * 1.6) * level * 0.38;
    add(DRUMS, i0 + k, o, o);
  }
}

function snare(t0, level) {
  const len = Math.floor(0.5 * SR);
  const i0 = Math.floor(t0 * SR);
  const bp = new Biquad().bp(1500, 0.6), lp = new Biquad().lp(4200, 0.7);
  for (let k = 0; k < len; k++) {
    const t = k / SR;
    const tone = Math.sin(2 * Math.PI * 180 * t) * Math.exp(-t / 0.06);
    const nz = lp.p(bp.p(white())) * Math.exp(-t / 0.13);
    const o = (tone * 0.5 + nz * 1.6) * level * 0.28;
    add(DRUMS, i0 + k, o * 0.9, o);
    add(SEND, i0 + k, o * 1.2, o * 1.2);
  }
}

function taiko(t0, level, pan = 0) {
  const len = Math.floor(1.2 * SR);
  const i0 = Math.floor(t0 * SR);
  const lp = new Biquad().lp(520, 0.8);
  const [pl, pr] = panLR(pan);
  let ph = 0;
  for (let k = 0; k < len; k++) {
    const t = k / SR;
    const f = 52 + 48 * Math.exp(-t * 14);
    ph += f / SR;
    const s = Math.sin(2 * Math.PI * ph) * Math.exp(-t / 0.42) + lp.p(white()) * Math.exp(-t / 0.05) * 0.9;
    const o = Math.tanh(s * 1.4) * level * 0.4;
    add(DRUMS, i0 + k, o * pl, o * pr);
    add(SEND, i0 + k, o * 0.8, o * 0.8);
  }
}

// --- deep transition: low filtered air swell into the downbeat + sub drop + body
function whoosh(tc, amp, maxCut, pre = BEAT * 1.5, post = 2.2, boomAmp = amp) {
  const i0 = Math.floor((tc - pre) * SR), len = Math.floor((pre + post) * SR);
  const f = [new Biquad(), new Biquad(), new Biquad(), new Biquad()];
  for (let k = 0; k < len; k++) {
    const x = k / SR - pre;
    let env, cut;
    if (x < 0) { const u = (x + pre) / pre; env = Math.pow(u, 2.6); cut = 70 * Math.pow(maxCut / 70, Math.pow(u, 1.4)); }
    else { env = Math.exp(-x / 0.5); cut = 70 + (maxCut - 70) * Math.exp(-x / 0.4); }
    if ((k & 31) === 0) { f[0].lp(cut, 1.3); f[1].lp(cut, 0.7); f[2].lp(cut, 1.3); f[3].lp(cut, 0.7); }
    const nl = f[1].p(f[0].p(white())), nr = f[3].p(f[2].p(white()));
    const sweep = Math.tanh(x / pre * 2);                    // pan drifts left -> right
    const [pl, pr] = panLR(sweep * 0.7);
    const g = amp * env * 1.9;
    add(FX, i0 + k, nl * g * pl * 1.4, nr * g * pr * 1.4);
    add(SEND, i0 + k, nl * g * 0.5, nr * g * 0.5);
  }
  if (boomAmp > 0) boom(tc, boomAmp);
}

function boom(tc, amp) {
  const i0 = Math.floor(tc * SR), len = Math.floor(3.2 * SR);
  let ph = 0, ph2 = 0;
  const lp = new Biquad().lp(300, 0.8);
  for (let k = 0; k < len; k++) {
    const t = k / SR;
    const f = 30 + 62 * Math.exp(-t / 0.28);
    ph += f / SR; ph2 += (58 + 30 * Math.exp(-t / 0.08)) / SR;
    const sub = Math.sin(2 * Math.PI * ph) * Math.exp(-t / 1.1);
    const body = Math.sin(2 * Math.PI * ph2) * Math.exp(-t / 0.25) * 0.7;
    const thud = lp.p(white()) * Math.exp(-t / 0.03) * 0.6;
    const o = Math.tanh((sub + body + thud) * 1.8) * amp * 0.55;
    add(FX, i0 + k, o, o);
    add(SEND, i0 + k, o * 0.35, o * 0.35);
  }
}

function riser(t0, t1, amp) {
  const i0 = Math.floor(t0 * SR), len = Math.floor((t1 - t0) * SR);
  const fl = new Biquad(), fr = new Biquad(), nf = new Biquad(), nf2 = new Biquad();
  let ph = [0, 0.3, 0.6];
  for (let k = 0; k < len; k++) {
    const u = k / len;
    const f0 = 98 * Math.pow(4, u);
    if ((k & 31) === 0) { const c = 250 + 1500 * u * u; fl.lp(c, 2); fr.lp(c, 2); nf.lp(150 + 900 * u * u, 1); nf2.lp(150 + 900 * u * u, 0.7); }
    let s = 0;
    [1, 1.5, 2.003].forEach((m, j) => { const ff = f0 * m; ph[j] += ff / SR; if (ph[j] >= 1) ph[j] -= 1; s += 2 * ph[j] - 1 - polyblep(ph[j], ff / SR); });
    const env = Math.pow(u, 2.2) * amp;
    const nz = nf2.p(nf.p(white())) * 1.5;
    add(FX, i0 + k, (fl.p(s) * 0.12 + nz) * env, (fr.p(s) * 0.12 + nz) * env);
    add(SEND, i0 + k, nz * env * 0.6, nz * env * 0.6);
  }
}

// ------------------------------------------------------------------ score
const MEL_HOOK = [[0, 69, 1], [1, 74, 1], [2, 76, 1], [3, 77, 3], [6, 76, 1], [7, 74, 1],
  [8, 74, 2], [10, 77, 1], [11, 74, 1], [12, 72, 4],
  [16, 72, 1], [17, 77, 1], [18, 81, 3], [21, 79, 1], [22, 77, 1], [23, 76, 1],
  [24, 76, 3], [27, 74, 1], [28, 72, 1], [29, 76, 1], [30, 79, 2]];
const MEL_CH4 = [[0, 74, 2], [2, 77, 2], [4, 72, 1.5], [5.5, 77, 0.5], [6, 81, 2], [8, 79, 2], [10, 76, 2], [12, 77, 1], [13, 76, 1], [14, 74, 2]];
const MEL_OUT = [[0, 77, 3], [3, 74, 1], [4, 72, 3], [7, 69, 1], [8, 67, 2], [10, 72, 2], [12, 69, 4], [16, 74, 2], [18, 77, 2], [20, 76, 2], [22, 79, 2], [24, 78, 4]];
const STR_TITLE = [[0, 69, 4], [4, 70, 2], [6, 74, 2], [8, 72, 2], [10, 76, 2]];
const STR_CH8 = [[0, 74, 2], [2, 77, 2], [4, 76, 2], [6, 79, 2], [8, 81, 4], [12, 84, 2], [14, 81, 2], [16, 82, 2], [18, 81, 2], [20, 79, 2], [22, 76, 2], [24, 77, 4], [28, 76, 3],
  [32, 86, 4], [36, 86, 2], [38, 84, 2], [40, 84, 2], [42, 79, 2], [44, 81, 4], [48, 82, 2], [50, 81, 2], [52, 79, 4]];

const inSilence = (beat) => TL.SILENCE.some((s) => beat >= s.from && beat < s.to);

console.time('score');
for (let bar = 0; bar < TL.TOTAL_BARS; bar++) {
  const a = TL.arrAt(bar), ch = TL.chordAt(bar), t = bt(bar * 4);
  const last = bar === TL.TOTAL_BARS - 1;
  const drive = a.kick === 'four';
  // pad: one chord per bar, merged when the chord is held
  const prevSame = bar > 0 && TL.PROG[bar - 1] === TL.PROG[bar] && TL.arrAt(bar - 1) === a;
  if (!prevSame) {
    let n = 1; while (bar + n < TL.TOTAL_BARS && TL.PROG[bar + n] === TL.PROG[bar] && TL.arrAt(bar + n) === a) n++;
    const notes = ch.tones.slice();
    if (a.pad > 0.85) notes.push(ch.tones[2] + 12);
    pad(t, bt(4 * n), notes, a.pad * 0.4, drive ? 2400 : 1500, last || bar + n >= TL.TOTAL_BARS ? 6 : 1.4);
    if (a.sub > 0) subNote(t, ch.root >= 36 ? ch.root - 12 : ch.root, bt(4 * n) - 0.05, a.sub);
    if (a.bass > 0 && !drive) bassNote(t, ch.root + 12, bt(4 * n) - 0.08, a.bass, false);
  }
  if (a.bass > 0 && drive) {
    for (let e = 0; e < 8; e++) {
      const b = bar * 4 + e / 2; if (inSilence(b)) continue;
      bassNote(bt(b), ch.root + 12, bt(0.45), a.bass * (e % 2 ? 1 : 0.75), true);
    }
  }
  // arp
  if (a.arp > 0 && !last) {
    const sixteenth = drive || a.kick === 'half';
    const steps = sixteenth ? 16 : 8;
    const ext = [ch.tones[1] + 12, ch.tones[2] + 12, ch.tones[0] + 24, ch.tones[1] + 24, ch.tones[2] + 24, ch.tones[0] + 36];
    const pat = [0, 1, 2, 3, 4, 3, 2, 1, 0, 2, 4, 5, 4, 2, 3, 1];
    for (let s = 0; s < steps; s++) {
      const b = bar * 4 + s * 4 / steps; if (inSilence(b)) continue;
      const acc = s % (steps / 4) === 0 ? 1 : 0.62;
      pluck(bt(b), ext[pat[s % pat.length]], a.arp * acc * 0.75, s % 2 ? 0.5 : -0.5);
    }
  }
  // drums
  for (const kb of TL.kickBeats()) if (kb >= bar * 4 && kb < bar * 4 + 4) kick(bt(kb), kb % 1 ? 0.55 : 1);
  if (a.snare > 0) for (const b of [1, 3]) if (!inSilence(bar * 4 + b)) snare(bt(bar * 4 + b), a.snare);
  if (a.taiko > 0) {
    const ph = bar % 4;
    const hitsT = ph === 3 ? [0, 2, 2.5, 3, 3.5] : (ph % 2 === 0 ? [0, 2.75] : [0]);
    for (const b of hitsT) if (!inSilence(bar * 4 + b)) taiko(bt(bar * 4 + b), a.taiko * (b >= 3 ? 0.8 : 1), b % 1 ? 0.3 : -0.2);
  }
  // sustained strings (chord voicing) unless a melody covers the section
  if (a.strings > 0 && !(bar >= 8 && bar < 11) && !(bar >= 102 && bar < 116) && !prevSame) {
    let n = 1; while (bar + n < TL.TOTAL_BARS && TL.PROG[bar + n] === TL.PROG[bar] && TL.arrAt(bar + n) === a) n++;
    for (const m of [ch.tones[0] + 24, ch.tones[2] + 12]) strings(t, m, bt(4 * n) - 0.1, a.strings * 0.55);
  }
}
// melodies
for (const [b, m, d] of MEL_HOOK) piano(bt(b), m, 0.75, bt(d));
for (let bar = 0; bar < 8; bar += 2) { const ch = TL.chordAt(bar); piano(bt(bar * 4), ch.root + 12, 0.45, bt(8)); piano(bt(bar * 4), ch.root + 19, 0.35, bt(8)); }
for (let bar = 15; bar < 22; bar++) {
  const ch = TL.chordAt(bar), b0 = bar * 4;
  [[0, ch.tones[0] + 12], [1, ch.tones[2] + 12], [1.5, ch.tones[1] + 24], [2.5, ch.tones[2] + 12], [3, ch.tones[0] + 24]]
    .forEach(([o, m]) => piano(bt(b0 + o), m, 0.42, bt(1.5)));
}
for (let rep = 0; rep < 4; rep++) for (const [b, m, d] of MEL_CH4) piano(bt(48 * 4 + rep * 16 + b), m + (rep === 3 ? 12 : 0), 0.5, bt(d));
for (const [b, m, d] of MEL_OUT) piano(bt(116 * 4 + b), m, 0.7, bt(d));
// brand ending: light hit as the logo appears, then the heavy beat (D major + bells + deep drum)
boom(bt(124 * 4 + 2), 0.45); taiko(bt(124 * 4 + 2), 0.3);
for (const m of [50, 57, 62, 66, 69, 74]) piano(bt(125 * 4), m, 0.75, bt(10));
for (const m of [81, 86]) piano(bt(125 * 4), m, 0.45, bt(6));
taiko(bt(125 * 4), 1);
for (const [b, m, d] of STR_TITLE) strings(bt(8 * 4 + b), m, bt(d), 0.9);
for (const [b, m, d] of STR_CH8) { if (!inSilence(102 * 4 + b)) { strings(bt(102 * 4 + b), m, bt(d) - 0.05, 1); strings(bt(102 * 4 + b), m - 12, bt(d) - 0.05, 0.6); } }

// FX
const ev = TL.events();
for (const tr of ev.trans) whoosh(bt(tr.beat), 0.9, 650);
for (const s of ev.subs) whoosh(bt(s.beat), 0.4, 420, BEAT, 1.4, 0.18);
for (const h of ev.hits) {
  if (h.k === 'big') { whoosh(bt(h.beat), 1.0, 700); taiko(bt(h.beat), 1); }
  else if (h.k === 'land') { boom(bt(h.beat), 0.55); }
  else boom(bt(h.beat), 0.3);
}
riser(bt(7 * 4), bt(8 * 4), 0.8);
riser(bt(108 * 4), bt(109 * 4 + 3), 0.9);
riser(bt(83 * 4), bt(84 * 4 + 3.5), 0.5);
boom(bt(125 * 4), 1.0);
riser(bt(123 * 4), bt(124.95 * 4), 0.55);
console.timeEnd('score');

// ------------------------------------------------------------------ mix
console.time('mix');
// sidechain + silence gates
const kicks = TL.kickBeats().map(bt);
const gate = new Float32Array(N), duck = new Float32Array(N);
{
  let ki = 0;
  for (let i = 0; i < N; i++) {
    const t = i / SR, beat = t / BEAT;
    while (ki + 1 < kicks.length && kicks[ki + 1] <= t) ki++;
    const a = TL.arrAt(Math.floor(beat / 4));
    const depth = a.kick === 'four' ? 0.42 : a.kick === 'none' ? 0 : 0.25;
    const dt = t - kicks[ki];
    duck[i] = kicks[ki] <= t ? 1 - depth * Math.exp(-dt / 0.13) * Math.min(1, dt / 0.004 + 0.3) : 1;
    let g = 1;
    for (const s of TL.SILENCE) {
      const t0 = bt(s.from), t1 = bt(s.to);
      if (t >= t0 - 0.03 && t < t1) g = Math.min(g, Math.max(0, (t0 - t) / 0.03));
    }
    gate[i] = g;
  }
}
// reverb (Freeverb)
function freeverb(inp, room = 0.88, damp = 0.45) {
  const sc = SR / 44100;
  const combT = [1116, 1188, 1277, 1356, 1422, 1491, 1557, 1617], apT = [556, 441, 341, 225];
  const out = [new Float32Array(N), new Float32Array(N)];
  const hp = [new Biquad().hp(140), new Biquad().hp(140)], lp = [new Biquad().lp(5500), new Biquad().lp(5500)];
  for (let c = 0; c < 2; c++) {
    const spread = c ? 23 : 0;
    const combs = combT.map((d) => ({ b: new Float32Array(Math.floor((d + spread) * sc)), i: 0, s: 0 }));
    const aps = apT.map((d) => ({ b: new Float32Array(Math.floor((d + spread) * sc)), i: 0 }));
    const fb = room * 0.28 + 0.7, d1 = damp * 0.4, d2 = 1 - d1;
    const src = inp[c], dst = out[c];
    for (let i = 0; i < N; i++) {
      const x = lp[c].p(hp[c].p(src[i])) * 0.015;
      let y = 0;
      for (const cb of combs) {
        const o = cb.b[cb.i];
        cb.s = o * d2 + cb.s * d1;
        cb.b[cb.i] = x + cb.s * fb;
        if (++cb.i >= cb.b.length) cb.i = 0;
        y += o;
      }
      for (const ap of aps) {
        const o = ap.b[ap.i];
        ap.b[ap.i] = y + o * 0.5;
        if (++ap.i >= ap.b.length) ap.i = 0;
        y = o - y;
      }
      dst[i] = y;
    }
  }
  return out;
}
const WET = freeverb(SEND);
// section dynamics (dB) applied to music, sub and drums
const DYN = [[0, -7], [8, 0], [11, -4], [15, -5], [22, -3], [36, -2], [48, -1], [64, 0], [80, -2], [85, -5], [88, -1], [92, -1], [102, 1], [116, -2], [123, -3], [125, 0]];
const dyn = new Float32Array(N);
{
  let g = Math.pow(10, DYN[0][1] / 20);
  const k = 1 - Math.exp(-1 / (0.25 * SR));
  for (let i = 0; i < N; i++) {
    const bar = i / SR / TL.BAR;
    let db = DYN[0][1]; for (const [b, d] of DYN) if (bar >= b - 0.08) db = d;
    g += (Math.pow(10, db / 20) - g) * k;
    dyn[i] = g;
  }
}
const outL = new Float32Array(N), outR = new Float32Array(N);
const hpL = new Biquad().hp(24, 0.7), hpR = new Biquad().hp(24, 0.7);
let peak = 0;
for (let i = 0; i < N; i++) {
  const g = gate[i];
  const d = dyn[i] * g;
  const l = (MUSIC[0][i] * duck[i] + DRUMS[0][i] + SUB[0][i]) * d + FX[0][i] * 0.8 + WET[0][i] * 0.55;
  const r = (MUSIC[1][i] * duck[i] + DRUMS[1][i] + SUB[1][i]) * d + FX[1][i] * 0.8 + WET[1][i] * 0.55;
  outL[i] = hpL.p(l); outR[i] = hpR.p(r);
}
// gentle glue + normalise
for (let i = 0; i < N; i++) { outL[i] = Math.tanh(outL[i] * 0.9); outR[i] = Math.tanh(outR[i] * 0.9); peak = Math.max(peak, Math.abs(outL[i]), Math.abs(outR[i])); }
const norm = 0.89 / peak;
const fadeOut = 2.5 * SR;
for (let i = 0; i < N; i++) {
  let g = norm * Math.min(1, i / (0.02 * SR));
  if (i > N - fadeOut) g *= (N - i) / fadeOut;
  outL[i] *= g; outR[i] *= g;
}
console.timeEnd('mix');

// ------------------------------------------------------------------ wav (24-bit)
const out = process.argv[2] || 'score.wav';
const data = Buffer.alloc(N * 6);
for (let i = 0; i < N; i++) {
  for (let c = 0; c < 2; c++) {
    const v = Math.max(-1, Math.min(1, c ? outR[i] : outL[i]));
    data.writeIntLE(Math.round(v * 8388607), i * 6 + c * 3, 3);
  }
}
const h = Buffer.alloc(44);
h.write('RIFF', 0); h.writeUInt32LE(36 + data.length, 4); h.write('WAVE', 8); h.write('fmt ', 12);
h.writeUInt32LE(16, 16); h.writeUInt16LE(1, 20); h.writeUInt16LE(2, 22); h.writeUInt32LE(SR, 24);
h.writeUInt32LE(SR * 6, 28); h.writeUInt16LE(6, 32); h.writeUInt16LE(24, 34); h.write('data', 36); h.writeUInt32LE(data.length, 40);
fs.writeFileSync(out, Buffer.concat([h, data]));
console.log('wrote', out, (N / SR).toFixed(2) + 's', 'peak before norm', peak.toFixed(3));

