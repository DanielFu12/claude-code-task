// Scene definitions. Each draw(c, b, info) receives the local beat b.
/* global TL, W, H, CX, CY, E, clamp, lerp, inv, rng, noise1, fmt, rgba, mixc, hex, glow, txt, hline, STY, FAM, fontStr, goldGrad, PAL, GOLD, WHITE, CYAN, RED */

// ---------------------------------------------------------------- data
// Berkshire per-share market value & S&P 500 (incl. dividends), 1965-2025, from the 2025 shareholder letter
const BRK_R = [49.5, -3.4, 13.3, 77.8, 19.4, -4.6, 80.5, 8.1, -2.5, -48.7, 2.5, 129.3, 46.8, 14.5, 102.5, 32.8, 31.8, 38.4, 69.0, -2.7, 93.7, 14.2, 4.6, 59.3, 84.6, -23.1, 35.6, 29.8, 38.9, 25.0, 57.4, 6.2, 34.9, 52.2, -19.9, 26.6, 6.5, -3.8, 15.8, 4.3, 0.8, 24.1, 28.7, -31.8, 2.7, 21.4, -4.7, 16.8, 32.7, 27.0, -12.5, 23.4, 21.9, 2.8, 11.0, 2.4, 29.6, 4.0, 15.8, 25.5, 10.9];
const SPX_R = [10.0, -11.7, 30.9, 11.0, -8.4, 3.9, 14.6, 18.9, -14.8, -26.4, 37.2, 23.6, -7.4, 6.4, 18.2, 32.3, -5.0, 21.4, 22.4, 6.1, 31.6, 18.6, 5.1, 16.6, 31.7, -3.1, 30.5, 7.6, 10.1, 1.3, 37.6, 23.0, 33.4, 28.6, 21.0, -9.1, -11.9, -22.1, 28.7, 10.9, 4.9, 15.8, 5.5, -37.0, 26.5, 15.1, 2.1, 16.0, 32.4, 13.7, 1.4, 12.0, 21.8, -4.4, 31.5, 18.4, 28.7, -18.1, 26.3, 25.0, 17.9];
function cumulate(r, target) {
  let v = 1; const raw = [1]; for (const x of r) { v *= 1 + x / 100; raw.push(v); }
  const f = Math.pow(target / v, 1 / r.length);
  return raw.map((x, i) => x * Math.pow(f, i));
}
const BRK = cumulate(BRK_R, 60993.94);   // +6,099,294 %
const SPX = cumulate(SPX_R, 461.61);     // +46,061 %
const seriesAt = (arr, yr) => { const p = clamp(yr - 1964, 0, arr.length - 1), i = Math.floor(p), f = p - i; return i >= arr.length - 1 ? arr[arr.length - 1] : arr[i] * Math.pow(arr[i + 1] / arr[i], f); };

const BPL = [[1957, 10.4, -8.4], [1958, 40.9, 38.5], [1959, 25.9, 20.0], [1960, 22.8, -6.2], [1961, 45.9, 22.4], [1962, 13.9, -7.6], [1963, 38.7, 20.6], [1964, 27.8, 18.7], [1965, 47.2, 14.2], [1966, 20.4, -15.6], [1967, 35.9, 19.0], [1968, 58.8, 7.7], [1969, 6.8, -11.6]];

// ---------------------------------------------------------------- helpers
const vis = (b, i, o, fi = 0.8, fo = 0.6) => E.outCubic(inv(i, i + fi, b)) * (1 - E.inCubic(inv(o, o + fo, b)));
function ptxt(c, str, x, y, styName, a = 1, o = {}) {
  if (a <= 0.003) return 0;
  const st = STY[styName], s = st.s * (o.scale || 1);
  c.save();
  c.font = fontStr(st, s); c.textBaseline = 'alphabetic';
  c.letterSpacing = (((o.ls !== undefined ? o.ls : st.ls)) * s).toFixed(1) + 'px';
  const w = c.measureText(str).width;
  const align = o.align || 'center';
  const x0 = align === 'center' ? x - w / 2 : align === 'right' ? x - w : x;
  const col = o.col || st.col;
  c.fillStyle = col === 'gold' ? goldGrad(c, x0, x0 + w, y, s, o.tint) : col === 'acc' ? rgba(PAL.acc) : (Array.isArray(col) ? rgba(col) : col);
  const g = o.glow !== undefined ? o.glow : (st.glow || 0);
  if (g > 0) { c.shadowColor = rgba(col === 'gold' ? [255, 186, 80] : (Array.isArray(col) ? col : PAL.acc), g * a); c.shadowBlur = s * 0.45; }
  if (o.blur > 0.4) c.filter = `blur(${o.blur.toFixed(1)}px)`;
  c.globalAlpha = a;
  c.fillText(str, x0, y);
  c.restore();
  return w;
}
function polyPath(c, pts, prog) {
  const n = pts.length - 1, k = clamp(prog) * n, i = Math.floor(k), f = k - i;
  c.beginPath(); c.moveTo(pts[0][0], pts[0][1]);
  for (let j = 1; j <= Math.min(i, n); j++) c.lineTo(pts[j][0], pts[j][1]);
  let hx = pts[Math.min(i, n)][0], hy = pts[Math.min(i, n)][1];
  if (i < n) { hx = lerp(pts[i][0], pts[i + 1][0], f); hy = lerp(pts[i][1], pts[i + 1][1], f); c.lineTo(hx, hy); }
  return [hx, hy];
}
function glowLine(c, pts, prog, col, w = 3, a = 1, dash) {
  if (prog <= 0 || a <= 0) return null;
  c.save(); c.globalCompositeOperation = 'lighter'; c.lineJoin = 'round'; c.lineCap = 'round';
  if (dash) c.setLineDash(dash);
  c.globalAlpha = a * 0.35; c.strokeStyle = rgba(col); c.lineWidth = w * 5; c.filter = 'blur(8px)';
  polyPath(c, pts, prog); c.stroke();
  c.filter = 'none'; c.globalAlpha = a; c.lineWidth = w; c.strokeStyle = rgba(mixc(col, WHITE, 0.25));
  const head = polyPath(c, pts, prog); c.stroke();
  c.restore();
  return head;
}
function pill(c, x, y, str, col, a, o = {}) {
  if (a <= 0.003) return;
  const s = o.s || 24;
  c.save(); c.globalAlpha = a;
  c.font = `${o.w || 500} ${s}px ${FAM.sans}`; c.letterSpacing = (s * 0.12) + 'px';
  const w = c.measureText(str).width + s * 1.6, h = s * 2;
  c.fillStyle = rgba(mixc(col, [0, 0, 0], 0.75), 0.55);
  c.strokeStyle = rgba(col, 0.9); c.lineWidth = 1.5;
  c.shadowColor = rgba(col, 0.6); c.shadowBlur = 18;
  c.beginPath(); c.roundRect(x - w / 2, y - h / 2, w, h, h / 2); c.fill(); c.stroke();
  c.shadowBlur = 0; c.fillStyle = rgba(mixc(col, WHITE, 0.6)); c.textAlign = 'center'; c.textBaseline = 'middle';
  c.fillText(str, x + s * 0.06, y + 1);
  c.restore();
}
function sparkle(c, x, y, r, col, a) { glow(c, x, y, r * 3, col, a * 0.8); glow(c, x, y, r, WHITE, a, 1); }

// fibonacci sphere used for the snowball motif
const SPH = (() => { const n = 520, out = [], r = rng(11); for (let i = 0; i < n; i++) { const y = 1 - (i / (n - 1)) * 2, rad = Math.sqrt(1 - y * y), th = i * 2.39996; out.push({ x: Math.cos(th) * rad, y, z: Math.sin(th) * rad, fa: r() * Math.PI * 2, fr: 700 + r() * 900, d: r() }); } return out; })();
function snowball(c, x, y, R, rot, a, col, assemble = 1, explode = 0) {
  c.save(); c.globalCompositeOperation = 'lighter';
  const cr = Math.cos(rot), sr = Math.sin(rot), ct = Math.cos(0.4), st = Math.sin(0.4);
  glow(c, x, y, R * 2.6, col, 0.35 * a * assemble);
  for (const p of SPH) {
    let px = p.x * cr - p.z * sr, pz = p.x * sr + p.z * cr, py = p.y;
    const py2 = py * ct - pz * st; pz = py * st + pz * ct; py = py2;
    let sx = x + px * R, sy = y + py * R;
    const k = clamp(assemble * 1.25 - p.d * 0.25);
    if (k < 1) { const e = E.inOutCubic(k); sx = lerp(x + Math.cos(p.fa) * p.fr, sx, e); sy = lerp(y + Math.sin(p.fa) * p.fr * 0.7, sy, e); }
    if (explode > 0) { const d = E.outCubic(explode) * p.fr * (0.6 + p.d); sx += Math.cos(p.fa) * d; sy += Math.sin(p.fa) * d * 0.7; }
    const depth = (pz + 1) / 2;
    const aa = a * (0.25 + 0.75 * depth) * (explode > 0 ? 1 - explode : 1) * (0.3 + 0.7 * k);
    if (aa < 0.01) continue;
    c.fillStyle = rgba(mixc(col, WHITE, 0.3 + depth * 0.5), aa);
    const sz = 1.2 + depth * 2.2;
    c.fillRect(sx - sz / 2, sy - sz / 2, sz, sz);
  }
  glow(c, x, y, R * 0.9, mixc(col, WHITE, 0.5), 0.25 * a * assemble);
  c.restore();
}

function chapterCard(c, b, num, name, years, sub) {
  if (b > 4.4) return;
  const out = 3.35;
  const a = vis(b, 0, out, 1.0, 0.6);
  const acc = PAL.acc;
  // light beam
  c.save(); c.globalCompositeOperation = 'lighter';
  const bh = 520 * E.outExpo(inv(0, 1.4, b));
  const g = c.createLinearGradient(0, CY - bh / 2, 0, CY + bh / 2);
  g.addColorStop(0, rgba(acc, 0)); g.addColorStop(0.5, rgba(acc, 0.9 * a)); g.addColorStop(1, rgba(acc, 0));
  c.fillStyle = g; c.fillRect(838, CY - bh / 2, 2, bh);
  glow(c, 839, CY, 260, acc, 0.25 * a);
  c.restore();
  // big outlined numeral
  c.save();
  const e = E.outExpo(inv(0, 1.6, b));
  c.font = `500 400px ${FAM.cor}`; c.textAlign = 'right'; c.textBaseline = 'alphabetic';
  c.globalAlpha = a;
  const gr = c.createLinearGradient(0, CY - 260, 0, CY + 140);
  gr.addColorStop(0, rgba(mixc(acc, WHITE, 0.5), 0.95)); gr.addColorStop(1, rgba(acc, 0.05));
  c.strokeStyle = gr; c.lineWidth = 1.6;
  c.shadowColor = rgba(acc, 0.8); c.shadowBlur = 24;
  c.strokeText(num, 790 - (1 - e) * 80, CY + 140);
  c.globalAlpha = a * 0.08; c.fillStyle = rgba(acc); c.fillText(num, 790 - (1 - e) * 80, CY + 140);
  c.restore();
  txt(c, b, `CHAPTER ${num}`, 892, CY - 118, 'label', 0.3, out);
  txt(c, b, name, 886, CY + 30, 'mega', 0.4, out, { align: 'left', anim: 'blur', scale: 0.9 });
  txt(c, b, years, 892, CY + 100, 'label', 0.9, out, { col: '#e9e4da', ls: 0.3, scale: 1.15 });
  txt(c, b, sub, 892, CY + 162, 'bodyL', 1.2, out, { align: 'left' });
}

// ---------------------------------------------------------------- scenes
const SCENE_YEARS = {
  ch1: [[0, 1930], [4, 1942], [16, 1942], [20, 1949], [28, 1949]],
  ch2: [[0, 1950], [8, 1951], [52, 1954], [56, 1956]],
  ch3: [[0, 1956], [20, 1957], [28, 1969], [36, 1962], [44, 1969], [48, 1969]],
  ch4: [[0, 1970], [20, 1972], [48, 1967], [64, 1967]],
  ch5: [[0, 1973], [16, 1976], [28, 1988], [40, 1990], [64, 1998]],
  ch6: [[0, 1999], [4, 1995], [14, 2000], [20, 2008], [40, 2009], [48, 2011]],
  ch7: [[0, 2010], [14, 2016], [30, 2025], [40, 2025]],
  ch8: [[0, 1965], [4.5, 1965], [19, 2025], [56, 2025]],
};

const SCENE_DRAW = {
  // ============================================================ HOOK
  hook(c, b) {
    const acc = PAL.acc;
    // a single breathing point of light
    const dotA = vis(b, 0, 7.4, 1.5);
    c.save(); c.globalCompositeOperation = 'lighter';
    glow(c, CX, 522, 70 + 12 * Math.sin(b * 1.6), acc, 0.55 * dotA);
    glow(c, CX, 522, 7, WHITE, dotA, 1);
    c.restore();
    txt(c, b, '1965', CX, 440, 'year', 0.6, 7.3, { anim: 'blur' });
    txt(c, b, '假如你把 [1 万美元] 交给一个人', CX, 650, 'h2', 2.2, 7.3);
    txt(c, b, '六十一年后，他会还给你多少？', CX, 722, 'bodyL', 4.4, 7.3);

    // compounding counter
    if (b > 7.6 && b < 24) {
      const a = vis(b, 7.8, 22.6, 0.8);
      const p = E.inOutSine(inv(8.2, 19.6, b));
      const yr = 1965 + 60 * p;
      const pts = [];
      for (let y = 1965; y <= 2025.01; y += 0.25) {
        const v = seriesAt(BRK, y);
        pts.push([200 + (y - 1965) / 60 * 1520, 900 - (v / 60994) * 600]);
      }
      // grid
      c.save(); c.globalAlpha = a * 0.5;
      c.strokeStyle = rgba(WHITE, 0.06); c.lineWidth = 1;
      for (let i = 0; i <= 6; i++) { c.beginPath(); c.moveTo(200, 900 - i * 100); c.lineTo(1720, 900 - i * 100); c.stroke(); }
      c.restore();
      // area
      c.save(); c.globalAlpha = a;
      const head = polyPath(c, pts, p);
      c.lineTo(head[0], 900); c.lineTo(200, 900); c.closePath();
      const ga = c.createLinearGradient(0, 300, 0, 900);
      ga.addColorStop(0, rgba(acc, 0.32)); ga.addColorStop(1, rgba(acc, 0));
      c.fillStyle = ga; c.fill();
      c.restore();
      const h = glowLine(c, pts, p, acc, 3, a);
      if (h) { c.save(); c.globalCompositeOperation = 'lighter'; sparkle(c, h[0], h[1], 9, acc, a); c.restore(); }
      const v = 10000 * seriesAt(BRK, yr);
      const land = inv(19.6, 20.4, b);
      const pop = 1 + 0.1 * Math.exp(-Math.max(0, b - 20) * 3) * (b > 20 ? 1 : 0);
      ptxt(c, `${Math.floor(yr)}`, CX, 340, 'label', a, { col: '#e8e2d4', scale: 1.6, ls: 0.4 });
      ptxt(c, '$' + fmt(b >= 19.6 ? 609939400 : v), CX, 540, 'num', a, { scale: pop * (0.78 + 0.22 * land) });
      txt(c, b, '约 [6.1 亿美元] · 增长约 6.1 万倍', CX, 640, 'body', 20.3, 22.6);
      txt(c, b, '按伯克希尔·哈撒韦每股市值计算 · 1965—2025', CX, 690, 'small', 20.8, 22.6);
    }
    txt(c, b, '没有内幕消息，没有复杂模型，也没有频繁交易', CX, 470, 'h2', 23, 27.6);
    txt(c, b, '只有一种 [朴素到近乎笨拙] 的思考方式', CX, 550, 'body', 24.6, 27.6);
    // the snowball forms
    if (b > 25.5) {
      const as = inv(26, 31.6, b);
      snowball(c, CX, 500, 40 + 70 * E.inOutCubic(inv(28, 32, b)), b * 0.5, inv(25.6, 27, b), PAL.acc, as);
      txt(c, b, '这个人，叫——', CX, 760, 'bodyL', 28.6, 31.4, { scale: 1.1 });
    }
  },

  // ============================================================ TITLE
  title(c, b) {
    const acc = PAL.acc;
    snowball(c, CX, 500, 110, 4 + b * 0.5, 1, acc, 1, clamp(b / 1.6));
    c.save(); c.globalCompositeOperation = 'lighter';
    const f = Math.exp(-b / 1.2);
    const gr = c.createLinearGradient(0, 0, W, 0);
    gr.addColorStop(0, rgba(acc, 0)); gr.addColorStop(0.5, rgba(mixc(acc, WHITE, 0.6), 0.9 * f + 0.15)); gr.addColorStop(1, rgba(acc, 0));
    c.fillStyle = gr; c.fillRect(0, 498, W, 3);
    // drifting gold dust
    const r = rng(5);
    for (let i = 0; i < 140; i++) {
      const a0 = r() * Math.PI * 2, sp = 60 + r() * 260, x = CX + Math.cos(a0) * (sp * (b * 0.35 + 0.5)) * 2.2, y = 500 + Math.sin(a0) * sp * (b * 0.35 + 0.5);
      glow(c, x, y, 2 + r() * 4, acc, 0.6 * (1 - inv(6, 12, b)) * r(), 1);
    }
    c.restore();
    txt(c, b, '滚雪球的人', CX, 565, 'mega', 0.05, 10.6, { anim: 'blur', scale: 1.08 });
    hline(c, b, CX, 628, 760, 1.2, 10.6, acc, 0.7);
    txt(c, b, '沃伦·巴菲特的投资思想进化史', CX, 690, 'bodyL', 1.6, 10.6, { ls: 0.38, scale: 1.12, col: '#e7e1d6' });
    txt(c, b, 'WARREN  EDWARD  BUFFETT  ·  1930 —', CX, 760, 'label', 2.6, 10.6, { scale: 1.05 });
  },

  // ============================================================ THESIS
  thesis(c, b) {
    txt(c, b, '读懂巴菲特，只需要读懂 [三次进化]', CX, 290, 'h2', 0.2, 15.3);
    const nodes = [
      { x: 480, col: hex('#5fe1ff'), n: 'I', t: '买得便宜', s: '格雷厄姆 · 安全边际', e: '1950s', b: 4 },
      { x: 960, col: hex('#c9a7ff'), n: 'II', t: '买得好', s: '芒格 · 伟大的企业', e: '1970s', b: 8 },
      { x: 1440, col: hex('#f3c76e'), n: 'III', t: '拿得久', s: '时间 · 复利的雪球', e: '一生', b: 12 },
    ];
    const y = 540, out = 15.3, oa = 1 - E.inCubic(inv(out, out + 0.6, b));
    // connecting line
    for (let i = 0; i < 2; i++) {
      const p = E.inOutCubic(inv(nodes[i].b + 0.3, nodes[i + 1].b, b));
      const pts = [[nodes[i].x + 80, y], [nodes[i + 1].x - 80, y]];
      const h = glowLine(c, pts, p, mixc(nodes[i].col, nodes[i + 1].col, p), 2, 0.9 * oa);
      if (h && p < 1) { c.save(); c.globalCompositeOperation = 'lighter'; sparkle(c, h[0], h[1], 6, nodes[i + 1].col, oa); c.restore(); }
      if (p >= 1) { // flowing particles
        c.save(); c.globalCompositeOperation = 'lighter';
        for (let k = 0; k < 5; k++) { const u = ((b * 0.35 + k / 5) % 1); glow(c, lerp(pts[0][0], pts[1][0], u), y, 5, nodes[i + 1].col, 0.8 * oa, 1); }
        c.restore();
      }
    }
    for (const nd of nodes) {
      const u = inv(nd.b - 0.1, nd.b + 0.9, b);
      if (u <= 0) continue;
      const e = E.outBack(u), a = Math.min(1, u * 2) * oa;
      c.save(); c.globalCompositeOperation = 'lighter';
      glow(c, nd.x, y, 160 * e, nd.col, 0.35 * a);
      c.strokeStyle = rgba(nd.col, 0.9 * a); c.lineWidth = 2; c.shadowColor = rgba(nd.col, 1); c.shadowBlur = 20;
      c.beginPath(); c.arc(nd.x, y, 72 * e, 0, Math.PI * 2); c.stroke();
      c.lineWidth = 1; c.globalAlpha = 0.5 * a;
      c.beginPath(); c.arc(nd.x, y, 86 * e, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * E.outCubic(u)); c.stroke();
      c.restore();
      ptxt(c, nd.n, nd.x, y + 18, 'numS', a, { col: Array.from(mixc(nd.col, WHITE, 0.3)), scale: 0.7, glow: 0.6 });
      txt(c, b, nd.t, nd.x, y + 175, 'h2', nd.b + 0.2, out, { col: rgba(mixc(nd.col, WHITE, 0.55)), scale: 1.05 });
      txt(c, b, nd.s, nd.x, y + 228, 'bodyL', nd.b + 0.6, out, { scale: 0.92 });
      txt(c, b, nd.e, nd.x, y - 120, 'label', nd.b + 0.3, out, { acc: nd.col });
    }
  },

  // ============================================================ CH1 SEED
  ch1(c, b) {
    chapterCard(c, b, '01', '种子', '1930 — 1949', '一切，始于一个对数字着迷的孩子');
    const acc = PAL.acc;
    // first stock
    if (b > 3.8 && b < 16.6) {
      txt(c, b, '1942 · 11 岁', 260, 238, 'year', 4.1, 15.4, { align: 'left', scale: 0.62, anim: 'rise' });
      txt(c, b, '他买下人生第一支股票：[城市服务公司] 优先股 × 3 股', 262, 306, 'body', 4.8, 15.4, { align: 'left' });
      const a = vis(b, 5.4, 15.4);
      const X0 = 300, X1 = 1640, Y0 = 860, Y1 = 400;
      const rs = E.inOutCubic(inv(12.5, 13.6, b));
      const pMin = lerp(20, 0, rs), pMax = lerp(46, 215, rs);
      const Y = (p) => Y0 - (p - pMin) / (pMax - pMin) * (Y0 - Y1);
      // axis ticks
      c.save(); c.globalAlpha = a; c.strokeStyle = rgba(WHITE, 0.07); c.fillStyle = rgba(WHITE, 0.35);
      c.font = `400 14px ${FAM.mono}`; c.textAlign = 'right';
      const step = rs < 0.5 ? 5 : 50;
      for (let p = Math.ceil(pMin / step) * step; p <= pMax; p += step) { const yy = Y(p); if (yy < Y1 - 5 || yy > Y0 + 5) continue; c.beginPath(); c.moveTo(X0, yy); c.lineTo(X1, yy); c.stroke(); c.fillText('$' + p, X0 - 14, yy + 5); }
      c.restore();
      const key = [[0, 38], [0.12, 34], [0.25, 29], [0.32, 27], [0.4, 31], [0.47, 36], [0.52, 40]];
      const ghost = [[0.52, 40], [0.6, 52], [0.7, 85], [0.78, 110], [0.86, 150], [0.93, 180], [1, 202]];
      const mk = (ks, seed) => { const r = rng(seed), out = []; for (let i = 0; i < ks.length - 1; i++) for (let j = 0; j < 8; j++) { const f = j / 8; const x = lerp(ks[i][0], ks[i + 1][0], f), p = lerp(ks[i][1], ks[i + 1][1], f) + (j ? (r() - 0.5) * 2.2 : 0); out.push([x, p]); } out.push(ks[ks.length - 1]); return out; };
      const P1 = mk(key, 3), P2 = mk(ghost, 8);
      const toXY = (arr) => arr.map(([x, p]) => [lerp(X0, X1, x), Y(p)]);
      const p1 = E.inOutSine(inv(6, 11, b));
      const h1 = glowLine(c, toXY(P1), p1, acc, 3, a);
      if (h1 && p1 < 1) { c.save(); c.globalCompositeOperation = 'lighter'; sparkle(c, h1[0], h1[1], 7, acc, a); c.restore(); }
      const p2 = E.inOutCubic(inv(12.8, 14.6, b));
      const h2 = glowLine(c, toXY(P2), p2, hex('#ff8f6b'), 2.5, a * 0.95, [10, 9]);
      if (h2 && p2 > 0) { c.save(); c.globalCompositeOperation = 'lighter'; sparkle(c, h2[0], h2[1], 8, hex('#ff8f6b'), a); c.restore(); }
      const pt = (x, p) => [lerp(X0, X1, x), Y(p)];
      const marks = [[0, 38, '买入 $38', 6.6], [0.32, 27, '跌到 $27 · 煎熬', 8.4], [0.52, 40, '回本即卖 $40 · 赚了 5 美元', 10.4]];
      for (const [x, p, s, t0] of marks) {
        const [mx, my] = pt(x, p); const ma = vis(b, t0, 15.4);
        c.save(); c.globalCompositeOperation = 'lighter'; sparkle(c, mx, my, 5, acc, ma); c.restore();
        txt(c, b, s, mx, my + (p === 27 ? 52 : -26), 'small', t0, 15.4, { col: '#efe7da', scale: 1.05 });
      }
      if (b > 13) { const [ex, ey] = pt(1, 202); txt(c, b, '此后涨到 [$202]', ex - 10, ey + 64, 'h2', 13.6, 15.4, { align: 'right', scale: 0.9 }); }
    }
    // lesson
    txt(c, b, 'LESSON 01', CX, 410, 'label', 16.1, 19.4);
    txt(c, b, '人生第一课：[耐心]', CX, 510, 'h1', 16.3, 19.4, { col: '#f6f1e7', scale: 0.85 });
    hline(c, b, CX, 560, 640, 16.6, 19.4, acc);
    txt(c, b, '不被买入价绑架，也不急于卖出——这一课，他用了一生去实践', CX, 625, 'body', 17.2, 19.4);
    // the book
    if (b > 19.8) {
      const a = vis(b, 20, 27.4);
      const bx = 600, by = 545, rot = -0.1 + 0.04 * Math.sin(b * 0.4);
      c.save(); c.globalAlpha = a; c.translate(bx, by); c.rotate(rot);
      c.globalCompositeOperation = 'lighter';
      for (let i = 0; i < 18; i++) { const ang = -Math.PI / 2 + (i - 8.5) * 0.12 + Math.sin(b * 0.5 + i) * 0.02; c.strokeStyle = rgba(acc, 0.05 + 0.04 * Math.sin(i * 1.7 + b)); c.lineWidth = 18; c.beginPath(); c.moveTo(0, -60); c.lineTo(Math.cos(ang) * 900, Math.sin(ang) * 900); c.stroke(); }
      glow(c, 0, -40, 380, acc, 0.4);
      c.globalCompositeOperation = 'source-over';
      const g = c.createLinearGradient(-170, -230, 170, 230); g.addColorStop(0, '#2a1d10'); g.addColorStop(1, '#120c07');
      c.fillStyle = g; c.shadowColor = rgba(acc, 0.6); c.shadowBlur = 50;
      c.beginPath(); c.roundRect(-170, -230, 340, 460, 8); c.fill(); c.shadowBlur = 0;
      c.strokeStyle = rgba(acc, 0.85); c.lineWidth = 1.5; c.strokeRect(-150, -210, 300, 420);
      c.strokeStyle = rgba(acc, 0.4); c.strokeRect(-140, -200, 280, 400);
      c.fillStyle = goldGrad(c, -120, 120, -40, 40); c.textAlign = 'center';
      c.font = `600 34px ${FAM.cor}`; c.letterSpacing = '4px';
      c.fillText('THE', 0, -95); c.fillText('INTELLIGENT', 0, -48); c.fillText('INVESTOR', 0, -1);
      c.font = `500 15px ${FAM.mono}`; c.letterSpacing = '5px'; c.fillStyle = rgba(acc, 0.8);
      c.fillText('BENJAMIN GRAHAM', 0, 150);
      c.fillRect(-60, 40, 120, 1);
      c.restore();
      txt(c, b, '1949 · 19 岁', 900, 352, 'year', 20.3, 27.4, { align: 'left', scale: 0.62 });
      txt(c, b, '他读到一本改变一生的书', 902, 440, 'h2', 21, 27.4, { align: 'left' });
      txt(c, b, '《聪明的投资者》', 892, 568, 'h1', 22, 27.4, { align: 'left' });
      txt(c, b, '本杰明·格雷厄姆 著 · 价值投资的奠基之作', 904, 630, 'bodyL', 22.8, 27.4, { align: 'left' });
      txt(c, b, '“迄今为止，最好的一本投资书。” —— 巴菲特', 904, 720, 'body', 24, 27.4, { align: 'left', col: '#efe4cf' });
    }
  },

  // ============================================================ CH2 GRAHAM
  ch2(c, b) {
    chapterCard(c, b, '02', '导师', '1950 — 1956', '本杰明·格雷厄姆的三把钥匙');
    const acc = PAL.acc;
    txt(c, b, '为了师从格雷厄姆，他考入 [哥伦比亚商学院]', CX, 480, 'h2', 4.2, 7.4);
    txt(c, b, '毕业时，他提出不要薪水为老师工作——被拒绝了', CX, 565, 'body', 5.4, 7.4);

    // KEY 01 — a stock is a piece of a business
    if (b > 7.8 && b < 20.6) {
      const a = vis(b, 8, 19.4);
      txt(c, b, 'KEY 01 · 股权思维', CX, 196, 'label', 8.1, 19.4);
      // ticker box
      const tx = 520, ty = 520;
      c.save(); c.globalAlpha = a;
      c.strokeStyle = rgba(acc, 0.6); c.lineWidth = 1.5; c.fillStyle = rgba(acc, 0.05);
      c.beginPath(); c.roundRect(tx - 210, ty - 90, 420, 180, 14); c.fill(); c.stroke();
      c.font = `600 30px ${FAM.mono}`; c.textAlign = 'left'; c.fillStyle = rgba(acc);
      c.fillText('CITY SVC', tx - 180, ty - 30);
      const pr = 38 + noise1(b * 4) * 2.5, ch = noise1(b * 4 + 3);
      c.font = `700 54px ${FAM.mono}`; c.fillStyle = rgba(WHITE, 0.92);
      c.fillText(pr.toFixed(2), tx - 180, ty + 48);
      c.font = `500 26px ${FAM.mono}`; c.fillStyle = ch > 0 ? '#4ade80' : '#f87171';
      c.fillText((ch > 0 ? '▲ ' : '▼ ') + Math.abs(ch * 1.5).toFixed(2), tx + 50, ty + 46);
      c.restore();
      // particles flowing to the building
      const flow = vis(b, 9, 19.4);
      c.save(); c.globalCompositeOperation = 'lighter';
      for (let i = 0; i < 40; i++) {
        const u = ((b * 0.45 + i / 40) % 1), x = lerp(760, 1120, u), y = ty + Math.sin(u * Math.PI * 2 + i) * 30 * Math.sin(u * Math.PI);
        glow(c, x, y, 4, acc, flow * Math.sin(u * Math.PI), 1);
      }
      c.restore();
      // building
      const bx = 1380, by = 650, bp = E.inOutCubic(inv(9, 12.5, b));
      const outline = [[-220, 0], [-220, -160], [-150, -220], [-150, -160], [-80, -220], [-80, -160], [-10, -220], [-10, -160], [60, -160], [60, -330], [100, -330], [100, -160], [220, -160], [220, 0], [-220, 0]];
      glowLine(c, outline.map(([x, y]) => [bx + x, by + y]), bp, acc, 2, a);
      c.save(); c.globalCompositeOperation = 'lighter';
      for (let i = 0; i < 4; i++) for (let j = 0; j < 2; j++) {
        const wa = inv(12 + (i + j * 4) * 0.25, 12.4 + (i + j * 4) * 0.25, b) * a;
        c.fillStyle = rgba(mixc(acc, WHITE, 0.5), 0.75 * wa); c.fillRect(bx - 190 + i * 70, by - 120 + j * 60, 34, 30);
        glow(c, bx - 173 + i * 70, by - 105 + j * 60, 36, acc, 0.4 * wa);
      }
      // smoke from the chimney
      for (let i = 0; i < 14; i++) { const u = ((b * 0.3 + i / 14) % 1); glow(c, bx + 80 + Math.sin(u * 6 + i) * 18 + u * 60, by - 340 - u * 160, 10 + u * 30, acc, 0.12 * (1 - u) * a); }
      c.restore();
      const tags = [['厂房', -260, -250], ['品牌', 250, -250], ['员工', -280, 40], ['现金流', 270, 40]];
      tags.forEach(([s, dx, dy], i) => pill(c, bx + dx, by + dy, s, acc, vis(b, 12.6 + i * 0.5, 19.4)));
      txt(c, b, '股票不是屏幕上跳动的代码', CX, 840, 'h2', 10, 19.4);
      txt(c, b, '而是一家 [真实企业] 的部分所有权', CX, 915, 'h2', 13, 19.4);
    }

    // KEY 02 — Mr. Market
    if (b > 19.8 && b < 36.6) {
      const a = vis(b, 20, 35.4);
      txt(c, b, 'KEY 02 · 市场先生', CX, 190, 'label', 20.1, 35.4);
      txt(c, b, '他每天都来报价，情绪却极不稳定', CX, 258, 'bodyL', 21.2, 35.4);
      const X0 = 220, X1 = 1700, base = 560;
      const val = (u) => base - u * 60;
      const price = (u) => val(u) - (Math.sin(u * 13) * 120 + Math.sin(u * 31 + 1) * 45 + noise1(u * 60) * 25) * (0.6 + 0.4 * Math.sin(u * 3 + 1));
      const vp = [], pp = [];
      for (let i = 0; i <= 220; i++) { const u = i / 220; vp.push([lerp(X0, X1, u), val(u)]); pp.push([lerp(X0, X1, u), price(u)]); }
      const pr = E.inOutSine(inv(20.6, 30, b));
      glowLine(c, vp, pr, CYAN, 2.5, a);
      const head = glowLine(c, pp, pr, hex('#ff5fa2'), 2, a);
      if (head && pr < 1) { c.save(); c.globalCompositeOperation = 'lighter'; sparkle(c, head[0], head[1], 6, hex('#ff5fa2'), a); c.restore(); }
      ptxt(c, '内在价值', X1 + 10, val(1) - 14, 'small', a * inv(28, 29, b), { align: 'right', col: Array.from(CYAN) });
      // extremes
      let hiI = 0, loI = 0; for (let i = 0; i < pp.length; i++) { if (pp[i][1] < pp[hiI][1]) hiI = i; if (pp[i][1] > pp[loI][1]) loI = i; }
      const hiP = pp[hiI], loP = pp[loI];
      if (b > 24.5) { const ma = vis(b, 25, 35.4); c.save(); c.globalCompositeOperation = 'lighter'; sparkle(c, hiP[0], hiP[1], 7, hex('#ff8f6b'), ma); sparkle(c, loP[0], loP[1], 7, hex('#4ade80'), vis(b, 27, 35.4)); c.restore(); }
      txt(c, b, '狂喜：高价把股票卖给你', hiP[0], hiP[1] - 26, 'small', 25, 35.4, { col: '#ffb49a', scale: 1.1 });
      txt(c, b, '绝望：低价把股票甩给你', loP[0], loP[1] + 48, 'small', 27, 35.4, { col: '#86efac', scale: 1.1 });
      txt(c, b, '“市场先生是来为你服务的，而不是来指导你的。”', CX, 850, 'quote', 30, 35.4, { anim: 'type', stg: 0.09 });
      txt(c, b, '—— 巴菲特，1987 年致股东信', CX, 915, 'small', 33, 35.4);
    }

    // KEY 03 — margin of safety
    if (b > 35.8 && b < 52.6) {
      const a = vis(b, 36, 51.4);
      txt(c, b, 'KEY 03 · 安全边际', CX, 190, 'label', 36.1, 51.4);
      const base = 700, H1 = 400, H6 = 240, bw = 170;
      const g1 = E.outCubic(inv(36.8, 39.2, b)), g2 = E.outCubic(inv(37.6, 40, b));
      const lx = 760, rx = 1160;
      c.save(); c.globalAlpha = a;
      // intrinsic value bar (outline)
      c.strokeStyle = rgba(CYAN, 0.9); c.lineWidth = 2; c.shadowColor = rgba(CYAN, 0.9); c.shadowBlur = 20;
      c.strokeRect(lx - bw / 2, base - H1 * g1, bw, H1 * g1);
      const gv = c.createLinearGradient(0, base - H1, 0, base); gv.addColorStop(0, rgba(CYAN, 0.28)); gv.addColorStop(1, rgba(CYAN, 0.04));
      c.fillStyle = gv; c.fillRect(lx - bw / 2, base - H1 * g1, bw, H1 * g1);
      // price bar (gold)
      c.shadowColor = rgba(GOLD, 0.9);
      const gp = c.createLinearGradient(0, base - H6, 0, base); gp.addColorStop(0, rgba(GOLD2, 0.95)); gp.addColorStop(1, rgba(hex('#a8701f'), 0.8));
      c.fillStyle = gp; c.fillRect(rx - bw / 2, base - H6 * g2, bw, H6 * g2);
      c.shadowBlur = 0;
      // safety gap
      const gpU = E.outCubic(inv(41.5, 43.8, b));
      if (gpU > 0) {
        c.setLineDash([8, 8]); c.strokeStyle = rgba(CYAN, 0.7); c.lineWidth = 1.5;
        c.beginPath(); c.moveTo(lx + bw / 2, base - H1); c.lineTo(lx + bw / 2 + (rx + bw / 2 - lx - bw / 2) * gpU, base - H1); c.stroke(); c.setLineDash([]);
        const gh = (H1 - H6) * gpU;
        c.fillStyle = rgba(hex('#34f5a0'), 0.18); c.fillRect(rx - bw / 2, base - H6 - gh, bw, gh);
        c.strokeStyle = rgba(hex('#34f5a0'), 0.9); c.lineWidth = 2; c.shadowColor = rgba(hex('#34f5a0'), 1); c.shadowBlur = 24;
        c.strokeRect(rx - bw / 2, base - H6 - gh, bw, gh);
        c.save(); c.beginPath(); c.rect(rx - bw / 2, base - H6 - gh, bw, gh); c.clip();
        c.strokeStyle = rgba(hex('#34f5a0'), 0.35); c.lineWidth = 2; c.shadowBlur = 0;
        for (let k = -10; k < 20; k++) { const o = (k * 22 + b * 18) % 440; c.beginPath(); c.moveTo(rx - bw / 2 + o - 200, base); c.lineTo(rx - bw / 2 + o, base - 400); c.stroke(); }
        c.restore();
      }
      c.restore();
      ptxt(c, '$1.00', lx, base - H1 * g1 - 22, 'numS', a * g1, { col: Array.from(CYAN), scale: 0.6 });
      ptxt(c, '$0.60', rx, base - H6 * g2 - 22, 'numS', a * g2 * (1 - gpU), { scale: 0.6 });
      ptxt(c, '内在价值', lx, base + 42, 'body', a * g1, { scale: 0.85, col: '#bfefff' });
      ptxt(c, '买入价格', rx, base + 42, 'body', a * g2, { scale: 0.85, col: '#ffe2a8' });
      txt(c, b, '安全边际 40%', rx + bw / 2 + 24, base - (H1 + H6) / 2 + 12, 'h2', 43.6, 51.4, { align: 'left', col: '#7dffc4', scale: 0.72 });
      txt(c, b, '用 [6 毛钱]，买 [1 块钱] 的东西', CX, 850, 'h2', 44.4, 51.4);
      txt(c, b, '就算判断出错，也留有足够的缓冲——这是投资的第一道保险', CX, 918, 'bodyL', 46, 51.4);
    }
    txt(c, b, '1954 年，格雷厄姆终于雇用了他', CX, 480, 'h2', 52.2, 55.4);
    txt(c, b, '两年后老师退休，[25 岁] 的他回到故乡奥马哈', CX, 565, 'body', 53.3, 55.4);
  },

  // ============================================================ CH3 CIGAR BUTT
  ch3(c, b) {
    chapterCard(c, b, '03', '烟蒂', '1956 — 1969', '把格雷厄姆的方法用到极致');
    const acc = PAL.acc;
    if (b > 3.8 && b < 8.6) {
      const a = vis(b, 4, 7.4);
      c.save(); c.globalCompositeOperation = 'lighter';
      for (let i = 0; i < 8; i++) {
        const u = inv(4.2 + i * 0.25, 4.8 + i * 0.25, b), x = CX - 350 + i * 100, y = 340;
        const r = i === 7 ? 6 : 18;
        glow(c, x, y, r * 4 * E.outBack(u), i === 7 ? WHITE : acc, 0.5 * u * a);
        glow(c, x, y, r * 0.6, WHITE, u * a, 1);
      }
      c.restore();
      txt(c, b, '7 位亲友', CX - 50, 290, 'small', 4.6, 7.4);
      txt(c, b, '巴菲特', CX + 350, 290, 'small', 6, 7.4, { col: '#ffffff' });
      txt(c, b, '1956 年，[巴菲特合伙公司] 成立', CX, 500, 'h2', 4.3, 7.4);
      txt(c, b, '7 位亲友出资 10.5 万美元——他自己只投了 [100 美元]', CX, 585, 'body', 5.4, 7.4);
    }
    // cigar butt
    if (b > 7.8 && b < 20.6) {
      const a = vis(b, 8, 19.4);
      const cx0 = 560, cy0 = 590;
      c.save(); c.globalAlpha = a; c.translate(cx0, cy0); c.rotate(-0.18);
      const g = c.createLinearGradient(0, -34, 0, 34); g.addColorStop(0, '#8a5a34'); g.addColorStop(0.5, '#5a3418'); g.addColorStop(1, '#2a160a');
      c.fillStyle = g; c.beginPath(); c.roundRect(-230, -32, 300, 64, 10); c.fill();
      c.fillStyle = '#b8862e'; c.fillRect(-150, -32, 40, 64); c.fillStyle = 'rgba(255,230,160,0.35)'; c.fillRect(-150, -32, 40, 4);
      // ash & ember
      c.fillStyle = '#4a4440'; c.beginPath(); c.roundRect(60, -30, 34, 60, 6); c.fill();
      const fl = 0.75 + 0.25 * noise1(b * 6);
      c.globalCompositeOperation = 'lighter';
      glow(c, 96, 0, 120 * fl, hex('#ff5a1a'), 0.9);
      glow(c, 96, 0, 40, hex('#ffd08a'), fl, 1);
      c.restore();
      // smoke
      c.save(); c.globalCompositeOperation = 'lighter';
      for (let i = 0; i < 46; i++) {
        const u = ((b * 0.16 + i / 46) % 1);
        const x = cx0 + 92 + Math.sin(u * 7 + i * 0.4) * (20 + u * 90) + u * 60, y = cy0 - 20 - u * 430;
        glow(c, x, y, 14 + u * 70, hex('#d9c7b8'), 0.07 * (1 - u) * Math.min(1, u * 6) * a);
      }
      c.restore();
      txt(c, b, 'CIGAR BUTT INVESTING', 1000, 350, 'label', 8.3, 19.4, { align: 'left' });
      txt(c, b, '烟蒂股', 994, 470, 'h1', 8.8, 19.4, { align: 'left', scale: 1.15 });
      txt(c, b, '在街边捡起别人丢掉的烟蒂', 1002, 560, 'body', 10.4, 19.4, { align: 'left' });
      txt(c, b, '还能免费吸上 [最后一口]', 1002, 620, 'body', 12, 19.4, { align: 'left' });
      txt(c, b, '生意平庸也无妨——只要价格足够便宜', 1002, 700, 'bodyL', 14, 19.4, { align: 'left' });
    }
    // partnership record
    if (b > 19.8 && b < 36.6) {
      const a = vis(b, 20, 35.4);
      txt(c, b, '巴菲特合伙公司 vs 道琼斯指数 · 年度回报', CX, 196, 'label', 20.1, 35.4);
      const base = 600, sc = 4.2, X0 = 330, gw = 98;
      BPL.forEach(([yr, p, d], i) => {
        const u = E.outCubic(inv(20.5 + i * 0.5, 21.6 + i * 0.5, b));
        const x = X0 + i * gw;
        c.save(); c.globalAlpha = a;
        const hP = p * sc * u;
        const g = c.createLinearGradient(0, base - hP, 0, base); g.addColorStop(0, rgba(hex('#ffcf7a'))); g.addColorStop(1, rgba(hex('#c2410c'), 0.7));
        c.fillStyle = g; c.shadowColor = rgba(acc, 0.8); c.shadowBlur = 16;
        c.fillRect(x - 30, base - hP, 30, hP);
        c.shadowBlur = 0;
        const hD = d * sc * u;
        c.fillStyle = d >= 0 ? rgba(hex('#8aa4c8'), 0.75) : rgba(hex('#ff4d5e'), 0.8);
        if (d >= 0) c.fillRect(x + 4, base - hD, 26, hD); else c.fillRect(x + 4, base, 26, -hD);
        c.font = `500 15px ${FAM.mono}`; c.textAlign = 'center'; c.fillStyle = rgba(WHITE, 0.45 * u);
        c.fillText(String(yr), x, base + (d < 0 ? -d * sc + 26 : 26) + 6);
        c.fillStyle = rgba(hex('#ffd9a0'), 0.9 * u); c.font = `600 15px ${FAM.mono}`;
        c.fillText(p.toFixed(1), x - 15, base - hP - 10);
        c.restore();
      });
      c.save(); c.globalAlpha = a; c.fillStyle = rgba(WHITE, 0.25); c.fillRect(X0 - 50, base, gw * 13 + 40, 1); c.restore();
      ptxt(c, '■ 合伙公司', 1480, 300, 'small', a, { col: '#ffcf7a', align: 'left' });
      ptxt(c, '■ 道琼斯', 1480, 334, 'small', a, { col: '#8aa4c8', align: 'left' });
      txt(c, b, '年化 [29.5%]', 720, 820, 'h2', 28, 35.4, { scale: 1.1 });
      txt(c, b, '同期道指 7.4%', 1220, 820, 'h2', 29, 35.4, { col: '#9fb3cf', scale: 0.8 });
      txt(c, b, '13 年，[没有一年亏损]', CX, 915, 'h2', 32, 35.4, { scale: 0.9 });
    }
    // Berkshire
    if (b > 35.8 && b < 44.6) {
      const a = vis(b, 36, 43.4);
      const mx = CX, my = 470;
      const roof = [[-330, 0], [-330, -120], [-250, -190], [-250, -120], [-170, -190], [-170, -120], [-90, -190], [-90, -120], [-10, -190], [-10, -120], [70, -190], [70, -120], [150, -190], [150, -120], [230, -190], [230, -120], [330, -120], [330, 0]];
      const flick = 0.75 + 0.25 * noise1(b * 5);
      glowLine(c, roof.map(([x, y]) => [mx + x, my + y]), E.inOutCubic(inv(36, 38, b)), mixc(acc, [120, 60, 30], 0.3), 2, a * flick);
      c.save(); c.globalAlpha = a * 0.7; c.font = `600 22px ${FAM.cor}`; c.letterSpacing = '8px'; c.textAlign = 'center'; c.fillStyle = rgba(acc, 0.8 * flick);
      c.fillText('BERKSHIRE  FINE  SPINNING', mx, my - 40); c.restore();
      txt(c, b, '1962 年，他开始买入一家衰落的纺织厂', CX, 590, 'body', 36.5, 43.4);
      txt(c, b, '伯克希尔·哈撒韦', CX, 700, 'h1', 37.4, 43.4);
      txt(c, b, '一个典型的烟蒂——他后来称之为 [“我买过最蠢的股票”]', CX, 790, 'body', 39, 43.4);
      txt(c, b, '但这家公司，后来成了他滚雪球的容器', CX, 850, 'bodyL', 40.6, 43.4);
    }
    txt(c, b, '1969 年，市场一片狂热，便宜货消失了', CX, 470, 'h2', 44.2, 47.4);
    txt(c, b, '他做出罕见的决定：[解散合伙公司]——宁可离场，不降标准', CX, 555, 'body', 45.4, 47.4);
  },

  // ============================================================ CH4 MUNGER
  ch4(c, b) {
    chapterCard(c, b, '04', '进化', '1972 · 查理·芒格', '从「便宜」到「优秀」');
    const acc = PAL.acc, gold = PAL.acc2;
    txt(c, b, '烟蒂越来越难找', CX, 460, 'h2', 4.2, 7.4);
    txt(c, b, '而且，便宜的烂生意，往往会一直烂下去', CX, 545, 'body', 5.3, 7.4);
    // scale
    if (b > 7.8 && b < 20.6) {
      const a = vis(b, 8, 19.4);
      const tilt = -0.16 * E.outBack(inv(11.6, 12.8, b)) + 0.03 * Math.sin(b * 0.9) * (1 - inv(11, 12, b));
      const px = CX, py = 260, arm = 320;
      c.save(); c.globalAlpha = a; c.translate(px, py);
      c.strokeStyle = rgba(gold, 0.9); c.lineWidth = 2.5; c.shadowColor = rgba(gold, 1); c.shadowBlur = 18;
      c.beginPath(); c.moveTo(0, -30); c.lineTo(0, 210); c.stroke();
      c.beginPath(); c.moveTo(-60, 210); c.lineTo(60, 210); c.stroke();
      c.rotate(tilt);
      c.beginPath(); c.moveTo(-arm, 0); c.lineTo(arm, 0); c.stroke();
      c.restore();
      for (const side of [-1, 1]) {
        const ex = px + Math.cos(tilt) * arm * side, ey = py + Math.sin(tilt) * arm * side;
        c.save(); c.globalAlpha = a; c.strokeStyle = rgba(side < 0 ? hex('#9aa5b8') : gold, 0.8); c.lineWidth = 1.5;
        c.beginPath(); c.moveTo(ex, ey); c.lineTo(ex - 80, ey + 120); c.moveTo(ex, ey); c.lineTo(ex + 80, ey + 120); c.stroke();
        c.beginPath(); c.ellipse(ex, ey + 124, 96, 16, 0, 0, Math.PI * 2); c.stroke();
        c.restore();
        if (side > 0) { c.save(); c.globalCompositeOperation = 'lighter'; glow(c, ex, ey + 100, 90, gold, 0.5 * a * inv(12, 13, b)); c.restore(); }
        ptxt(c, side < 0 ? '平庸的公司' : '伟大的公司', ex, ey + 95, 'body', a, { scale: 0.8, col: side < 0 ? '#aab3c4' : '#ffe6a6' });
        ptxt(c, side < 0 ? '便宜的价格' : '合理的价格', ex, ey + 168, 'small', a, { col: side < 0 ? '#7d879a' : '#e9c98a' });
      }
      txt(c, b, '“以合理的价格买入一家伟大的公司，', CX, 640, 'quote', 9, 19.4);
      txt(c, b, '远胜于以便宜的价格买入一家平庸的公司。”', CX, 715, 'quote', 10.4, 19.4);
      txt(c, b, '—— 查理·芒格', CX, 785, 'small', 12, 19.4, { scale: 1.1 });
      txt(c, b, '时间是伟大企业的朋友，却是平庸企业的敌人', CX, 880, 'body', 14.4, 19.4, { col: '#e6dcff' });
    }
    // See's
    if (b > 19.8 && b < 32.6) {
      const a = vis(b, 20, 31.4);
      txt(c, b, "CASE · 1972 · 喜诗糖果 SEE'S CANDIES", CX, 190, 'label', 20.1, 31.4);
      const base = 700, sx = 760, gx = 1160;
      const g = E.outCubic(inv(24.8, 28, b));
      c.save(); c.globalAlpha = a;
      c.fillStyle = rgba(hex('#cbb6ff'), 0.9); c.shadowColor = rgba(acc, 1); c.shadowBlur = 20;
      c.fillRect(sx - 60, base - 14 * E.outCubic(inv(21, 22, b)), 120, 14 * E.outCubic(inv(21, 22, b)));
      const hh = 440 * g;
      const gg = c.createLinearGradient(0, base - 440, 0, base); gg.addColorStop(0, rgba(GOLD2)); gg.addColorStop(1, rgba(hex('#7c3aed'), 0.6));
      c.fillStyle = gg; c.shadowColor = rgba(GOLD, 1); c.shadowBlur = 30;
      c.fillRect(gx - 60, base - hh, 120, hh);
      c.restore();
      c.save(); c.globalCompositeOperation = 'lighter';
      for (let i = 0; i < 26; i++) { const u = ((b * 0.5 + i / 26) % 1); glow(c, gx - 50 + (i * 37 % 100), base - u * hh, 4, GOLD, a * g * (1 - u), 1); }
      c.restore();
      ptxt(c, '收购价', sx, base - 70, 'small', a * inv(21, 22, b), { col: '#d8ccff' });
      ptxt(c, '$2,500 万', sx, base - 30, 'numS', a * inv(21, 22, b), { scale: 0.5, col: '#e8deff', glow: 0 });
      ptxt(c, '累计税前利润', gx, base - hh - 78, 'small', a * g, { col: '#ffe6a6' });
      ptxt(c, '> $' + fmt(lerp(0, 20, g)) + ' 亿', gx, base - hh - 26, 'numS', a * g, { scale: 0.66 });
      txt(c, b, '买价是账面价值的 3 倍——当时，他觉得“太贵了”', CX, 790, 'body', 21.5, 31.4);
      txt(c, b, '秘密是 [定价权]：年年涨价，顾客依然买单', CX, 880, 'h2', 28.5, 31.4);
    }
    // Moat
    if (b > 31.8 && b < 48.6) {
      const a = vis(b, 32, 47.4);
      const mx = CX, my = 610, rx = 440, ry = 120;
      txt(c, b, 'ECONOMIC MOAT', CX, 170, 'label', 32.1, 47.4);
      txt(c, b, '护城河', CX, 270, 'h1', 32.4, 47.4);
      const moatCol = hex('#5fe1ff');
      const ring = (a0, a1) => {
        c.save(); c.globalCompositeOperation = 'lighter'; c.globalAlpha = a;
        c.strokeStyle = rgba(moatCol, 0.35); c.lineWidth = 34; c.filter = 'blur(10px)';
        c.beginPath(); c.ellipse(mx, my, rx, ry, 0, a0, a1); c.stroke();
        c.filter = 'none'; c.strokeStyle = rgba(mixc(moatCol, WHITE, 0.4), 0.9); c.lineWidth = 2;
        c.beginPath(); c.ellipse(mx, my, rx, ry, 0, a0, a1); c.stroke();
        for (let i = 0; i < 60; i++) { const th = a0 + (a1 - a0) * ((i / 60 + b * 0.02) % 1); glow(c, mx + Math.cos(th) * rx, my + Math.sin(th) * ry + Math.sin(th * 8 + b * 2) * 4, 3, moatCol, 0.8, 1); }
        c.restore();
      };
      const mp = E.outCubic(inv(32.6, 34.5, b));
      ring(Math.PI, Math.PI + Math.PI * mp);
      // castle
      const cp = E.inOutCubic(inv(33, 35.5, b));
      const cs = [[-190, 0], [-190, -200], [-170, -200], [-170, -220], [-150, -220], [-150, -200], [-130, -200], [-130, -220], [-110, -220], [-110, -130],
        [-60, -130], [-60, -150], [-40, -150], [-40, -130], [-20, -130], [-20, -270], [0, -310], [20, -270], [20, -130], [40, -130], [40, -150], [60, -150], [60, -130],
        [110, -130], [110, -220], [130, -220], [130, -200], [150, -200], [150, -220], [170, -220], [170, -200], [190, -200], [190, 0]];
      c.save(); c.globalAlpha = a * 0.85;
      const cg = c.createLinearGradient(0, my - 310, 0, my); cg.addColorStop(0, 'rgba(60,40,90,0.55)'); cg.addColorStop(1, 'rgba(20,10,40,0.9)');
      c.fillStyle = cg; c.beginPath(); cs.forEach(([x, y], i) => (i ? c.lineTo(mx + x, my + y) : c.moveTo(mx + x, my + y))); c.closePath(); c.fill();
      c.restore();
      glowLine(c, cs.map(([x, y]) => [mx + x, my + y]), cp, gold, 2, a);
      c.save(); c.globalCompositeOperation = 'lighter';
      [[-150, -160], [150, -160], [0, -220], [-70, -80], [70, -80]].forEach(([x, y], i) => { const wa = inv(35 + i * 0.3, 35.5 + i * 0.3, b) * a; glow(c, mx + x, my + y, 30, gold, 0.6 * wa); c.fillStyle = rgba(GOLD2, wa); c.fillRect(mx + x - 6, my + y - 12, 12, 20); });
      c.restore();
      ring(0, Math.PI * mp);
      // attackers bouncing off the moat
      c.save(); c.globalCompositeOperation = 'lighter';
      for (let i = 0; i < 10; i++) {
        const t0 = 36 + i * 0.9, th = -Math.PI * 0.9 + (i * 2.3 % 1) * Math.PI * 0.8 + (i % 2 ? Math.PI * 1.0 : 0);
        const k = (b - t0) / 1.3; if (k < 0 || k > 2) continue;
        const far = 900;
        const d = k < 1 ? lerp(far, 1, E.inCubic(k)) : 1 + E.outCubic(k - 1) * 260;
        const fa = k < 1 ? k : 2 - k;
        const px2 = mx + Math.cos(th) * (rx + (d - 1)), py2 = my + Math.sin(th) * (ry + (d - 1) * 0.6);
        glow(c, px2, py2, 6, RED, fa * a, 1); glow(c, px2, py2, 26, RED, 0.4 * fa * a);
        if (k > 1 && k < 1.3) glow(c, mx + Math.cos(th) * rx, my + Math.sin(th) * ry, 70 * (1.3 - k) * 3, mixc(moatCol, WHITE, 0.5), a * (1.3 - k) * 2);
      }
      c.restore();
      const tags = [['品牌', -600, -170], ['成本优势', 600, -170], ['网络效应', -640, 20], ['转换成本', 640, 20]];
      tags.forEach(([s, dx, dy], i) => pill(c, mx + dx, my + dy, s, acc, vis(b, 38 + i * 0.6, 47.4), { s: 26 }));
      txt(c, b, '伟大的企业，是一座被宽阔护城河环绕的 [经济城堡]', CX, 830, 'h2', 34.5, 47.4, { scale: 0.9 });
      txt(c, b, '城堡里，还要有 [诚实而能干] 的管理者', CX, 900, 'body', 43, 47.4);
    }
    // Float
    if (b > 47.8 && b < 64) {
      const a = vis(b, 48, 63.4);
      txt(c, b, 'THE HIDDEN ENGINE · 浮存金', CX, 175, 'label', 48.1, 63.4);
      txt(c, b, '1967 年，他收购了 [国民保险公司]', CX, 250, 'h2', 48.3, 63.4, { scale: 0.92 });
      const lx = 420, mxx = CX, rx2 = 1500, yy = 470;
      const lev = E.inOutSine(inv(49, 56, b));
      c.save(); c.globalCompositeOperation = 'lighter';
      for (const [x, s, col] of [[lx, '保费', hex('#c9a7ff')], [rx2, '投资', GOLD]]) { glow(c, x, yy, 80, col, 0.35 * a); glow(c, x, yy, 10, WHITE, a, 1); }
      // streams
      for (let i = 0; i < 36; i++) {
        const u = ((b * 0.4 + i / 36) % 1);
        glow(c, lerp(lx + 30, mxx - 120, u), yy + Math.sin(u * 9 + i) * 10, 4, hex('#c9a7ff'), a * vis(b, 49, 63.4), 1);
        glow(c, lerp(mxx + 120, rx2 - 30, u), yy + Math.sin(u * 9 + i) * 10, 4, GOLD, a * vis(b, 51, 63.4), 1);
      }
      for (let i = 0; i < 6; i++) { const u = ((b * 0.12 + i / 6) % 1); glow(c, mxx, lerp(yy + 120, yy + 210, u), 3, WHITE, 0.4 * a * vis(b, 52, 63.4), 1); }
      c.restore();
      // tank
      c.save(); c.globalAlpha = a;
      c.beginPath(); c.arc(mxx, yy, 110, 0, Math.PI * 2); c.strokeStyle = rgba(acc, 0.9); c.lineWidth = 2; c.shadowColor = rgba(acc, 1); c.shadowBlur = 24; c.stroke();
      c.save(); c.clip();
      const top = yy + 110 - 220 * (0.15 + 0.7 * lev);
      const wg = c.createLinearGradient(0, top, 0, yy + 110); wg.addColorStop(0, rgba(GOLD2, 0.8)); wg.addColorStop(1, rgba(hex('#7c3aed'), 0.6));
      c.fillStyle = wg; c.beginPath(); c.moveTo(mxx - 120, yy + 120);
      for (let x = -120; x <= 120; x += 6) c.lineTo(mxx + x, top + Math.sin(x * 0.05 + b * 2.5) * 6);
      c.lineTo(mxx + 120, yy + 120); c.closePath(); c.fill();
      c.restore(); c.restore();
      ptxt(c, '保费', lx, yy + 70, 'body', a, { col: '#e1d4ff' });
      ptxt(c, '先收进来', lx, yy + 110, 'small', a);
      ptxt(c, '投资', rx2, yy + 70, 'body', a * vis(b, 51, 63.4), { col: '#ffe6a6' });
      ptxt(c, '长期复利', rx2, yy + 110, 'small', a * vis(b, 51, 63.4));
      ptxt(c, '浮存金', mxx, yy + 12, 'h2', a, { scale: 0.75, col: '#ffffff', glow: 0.5 });
      ptxt(c, '理赔 · 多年以后才付', mxx, yy + 250, 'small', a * vis(b, 52, 63.4));
      txt(c, b, '先收保费、后付理赔——中间这笔钱，可以长期拿去投资', CX, 790, 'body', 50.5, 63.4);
      // float counter
      const g = E.inOutCubic(inv(56.5, 60, b));
      const fv = Math.exp(lerp(Math.log(0.39), Math.log(1760), g)); // 亿美元
      const fstr = fv < 1 ? `${fmt(fv * 10000)} 万美元` : `${fmt(fv)} 亿美元`;
      ptxt(c, `${Math.round(lerp(1970, 2025, g))} · ${fstr}`, CX, 925, 'numS', a * inv(56.2, 57, b), { scale: 0.6 });
      txt(c, b, '——雪球有了源源不断的 [“湿雪”]', CX, 985, 'bodyL', 60.6, 63.4);
    }
  },

  // ============================================================ CH5 CONVICTION
  ch5(c, b) {
    chapterCard(c, b, '05', '重仓', '1973 — 1998', '看准了，就下重注');
    const acc = PAL.acc;
    // Washington Post
    if (b > 3.8 && b < 16.6) {
      const a = vis(b, 4, 15.4);
      txt(c, b, 'CASE · 1973 · 华盛顿邮报', CX, 190, 'label', 4.1, 15.4);
      const px = 720, py = 500, R = 220;
      const p1 = E.outCubic(inv(4.5, 6.5, b)), p2 = E.outCubic(inv(7, 9.5, b));
      c.save(); c.globalAlpha = a;
      c.strokeStyle = rgba(hex('#9ad8ff'), 0.85); c.lineWidth = 2; c.shadowColor = rgba(hex('#9ad8ff'), 1); c.shadowBlur = 20;
      c.beginPath(); c.arc(px, py, R, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * p1); c.stroke();
      c.fillStyle = rgba(hex('#9ad8ff'), 0.07); c.beginPath(); c.arc(px, py, R, 0, Math.PI * 2); c.fill();
      const wedge = Math.PI * 2 / 5 * p2;
      const wg = c.createRadialGradient(px, py, 0, px, py, R); wg.addColorStop(0, rgba(GOLD2, 0.95)); wg.addColorStop(1, rgba(hex('#b7791f'), 0.85));
      c.fillStyle = wg; c.shadowColor = rgba(GOLD, 1); c.shadowBlur = 30;
      c.beginPath(); c.moveTo(px, py); c.arc(px, py, R - 8, -Math.PI / 2, -Math.PI / 2 + wedge); c.closePath(); c.fill();
      c.restore();
      ptxt(c, '内在价值  4 亿美元+', 1000, 420, 'h2', a * p1, { align: 'left', scale: 0.78, col: '#bfe6ff' });
      ptxt(c, '市场估值  8,000 万美元', 1000, 500, 'h2', a * p2, { align: 'left', scale: 0.78, col: '#ffe1a0' });
      txt(c, b, '不到内在价值的 [1/5]', 1000, 610, 'h1', 10, 15.4, { align: 'left', col: '#f6f1e7', scale: 0.72 });
      txt(c, b, '买入后股价继续下跌——他不为所动，一股未卖', CX, 860, 'body', 11.5, 15.4);
    }
    // GEICO
    if (b > 15.8 && b < 28.6) {
      const a = vis(b, 16, 27.4);
      txt(c, b, 'CASE · 1976 · GEICO 政府雇员保险', CX, 190, 'label', 16.1, 27.4);
      const X0 = 360, X1 = 1560, Y = (v) => 700 - v / 65 * 420;
      const down = [[0, 61], [0.08, 58], [0.15, 50], [0.22, 42], [0.3, 30], [0.36, 26], [0.42, 15], [0.48, 9], [0.53, 4], [0.58, 2]];
      const up = [[0.58, 2], [0.66, 5], [0.74, 11], [0.82, 19], [0.9, 29], [1, 44]];
      const r = rng(21);
      const jag = (arr) => { const o = []; for (let i = 0; i < arr.length - 1; i++) for (let j = 0; j < 5; j++) { const f = j / 5; o.push([lerp(X0, X1, lerp(arr[i][0], arr[i + 1][0], f)), Y(Math.max(1, lerp(arr[i][1], arr[i + 1][1], f) + (j ? (r() - 0.5) * 4 : 0)))]); } const l = arr[arr.length - 1]; o.push([lerp(X0, X1, l[0]), Y(l[1])]); return o; };
      const D = jag(down), U = jag(up);
      const p1 = E.inOutSine(inv(16.6, 21.4, b));
      const h = glowLine(c, D, p1, RED, 3, a);
      if (h && p1 < 1) { c.save(); c.globalCompositeOperation = 'lighter'; sparkle(c, h[0], h[1], 7, RED, a); c.restore(); }
      const bxy = [lerp(X0, X1, 0.58), Y(2)];
      if (b > 21.8) { c.save(); c.globalCompositeOperation = 'lighter'; const u = inv(22, 22.6, b); glow(c, bxy[0], bxy[1], 120 * u, GOLD, 0.6 * a); sparkle(c, bxy[0], bxy[1], 10, GOLD, a * u); c.restore(); }
      txt(c, b, '伯克希尔逆势买入', bxy[0], bxy[1] + 60, 'small', 22.2, 27.4, { col: '#ffe1a0', scale: 1.15 });
      const p2 = E.inOutSine(inv(22.5, 25.5, b));
      const h2 = glowLine(c, U, p2, GOLD, 3, a);
      if (h2 && p2 < 1 && p2 > 0) { c.save(); c.globalCompositeOperation = 'lighter'; sparkle(c, h2[0], h2[1], 7, GOLD, a); c.restore(); }
      ptxt(c, '$61', X0 - 20, Y(61) + 8, 'body', a, { align: 'right', col: '#ffb4b4' });
      txt(c, b, '公司濒临破产，股价从 [61 美元] 跌到 [2 美元]', CX, 800, 'body', 17.4, 27.4);
      txt(c, b, '他看到的是：低成本直销的 [护城河] 依然完好', CX, 870, 'h2', 22.6, 27.4, { scale: 0.88 });
      txt(c, b, '1996 年，伯克希尔全资收购了 GEICO', CX, 935, 'bodyL', 25, 27.4);
    }
    // Coca-Cola
    if (b > 27.8 && b < 40.6) {
      const a = vis(b, 28, 39.4);
      const red = hex('#ff3048');
      c.save(); c.globalCompositeOperation = 'lighter';
      glow(c, CX, 560, 700, red, 0.35 * a);
      const r = rng(77);
      for (let i = 0; i < 70; i++) {
        const sp = 40 + r() * 90, x0 = r() * W, ph = r() * 10, sz = 3 + r() * 10;
        const y = H + 40 - ((b * sp * 0.7 + ph * 100) % (H + 100));
        const x = x0 + Math.sin(b + ph) * 20;
        c.strokeStyle = rgba(mixc(red, WHITE, 0.5), 0.35 * a); c.lineWidth = 1.2;
        c.beginPath(); c.arc(x, y, sz, 0, Math.PI * 2); c.stroke();
      }
      c.restore();
      txt(c, b, 'CASE · 1988 · 可口可乐', CX, 190, 'label', 28.1, 39.4, { acc: hex('#ff8a9a') });
      txt(c, b, '1987 年股灾之后', CX, 330, 'bodyL', 28.4, 39.4);
      txt(c, b, '他投入约 [13 亿美元] 买入可口可乐', CX, 420, 'h2', 29.2, 39.4);
      txt(c, b, '此后几十年，一股未卖', CX, 500, 'body', 31.5, 39.4);
      hline(c, b, CX, 560, 700, 33, 39.4, hex('#ff8a9a'));
      txt(c, b, '如今每年分红', CX, 640, 'body', 34.5, 39.4, { col: '#ffd0d6' });
      txt(c, b, '超过 8 亿美元', CX, 770, 'num', 36, 39.4, { scale: 0.75 });
      txt(c, b, '一年的股息，就超过当初投入成本的一半', CX, 850, 'bodyL', 37, 39.4);
    }
    // Circle of competence
    if (b > 39.8 && b < 52.6) {
      const a = vis(b, 40, 51.4);
      txt(c, b, 'CIRCLE OF COMPETENCE', CX, 172, 'label', 40.1, 51.4);
      txt(c, b, '能力圈', CX, 262, 'h1', 40.4, 51.4);
      const ox = CX, oy = 520, R = 190 * E.outBack(inv(40.6, 42, b));
      c.save(); c.globalCompositeOperation = 'lighter';
      glow(c, ox, oy, R * 1.6, acc, 0.35 * a);
      c.strokeStyle = rgba(acc, 0.95 * a); c.lineWidth = 2.5; c.shadowColor = rgba(acc, 1); c.shadowBlur = 26;
      c.beginPath(); c.arc(ox, oy, Math.max(1, R), 0, Math.PI * 2); c.stroke();
      c.lineWidth = 1; c.globalAlpha = 0.4 * a; c.setLineDash([4, 10]);
      c.beginPath(); c.arc(ox, oy, Math.max(1, R * 1.25), b * 0.1, b * 0.1 + Math.PI * 2); c.stroke();
      c.restore();
      const inside = [['保险', -80, -70], ['饮料', 70, -40], ['糖果', -60, 40], ['报纸', 60, 80], ['银行', 0, -5]];
      inside.forEach(([s, dx, dy], i) => ptxt(c, s, ox + dx + Math.sin(b * 0.6 + i) * 6, oy + dy + Math.cos(b * 0.5 + i) * 6, 'body', a * vis(b, 41.5 + i * 0.3, 51.4), { col: '#fff1c9', scale: 0.9, glow: 0.4 }));
      const outside = [['科技热股', -470, -160], ['期货', 480, -120], ['热门概念', -520, 120], ['生物科技', 470, 160], ['加密?', -300, 250], ['预测宏观', 330, -250]];
      outside.forEach(([s, dx, dy], i) => ptxt(c, s, ox + dx + Math.sin(b * 0.4 + i) * 14, oy + dy, 'body', 0.45 * a * vis(b, 42.5 + i * 0.25, 51.4), { col: '#7f8798', blur: 3 + 2 * Math.sin(b + i) }));
      txt(c, b, '“能力圈的大小并不重要，重要的是清楚它的边界在哪里。”', CX, 850, 'quote', 44, 51.4, { scale: 0.92 });
      txt(c, b, '—— 巴菲特', CX, 915, 'small', 46, 51.4);
    }
    // punch card + forever
    if (b > 51.8) {
      const a = vis(b, 52, 63.4);
      txt(c, b, '如果一生只能做 [20 次] 投资决策', CX, 232, 'h2', 52.3, 63.4);
      const cw0 = 820, ch0 = 250, x0 = CX - cw0 / 2, y0 = 300;
      const ca = a * (1 - 0.55 * inv(58, 59, b));
      c.save(); c.globalAlpha = ca;
      const g = c.createLinearGradient(x0, y0, x0 + cw0, y0 + ch0); g.addColorStop(0, 'rgba(255,220,150,0.10)'); g.addColorStop(1, 'rgba(255,220,150,0.03)');
      c.fillStyle = g; c.strokeStyle = rgba(acc, 0.8); c.lineWidth = 1.5; c.shadowColor = rgba(acc, 0.8); c.shadowBlur = 18;
      c.beginPath(); c.moveTo(x0 + 40, y0); c.lineTo(x0 + cw0, y0); c.lineTo(x0 + cw0, y0 + ch0); c.lineTo(x0, y0 + ch0); c.lineTo(x0, y0 + 40); c.closePath(); c.fill(); c.stroke();
      c.shadowBlur = 0; c.font = `500 14px ${FAM.mono}`; c.fillStyle = rgba(acc, 0.7); c.letterSpacing = '4px';
      c.fillText('LIFETIME INVESTMENT PUNCH CARD · 20', x0 + 60, y0 + 34);
      c.restore();
      const punched = { 2: 53, 7: 54, 11: 55, 14: 56, 18: 57 };
      for (let i = 0; i < 20; i++) {
        const hx = x0 + 95 + (i % 10) * 70, hy = y0 + 110 + Math.floor(i / 10) * 80;
        const pt = punched[i];
        c.save(); c.globalAlpha = ca;
        c.strokeStyle = rgba(acc, 0.55); c.lineWidth = 1.5; c.beginPath(); c.arc(hx, hy, 17, 0, Math.PI * 2); c.stroke();
        if (pt !== undefined && b >= pt) {
          const u = inv(pt, pt + 0.8, b);
          c.globalCompositeOperation = 'lighter';
          glow(c, hx, hy, 90 * (1 - u) + 30, GOLD, 0.8 * (1 - u * 0.6));
          c.fillStyle = rgba(GOLD2, 0.9); c.beginPath(); c.arc(hx, hy, 12, 0, Math.PI * 2); c.fill();
        }
        c.restore();
      }
      txt(c, b, '你会想得更清楚，每一次都下得更重', CX, 650, 'body', 54.5, 63.4);
      txt(c, b, '“我们最喜欢的持有期限是——”', CX, 760, 'quote', 58, 63.4);
      txt(c, b, '永远', CX, 905, 'mega', 60, 63.4, { scale: 0.8 });
    }
  },

  // ============================================================ CH6 CONVICTION UNDER PRESSURE
  ch6(c, b) {
    chapterCard(c, b, '06', '定力', '1999 — 2011', '在贪婪与恐惧中逆行');
    const acc = PAL.acc;
    if (b > 3.8 && b < 20.6) {
      const a = vis(b, 4, 19.4);
      txt(c, b, '1995 — 2002 · 纳斯达克综合指数', CX, 190, 'label', 4.1, 19.4, { acc: hex('#7df3ff') });
      const K = [[1995.0, 750], [1995.6, 1000], [1996.0, 1050], [1996.6, 1150], [1997.0, 1290], [1997.6, 1600], [1998.0, 1570], [1998.7, 1500], [1999.0, 2190], [1999.5, 2700], [1999.9, 4070], [2000.2, 5048], [2000.4, 3300], [2000.7, 4200], [2000.95, 2470], [2001.3, 1840], [2001.7, 1420], [2001.9, 1950], [2002.4, 1460], [2002.78, 1114], [2002.95, 1335]];
      const X = (y) => lerp(260, 1660, (y - 1995) / 8), Y = (v) => 780 - v / 5200 * 470;
      const r = rng(5);
      const pts = []; for (let i = 0; i < K.length - 1; i++) for (let j = 0; j < 6; j++) { const f = j / 6; pts.push([X(lerp(K[i][0], K[i + 1][0], f)), Y(lerp(K[i][1], K[i + 1][1], f) * (1 + (j ? (r() - 0.5) * 0.06 : 0)))]); }
      pts.push([X(2002.95), Y(1335)]);
      const pk = 11 * 6;
      const rise = pts.slice(0, pk + 1), fall = pts.slice(pk);
      const p1 = E.inOutSine(inv(4.6, 13.8, b)), p2 = E.outCubic(inv(14, 16.2, b));
      const h = glowLine(c, rise, p1, hex('#3ff0ff'), 3, a * (1 - 0.6 * inv(14, 15, b)));
      if (h && p1 < 1) { c.save(); c.globalCompositeOperation = 'lighter'; sparkle(c, h[0], h[1], 8, hex('#3ff0ff'), a); c.restore(); }
      const h2 = glowLine(c, fall, p2, RED, 3.5, a);
      if (h2 && p2 > 0 && p2 < 1) { c.save(); c.globalCompositeOperation = 'lighter'; sparkle(c, h2[0], h2[1], 9, RED, a); c.restore(); }
      txt(c, b, '人人都在买科技股', X(1998.2), Y(3300), 'body', 7.6, 19.4, { col: '#aef6ff' });
      if (b > 8.8) {
        const ha = vis(b, 9, 13.6);
        c.save(); c.globalAlpha = ha; c.fillStyle = 'rgba(10,20,30,0.75)'; c.strokeStyle = rgba(hex('#3ff0ff'), 0.6); c.lineWidth = 1;
        c.beginPath(); c.roundRect(300, 330, 560, 150, 10); c.fill(); c.stroke(); c.restore();
        txt(c, b, '“巴菲特，你怎么了？”', 580, 410, 'h2', 9.2, 13.6, { scale: 0.85 });
        txt(c, b, '1999 年末，《巴伦周刊》封面', 580, 455, 'small', 10, 13.6);
      }
      txt(c, b, '泡沫破裂：纳斯达克暴跌 [78%]', CX, 870, 'h2', 14.4, 19.4);
      txt(c, b, '他始终坚守一条朴素的原则——[不懂的，不碰]', CX, 940, 'body', 16.2, 19.4);
    }
    if (b > 19.8 && b < 40.6) {
      const a = vis(b, 20, 39.4);
      c.save(); c.globalCompositeOperation = 'lighter'; glow(c, CX, CY, 1000, RED, 0.22 * a * (0.8 + 0.2 * Math.sin(b * Math.PI))); c.restore();
      txt(c, b, '2008 · 全球金融危机', CX, 190, 'label', 20.1, 39.4);
      txt(c, b, '雷曼兄弟倒下，全世界都在恐慌抛售', CX, 270, 'body', 21, 39.4);
      const K = [[0, 1560], [0.15, 1470], [0.3, 1400], [0.45, 1280], [0.55, 1250], [0.62, 1100], [0.7, 900], [0.8, 870], [0.9, 760], [1, 680]];
      const r = rng(9), pts = [];
      for (let i = 0; i < K.length - 1; i++) for (let j = 0; j < 6; j++) { const f = j / 6; pts.push([lerp(300, 1620, lerp(K[i][0], K[i + 1][0], f)), 360 + (1600 - lerp(K[i][1], K[i + 1][1], f) * (1 + (j ? (r() - 0.5) * 0.05 : 0))) * 0.5]); }
      const ca = a * (1 - 0.75 * inv(25, 26, b));
      const p = E.inOutSine(inv(20.6, 24.4, b));
      const h = glowLine(c, pts, p, RED, 3, ca);
      if (h && p < 1) { c.save(); c.globalCompositeOperation = 'lighter'; sparkle(c, h[0], h[1], 8, RED, ca); c.restore(); }
      const lx = lerp(300, 1620, 0.55);
      if (b > 22.6) { c.save(); c.globalAlpha = ca * inv(22.6, 23.2, b); c.strokeStyle = rgba(WHITE, 0.4); c.setLineDash([4, 6]); c.beginPath(); c.moveTo(lx, 330); c.lineTo(lx, 760); c.stroke(); c.restore(); ptxt(c, '雷曼破产 · 2008.9.15', lx + 12, 340, 'small', ca * inv(22.6, 23.2, b), { align: 'left', col: '#ffc2c2' }); }
      // debris
      c.save(); c.globalCompositeOperation = 'lighter';
      const rr = rng(12);
      for (let i = 0; i < 60; i++) { const x = rr() * W, sp = 80 + rr() * 200, y = ((b - 20) * sp * 0.6 + rr() * H) % H; glow(c, x, y, 2 + rr() * 3, RED, 0.5 * a * (1 - inv(25, 27, b) * 0.6), 1); }
      c.restore();
      txt(c, b, '别人贪婪时，我恐惧', CX, 560, 'h1', 26, 39.4, { col: '#e8edf5', anim: 'scale', from: 1.25 });
      txt(c, b, '别人恐惧时，我贪婪', CX, 690, 'h1', 30, 39.4, { anim: 'scale', from: 1.4, scale: 1.08 });
      ['高盛 · 50 亿美元', '通用电气 · 30 亿美元', '美国银行 · 50 亿美元'].forEach((s, i) => pill(c, CX - 420 + i * 420, 820, s, GOLD, vis(b, 33 + i, 39.4), { s: 24 }));
      txt(c, b, '他在《纽约时报》撰文：《买美国货，我正在买》', CX, 912, 'bodyL', 36.5, 39.4);
    }
    if (b > 39.8) {
      const a = vis(b, 40, 47.4);
      const lvl = E.inOutSine(inv(40, 46, b));
      c.save(); c.globalCompositeOperation = 'lighter';
      for (let i = 0; i < 6; i++) {
        const y0 = lerp(600, 880, lvl) + i * 30;
        c.strokeStyle = rgba(hex('#5aa9ff'), (0.55 - i * 0.07) * a); c.lineWidth = 2 - i * 0.2;
        c.beginPath(); for (let x = 0; x <= W; x += 12) { const y = y0 + Math.sin(x * 0.006 + b * 1.2 + i) * (12 - i) + Math.sin(x * 0.017 - b * 0.8) * 5; x ? c.lineTo(x, y) : c.moveTo(x, y); } c.stroke();
      }
      c.restore();
      txt(c, b, '“只有当潮水退去，', CX, 380, 'quote', 40.6, 47.4, { scale: 1.1 });
      txt(c, b, '你才知道谁一直在裸泳。”', CX, 470, 'quote', 41.6, 47.4, { scale: 1.1 });
      txt(c, b, '—— 巴菲特', CX, 545, 'small', 43, 47.4);
    }
  },

  // ============================================================ CH7 EVOLVE AGAIN
  ch7(c, b) {
    chapterCard(c, b, '07', '再进化', '2010 — 2025', '内核不变，边界生长');
    const acc = PAL.acc;
    if (b > 3.8 && b < 14.6) {
      const a = vis(b, 4, 13.4);
      const vx = CX, vy = 560;
      c.save(); c.globalAlpha = a; c.globalCompositeOperation = 'lighter';
      for (const side of [-1, 1]) {
        const g = c.createLinearGradient(vx, vy, vx + side * 700, H); g.addColorStop(0, rgba(acc, 0)); g.addColorStop(1, rgba(acc, 0.6));
        c.strokeStyle = g; c.lineWidth = 2; c.beginPath(); c.moveTo(vx + side * 4, vy); c.lineTo(vx + side * 760, H + 40); c.stroke();
      }
      for (let k = 0; k < 26; k++) {
        const z = ((k / 26 + b * 0.12) % 1), zz = z * z;
        const y = vy + (H + 40 - vy) * zz, hw = 4 + 756 * zz;
        c.strokeStyle = rgba(acc, 0.35 * z); c.lineWidth = 1 + 4 * zz;
        c.beginPath(); c.moveTo(vx - hw * 1.08, y); c.lineTo(vx + hw * 1.08, y); c.stroke();
      }
      for (let i = 0; i < 14; i++) {
        const u = ((b * 0.35 + i / 14) % 1), uu = u * u * u, side = i % 2 ? 1 : -1;
        const x = vx + side * (20 + 900 * uu), y = vy - 60 * (1 - u) + (H - vy) * uu * 0.4 - 80 * uu;
        glow(c, x, y, 10 + 60 * uu, i % 3 ? acc : WHITE, 0.6 * u, 1);
      }
      glow(c, vx, vy, 260, acc, 0.3);
      c.restore();
      txt(c, b, 'CASE · 2010 · 北伯灵顿铁路 BNSF', CX, 190, 'label', 4.1, 13.4);
      txt(c, b, '440 亿美元', CX, 310, 'num', 4.8, 13.4, { scale: 0.75 });
      txt(c, b, '伯克希尔史上规模最大的收购', CX, 390, 'h2', 6.2, 13.4, { scale: 0.85 });
      txt(c, b, '押注的，是美国经济的百年未来', CX, 450, 'bodyL', 7.8, 13.4);
    }
    if (b > 13.8 && b < 30.6) {
      const a = vis(b, 14, 29.4);
      txt(c, b, 'CASE · 2016 · 苹果 APPLE', CX, 172, 'label', 14.1, 29.4);
      txt(c, b, '一个 [“从不碰科技股”] 的人，开始买入苹果', CX, 250, 'h2', 14.5, 29.4);
      const dx = CX, dy = 455;
      const dp = E.outCubic(inv(15.5, 17.5, b));
      c.save(); c.globalAlpha = a; c.globalCompositeOperation = 'lighter';
      glow(c, dx, dy, 240, acc, 0.3 * dp);
      for (let k = 0; k < 3; k++) {
        const rx = 230 + k * 110, ry = 70 + k * 30;
        c.strokeStyle = rgba(acc, 0.25 * dp); c.lineWidth = 1;
        c.beginPath(); c.ellipse(dx, dy, rx * dp, ry * dp, -0.15, 0, Math.PI * 2); c.stroke();
        const n = 8 + k * 6;
        for (let i = 0; i < n; i++) {
          const th = i / n * Math.PI * 2 + b * (0.5 - k * 0.12), on = inv(17 + (i + k * 4) * 0.12, 17.4 + (i + k * 4) * 0.12, b);
          const x = dx + Math.cos(th) * rx * Math.cos(-0.15) - Math.sin(th) * ry * Math.sin(-0.15), y = dy + Math.cos(th) * rx * Math.sin(-0.15) + Math.sin(th) * ry * Math.cos(-0.15);
          glow(c, x, y, 4, i % 4 ? acc : WHITE, on * dp, 1); glow(c, x, y, 16, acc, 0.3 * on * dp);
        }
      }
      c.restore();
      c.save(); c.globalAlpha = a * dp;
      c.strokeStyle = rgba(mixc(acc, WHITE, 0.4)); c.lineWidth = 2.5; c.shadowColor = rgba(acc, 1); c.shadowBlur = 24;
      c.beginPath(); c.roundRect(dx - 62, dy - 118, 124, 236, 22); c.stroke();
      c.fillStyle = rgba(acc, 0.08); c.fill();
      c.restore();
      txt(c, b, '在他眼里，这不是科技公司，而是一家 [消费品公司]：用户离不开它', CX, 690, 'body', 18, 29.4);
      const bp = E.outCubic(inv(21.5, 24.2, b));
      c.save(); c.globalAlpha = a * inv(20.5, 21.3, b);
      c.fillStyle = rgba(hex('#9fb3cf'), 0.85); c.fillRect(560, 772, 190, 30);
      const gg = c.createLinearGradient(560, 0, 1535, 0); gg.addColorStop(0, rgba(acc, 0.7)); gg.addColorStop(1, rgba(GOLD2, 1));
      c.fillStyle = gg; c.shadowColor = rgba(acc, 1); c.shadowBlur = 24; c.fillRect(560, 840, 975 * bp, 30);
      c.restore();
      ptxt(c, '投入成本', 530, 797, 'body', a * inv(20.5, 21.3, b), { align: 'right', scale: 0.8 });
      ptxt(c, '约 340 亿美元', 770, 797, 'body', a * inv(20.5, 21.3, b), { align: 'left', scale: 0.8, col: '#cfdbec' });
      ptxt(c, '市值', 530, 865, 'body', a * inv(21.5, 22, b), { align: 'right', scale: 0.8 });
      ptxt(c, `约 ${fmt(lerp(340, 1740, bp))} 亿美元（2023 年末）`, 560 + 975 * bp - 10, 828, 'body', a * inv(22, 22.6, b), { align: 'right', scale: 0.8, col: '#fff2c9' });
    }
    if (b > 29.8) {
      const a = vis(b, 30, 39.4);
      const u = E.inOutCubic(inv(31, 34, b));
      const ox = lerp(700, 1220, u), oy = 620 - Math.sin(u * Math.PI) * 90;
      c.save(); c.globalCompositeOperation = 'lighter';
      glow(c, 700, 620, 80, GOLD, 0.5 * a); glow(c, 700, 620, 8, WHITE, a, 1);
      glow(c, 1220, 620, 80, acc, 0.5 * a * (0.4 + 0.6 * u)); glow(c, 1220, 620, 8, WHITE, a, 1);
      glow(c, ox, oy, 50, mixc(GOLD, acc, u), 0.9 * a); glow(c, ox, oy, 12, WHITE, a, 1);
      c.restore();
      ptxt(c, '巴菲特', 700, 690, 'small', a, { col: '#ffe6a6' });
      ptxt(c, '格雷格·阿贝尔', 1220, 690, 'small', a * inv(32, 33, b), { col: '#b8ffe9' });
      txt(c, b, '2025 年，94 岁的他宣布：年底卸任 CEO', CX, 330, 'h2', 30.3, 39.4);
      txt(c, b, '接力棒，交给了 [格雷格·阿贝尔]', CX, 410, 'body', 31.6, 39.4);
      txt(c, b, '方法在进化，但内核从未改变——', CX, 800, 'body', 34.6, 39.4);
      txt(c, b, '以合理的价格，买入并长期持有伟大的企业', CX, 885, 'h2', 35.8, 39.4, { col: 'gold', glow: 0.4 });
    }
  },

  // ============================================================ CH8 COMPOUNDING
  ch8(c, b) {
    chapterCard(c, b, '08', '复利', '1965 — 2025', '时间的魔法');
    const acc = PAL.acc, cy = hex('#5fe1ff');
    if (b > 3.8 && b < 24.6) {
      const a = vis(b, 4, 23.4);
      txt(c, b, '1965 — 2025 · 累计回报（对数坐标）', CX, 178, 'label', 4.1, 23.4);
      const X0 = 230, X1 = 1500, Y0 = 790, Y1 = 260;
      const X = (y) => lerp(X0, X1, (y - 1964) / 61), Y = (v) => Y0 - Math.log10(v) / 5 * (Y0 - Y1);
      c.save(); c.globalAlpha = a; c.font = `400 15px ${FAM.mono}`; c.textAlign = 'right';
      ['1×', '10×', '100×', '1,000×', '10,000×', '100,000×'].forEach((s, i) => { const y = Y(Math.pow(10, i)); c.strokeStyle = rgba(WHITE, 0.07); c.beginPath(); c.moveTo(X0, y); c.lineTo(X1, y); c.stroke(); c.fillStyle = rgba(WHITE, 0.35); c.fillText(s, X0 - 14, y + 5); });
      c.textAlign = 'center'; for (let yr = 1970; yr <= 2020; yr += 10) c.fillText(String(yr), X(yr), Y0 + 32);
      c.restore();
      const p = E.inOutSine(inv(4.5, 19, b));
      const bp = BRK.map((v, i) => [X(1964 + i), Y(v)]), sp = SPX.map((v, i) => [X(1964 + i), Y(v)]);
      const hs = glowLine(c, sp, p, cy, 2.5, a);
      const hb = glowLine(c, bp, p, acc, 3.5, a);
      const yr = 1964 + 61 * p;
      c.save(); c.globalCompositeOperation = 'lighter';
      if (hb) sparkle(c, hb[0], hb[1], 9, acc, a);
      if (hs) sparkle(c, hs[0], hs[1], 7, cy, a);
      c.restore();
      if (hb && b < 20) { ptxt(c, fmt(seriesAt(BRK, yr)) + '×', hb[0] + 18, hb[1] - 14, 'body', a, { align: 'left', col: '#ffe6a6', scale: 0.8 }); ptxt(c, fmt(seriesAt(SPX, yr)) + '×', hs[0] + 18, hs[1] + 34, 'body', a, { align: 'left', col: '#bfefff', scale: 0.8 }); }
      txt(c, b, '+6,099,294%', X1 + 24, Y(BRK[61]) + 20, 'numS', 20, 23.4, { align: 'left', scale: 0.62, anim: 'scale' });
      txt(c, b, '伯克希尔', X1 + 26, Y(BRK[61]) + 64, 'small', 20.4, 23.4, { align: 'left', col: '#ffe6a6' });
      txt(c, b, '+46,061%', X1 + 24, Y(SPX[61]) + 20, 'numS', 20.6, 23.4, { align: 'left', scale: 0.5, col: '#bfefff', anim: 'scale', glow: 0.2 });
      txt(c, b, '标普 500（含股息）', X1 + 26, Y(SPX[61]) + 58, 'small', 21, 23.4, { align: 'left', col: '#bfefff' });
      txt(c, b, '数据：伯克希尔·哈撒韦 2025 年致股东信 · 每股市值变化 vs 标普 500 总回报', CX, 880, 'small', 21, 23.4);
    }
    if (b > 23.8 && b < 36.6) {
      const a = vis(b, 24, 35.4);
      txt(c, b, '伯克希尔 · 年化', 600, 260, 'label', 24.1, 35.4);
      txt(c, b, '19.7%', 600, 420, 'num', 24.3, 35.4, { scale: 0.95 });
      txt(c, b, '标普 500 · 年化', 1320, 260, 'label', 24.6, 35.4, { acc: cy });
      txt(c, b, '10.5%', 1320, 420, 'num', 24.8, 35.4, { scale: 0.95, col: '#bfefff', glow: 0.3 });
      ptxt(c, 'VS', CX, 395, 'label', a * inv(25, 26, b), { scale: 1.6, col: '#ffffff' });
      txt(c, b, '每年的回报，差距 [还不到 2 倍]', CX, 560, 'h2', 28, 35.4);
      txt(c, b, '可是，61 年复利下来——', CX, 650, 'bodyL', 30, 35.4, { scale: 1.1 });
      txt(c, b, '相差 132 倍', CX, 830, 'mega', 32, 35.4, { scale: 1.05, from: 2.2 });
      if (b > 32) { c.save(); c.globalCompositeOperation = 'lighter'; const u = inv(32, 34, b); c.strokeStyle = rgba(acc, (1 - u) * 0.8); c.lineWidth = 3; c.beginPath(); c.ellipse(CX, 770, 200 + 900 * E.outExpo(u), 60 + 280 * E.outExpo(u), 0, 0, Math.PI * 2); c.stroke(); c.restore(); }
    }
    if (b > 35.8 && b < 44.6) {
      const a = vis(b, 36, 43.4);
      const D = [[25, 0.0001], [30, 0.001], [35, 0.007], [39, 0.025], [44, 0.034], [47, 0.067], [52, 0.376], [56, 1.4], [59, 2.3], [60, 3.8], [63, 8], [66, 17], [70, 36], [75, 42], [80, 62], [85, 73], [90, 100], [94, 150]];
      const X = (age) => lerp(300, 1620, (age - 25) / 70), Y = (v) => 720 - v / 155 * 450;
      const pts = []; for (let i = 0; i < D.length - 1; i++) for (let j = 0; j < 6; j++) { const f = j / 6; pts.push([X(lerp(D[i][0], D[i + 1][0], f)), Y(Math.exp(lerp(Math.log(D[i][1]), Math.log(D[i + 1][1]), f)))]); }
      pts.push([X(94), Y(150)]);
      const p = E.inOutSine(inv(36.5, 40.5, b));
      c.save(); c.globalAlpha = a;
      c.font = `400 15px ${FAM.mono}`; c.textAlign = 'center'; c.fillStyle = rgba(WHITE, 0.4);
      for (let age = 30; age <= 90; age += 10) c.fillText(age + ' 岁', X(age), 760);
      c.fillStyle = rgba(WHITE, 0.15); c.fillRect(300, 720, 1320, 1);
      const x65 = X(65);
      c.setLineDash([5, 7]); c.strokeStyle = rgba(acc, 0.6); c.beginPath(); c.moveTo(x65, 250); c.lineTo(x65, 720); c.stroke(); c.setLineDash([]);
      const head = polyPath(c, pts, p); c.lineTo(head[0], 720); c.lineTo(300, 720); c.closePath();
      const gg = c.createLinearGradient(300, 0, 1620, 0); gg.addColorStop(0, rgba(WHITE, 0.06)); gg.addColorStop((x65 - 300) / 1320, rgba(WHITE, 0.08)); gg.addColorStop((x65 - 300) / 1320 + 0.001, rgba(acc, 0.45)); gg.addColorStop(1, rgba(GOLD2, 0.6));
      c.fillStyle = gg; c.fill();
      c.restore();
      const h = glowLine(c, pts, p, acc, 3, a);
      if (h) { c.save(); c.globalCompositeOperation = 'lighter'; sparkle(c, h[0], h[1], 8, acc, a); c.restore(); }
      ptxt(c, '65 岁', X(65), 235, 'body', a, { col: '#ffe6a6', scale: 0.8 });
      txt(c, b, '他 [90% 以上] 的财富，是在 65 岁之后获得的', CX, 850, 'h2', 37, 43.4);
      txt(c, b, '复利最关键的变量，不是收益率，而是 [时间]', CX, 925, 'body', 39.6, 43.4);
    }
    if (b > 43.8) {
      const a = vis(b, 44, 55.4);
      const P0 = [140, 360], P1 = [760, 880], P2 = [1780, 900];
      const bez = (u) => [(1 - u) * (1 - u) * P0[0] + 2 * (1 - u) * u * P1[0] + u * u * P2[0], (1 - u) * (1 - u) * P0[1] + 2 * (1 - u) * u * P1[1] + u * u * P2[1]];
      const pts = []; for (let i = 0; i <= 80; i++) pts.push(bez(i / 80));
      glowLine(c, pts, E.outCubic(inv(44, 45.5, b)), mixc(acc, WHITE, 0.4), 2, a);
      c.save(); c.globalAlpha = a; c.beginPath(); pts.forEach(([x, y], i) => (i ? c.lineTo(x, y) : c.moveTo(x, y))); c.lineTo(1780, H); c.lineTo(140, H); c.closePath();
      const sg = c.createLinearGradient(0, 360, 0, H); sg.addColorStop(0, rgba(WHITE, 0.10)); sg.addColorStop(1, rgba(WHITE, 0)); c.fillStyle = sg; c.fill(); c.restore();
      const u = 0.04 + 0.93 * E.inOutSine(inv(45, 55.2, b));
      const [bx, by] = bez(u);
      const R = 10 + 80 * Math.pow(u, 1.4);
      c.save(); c.globalCompositeOperation = 'lighter';
      for (let k = 0; k < 40; k++) { const uu = u - k * 0.006; if (uu < 0.04) break; const [tx, ty] = bez(uu); glow(c, tx, ty - 4, 3 + (40 - k) * 0.08, WHITE, (1 - k / 40) * 0.6 * a, 1); }
      c.restore();
      snowball(c, bx, by - R, R, -b * 1.6, a, mixc(acc, WHITE, 0.55));
      // falling snow
      c.save(); c.globalCompositeOperation = 'lighter';
      const r = rng(31);
      for (let i = 0; i < 90; i++) { const x0 = r() * W, sp = 20 + r() * 50, y = ((b - 44) * sp + r() * H) % H; glow(c, x0 + Math.sin(b * 0.8 + i) * 18, y, 2 + r() * 2.5, WHITE, 0.5 * a, 1); }
      c.restore();
      txt(c, b, '“人生就像滚雪球。', CX, 200, 'quote', 45, 55.4, { scale: 1.05 });
      txt(c, b, '重要的是，找到 [很湿的雪] 和 [很长的坡]。”', CX, 282, 'quote', 46.6, 55.4, { scale: 1.05 });
      txt(c, b, '湿雪 = 优秀的企业 + 源源不断的现金流', 960, 520, 'body', 50, 55.4, { col: '#fff1c9' });
      txt(c, b, '长坡 = 足够长的时间', 1400, 700, 'body', 52, 55.4, { col: '#fff1c9' });
    }
  },

  // ============================================================ OUTRO
  outro(c, b) {
    const acc = PAL.acc;
    if (b < 14.6) {
      const a = vis(b, 0, 13.4);
      txt(c, b, '一张图，看懂巴菲特', CX, 150, 'h2', 0.3, 13.4, { scale: 0.9 });
      const names = ['股权思维', '市场先生', '安全边际', '能力圈', '护城河', '定价权', '管理层', '浮存金', '集中投资', '长期持有', '逆向思考', '复利'];
      const cols = ['#5fe1ff', '#5fe1ff', '#5fe1ff', '#ffd479', '#c9a7ff', '#c9a7ff', '#c9a7ff', '#c9a7ff', '#ffd479', '#ffd479', '#ff7a7a', '#f3c76e'].map(hex);
      const N = names.length, ox = CX, oy = 570, rx = 640, ry = 300;
      const P = names.map((_, i) => { const th = -Math.PI / 2 + i / N * Math.PI * 2 + Math.sin(b * 0.1) * 0.03; return [ox + Math.cos(th) * rx, oy + Math.sin(th) * ry]; });
      c.save(); c.globalCompositeOperation = 'lighter';
      for (let i = 0; i < N; i++) {
        const t0 = 0.6 + i * 0.95, u = inv(t0, t0 + 0.6, b);
        if (u <= 0) continue;
        c.strokeStyle = rgba(cols[i], 0.35 * u * a); c.lineWidth = 1;
        c.beginPath(); c.moveTo(ox, oy); c.lineTo(lerp(ox, P[i][0], u), lerp(oy, P[i][1], u)); c.stroke();
        const j = (i + 1) % N, uj = inv(0.6 + Math.max(i, j) * 0.95 + 0.4, 0.6 + Math.max(i, j) * 0.95 + 1, b);
        if (uj > 0) { c.strokeStyle = rgba(mixc(cols[i], cols[j], 0.5), 0.5 * uj * a); c.beginPath(); c.moveTo(P[i][0], P[i][1]); c.lineTo(lerp(P[i][0], P[j][0], uj), lerp(P[i][1], P[j][1], uj)); c.stroke(); }
        const e = E.outBack(u);
        glow(c, P[i][0], P[i][1], 50 * e, cols[i], 0.45 * a);
        glow(c, P[i][0], P[i][1], 7, WHITE, a * u, 1);
        const fu = ((b * 0.3 + i * 0.37) % 1);
        glow(c, lerp(P[i][0], ox, fu), lerp(P[i][1], oy, fu), 3, cols[i], 0.7 * a * u, 1);
      }
      glow(c, ox, oy, 220, acc, 0.4 * a); glow(c, ox, oy, 14, WHITE, a, 1);
      c.restore();
      names.forEach((s, i) => { const t0 = 0.6 + i * 0.95; const below = P[i][1] >= oy - 10; txt(c, b, s, P[i][0], P[i][1] + (below ? 48 : -26), 'body', t0 + 0.1, 13.4, { col: rgba(mixc(cols[i], WHITE, 0.55)), scale: 0.85 }); });
      txt(c, b, '价值', ox, oy + 18, 'h2', 0.3, 13.4, { col: 'gold', glow: 0.6 });
    }
    if (b > 13.8 && b < 20.6) {
      txt(c, b, '规则一：[永远不要亏钱]。', CX, 470, 'h2', 14.3, 19.4, { scale: 1.15 });
      txt(c, b, '规则二：[永远不要忘记规则一]。', CX, 570, 'h2', 16, 19.4, { scale: 1.15 });
      hline(c, b, CX, 625, 520, 17, 19.4, acc);
      txt(c, b, '—— 沃伦·巴菲特', CX, 680, 'small', 17.5, 19.4, { scale: 1.15 });
    }
    if (b > 19.8 && b < 28.6) {
      const items = [['买得便宜', '#5fe1ff', 480, 20], ['买得好', '#c9a7ff', 960, 22], ['拿得久', '#f3c76e', 1440, 24]];
      items.forEach(([s, col, x, t0], i) => {
        const cc = hex(col), u = inv(t0, t0 + 0.8, b), a = vis(b, t0, 27.4);
        c.save(); c.globalCompositeOperation = 'lighter'; glow(c, x, 460, 200 * E.outBack(u), cc, 0.35 * a); c.restore();
        txt(c, b, s, x, 490, 'h1', t0, 27.4, { col: rgba(mixc(cc, WHITE, 0.45)), scale: 0.85, glow: 0.5, acc: cc });
        txt(c, b, ['格雷厄姆', '芒格 · 费雪', '时间'][i], x, 560, 'label', t0 + 0.3, 27.4, { acc: cc });
        if (i < 2) { const p = E.outCubic(inv(t0 + 0.6, t0 + 1.8, b)); glowLine(c, [[x + 180, 460], [x + 300, 460]], p, cc, 2, a); }
      });
      txt(c, b, '便宜是起点，优秀是核心，时间是答案。', CX, 720, 'quote', 25, 27.4, { scale: 1.05 });
    }
    if (b > 27.8) {
      snowball(c, CX, 330, 70, b * 0.4, vis(b, 28, 40), PAL.acc, 1);
      txt(c, b, '滚雪球的人', CX, 560, 'h1', 28, 40, { anim: 'blur', scale: 1.1 });
      txt(c, b, '沃伦·巴菲特的投资思想进化史', CX, 630, 'bodyL', 28.8, 40, { ls: 0.35 });
      txt(c, b, '数据来源：伯克希尔·哈撒韦历年致股东信及公开资料 · 仅供学习交流，不构成任何投资建议', CX, 960, 'small', 29.4, 40, { scale: 0.85 });
    }
  },
};
window.SCENE_DRAW = SCENE_DRAW;
window.SCENE_YEARS = SCENE_YEARS;
