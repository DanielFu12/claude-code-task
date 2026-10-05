// Rendering engine: deterministic, every frame is a pure function of time.
/* global TL, SCENE_DRAW */
const W = 1920, H = 1080, CX = W / 2, CY = H / 2;
const cv = document.getElementById('c');
const ctx = cv.getContext('2d');
const layer = document.createElement('canvas'); layer.width = W; layer.height = H;
const lctx = layer.getContext('2d');

// ---------------------------------------------------------------- math
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const lerp = (a, b, t) => a + (b - a) * t;
const inv = (a, b, x) => clamp((x - a) / (b - a));
const E = {
  outCubic: (t) => 1 - Math.pow(1 - t, 3),
  inCubic: (t) => t * t * t,
  inOutCubic: (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),
  outExpo: (t) => (t >= 1 ? 1 : 1 - Math.pow(2, -10 * t)),
  inExpo: (t) => (t <= 0 ? 0 : Math.pow(2, 10 * t - 10)),
  outBack: (t) => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2); },
  inOutSine: (t) => -(Math.cos(Math.PI * t) - 1) / 2,
  outQuint: (t) => 1 - Math.pow(1 - t, 5),
};
function rng(seed) { let a = seed >>> 0; return () => { a = (a + 0x6d2b79f5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
const hash = (n) => { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };
function noise1(x) { const i = Math.floor(x), f = x - i, u = f * f * (3 - 2 * f); return lerp(hash(i), hash(i + 1), u) * 2 - 1; }
const fmt = (n) => Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');

// ---------------------------------------------------------------- colour
const hex = (h) => { h = h.replace('#', ''); return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)]; };
const rgba = (c, a = 1) => `rgba(${c[0] | 0},${c[1] | 0},${c[2] | 0},${a})`;
const mixc = (a, b, t) => [lerp(a[0], b[0], t), lerp(a[1], b[1], t), lerp(a[2], b[2], t)];
const GOLD = hex('#f3c76e'), GOLD2 = hex('#ffdf9e'), WHITE = [255, 255, 255], CYAN = hex('#5fe1ff'), RED = hex('#ff4d5e');

const PALS = {
  hook:   { bg: ['#05060b', '#0a0b14'], neb: ['#a8761c', '#1b2a5a', '#3a1f5c'], acc: '#f3c76e', acc2: '#7aa7ff' },
  title:  { bg: ['#06050a', '#0d0a12'], neb: ['#c08a24', '#5b2a86', '#1d3b7a'], acc: '#f3c76e', acc2: '#c9a7ff' },
  thesis: { bg: ['#05070d', '#0a0c16'], neb: ['#0e7490', '#6d28d9', '#b7791f'], acc: '#f3c76e', acc2: '#7dd3fc' },
  ch1:    { bg: ['#07060a', '#0e0b0a'], neb: ['#b45309', '#7c2d12', '#1e3a8a'], acc: '#ffc477', acc2: '#ffd9a0' },
  ch2:    { bg: ['#02080f', '#041220'], neb: ['#0891b2', '#1d4ed8', '#0f766e'], acc: '#5fe1ff', acc2: '#9ad8ff' },
  ch3:    { bg: ['#0d0504', '#120806'], neb: ['#ea580c', '#991b1b', '#78350f'], acc: '#ffae5c', acc2: '#ff7a45' },
  ch4:    { bg: ['#08051a', '#0e0820'], neb: ['#7c3aed', '#c026d3', '#b7791f'], acc: '#c9a7ff', acc2: '#f3c76e' },
  ch5:    { bg: ['#0c0705', '#120a08'], neb: ['#be123c', '#d97706', '#1d4ed8'], acc: '#ffd479', acc2: '#ff5a6e' },
  ch6:    { bg: ['#0b0306', '#04040c'], neb: ['#b91c1c', '#1e3a8a', '#7f1d1d'], acc: '#ff5a5a', acc2: '#8fb3ff' },
  ch7:    { bg: ['#02100e', '#03090d'], neb: ['#059669', '#0891b2', '#2563eb'], acc: '#5ef2c2', acc2: '#7dd3fc' },
  ch8:    { bg: ['#07050c', '#0b0710'], neb: ['#d97706', '#db2777', '#0891b2'], acc: '#ffd36b', acc2: '#ff7ab6' },
  outro:  { bg: ['#05060b', '#0a0a12'], neb: ['#b7791f', '#4c1d95', '#0e7490'], acc: '#f3c76e', acc2: '#a5b4fc' },
};
const PAL_RGB = {};
for (const k in PALS) PAL_RGB[k] = { bg: PALS[k].bg.map(hex), neb: PALS[k].neb.map(hex), acc: hex(PALS[k].acc), acc2: hex(PALS[k].acc2) };
function blendPal(a, b, t) {
  return { bg: a.bg.map((c, i) => mixc(c, b.bg[i], t)), neb: a.neb.map((c, i) => mixc(c, b.neb[i], t)), acc: mixc(a.acc, b.acc, t), acc2: mixc(a.acc2, b.acc2, t) };
}
let PAL = PAL_RGB.hook;

// ---------------------------------------------------------------- sprites
const spriteCache = new Map();
function sprite(col, hard = 0) {
  const key = col.join(',') + '|' + hard;
  let s = spriteCache.get(key);
  if (s) return s;
  s = document.createElement('canvas'); s.width = s.height = 256;
  const g = s.getContext('2d'), gr = g.createRadialGradient(128, 128, 0, 128, 128, 128);
  if (hard) {
    gr.addColorStop(0, rgba(mixc(col, WHITE, 0.7), 1)); gr.addColorStop(0.12, rgba(col, 0.9));
    gr.addColorStop(0.3, rgba(col, 0.25)); gr.addColorStop(1, rgba(col, 0));
  } else {
    gr.addColorStop(0, rgba(col, 1)); gr.addColorStop(0.25, rgba(col, 0.55));
    gr.addColorStop(0.6, rgba(col, 0.12)); gr.addColorStop(1, rgba(col, 0));
  }
  g.fillStyle = gr; g.fillRect(0, 0, 256, 256);
  spriteCache.set(key, s);
  return s;
}
function glow(c, x, y, r, col, a = 1, hard = 0) {
  if (a <= 0.002 || r <= 0) return;
  const pa = c.globalAlpha; c.globalAlpha = pa * Math.min(1, a);
  c.drawImage(sprite(col.map((v) => Math.round(v / 8) * 8), hard), x - r, y - r, r * 2, r * 2);
  c.globalAlpha = pa;
}

// ---------------------------------------------------------------- text
const FAM = {
  serif: '"Noto Serif SC", serif',
  sans: '"Noto Sans SC", sans-serif',
  cor: '"Cormorant Garamond", "Noto Serif SC", serif',
  mono: '"JetBrains Mono", "Noto Sans SC", monospace',
  play: '"Playfair Display", "Noto Serif SC", serif',
};
const STY = {
  mega:  { w: 900, fam: 'serif', s: 168, col: 'gold', ls: 0.1, glow: 0.7 },
  h1:    { w: 900, fam: 'serif', s: 92, col: 'gold', ls: 0.06, glow: 0.5 },
  h2:    { w: 700, fam: 'serif', s: 54, col: '#f6f1e7', ls: 0.05, glow: 0.16 },
  quote: { w: 500, fam: 'serif', s: 50, col: '#fbf7ee', ls: 0.04, glow: 0.2 },
  body:  { w: 400, fam: 'sans', s: 34, col: '#d9dee8', ls: 0.06 },
  bodyL: { w: 300, fam: 'sans', s: 29, col: '#aab3c4', ls: 0.07 },
  small: { w: 300, fam: 'sans', s: 23, col: '#8f99ac', ls: 0.08 },
  label: { w: 500, fam: 'mono', s: 17, col: 'acc', ls: 0.34 },
  year:  { w: 600, fam: 'cor', s: 100, col: 'gold', ls: 0.02, glow: 0.4 },
  num:   { w: 900, fam: 'play', s: 150, col: 'gold', ls: 0.01, glow: 0.55 },
  numS:  { w: 700, fam: 'play', s: 74, col: 'gold', ls: 0.01, glow: 0.4 },
};
const fontStr = (st, s) => `${st.w} ${s}px ${FAM[st.fam]}`;
const widthCache = new Map();
function cw(c, font, ch) {
  const k = font + ch; let w = widthCache.get(k);
  if (w === undefined) { c.font = font; w = c.measureText(ch).width; widthCache.set(k, w); }
  return w;
}
function parse(str) {
  const out = []; let hl = false;
  for (const ch of str) { if (ch === '[') { hl = true; continue; } if (ch === ']') { hl = false; continue; } out.push({ ch, hl }); }
  return out;
}
function goldGrad(c, x0, x1, y, s, tint) {
  const g = c.createLinearGradient(x0, y - s, x1, y + s * 0.3);
  const base = tint || GOLD;
  const dark = mixc(base, [80, 50, 10], 0.35), light = mixc(base, WHITE, 0.45);
  const p = ((GT * 0.22) % 1.8) - 0.4;
  const stops = [[0, dark], [0.3, light], [0.62, base], [1, dark]];
  for (const [o, col] of [[p - 0.07, base], [p, mixc(base, WHITE, 0.85)], [p + 0.07, base]]) if (o > 0 && o < 1) stops.push([o, col]);
  stops.sort((a, b) => a[0] - b[0]);
  for (const [o, col] of stops) g.addColorStop(o, rgba(col));
  return g;
}
let GT = 0; // global time (s) for shimmer

// main text call. b = current local beat.
function txt(c, b, str, x, y, styName, inB, outB = 1e9, o = {}) {
  if (b < inB - 0.01 || b > outB + 1.2) return;
  const st = STY[styName];
  const s = st.s * (o.scale || 1);
  const font = fontStr(st, s);
  const chars = parse(str);
  const n = chars.length;
  const ls = (o.ls !== undefined ? o.ls : st.ls) * s;
  const anim = o.anim || (styName === 'mega' || styName === 'num' ? 'scale' : 'rise');
  const stg = o.stg !== undefined ? o.stg : (anim === 'type' ? 0.11 : Math.min(0.07, 1.2 / Math.max(1, n)));
  const dur = o.dur || 1.1;
  // whole-line envelopes
  let lineA = 1, lineBlur = 0, lineScale = 1, extraLs = 0;
  if (anim === 'scale') {
    const u = inv(inB, inB + 1.0, b), e = E.outExpo(u);
    lineA = Math.min(1, u * 3); lineScale = lerp(o.from || 1.5, 1, e); lineBlur = (1 - e) * 22;
  } else if (anim === 'blur') {
    const u = inv(inB, inB + 1.6, b), e = E.outCubic(u);
    lineA = e; lineBlur = (1 - e) * 26; extraLs = (1 - e) * s * 0.7;
  }
  const outU = inv(outB, outB + 0.7, b);
  if (outU >= 1) return;
  const outE = E.inCubic(outU);
  let widths = chars.map((d) => cw(c, font, d.ch));
  const total = widths.reduce((a, w) => a + w, 0) + (ls + extraLs) * (n - 1);
  let x0 = x;
  const align = o.align || 'center';
  if (align === 'center') x0 = x - total / 2; else if (align === 'right') x0 = x - total;
  const baseCol = o.col || st.col;
  const accCol = o.acc || PAL.acc;
  const isGoldBase = baseCol === 'gold';
  const fillBase = isGoldBase ? goldGrad(c, x0, x0 + total, y, s, o.tint) : (baseCol === 'acc' ? rgba(accCol) : baseCol);
  const fillHl = isGoldBase ? rgba(mixc(accCol, WHITE, 0.15)) : goldGrad(c, x0, x0 + total, y, s, o.tint);
  const glowA = o.glow !== undefined ? o.glow : (st.glow || 0);
  const glowCol = isGoldBase ? [255, 186, 80] : accCol;
  c.save();
  c.font = font;
  c.textBaseline = 'alphabetic';
  if (lineScale !== 1) { c.translate(x, y - s * 0.35); c.scale(lineScale, lineScale); c.translate(-x, -(y - s * 0.35)); }
  let cx = x0;
  for (let i = 0; i < n; i++) {
    const d = chars[i], w = widths[i];
    let a = lineA, dy = 0, blur = lineBlur;
    if (anim === 'rise') {
      const u = inv(inB + i * stg, inB + i * stg + dur, b), e = E.outCubic(u);
      a *= e; dy = (1 - e) * s * 0.45; blur += (1 - e) * Math.min(14, s * 0.18);
    } else if (anim === 'type') {
      const u = inv(inB + i * stg, inB + i * stg + 0.18, b);
      a *= u; blur += (1 - u) * 6;
    }
    a *= 1 - outE; dy -= outE * s * 0.25; blur += outE * 12;
    a *= (o.alpha !== undefined ? o.alpha : 1);
    if (a > 0.004 && d.ch !== ' ') {
      c.globalAlpha = a;
      c.filter = blur > 0.4 ? `blur(${blur.toFixed(1)}px)` : 'none';
      c.fillStyle = d.hl ? fillHl : fillBase;
      if (glowA > 0 || d.hl) {
        c.shadowColor = rgba(d.hl && !isGoldBase ? [255, 186, 80] : glowCol, Math.min(1, (glowA + (d.hl ? 0.35 : 0)) * a));
        c.shadowBlur = s * 0.45;
      } else c.shadowBlur = 0;
      c.fillText(d.ch, cx, y + dy);
    }
    cx += w + ls + extraLs;
  }
  // typing caret
  if (anim === 'type' && outU <= 0) {
    const k = clamp(Math.floor((b - inB) / stg) + 1, 0, n);
    let px = x0; for (let i = 0; i < k; i++) px += widths[i] + ls;
    const blink = (b - inB) / stg < n + 2 ? 1 : (Math.sin(b * Math.PI * 2) > 0 ? 1 : 0);
    c.filter = 'none'; c.shadowBlur = 12; c.shadowColor = rgba(accCol, 1);
    c.globalAlpha = blink * lineA; c.fillStyle = rgba(accCol);
    c.fillRect(px + 4, y - s * 0.8, 3, s * 0.95);
  }
  c.restore();
  return total;
}

// thin decorative line that draws from the centre outwards
function hline(c, b, x, y, w, inB, outB, col, a = 0.6) {
  const u = E.outExpo(inv(inB, inB + 1.2, b)) * (1 - E.inCubic(inv(outB, outB + 0.6, b)));
  if (u <= 0) return;
  const g = c.createLinearGradient(x - w / 2, 0, x + w / 2, 0);
  g.addColorStop(0, rgba(col, 0)); g.addColorStop(0.5, rgba(col, a)); g.addColorStop(1, rgba(col, 0));
  c.fillStyle = g; c.fillRect(x - (w / 2) * u, y - 0.75, w * u, 1.5);
}

// ---------------------------------------------------------------- background
const STARS = (() => { const r = rng(7); return Array.from({ length: 260 }, () => ({ x: r() * W, y: r() * H, z: 0.2 + r() * 0.8, ph: r() * 6.28, sp: 0.5 + r() * 2 })); })();
const BOKEH = (() => { const r = rng(99); return Array.from({ length: 22 }, () => ({ x: r() * W, y: r() * H, r: 30 + r() * 110, sp: 4 + r() * 12, ph: r() * 6.28, c: Math.floor(r() * 3) })); })();
let vignette;
function makeVignette() {
  vignette = document.createElement('canvas'); vignette.width = W; vignette.height = H;
  const g = vignette.getContext('2d');
  const gr = g.createRadialGradient(CX, CY, H * 0.35, CX, CY, H * 1.05);
  gr.addColorStop(0, 'rgba(0,0,0,0)'); gr.addColorStop(0.7, 'rgba(0,0,0,0.35)'); gr.addColorStop(1, 'rgba(0,0,0,0.85)');
  g.fillStyle = gr; g.fillRect(0, 0, W, H);
}
const GRAIN = [];
function makeGrain() {
  const r = rng(3);
  for (let k = 0; k < 4; k++) {
    const g = document.createElement('canvas'); g.width = g.height = 256;
    const gc = g.getContext('2d'), id = gc.createImageData(256, 256);
    for (let i = 0; i < id.data.length; i += 4) { const v = r() * 255; id.data[i] = id.data[i + 1] = id.data[i + 2] = v; id.data[i + 3] = 255; }
    gc.putImageData(id, 0, 0); GRAIN.push(g);
  }
}

function drawBackground(c, t, pulse) {
  const g = c.createLinearGradient(0, 0, 0, H);
  g.addColorStop(0, rgba(PAL.bg[0])); g.addColorStop(1, rgba(PAL.bg[1]));
  c.fillStyle = g; c.fillRect(0, 0, W, H);
  c.globalCompositeOperation = 'lighter';
  const nb = [
    [CX + Math.sin(t * 0.05) * 500, CY + Math.cos(t * 0.04) * 200, 1050, 0.2],
    [CX - 560 + Math.cos(t * 0.03) * 250, CY - 200 + Math.sin(t * 0.06) * 160, 820, 0.16],
    [CX + 620 + Math.sin(t * 0.045 + 2) * 230, CY + 260 + Math.cos(t * 0.035) * 150, 900, 0.15],
  ];
  nb.forEach(([x, y, r, a], i) => glow(c, x, y, r, PAL.neb[i], a * (1 + pulse * 0.35)));
  // stars
  for (const s of STARS) {
    const x = ((s.x - t * 6 * s.z) % W + W) % W;
    const tw = 0.5 + 0.5 * Math.sin(t * s.sp + s.ph);
    const a = (0.15 + 0.55 * tw) * s.z;
    c.fillStyle = rgba(mixc(WHITE, PAL.acc, 0.3), a);
    const sz = s.z > 0.85 ? 2.2 : 1.3;
    c.fillRect(x, s.y, sz, sz);
    if (s.z > 0.93) glow(c, x + 1, s.y + 1, 10, PAL.acc, a * 0.6);
  }
  for (const k of BOKEH) {
    const y = ((k.y - t * k.sp) % (H + 300) + H + 300) % (H + 300) - 150;
    const x = k.x + Math.sin(t * 0.2 + k.ph) * 40;
    glow(c, x, y, k.r, k.c === 0 ? PAL.acc : PAL.neb[k.c], 0.05 + 0.03 * Math.sin(t * 0.5 + k.ph));
  }
  c.globalCompositeOperation = 'source-over';
}

// ---------------------------------------------------------------- HUD
const CHNAME = { ch1: '种子', ch2: '导师', ch3: '烟蒂', ch4: '进化', ch5: '重仓', ch6: '定力', ch7: '再进化', ch8: '复利' };
const KEYYEARS = [1930, 1942, 1950, 1956, 1965, 1972, 1988, 1999, 2008, 2016, 2025];
function drawHUD(c, t, scene, lb, year, hudA) {
  c.save();
  const acc = PAL.acc;
  // corner marks
  c.strokeStyle = rgba(WHITE, 0.16); c.lineWidth = 1;
  const m = 46, L = 26;
  for (const [x, y, dx, dy] of [[m, m, 1, 1], [W - m, m, -1, 1], [m, H - m, 1, -1], [W - m, H - m, -1, -1]]) {
    c.beginPath(); c.moveTo(x, y + dy * L); c.lineTo(x, y); c.lineTo(x + dx * L, y); c.stroke();
  }
  c.font = `500 15px ${FAM.mono}`; c.textBaseline = 'middle';
  c.letterSpacing = '4px';
  c.textAlign = 'left';
  if (CHNAME[scene.id]) {
    const n = scene.id.slice(2);
    c.fillStyle = rgba(acc, 0.9); c.fillText(`CH.0${n}`, 84, 70);
    c.font = `500 17px ${FAM.sans}`; c.fillStyle = rgba(WHITE, 0.75); c.letterSpacing = '6px';
    c.fillText(CHNAME[scene.id], 164, 70);
    c.fillStyle = rgba(acc, 0.7); c.fillRect(84, 88, 64 * Math.min(1, lb / 2), 1.5);
  }
  c.letterSpacing = '0px';
  // timeline
  if (hudA > 0.01) {
    c.globalAlpha = hudA;
    const x0 = 260, x1 = W - 260, y = H - 62;
    const X = (yr) => x0 + (x1 - x0) * (yr - 1930) / (2025 - 1930);
    c.fillStyle = rgba(WHITE, 0.14); c.fillRect(x0, y, x1 - x0, 1);
    const xc = X(year);
    const g = c.createLinearGradient(x0, 0, xc, 0); g.addColorStop(0, rgba(acc, 0)); g.addColorStop(1, rgba(acc, 0.9));
    c.fillStyle = g; c.fillRect(x0, y - 0.5, xc - x0, 2);
    c.font = `400 12px ${FAM.mono}`; c.textAlign = 'center'; c.letterSpacing = '1px';
    for (const k of KEYYEARS) {
      const kx = X(k), near = Math.max(0, 1 - Math.abs(k - year) / 6);
      c.fillStyle = rgba(WHITE, 0.25 + near * 0.5); c.fillRect(kx - 0.5, y - 4, 1, 8);
      c.fillStyle = rgba(WHITE, 0.28 + near * 0.5); c.fillText(String(k), kx, y + 20);
    }
    c.globalCompositeOperation = 'lighter';
    glow(c, xc, y, 26, acc, 0.9); glow(c, xc, y, 8, WHITE, 0.9, 1);
    c.globalCompositeOperation = 'source-over';
    c.font = `600 22px ${FAM.cor}`; c.fillStyle = rgba(acc, 1); c.letterSpacing = '2px';
    c.fillText(String(Math.round(year)), xc, y - 22);
  }
  c.restore();
}

// ---------------------------------------------------------------- brand logo (top-right, every frame)
const LOGO_TEXT = '巴芒价值';
function drawLogo(c, a) {
  if (a <= 0.01) return;
  const right = W - 76, base = 80;
  c.save();
  c.globalAlpha = a;
  c.textBaseline = 'alphabetic'; c.textAlign = 'left';
  c.font = `700 30px ${FAM.serif}`; c.letterSpacing = '6px';
  const tw = c.measureText(LOGO_TEXT).width - 6;
  const tx = right - tw;
  c.shadowColor = 'rgba(0,0,0,0.6)'; c.shadowBlur = 10;
  c.fillStyle = goldGrad(c, tx, right, base, 30);
  c.fillText(LOGO_TEXT, tx, base);
  c.shadowColor = 'rgba(255,186,80,0.35)'; c.shadowBlur = 14;
  c.fillText(LOGO_TEXT, tx, base);
  c.shadowBlur = 0;
  c.font = `500 10.5px ${FAM.mono}`; c.letterSpacing = '3.6px';
  c.fillStyle = 'rgba(243,199,110,0.62)';
  c.fillText('BUFFETT · MUNGER', tx + 1, base + 20);
  // seal emblem
  const s = 52, sx = tx - 16 - s, sy = base - 37;
  c.shadowColor = 'rgba(255,186,80,0.5)'; c.shadowBlur = 14;
  c.strokeStyle = 'rgba(243,199,110,0.95)'; c.lineWidth = 1.8;
  c.fillStyle = 'rgba(120,70,10,0.28)';
  c.beginPath(); c.roundRect(sx, sy, s, s, 7); c.fill(); c.stroke();
  c.shadowBlur = 0; c.lineWidth = 0.8; c.strokeStyle = 'rgba(243,199,110,0.5)';
  c.beginPath(); c.roundRect(sx + 4, sy + 4, s - 8, s - 8, 4); c.stroke();
  c.font = `900 19px ${FAM.serif}`; c.letterSpacing = '0px'; c.textAlign = 'center';
  c.fillStyle = goldGrad(c, sx, sx + s, sy + s, 30);
  c.fillText('巴', sx + s / 2, sy + 23);
  c.fillText('芒', sx + s / 2, sy + 44);
  c.restore();
}

// ---------------------------------------------------------------- transitions
const BURST = (() => { const r = rng(4242); return Array.from({ length: 160 }, () => ({ a: r() * Math.PI * 2, v: 300 + r() * 1300, s: 1 + r() * 3, l: 0.6 + r() * 0.9 })); })();
const STREAKS = (() => { const r = rng(777); return Array.from({ length: 90 }, () => ({ a: r() * Math.PI * 2, r: 300 + r() * 900, l: 80 + r() * 260, w: 0.5 + r() * 2 })); })();
function drawTransition(c, t, T, strength, col) {
  const d = t - T;
  c.save(); c.globalCompositeOperation = 'lighter';
  if (d < 0 && d > -TL.BEAT) {           // converging streaks
    const u = 1 + d / TL.BEAT;
    for (const s of STREAKS) {
      const rr = s.r * (1 - E.inCubic(u) * 0.85);
      const x = CX + Math.cos(s.a) * rr, y = CY + Math.sin(s.a) * rr * 0.62;
      const x2 = CX + Math.cos(s.a) * (rr + s.l * u), y2 = CY + Math.sin(s.a) * (rr + s.l * u) * 0.62;
      c.strokeStyle = rgba(mixc(col, WHITE, 0.4), 0.5 * u * strength); c.lineWidth = s.w;
      c.beginPath(); c.moveTo(x, y); c.lineTo(x2, y2); c.stroke();
    }
    glow(c, CX, CY, 200 + 500 * u, col, 0.35 * u * u * strength);
  }
  if (d >= 0 && d < 1.8) {
    const f = Math.exp(-d / 0.16);
    glow(c, CX, CY, 1300, mixc(col, WHITE, 0.5), 0.75 * f * strength);
    const u = E.outExpo(clamp(d / 1.3));
    const R = 30 + 1500 * u;
    c.strokeStyle = rgba(mixc(col, WHITE, 0.3), (1 - u) * 0.85 * strength);
    c.lineWidth = 2 + 26 * (1 - u);
    c.filter = 'blur(6px)';
    c.beginPath(); c.ellipse(CX, CY, R, R * 0.62, 0, 0, Math.PI * 2); c.stroke();
    c.filter = 'none'; c.lineWidth = 1.5;
    c.beginPath(); c.ellipse(CX, CY, R * 0.97, R * 0.6, 0, 0, Math.PI * 2); c.stroke();
    // anamorphic flare
    const fa = Math.exp(-d / 0.35) * strength;
    const gr = c.createLinearGradient(0, 0, W, 0);
    gr.addColorStop(0, rgba(col, 0)); gr.addColorStop(0.5, rgba(mixc(col, WHITE, 0.6), 0.8 * fa)); gr.addColorStop(1, rgba(col, 0));
    c.fillStyle = gr; c.fillRect(0, CY - 2, W, 4);
    c.globalAlpha = 0.5 * fa; c.fillRect(0, CY - 18, W, 36); c.globalAlpha = 1;
    for (const p of BURST) {
      const k = d / p.l; if (k >= 1) continue;
      const dist = p.v * E.outCubic(k) * strength;
      glow(c, CX + Math.cos(p.a) * dist, CY + Math.sin(p.a) * dist * 0.62, 6 * p.s, mixc(col, WHITE, 0.5), (1 - k) * 0.9, 1);
    }
  }
  c.restore();
}
function drawSubCut(c, t, T, col) {
  const d = t - T; if (d < -0.3 || d > 1.2) return;
  c.save(); c.globalCompositeOperation = 'lighter';
  if (d < 0) glow(c, CX, CY, 900, col, 0.18 * (1 + d / 0.3));
  else {
    glow(c, CX, CY, 900, col, 0.22 * Math.exp(-d / 0.2));
    // horizontal light sweep
    const x = -400 + (W + 800) * E.outCubic(clamp(d / 0.9));
    const g = c.createLinearGradient(x - 300, 0, x + 300, 0);
    g.addColorStop(0, rgba(col, 0)); g.addColorStop(0.5, rgba(col, 0.12 * (1 - d / 1.2))); g.addColorStop(1, rgba(col, 0));
    c.fillStyle = g; c.fillRect(x - 300, 0, 600, H);
  }
  c.restore();
}

// ---------------------------------------------------------------- frame
const KICKS = TL.kickBeats().map((b) => b * TL.BEAT);
const EV = TL.events();
const SUBT = EV.subs.map((s) => s.beat * TL.BEAT);
const HITT = EV.hits.map((h) => ({ t: h.beat * TL.BEAT, k: h.k }));
function lastBefore(arr, t) { let lo = 0, hi = arr.length - 1, r = -1; while (lo <= hi) { const m = (lo + hi) >> 1; if (arr[m] <= t) { r = m; lo = m + 1; } else hi = m - 1; } return r; }

function sceneYear(sc, lb) {
  const kf = (SCENE_YEARS[sc.id]) || [[0, sc.years[0]], [sc.bars * 4, sc.years[1]]];
  if (lb <= kf[0][0]) return kf[0][1];
  for (let i = 1; i < kf.length; i++) if (lb <= kf[i][0]) return lerp(kf[i - 1][1], kf[i][1], E.inOutSine(inv(kf[i - 1][0], kf[i][0], lb)));
  return kf[kf.length - 1][1];
}
const HUD_ON = { hook: 0, title: 0, thesis: 0, outro: 0 };

function renderFrame(t) {
  GT = t;
  const B = TL.BEAT;
  const sIdx = TL.SCENES.findIndex((s, i) => t >= s.bar * TL.BAR && (i === TL.SCENES.length - 1 || t < TL.SCENES[i + 1].bar * TL.BAR));
  const sc = TL.SCENES[sIdx];
  const next = TL.SCENES[sIdx + 1];
  const T0 = sc.bar * TL.BAR, lb = (t - T0) / B;
  // palette
  const prev = TL.SCENES[sIdx - 1];
  const pu = prev ? inv(0, 1.5 * B, t - T0) : 1;
  PAL = pu < 1 ? blendPal(PAL_RGB[prev.id], PAL_RGB[sc.id], E.inOutSine(pu)) : PAL_RGB[sc.id];
  // beat pulse
  const ki = lastBefore(KICKS, t);
  const pulse = ki >= 0 ? Math.exp(-(t - KICKS[ki]) / 0.16) : 0;
  // hits
  let punch = 0, shake = 0, flash = 0;
  for (const h of HITT) {
    const d = t - h.t; if (d < 0 || d > 1.5) continue;
    const k = h.k === 'big' ? 1 : h.k === 'land' ? 0.55 : 0.3;
    punch += k * 0.03 * Math.exp(-d / 0.18);
    flash += k * 0.35 * Math.exp(-d / 0.14);
    if (h.k === 'big') shake += 14 * Math.exp(-d / 0.18);
  }
  for (const st of SUBT) { const d = t - st; if (d >= 0 && d < 0.6) punch += 0.018 * Math.exp(-d / 0.15); }

  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.globalAlpha = 1; ctx.filter = 'none';
  drawBackground(ctx, t, pulse * (TL.arrAt(t / TL.BAR).kick === 'four' ? 1 : 0.5));

  // scene layer
  lctx.setTransform(1, 0, 0, 1, 0, 0); lctx.globalAlpha = 1; lctx.filter = 'none'; lctx.globalCompositeOperation = 'source-over';
  lctx.clearRect(0, 0, W, H);
  SCENE_DRAW[sc.id](lctx, lb, { t, dur: sc.bars * 4, pulse, sc });

  // enter / exit transforms
  let sA = 1, sS = 1 + punch + pulse * 0.0035, sB = 0;
  const enterU = sIdx > 0 ? inv(0, 0.9 * B, t - T0) : 1;
  if (enterU < 1) { const e = E.outExpo(enterU); sA *= e; sS *= lerp(0.88, 1, e); sB += (1 - e) * 14; }
  if (next) {
    const T1 = next.bar * TL.BAR;
    const xu = inv(T1 - 0.75 * B, T1, t);
    if (xu > 0) { const e = E.inCubic(xu); sA *= 1 - e; sS *= 1 + 0.3 * e; sB += e * 16; }
  }
  const tail = inv(TL.TOTAL_BARS * TL.BAR - 0.2, TL.TOTAL_BARS * TL.BAR + 2.4, t);
  sA *= 1 - tail;
  const shx = shake ? (noise1(t * 40) * shake) : 0, shy = shake ? (noise1(t * 40 + 50) * shake) : 0;
  ctx.save();
  ctx.globalAlpha = sA;
  if (sB > 0.3) ctx.filter = `blur(${sB.toFixed(1)}px)`;
  ctx.translate(CX + shx, CY + shy); ctx.scale(sS, sS); ctx.translate(-CX, -CY);
  ctx.drawImage(layer, 0, 0);
  ctx.restore();
  ctx.filter = 'none';

  // transitions
  if (sIdx > 0 && t - T0 < 1.8) drawTransition(ctx, t, T0, 1, PAL_RGB[sc.id].acc);
  if (next && next.bar * TL.BAR - t < B) drawTransition(ctx, t, next.bar * TL.BAR, 1, PAL_RGB[next.id].acc);
  for (const st of SUBT) if (t - st > -0.3 && t - st < 1.2) drawSubCut(ctx, t, st, PAL.acc);
  if (flash > 0.005) { ctx.save(); ctx.globalCompositeOperation = 'lighter'; glow(ctx, CX, CY, 1100, mixc(PAL.acc, WHITE, 0.4), Math.min(0.6, flash)); ctx.restore(); }

  // HUD
  let hudA = HUD_ON[sc.id] === 0 ? 0 : 1;
  if (sc.id === 'ch1') hudA = inv(0, 2, lb);
  if (sc.id === 'outro') hudA = 0;
  ctx.save(); ctx.globalAlpha = 1 - tail;
  drawHUD(ctx, t, sc, lb, sceneYear(sc, lb), hudA);
  ctx.restore();

  // vignette + grain + global fade in/out
  ctx.drawImage(vignette, 0, 0);
  ctx.save();
  ctx.globalAlpha = 0.045;
  const gimg = GRAIN[Math.floor(t * TL.FPS) % 4];
  const ox = Math.floor(hash(Math.floor(t * TL.FPS)) * 256), oy = Math.floor(hash(Math.floor(t * TL.FPS) + 9) * 256);
  for (let y = -oy; y < H; y += 256) for (let x = -ox; x < W; x += 256) ctx.drawImage(gimg, x, y);
  ctx.restore();
  const fin = 1 - inv(0, 0.6, t);
  const fout = tail;
  const black = Math.max(fin, fout * 0.85);
  if (black > 0) { ctx.fillStyle = `rgba(0,0,0,${black})`; ctx.fillRect(0, 0, W, H); }
  drawLogo(ctx, 0.92 * Math.min(1, 0.35 + inv(0, 0.6, t)) * (1 - 0.25 * tail));
}

async function init() {
  makeVignette(); makeGrain();
  const all = Object.values(SCENE_DRAW).map((f) => f.toString()).join('') + Object.values(CHNAME).join('') + LOGO_TEXT + '0123456789$%×·—';
  const loads = [];
  for (const k in STY) loads.push(document.fonts.load(fontStr(STY[k], 40), all));
  for (const w of [300, 400, 500, 700, 900]) { loads.push(document.fonts.load(`${w} 40px ${FAM.sans}`, all)); loads.push(document.fonts.load(`${w} 40px ${FAM.serif}`, all)); }
  loads.push(document.fonts.load(`500 15px ${FAM.mono}`, all), document.fonts.load(`600 22px ${FAM.cor}`, all), document.fonts.load(`400 12px ${FAM.mono}`, all));
  await Promise.all(loads);
  await document.fonts.ready;
  window.READY = true;
}
window.renderFrame = renderFrame;
window.addEventListener('load', init);
