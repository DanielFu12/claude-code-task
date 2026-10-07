// Scene definitions for the Munger video. Each draw(c, b, info) receives the local beat b.
/* global TL, W, H, CX, CY, E, clamp, lerp, inv, rng, noise1, fmt, rgba, mixc, hex, glow, txt, hline, STY, FAM, fontStr, goldGrad, PAL, GOLD, GOLD2, WHITE, CYAN, RED */

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


// ---------------------------------------------------------------- munger helpers
// the "latticework": nodes on a sphere, each wired to its nearest neighbours
const LAT = (() => {
  const n = 96, r = rng(77), nodes = [];
  for (let i = 0; i < n; i++) {
    const y = 1 - (i / (n - 1)) * 2, rad = Math.sqrt(1 - y * y), th = i * 2.39996, k = 0.82 + r() * 0.3;
    nodes.push({ x: Math.cos(th) * rad * k, y: y * k, z: Math.sin(th) * rad * k, o: r(), c: Math.floor(r() * 5) });
  }
  const edges = [];
  for (let i = 0; i < n; i++) {
    const d = nodes.map((m, j) => [j, (m.x - nodes[i].x) ** 2 + (m.y - nodes[i].y) ** 2 + (m.z - nodes[i].z) ** 2]).filter(([j]) => j !== i).sort((p, q) => p[1] - q[1]);
    for (const [j] of d.slice(0, 3)) if (i < j) edges.push([i, j]);
  }
  return { nodes, edges };
})();
const LATCOL = ['#5fe1ff', '#f3c76e', '#c9a7ff', '#7ef0c4', '#ff9f8a'].map(hex);
function lattice(c, x, y, R, rot, a, grow = 1, burst = 0, multi = true) {
  if (a <= 0.01) return;
  const cr = Math.cos(rot), sr = Math.sin(rot), ct = Math.cos(0.38), st = Math.sin(0.38);
  const P = LAT.nodes.map((p) => {
    let px = p.x * cr - p.z * sr, pz = p.x * sr + p.z * cr, py = p.y;
    const py2 = py * ct - pz * st; pz = py * st + pz * ct; py = py2;
    const k = 1 + burst * (1.2 + p.o * 2.4);
    return [x + px * R * k, y + py * R * k, (pz + 1) / 2, clamp(grow * 1.35 - p.o * 0.35)];
  });
  c.save(); c.globalCompositeOperation = 'lighter';
  glow(c, x, y, R * 2.2, PAL.acc2, 0.16 * a * grow * (1 - burst));
  for (const [i, j] of LAT.edges) {
    const vi = Math.min(P[i][3], P[j][3]); if (vi <= 0) continue;
    const dep = (P[i][2] + P[j][2]) / 2;
    c.strokeStyle = rgba(mixc(PAL.acc2, WHITE, dep * 0.35), (0.06 + 0.34 * dep) * a * vi * (1 - burst));
    c.lineWidth = 0.6 + dep * 1.1;
    c.beginPath(); c.moveTo(P[i][0], P[i][1]); c.lineTo(lerp(P[i][0], P[j][0], vi), lerp(P[i][1], P[j][1], vi)); c.stroke();
  }
  LAT.nodes.forEach((p, i) => {
    const v = P[i][3]; if (v <= 0) return;
    const dep = P[i][2], col = multi ? LATCOL[p.c] : PAL.acc;
    glow(c, P[i][0], P[i][1], 4 + dep * 7, col, (0.25 + 0.75 * dep) * a * v * (1 - burst * 0.6), 1);
    if (dep > 0.75) glow(c, P[i][0], P[i][1], 18, col, 0.25 * a * v);
  });
  c.restore();
}
// glass card
function card(c, x, y, w, h, col, a, hi = 0) {
  if (a <= 0.01) return;
  c.save(); c.globalAlpha = a;
  const g = c.createLinearGradient(x, y, x, y + h);
  g.addColorStop(0, rgba(mixc(col, [10, 10, 20], 0.82), 0.62)); g.addColorStop(1, rgba([8, 8, 14], 0.5));
  c.fillStyle = g; c.strokeStyle = rgba(col, 0.35 + 0.5 * hi); c.lineWidth = 1.2;
  c.shadowColor = rgba(col, 0.25 + 0.5 * hi); c.shadowBlur = 20 + 30 * hi;
  c.beginPath(); c.roundRect(x, y, w, h, 14); c.fill(); c.stroke();
  c.shadowBlur = 0; c.fillStyle = rgba(col, 0.9); c.fillRect(x + 22, y, w - 44, 2);
  c.restore();
}
const lines = (c, arr, x, y, sty, a, o = {}, lh = 40) => arr.forEach((s, i) => ptxt(c, s, x, y + i * lh, sty, a, o));
function orb(c, x, y, r, col, a) { c.save(); c.globalCompositeOperation = 'lighter'; glow(c, x, y, r * 4, col, 0.35 * a); glow(c, x, y, r, mixc(col, WHITE, 0.5), a, 1); c.restore(); }

// Wheeler, Munger & Co. annual results vs Dow (Buffett, "The Superinvestors of Graham-and-Doddsville", 1984)
const WMC = [30.1, 71.7, 49.7, 8.4, 12.4, 56.2, 40.4, 28.3, -0.1, 25.4, 8.3, -31.9, -31.5, 73.2];
const DJI = [-7.6, 20.6, 18.7, 14.2, -15.8, 19.0, 7.7, -11.6, 8.7, 9.8, 18.2, -13.1, -23.1, 44.4];
const cum = (r) => { let v = 1; const o = [1]; for (const x of r) { v *= 1 + x / 100; o.push(v); } return o; };

// ---------------------------------------------------------------- scenes
const SCENE_YEARS = {
  ch1: [[0, 1924], [4, 1924], [12, 1962], [16, 1955], [24, 1959], [34, 1962], [44, 1975], [48, 1978], [56, 1978]],
  ch2: [[0, 1994], [56, 1996], [80, 1996]],
  ch3: [[0, 1986], [28, 1995], [80, 1995]],
  ch4: [[0, 1996], [40, 1996]],
  ch5: [[0, 1972], [40, 1972], [44, 2023], [52, 1997], [80, 1997]],
  ch6: [[0, 2000], [48, 2008], [56, 2009], [64, 2009]],
  ch7: [[0, 2009], [20, 1973], [32, 2009], [56, 2009]],
  ch8: [[0, 2007], [64, 2023], [80, 2023]],
};

const SCENE_DRAW = {
  // ============================================================ HOOK
  hook(c, b) {
    const acc = PAL.acc;
    txt(c, b, '1924 — 2023', CX, 330, 'label', 0.4, 7.3, { scale: 1.3, col: '#e9e1d2' });
    txt(c, b, '“我只想知道将来我会死在哪里，', CX, 480, 'quote', 1, 7.3, { anim: 'type', stg: 0.13, scale: 1.05 });
    txt(c, b, '这样我就永远不去那个地方。”', CX, 565, 'quote', 3.4, 7.3, { anim: 'type', stg: 0.13, scale: 1.05 });
    txt(c, b, '—— 查理·芒格', CX, 645, 'small', 5.4, 7.3, { scale: 1.15 });
    // the reversal
    if (b > 7.6 && b < 16.6) {
      const a = vis(b, 8, 15.4);
      txt(c, b, '这是一句玩笑，', CX, 290, 'h2', 8.3, 15.4);
      txt(c, b, '也是一整套看世界的方法：[反过来想]', CX, 365, 'body', 9.4, 15.4);
      const y1 = 540, y2 = 680, x0 = 520, x1 = 1400;
      const p1 = E.inOutCubic(inv(9.6, 11.2, b)), p2 = E.inOutCubic(inv(12, 13.6, b));
      const h1 = glowLine(c, [[x0, y1], [x1, y1]], p1, hex('#9aa5b8'), 2.5, a * (1 - 0.6 * inv(12, 13, b)));
      if (h1 && p1 > 0.98) { c.save(); c.globalAlpha = a * (1 - 0.6 * inv(12, 13, b)); c.strokeStyle = '#9aa5b8'; c.lineWidth = 2.5; c.beginPath(); c.moveTo(x1 - 18, y1 - 12); c.lineTo(x1, y1); c.lineTo(x1 - 18, y1 + 12); c.stroke(); c.restore(); }
      ptxt(c, '大多数人问：怎样才能成功？', x0, y1 - 26, 'body', a * inv(10, 10.8, b) * (1 - 0.6 * inv(12, 13, b)), { align: 'left', col: '#aab3c4', scale: 0.85 });
      const h2 = glowLine(c, [[x1, y2], [x0, y2]], p2, acc, 3, a);
      if (h2) { c.save(); c.globalCompositeOperation = 'lighter'; sparkle(c, h2[0], h2[1], 8, acc, a); c.restore(); }
      if (p2 > 0.98) { c.save(); c.globalAlpha = a; c.strokeStyle = rgba(acc); c.lineWidth = 3; c.shadowColor = rgba(acc); c.shadowBlur = 16; c.beginPath(); c.moveTo(x0 + 18, y2 - 12); c.lineTo(x0, y2); c.lineTo(x0 + 18, y2 + 12); c.stroke(); c.restore(); }
      ptxt(c, '芒格问：怎样会彻底失败？——然后避开它', x1, y2 + 52, 'body', a * inv(12.6, 13.4, b), { align: 'right', col: '#ffe6a6', scale: 0.9 });
    }
    // who he was
    if (b > 15.6 && b < 24.6) {
      const a = vis(b, 16, 23.4);
      const r0 = 70, ph = b * 0.9;
      orb(c, CX + Math.cos(ph) * r0, 300 + Math.sin(ph) * r0 * 0.35, 9, GOLD, a);
      orb(c, CX - Math.cos(ph) * r0, 300 - Math.sin(ph) * r0 * 0.35, 9, hex('#8fb8ff'), a);
      txt(c, b, '他是巴菲特 60 多年的搭档', CX, 480, 'h2', 16.3, 23.4, { scale: 1.1 });
      txt(c, b, '伯克希尔·哈撒韦副董事长 · 律师出身的“通才”', CX, 565, 'body', 17.6, 23.4);
      txt(c, b, '他活了 99 岁，留下的不是选股秘诀，而是一种 [思考方式]', CX, 640, 'bodyL', 19.2, 23.4);
    }
    if (b > 23.6) {
      lattice(c, CX, 450, 190, b * 0.25, vis(b, 24, 40, 1), E.inOutSine(inv(24, 31, b)));
      txt(c, b, '一张由几十种思维模型编织而成的网——', CX, 790, 'bodyL', 25.5, 31.4, { scale: 1.1 });
    }
  },

  // ============================================================ TITLE
  title(c, b) {
    const acc = PAL.acc;
    lattice(c, CX, 450, 190, (32 + b) * 0.25, 1 - inv(4, 11, b) * 0.85, 1, E.outCubic(clamp(b / 3)) * 0.9);
    c.save(); c.globalCompositeOperation = 'lighter';
    const f = Math.exp(-b / 1.2);
    const gr = c.createLinearGradient(0, 0, W, 0);
    gr.addColorStop(0, rgba(acc, 0)); gr.addColorStop(0.5, rgba(mixc(acc, WHITE, 0.6), 0.9 * f + 0.15)); gr.addColorStop(1, rgba(acc, 0));
    c.fillStyle = gr; c.fillRect(0, 498, W, 3);
    c.restore();
    txt(c, b, '像芒格一样思考', CX, 565, 'mega', 0.05, 10.6, { anim: 'blur', scale: 1.0 });
    hline(c, b, CX, 628, 760, 1.2, 10.6, acc, 0.7);
    txt(c, b, '查理·芒格如何思考世界、投资与人生', CX, 690, 'bodyL', 1.6, 10.6, { ls: 0.3, scale: 1.12, col: '#e7e1d6' });
    txt(c, b, 'CHARLES  THOMAS  MUNGER  ·  1924 — 2023', CX, 760, 'label', 2.6, 10.6, { scale: 1.05 });
  },

  // ============================================================ MAP
  map(c, b) {
    txt(c, b, '芒格真正独特的地方：把投资放进一个 [更大的框架]', CX, 250, 'h2', 0.2, 19.3);
    const names = [['多学科', '思维模型'], ['避免', '愚蠢'], ['判断', '企业质量'], ['等待', '高胜率机会'], ['长期', '复利'], ['同一套原则', '处理人生']];
    const cols = ['#5fe1ff', '#ff6b7a', '#ffd479', '#6ee7f9', '#ffb347', '#7ef0c4'].map(hex);
    const out = 19.3, oa = 1 - E.inCubic(inv(out, out + 0.6, b));
    const P = names.map((_, i) => [250 + i * 284, 560 - Math.sin(i / 5 * Math.PI) * 60]);
    for (let i = 0; i < 5; i++) {
      const p = E.inOutCubic(inv(2 + i * 2 + 0.3, 4 + i * 2, b));
      const h = glowLine(c, [[P[i][0] + 62, P[i][1]], [P[i + 1][0] - 62, P[i + 1][1]]], p, mixc(cols[i], cols[i + 1], p), 2, 0.9 * oa);
      if (h && p < 1) { c.save(); c.globalCompositeOperation = 'lighter'; sparkle(c, h[0], h[1], 6, cols[i + 1], oa); c.restore(); }
      if (p >= 1) { c.save(); c.globalCompositeOperation = 'lighter'; for (let k = 0; k < 3; k++) { const u = (b * 0.4 + k / 3) % 1; glow(c, lerp(P[i][0] + 62, P[i + 1][0] - 62, u), lerp(P[i][1], P[i + 1][1], u), 4, cols[i + 1], 0.8 * oa, 1); } c.restore(); }
    }
    names.forEach((nm, i) => {
      const t0 = 2 + i * 2, u = inv(t0 - 0.1, t0 + 0.9, b);
      if (u <= 0) return;
      const e = E.outBack(u), a = Math.min(1, u * 2) * oa, [x, y] = P[i];
      const hl = i >= 2 && i <= 4 ? inv(14, 15, b) : 0;
      c.save(); c.globalCompositeOperation = 'lighter';
      glow(c, x, y, 120 * e * (1 + hl * 0.4), cols[i], (0.3 + 0.2 * hl) * a);
      c.strokeStyle = rgba(cols[i], 0.9 * a); c.lineWidth = 2; c.shadowColor = rgba(cols[i], 1); c.shadowBlur = 18;
      c.beginPath(); c.arc(x, y, 54 * e, 0, Math.PI * 2); c.stroke();
      c.restore();
      ptxt(c, '0' + (i + 1), x, y + 12, 'numS', a, { col: Array.from(mixc(cols[i], WHITE, 0.3)), scale: 0.5, glow: 0.5 });
      ptxt(c, nm[0], x, y + 112, 'h2', a, { col: rgba(mixc(cols[i], WHITE, 0.55)), scale: 0.6, glow: 0.2 });
      ptxt(c, nm[1], x, y + 152, 'h2', a, { col: rgba(mixc(cols[i], WHITE, 0.55)), scale: 0.6, glow: 0.2 });
    });
    // bracket over the value-investing stretch
    const bp = E.outCubic(inv(14, 15.2, b));
    if (bp > 0) {
      const x0 = P[2][0] - 100, x1 = P[4][0] + 100, y = 770;
      c.save(); c.globalAlpha = bp * oa; c.strokeStyle = rgba(GOLD, 0.9); c.lineWidth = 2; c.shadowColor = rgba(GOLD); c.shadowBlur = 14;
      c.beginPath(); c.moveTo(x0, y - 16); c.lineTo(x0, y); c.lineTo(lerp(x0, x1, bp), y); if (bp > 0.99) c.lineTo(x1, y - 16); c.stroke(); c.restore();
    }
    txt(c, b, '价值投资，只是这条链上的 [一段]', (P[2][0] + P[4][0]) / 2, 830, 'body', 14.4, out);
    txt(c, b, '链的起点是“怎么想”，终点是“怎么活”', CX, 905, 'bodyL', 16.2, out, { scale: 1.05 });
  },

  // ============================================================ CH1 THE MAN
  ch1(c, b) {
    chapterCard(c, b, '01', '其人', '1924 — 1978', '律师、通才、巴菲特的合伙人');
    const acc = PAL.acc;
    if (b > 3.8 && b < 14.6) {
      const a = vis(b, 4, 13.4);
      txt(c, b, 'EARLY YEARS', CX, 200, 'label', 4.1, 13.4);
      txt(c, b, '一个从不按常理出牌的人', CX, 285, 'h2', 4.3, 13.4);
      const M = [['1924', '生于奥马哈', ['少年时在巴菲特祖父的', '杂货店打过工']], ['1941', '密歇根大学', ['17 岁入学', '主修数学']], ['1943', '二战入伍', ['在加州理工受训', '成为气象官']], ['1948', '哈佛法学院', ['没有本科学位', '却以优等成绩毕业']], ['1962', '自立门户', ['创办律师事务所', '同时开始投资合伙']]];
      const X0 = 260, X1 = 1660, y = 560;
      const pr = E.inOutSine(inv(4.6, 12, b));
      glowLine(c, [[X0 - 60, y], [X1 + 60, y]], pr, acc, 2, a);
      M.forEach(([yr, t, d], i) => {
        const x = lerp(X0, X1, i / 4), t0 = 5 + i * 1.6, u = inv(t0, t0 + 0.6, b);
        if (u <= 0) return;
        c.save(); c.globalCompositeOperation = 'lighter'; glow(c, x, y, 50 * E.outBack(u), acc, 0.5 * a); glow(c, x, y, 7, WHITE, a * u, 1); c.restore();
        ptxt(c, yr, x, y - 36, 'numS', a * u, { scale: 0.55 });
        ptxt(c, t, x, y + 64, 'h2', a * u, { scale: 0.58, col: '#f4ead7' });
        lines(c, d, x, y + 108, 'small', a * u, { scale: 0.95 }, 32);
      });
    }
    if (b > 13.8 && b < 24.6) {
      const a = vis(b, 14, 23.4);
      const dim = 1 - 0.75 * E.inOutSine(inv(16, 18, b)) + 1.1 * E.inOutSine(inv(20, 22, b));
      const fl = 0.85 + 0.15 * noise1(b * 5);
      c.save(); c.globalCompositeOperation = 'lighter';
      glow(c, CX, 400, 220 * dim * fl, acc, 0.45 * a);
      glow(c, CX, 400, 26 * Math.max(0.3, dim), mixc(acc, WHITE, 0.6), a, 1);
      const r = rng(19);
      for (let i = 0; i < 80; i++) { const x = r() * W, sp = 200 + r() * 300, y = ((b - 14) * sp * 0.5 + r() * H) % H; c.strokeStyle = rgba([150, 170, 200], 0.18 * a * (1 - inv(19, 21, b))); c.lineWidth = 1; c.beginPath(); c.moveTo(x, y); c.lineTo(x - 3, y + 22); c.stroke(); }
      c.restore();
      txt(c, b, '三十出头，他跌入人生谷底', CX, 620, 'h2', 14.4, 23.4);
      txt(c, b, '婚姻破裂；9 岁的儿子因白血病离世', CX, 700, 'body', 15.8, 23.4);
      txt(c, b, '多年后，一次白内障手术的并发症，又让他失去了左眼', CX, 760, 'bodyL', 17.6, 23.4);
      txt(c, b, '他没有自怜，而是继续向前', CX, 870, 'h2', 20.4, 23.4, { col: 'gold', glow: 0.35 });
    }
    if (b > 23.8 && b < 34.6) {
      const a = vis(b, 24, 33.4);
      const u = E.inOutCubic(inv(22.5, 24, b));
      const bx = lerp(520, CX - 40, u), mx = lerp(1400, CX + 40, u), ph = Math.max(0, b - 24) * 0.8;
      const ox = u >= 1 ? Math.cos(ph) * 40 : 40, oy = u >= 1 ? Math.sin(ph) * 14 : 0;
      orb(c, u >= 1 ? CX - ox : bx, 420 - oy, 12, GOLD, a);
      orb(c, u >= 1 ? CX + ox : mx, 420 + oy, 12, hex('#8fb8ff'), a);
      if (b > 24) { c.save(); c.globalCompositeOperation = 'lighter'; const k = inv(24, 25.5, b); glow(c, CX, 420, 300 * E.outCubic(k), GOLD, 0.4 * (1 - k) * a); c.restore(); }
      ptxt(c, '巴菲特', 520, 480, 'small', a * (1 - u), { col: '#ffe6a6' });
      ptxt(c, '芒格', 1400, 480, 'small', a * (1 - u), { col: '#bcd4ff' });
      txt(c, b, '1959', CX, 300, 'year', 24.2, 33.4, { scale: 0.75 });
      txt(c, b, '奥马哈的一场晚宴，两人一见如故', CX, 620, 'h2', 25, 33.4);
      txt(c, b, '巴菲特劝他：做律师赚钱太慢，不如来做投资', CX, 700, 'body', 27.4, 33.4);
      txt(c, b, '一段持续 64 年的伙伴关系，从此开始', CX, 770, 'bodyL', 29.4, 33.4);
    }
    if (b > 33.8 && b < 46.6) {
      const a = vis(b, 34, 45.4);
      txt(c, b, '1962 — 1975 · 惠勒-芒格合伙公司 vs 道琼斯指数', CX, 196, 'label', 34.2, 45.4);
      const m = cum(WMC), d = cum(DJI);
      const X = (i) => lerp(330, 1500, i / 14), Y = (v) => 760 - v / 13.5 * 440;
      c.save(); c.globalAlpha = a * 0.6; c.strokeStyle = rgba(WHITE, 0.07); c.fillStyle = rgba(WHITE, 0.35); c.font = `400 14px ${FAM.mono}`; c.textAlign = 'right';
      for (const v of [1, 4, 8, 12]) { c.beginPath(); c.moveTo(330, Y(v)); c.lineTo(1500, Y(v)); c.stroke(); c.fillText(v + '×', 316, Y(v) + 5); }
      c.textAlign = 'center'; for (const i of [0, 4, 8, 12]) c.fillText(String(1962 + i), X(i), 795);
      c.restore();
      const p = E.inOutSine(inv(35, 40.5, b));
      if (b > 41.5) { c.save(); c.globalCompositeOperation = 'lighter'; glow(c, X(12), Y(m[12]), 160, RED, 0.35 * a * vis(b, 41.6, 45.4)); c.restore(); }
      glowLine(c, d.map((v, i) => [X(i), Y(v)]), p, hex('#8aa4c8'), 2.5, a);
      const h = glowLine(c, m.map((v, i) => [X(i), Y(v)]), p, acc, 3.5, a);
      if (h) { c.save(); c.globalCompositeOperation = 'lighter'; sparkle(c, h[0], h[1], 8, acc, a); c.restore(); }
      ptxt(c, '芒格  ×' + (m[14]).toFixed(1), X(14) + 18, Y(m[14]) + 8, 'body', a * inv(40.5, 41, b), { align: 'left', col: '#ffe6a6', scale: 0.85 });
      ptxt(c, '道指  ×' + (d[14]).toFixed(1), X(14) + 18, Y(d[14]) + 8, 'body', a * inv(40.5, 41, b), { align: 'left', col: '#bcd0ea', scale: 0.85 });
      txt(c, b, '年化 [19.8%] · 同期道指 5.0%', CX, 870, 'h2', 40, 45.4, { scale: 0.95 });
      txt(c, b, '其中 1973—1974 年，连续两年下跌超过 30%', CX, 935, 'bodyL', 42, 45.4);
    }
    if (b > 45.8) {
      const a = vis(b, 46, 55.4);
      orb(c, CX - 60, 330, 11, GOLD, a); orb(c, CX + 60, 330, 11, hex('#8fb8ff'), a);
      c.save(); c.globalAlpha = a * 0.6; c.strokeStyle = rgba(GOLD, 0.6); c.beginPath(); c.moveTo(CX - 45, 330); c.lineTo(CX + 45, 330); c.stroke(); c.restore();
      txt(c, b, '1978 年，他出任伯克希尔·哈撒韦副董事长', CX, 480, 'h2', 46.3, 55.4);
      txt(c, b, '此后 45 年，他是巴菲特最重要的思想伙伴', CX, 565, 'body', 48, 55.4);
      txt(c, b, '巴菲特称他为 [“可怕的说不先生”]——他最常对巴菲特说“不”', CX, 635, 'bodyL', 50, 55.4);
    }
  },

  // ============================================================ CH2 LATTICEWORK
  ch2(c, b) {
    chapterCard(c, b, '02', '思维模型', '多学科 · 多元思维', '拿着锤子的人，看什么都像钉子');
    const acc = PAL.acc, acc2 = PAL.acc2;
    if (b > 3.8 && b < 16.6) {
      const a = vis(b, 4, 15.4);
      // a field of nails
      const r = rng(5);
      c.save(); c.globalAlpha = a * (1 - 0.7 * inv(12, 13.5, b));
      for (let i = 0; i < 46; i++) {
        const x = 160 + r() * 1600, y = 200 + r() * 330, h = 18 + r() * 14, on = inv(4.2 + r() * 2, 5 + r() * 2, b);
        c.strokeStyle = rgba(hex('#9aa5b8'), 0.6 * on); c.lineWidth = 2;
        c.beginPath(); c.moveTo(x, y); c.lineTo(x, y + h); c.stroke();
        c.beginPath(); c.moveTo(x - 6, y); c.lineTo(x + 6, y); c.stroke();
      }
      c.restore();
      // the hammer swinging on every beat
      const sw = Math.exp(-((b % 1)) * 6), ang = -0.9 + sw * 0.9;
      c.save(); c.globalAlpha = a * (1 - 0.8 * inv(12, 13.5, b)); c.translate(CX + 40, 470); c.rotate(ang);
      c.fillStyle = rgba(acc, 0.85); c.shadowColor = rgba(acc); c.shadowBlur = 24;
      c.fillRect(-10, -150, 20, 160); c.fillRect(-52, -182, 104, 40);
      c.restore();
      txt(c, b, '“在拿着锤子的人眼里，世界上的一切都像钉子。”', CX, 650, 'quote', 5, 15.4, { scale: 0.95 });
      txt(c, b, '只懂一门学问的人，会用同一个答案，去解释所有问题', CX, 725, 'body', 8.4, 15.4);
      txt(c, b, '他的解药：在脑中装下 [多个学科] 的模型', CX, 835, 'h2', 12, 15.4);
    }
    if (b > 15.8 && b < 36.6) {
      const a = vis(b, 16, 35.4);
      txt(c, b, 'LATTICEWORK OF MENTAL MODELS', CX, 172, 'label', 16.2, 35.4);
      const ox = CX, oy = 455, rx = 590, ry = 235;
      lattice(c, ox, oy, 150, b * 0.22, a, E.inOutSine(inv(16, 20, b)));
      const D = [['数学', '复利 · 概率'], ['物理', '临界点 · 均衡'], ['生物', '进化 · 适应'], ['心理学', '激励 · 偏差'], ['经济学', '机会成本 · 规模'], ['工程学', '冗余 · 安全边际'], ['会计', '企业的语言'], ['历史', '人性的样本']];
      D.forEach(([t, s], i) => {
        const th = -Math.PI / 2 + i / D.length * Math.PI * 2, x = ox + Math.cos(th) * rx, y = oy + Math.sin(th) * ry;
        const u = inv(17 + i, 17.7 + i, b); if (u <= 0) return;
        const col = LATCOL[i % LATCOL.length];
        c.save(); c.globalCompositeOperation = 'lighter';
        c.strokeStyle = rgba(col, 0.35 * a * u); c.lineWidth = 1; c.setLineDash([3, 6]);
        c.beginPath(); c.moveTo(lerp(ox, x, 0.3), lerp(oy, y, 0.3)); c.lineTo(lerp(ox, x, 0.3 + 0.62 * E.outCubic(u)), lerp(oy, y, 0.3 + 0.62 * E.outCubic(u))); c.stroke();
        const fu = (b * 0.5 + i * 0.13) % 1; glow(c, lerp(x, ox, fu * 0.7), lerp(y, oy, fu * 0.7), 3, col, 0.8 * a * u, 1);
        c.restore();
        pill(c, x, y, t, col, a * u, { s: 26, w: 700 });
        ptxt(c, s, x, y + 52, 'small', a * u, { col: rgba(mixc(col, WHITE, 0.5)), scale: 0.95 });
      });
      txt(c, b, '“大约 80 到 90 个重要模型，就能承担 90% 的工作。”', CX, 860, 'quote', 26, 35.4, { scale: 0.9 });
      txt(c, b, '—— 1994 年，南加州大学商学院演讲', CX, 925, 'small', 28.5, 35.4);
    }
    if (b > 35.8 && b < 48.6) {
      const a = vis(b, 36, 47.4);
      txt(c, b, 'LOLLAPALOOZA EFFECT', CX, 172, 'label', 36.1, 47.4);
      txt(c, b, '鲁拉帕路萨效应', CX, 265, 'h1', 36.4, 47.4, { scale: 0.85 });
      const cx0 = CX, cy0 = 520;
      const F = [['激励', -1, -1], ['社会认同', 1, -1], ['承诺一致', -1, 1], ['权威', 1, 1]];
      F.forEach(([t, sx, sy], i) => {
        const col = LATCOL[i], x0 = cx0 + sx * 620, y0 = cy0 + sy * 200;
        const p = E.inCubic(inv(37.5 + i * 0.4, 43.8, b));
        const x = lerp(x0, cx0, p), y = lerp(y0, cy0, p);
        glowLine(c, [[x0, y0], [x, y]], 1, col, 3, a * (1 - inv(44, 45, b)) * inv(37.5 + i * 0.4, 38 + i * 0.4, b));
        if (b < 44.2) { c.save(); c.globalCompositeOperation = 'lighter'; sparkle(c, x, y, 9, col, a); c.restore(); }
        pill(c, x0 - sx * 10, y0 + sy * 46, t, col, a * inv(37.5 + i * 0.4, 38.2 + i * 0.4, b) * (1 - inv(44, 45, b) * 0.5), { s: 24 });
      });
      if (b > 44) {
        const u = inv(44, 46.5, b);
        c.save(); c.globalCompositeOperation = 'lighter';
        glow(c, cx0, cy0, 500 * E.outExpo(u), GOLD, 0.6 * (1 - u * 0.5) * a);
        glow(c, cx0, cy0, 40, WHITE, a, 1);
        for (let k = 0; k < 3; k++) { const uu = clamp(u * 1.4 - k * 0.15); c.strokeStyle = rgba(GOLD, (1 - uu) * 0.7 * a); c.lineWidth = 2; c.beginPath(); c.arc(cx0, cy0, 40 + 520 * E.outExpo(uu), 0, Math.PI * 2); c.stroke(); }
        c.restore();
      }
      txt(c, b, '多种力量朝同一方向同时发力，结果不是相加，而是 [爆炸]', CX, 820, 'body', 40, 47.4);
      txt(c, b, '它能解释狂热的泡沫与骗局，也能解释伟大企业的崛起', CX, 885, 'bodyL', 45, 47.4);
    }
    if (b > 47.8 && b < 56.6) {
      const a = vis(b, 48, 55.4);
      const r = rng(23), sh = [hex('#c08a24'), hex('#8b5cf6'), hex('#0891b2'), hex('#be123c'), hex('#059669'), hex('#d97706')];
      for (let row = 0; row < 2; row++) {
        let x = 360; const yb = 360 + row * 190;
        c.save(); c.globalAlpha = a; c.fillStyle = rgba(acc, 0.5); c.fillRect(330, yb + 2, 1260, 3); c.restore();
        let k = 0;
        while (x < 1560) {
          const w = 18 + r() * 22, h = 110 + r() * 60, on = inv(48.2 + row * 1.2 + k * 0.06, 48.6 + row * 1.2 + k * 0.06, b);
          k++;
          if (on > 0) {
            const col = sh[Math.floor(r() * sh.length)];
            c.save(); c.globalAlpha = a * on;
            const g = c.createLinearGradient(x, 0, x + w, 0); g.addColorStop(0, rgba(mixc(col, [0, 0, 0], 0.35))); g.addColorStop(0.5, rgba(col)); g.addColorStop(1, rgba(mixc(col, [0, 0, 0], 0.45)));
            c.fillStyle = g; c.fillRect(x, yb - h * E.outBack(on), w - 3, h * E.outBack(on));
            c.fillStyle = rgba(GOLD2, 0.5); c.fillRect(x + 3, yb - h * on + 14, w - 9, 2);
            c.restore();
          } else r();
          x += w;
        }
      }
      txt(c, b, '“我这辈子遇到的智者，没有一个不是每天阅读的——一个都没有。”', CX, 700, 'quote', 49, 55.4, { scale: 0.82 });
      txt(c, b, '孩子们笑称他是 [“一本长了两条腿的书”]', CX, 785, 'body', 52, 55.4);
    }
    if (b > 55.8 && b < 68.6) {
      const a = vis(b, 56, 67.4);
      txt(c, b, '1996 · 一个思想实验', CX, 188, 'label', 56.2, 67.4);
      txt(c, b, '如何把 200 万美元，变成一家 2 万亿美元的可口可乐？', CX, 275, 'h2', 57, 67.4, { scale: 0.9 });
      const rx = CX, ry = 420;
      const leaves = [['数学', '要卖出多少杯？'], ['巴甫洛夫', '条件反射'], ['社会认同', '人人都在喝'], ['规模经济', '成本优势'], ['品牌', '占领心智']];
      leaves.forEach(([t, s], i) => {
        const x = 300 + i * 330, y = 640, u = inv(58.5 + i * 0.6, 59.3 + i * 0.6, b);
        const col = LATCOL[i % LATCOL.length];
        glowLine(c, [[rx, ry + 40], [rx, ry + 110], [x, ry + 110], [x, y - 40]], E.outCubic(u), col, 1.8, a);
        pill(c, x, y, t, col, a * inv(59 + i * 0.6, 59.5 + i * 0.6, b), { s: 24, w: 700 });
        ptxt(c, s, x, y + 50, 'small', a * inv(59 + i * 0.6, 59.5 + i * 0.6, b), { col: rgba(mixc(col, WHITE, 0.5)) });
      });
      c.save(); c.globalCompositeOperation = 'lighter'; glow(c, rx, ry, 150, hex('#ff3048'), 0.4 * a); c.restore();
      pill(c, rx, ry, '200 万 → 2 万亿', hex('#ff5a6e'), a * inv(57.5, 58.2, b), { s: 28, w: 700 });
      txt(c, b, '答案不来自任何一个学科，而来自它们的 [交汇]', CX, 820, 'body', 62, 67.4);
    }
    if (b > 67.8) {
      const a = vis(b, 68, 79.4);
      lattice(c, CX, 380, 180, b * 0.22, a, 1);
      txt(c, b, '模型足够多时，世界从一团噪音，变成一张地图', CX, 680, 'h2', 69, 79.4, { scale: 0.92 });
      txt(c, b, '而其中最锋利的一把工具，是——', CX, 765, 'body', 72, 79.4);
      txt(c, b, '反过来想', CX, 890, 'h1', 75, 79.4, { anim: 'scale', from: 1.4 });
    }
  },

  // ============================================================ CH3 INVERSION
  ch3(c, b) {
    chapterCard(c, b, '03', '逆向', '反过来想 · 避免愚蠢', 'Invert, always invert');
    const acc = PAL.acc;
    if (b > 3.8 && b < 16.6) {
      const a = vis(b, 4, 15.4);
      txt(c, b, '“反过来想，总是反过来想。”', CX, 280, 'quote', 4.5, 15.4, { scale: 1.1 });
      txt(c, b, '—— 数学家卡尔·雅可比 · 芒格最爱引用的一句话', CX, 345, 'small', 6, 15.4);
      txt(c, b, '想要幸福？先列出所有 [通往痛苦] 的路', CX, 460, 'h2', 8, 15.4);
      const items = ['嫉妒', '怨恨', '不可靠', '只从自己的经历中学习'];
      const xs = [540, 780, 1040, 1380];
      items.forEach((s, i) => {
        const u = inv(10 + i * 0.8, 10.6 + i * 0.8, b);
        pill(c, xs[i], 590, s, hex('#ff6b7a'), a * u, { s: 26 });
        const st = E.outCubic(inv(13.4 + i * 0.25, 14.2 + i * 0.25, b));
        if (st > 0) { c.save(); c.globalAlpha = a; c.strokeStyle = rgba(hex('#ff3048'), 0.95); c.lineWidth = 3; c.shadowColor = rgba(RED); c.shadowBlur = 12; const w = s.length * 34 + 60; c.beginPath(); c.moveTo(xs[i] - w / 2, 590); c.lineTo(xs[i] - w / 2 + w * st, 590); c.stroke(); c.restore(); }
      });
      txt(c, b, '——然后，远远避开它们', CX, 700, 'body', 14, 15.4);
      txt(c, b, '1986 年，他在一场毕业演讲中，开出了这份“保证痛苦的处方”', CX, 770, 'bodyL', 14.4, 15.4, { scale: 0.92 });
    }
    if (b > 15.8 && b < 28.6) {
      const a = vis(b, 16, 27.4);
      txt(c, b, '“像我们这样的人，靠持续地 [避免愚蠢]，', CX, 245, 'quote', 16.5, 27.4, { scale: 0.92 });
      txt(c, b, '而不是努力变得非常聪明，获得了惊人的长期优势。”', CX, 318, 'quote', 18, 27.4, { scale: 0.92 });
      const n = 30, A = [1], Bv = [1], r = rng(3);
      for (let i = 1; i <= n; i++) { A.push(A[i - 1] * ([9, 17, 26].includes(i) ? 0.55 : 1.15 + (r() - 0.5) * 0.08)); Bv.push(Bv[i - 1] * (1.09 + (r() - 0.5) * 0.02)); }
      const X = (i) => lerp(320, 1480, i / n), Y = (v) => 800 - v / 15 * 380;
      const p = E.inOutSine(inv(19.5, 25.5, b));
      glowLine(c, A.map((v, i) => [X(i), Y(v)]), p, hex('#ff6b7a'), 2.5, a);
      const h = glowLine(c, Bv.map((v, i) => [X(i), Y(v)]), p, GOLD, 3.5, a);
      if (h) { c.save(); c.globalCompositeOperation = 'lighter'; sparkle(c, h[0], h[1], 8, GOLD, a); c.restore(); }
      ptxt(c, '追求聪明 · 偶尔犯大错', X(n) + 16, Y(A[n]) + 8, 'body', a * inv(25.5, 26, b), { align: 'left', col: '#ffb4b4', scale: 0.8 });
      ptxt(c, '持续不犯蠢', X(n) + 16, Y(Bv[n]) + 8, 'body', a * inv(25.5, 26, b), { align: 'left', col: '#ffe6a6', scale: 0.8 });
      txt(c, b, '示意：前者每年多赚，但几次大错就足以抹平一切', CX, 870, 'small', 26, 27.4, { scale: 1.05 });
    }
    if (b > 27.8 && b < 56.6) {
      const a = vis(b, 28, 55.4);
      txt(c, b, 'THE PSYCHOLOGY OF HUMAN MISJUDGMENT', CX, 172, 'label', 28.2, 55.4);
      txt(c, b, '人类误判心理学', CX, 262, 'h1', 28.5, 55.4, { scale: 0.8 });
      txt(c, b, '1995 年哈佛演讲（2005 年修订）：25 种让聪明人犯错的心理倾向', CX, 330, 'body', 30, 55.4, { scale: 0.92 });
      const C = [
        ['激励机制', ['“给我看激励，', '我就告诉你结果。”', '联邦快递夜班改为', '按“趟”计酬后，', '拖延立刻消失'], hex('#ffd479')],
        ['社会认同', ['别人都在做，', '所以一定是对的？', '从众，是泡沫', '最好的燃料'], hex('#5fe1ff')],
        ['承诺与一致', ['一旦公开表态，', '就很难再改口——', '哪怕事实', '已经变了'], hex('#c9a7ff')],
        ['嫉妒', ['“驱动世界的不是贪婪，', '而是嫉妒。”', '七宗罪里唯一', '毫无乐趣的一种'], hex('#7ef0c4')],
        ['否认现实', ['现实太痛苦时，', '大脑会选择扭曲它', '——于是', '越陷越深'], hex('#ff6b7a')],
      ];
      C.forEach(([t, ls, col], i) => {
        const t0 = 32 + i * 4, u = E.outCubic(inv(t0, t0 + 0.8, b));
        if (u <= 0) return;
        const x = 140 + i * 336, y = 400 + (1 - u) * 40, active = inv(t0, t0 + 0.5, b) * (1 - inv(t0 + 4, t0 + 4.5, b) * (i < 4 ? 1 : 0));
        card(c, x, y, 312, 380, col, a * u, active);
        ptxt(c, '0' + (i + 1), x + 34, y + 62, 'numS', a * u, { align: 'left', scale: 0.45, col: Array.from(col), glow: 0.4 });
        ptxt(c, t, x + 34, y + 120, 'h2', a * u, { align: 'left', scale: 0.62, col: rgba(mixc(col, WHITE, 0.6)) });
        lines(c, ls, x + 34, y + 180, 'body', a * u * (0.75 + 0.25 * active), { align: 'left', scale: 0.72, col: '#d5dbe6' }, 38);
      });
      txt(c, b, '几种倾向一旦叠加，就是“鲁拉帕路萨”式的灾难', CX, 860, 'bodyL', 52.5, 55.4, { scale: 1.05 });
    }
    if (b > 55.8 && b < 68.6) {
      const a = vis(b, 56, 67.4);
      const x0 = 300, y0 = 300, w = 560, h = 470;
      c.save(); c.globalAlpha = a;
      c.fillStyle = 'rgba(30,14,22,0.7)'; c.strokeStyle = rgba(acc, 0.7); c.lineWidth = 1.5; c.shadowColor = rgba(acc, 0.5); c.shadowBlur = 24;
      c.beginPath(); c.roundRect(x0, y0, w, h, 16); c.fill(); c.stroke();
      c.shadowBlur = 0; c.fillStyle = rgba(acc, 0.8); c.beginPath(); c.roundRect(x0 + w / 2 - 70, y0 - 16, 140, 32, 8); c.fill();
      c.restore();
      const Q = ['这在我的能力圈内吗？', '激励有没有扭曲判断？', '我是否只看了支持自己的证据？', '反过来想：怎样会彻底失败？'];
      Q.forEach((q, i) => {
        const y = y0 + 90 + i * 98, t0 = 57.5 + i * 1.4, tick = E.outBack(inv(t0 + 0.4, t0 + 0.9, b));
        c.save(); c.globalAlpha = a * inv(t0, t0 + 0.4, b);
        c.strokeStyle = rgba(acc, 0.9); c.lineWidth = 2; c.strokeRect(x0 + 40, y - 22, 30, 30);
        if (tick > 0) { c.strokeStyle = rgba(hex('#7ef0c4')); c.lineWidth = 4; c.shadowColor = rgba(hex('#7ef0c4')); c.shadowBlur = 14; c.beginPath(); c.moveTo(x0 + 45, y - 8); c.lineTo(x0 + 55, y + 3 * tick); c.lineTo(x0 + 55 + 24 * tick, y - 26 * tick); c.stroke(); }
        c.restore();
        ptxt(c, q, x0 + 92, y + 2, 'body', a * inv(t0, t0 + 0.4, b), { align: 'left', scale: 0.78 });
      });
      txt(c, b, 'CHECKLIST', 960, 370, 'label', 56.4, 67.4, { align: 'left' });
      txt(c, b, '他的对策：像飞行员一样用 [清单]', 956, 455, 'h2', 57, 67.4, { align: 'left', scale: 0.88 });
      txt(c, b, '清单不会让你更聪明，', 962, 560, 'body', 63, 67.4, { align: 'left' });
      txt(c, b, '但能拦住 [大多数愚蠢]', 962, 615, 'body', 64, 67.4, { align: 'left' });
    }
    if (b > 67.8) {
      const a = vis(b, 68, 79.4);
      const sw = Math.sin(b * 0.9) * 0.05;
      c.save(); c.globalAlpha = a;
      for (const [sx, lab, col, k] of [[-1, '我的观点', hex('#9aa5b8'), 0.6], [1, '最强的反方论证', hex('#ffd479'), 1]]) {
        const x = CX + sx * 300, y = 380 + sx * sw * 300;
        c.strokeStyle = rgba(col, 0.9 * k); c.lineWidth = 2; c.shadowColor = rgba(col, k); c.shadowBlur = 20 * k;
        c.beginPath(); c.roundRect(x - 170, y - 70, 340, 140, 14); c.stroke();
        c.shadowBlur = 0;
        ptxt(c, lab, x, y + 12, 'h2', 1, { scale: 0.6, col: rgba(mixc(col, WHITE, 0.4)) });
      }
      c.strokeStyle = rgba(WHITE, 0.3); c.beginPath(); c.moveTo(CX - 130, 380 - sw * 300); c.lineTo(CX + 130, 380 + sw * 300); c.stroke();
      c.restore();
      txt(c, b, '“除非我能比对手更好地驳倒自己的观点，', CX, 630, 'quote', 69, 79.4);
      txt(c, b, '否则我就没有资格发表意见。”', CX, 708, 'quote', 70.5, 79.4);
      txt(c, b, '—— 芒格的“铁律”', CX, 780, 'small', 72.5, 79.4, { scale: 1.1 });
    }
  },

  // ============================================================ CH4 CIRCLE OF COMPETENCE
  ch4(c, b) {
    chapterCard(c, b, '04', '能力圈', 'Circle of Competence', '知道自己不知道什么');
    const acc = PAL.acc;
    if (b > 3.8 && b < 24.6) {
      const a = vis(b, 4, 23.4);
      txt(c, b, '投资只有 [三个篮子]', CX, 230, 'h2', 4.5, 23.4, { scale: 1.1 });
      const K = [[480, '可以投', hex('#7ef0c4'), 6], [960, '不能投', hex('#ff6b7a'), 7], [1440, '太难了', hex('#a5b4fc'), 8]];
      K.forEach(([x, t, col, t0], i) => {
        const u = E.outBack(inv(t0 - 0.5, t0 + 0.3, b)), s = i === 2 ? 1.25 : 1;
        c.save(); c.globalAlpha = a * clamp(u); c.strokeStyle = rgba(col, 0.9); c.lineWidth = 2.5; c.shadowColor = rgba(col); c.shadowBlur = 20;
        c.beginPath(); c.moveTo(x - 130 * s, 540); c.lineTo(x - 95 * s, 680); c.lineTo(x + 95 * s, 680); c.lineTo(x + 130 * s, 540); c.stroke();
        c.restore();
        ptxt(c, t, x, 740, 'h2', a * inv(t0 - 0.3, t0 + 0.3, b), { scale: 0.75, col: rgba(mixc(col, WHITE, 0.5)) });
      });
      const r = rng(8);
      for (let i = 0; i < 34; i++) {
        const t0 = 9 + i * 0.22, dest = r() < 0.12 ? 0 : r() < 0.38 ? 1 : 2, sx = 300 + r() * 1320, jitter = (r() - 0.5);
        const u = inv(t0, t0 + 0.9, b); if (u <= 0) continue;
        const [bx, , col] = K[dest];
        const cnt = i % 9, tx = bx + jitter * (dest === 2 ? 170 : 120), ty = 660 - Math.floor(cnt / 3) * 18 - (dest === 2 ? (i % 4) * 14 : 0);
        const e = E.inCubic(u), x = lerp(sx, tx, E.outCubic(u)), y = lerp(330, ty, e);
        c.save(); c.globalCompositeOperation = 'lighter'; glow(c, x, y, 9, col, a, 1); glow(c, x, y, 22, col, 0.3 * a); c.restore();
      }
      txt(c, b, '“我们把大多数东西，都放进了‘太难’那一堆。”', CX, 840, 'quote', 14, 23.4, { scale: 0.92 });
      txt(c, b, '—— 芒格', CX, 905, 'small', 16, 23.4);
    }
    if (b > 23.8) {
      const a = vis(b, 24, 39.4);
      const ox = CX, oy = 420, R = 190 * E.outBack(inv(24.3, 25.8, b));
      c.save(); c.globalCompositeOperation = 'lighter';
      glow(c, ox, oy, R * 1.6, acc, 0.35 * a);
      c.strokeStyle = rgba(acc, 0.95 * a); c.lineWidth = 2.5; c.shadowColor = rgba(acc); c.shadowBlur = 26;
      c.beginPath(); c.arc(ox, oy, Math.max(1, R), 0, Math.PI * 2); c.stroke();
      c.restore();
      [['保险', -70, -60], ['零售', 70, -30], ['银行', -60, 50], ['消费品', 60, 75]].forEach(([s, dx, dy], i) => ptxt(c, s, ox + dx, oy + dy, 'body', a * inv(26 + i * 0.3, 26.6 + i * 0.3, b), { col: '#e8ecff', scale: 0.85, glow: 0.4 }));
      [['新潮科技', -460, -120], ['大宗商品', 470, -90], ['彩票式机会', -480, 120], ['别人的主场', 460, 140]].forEach(([s, dx, dy], i) => ptxt(c, s, ox + dx + Math.sin(b * 0.4 + i) * 12, oy + dy, 'body', 0.45 * a * inv(27 + i * 0.3, 27.6 + i * 0.3, b), { col: '#7f8798', blur: 3 + 2 * Math.sin(b + i) }));
      txt(c, b, '“知道自己不知道什么，比聪明更有用。”', CX, 740, 'quote', 25, 39.4, { scale: 1.05 });
      txt(c, b, '在别人有优势的游戏里，你注定会输', CX, 830, 'body', 29, 39.4);
      txt(c, b, '所以，只在自己 [真正懂] 的地方下注', CX, 895, 'bodyL', 32, 39.4, { scale: 1.05 });
    }
  },

  // ============================================================ CH5 QUALITY + BUFFETT
  ch5(c, b) {
    chapterCard(c, b, '05', '好生意', '判断企业质量', '他如何改变了巴菲特');
    const acc = PAL.acc, vio = PAL.acc2;
    if (b > 3.8 && b < 20.6) {
      const a = vis(b, 4, 19.4);
      txt(c, b, 'THE MATH OF QUALITY', CX, 170, 'label', 4.1, 19.4);
      txt(c, b, '“长期来看，股票的回报很难超过企业本身的资本回报率。”', CX, 250, 'quote', 4.5, 19.4, { scale: 0.84 });
      const n = 30, A = [], Bv = [];
      for (let i = 0; i <= n; i++) { const k = clamp(i / 5); A.push(Math.pow(1.06, i) * lerp(1, 2, k)); Bv.push(Math.pow(1.18, i) * lerp(1, 0.5, k)); }
      const X = (i) => lerp(320, 1420, i / n), Y = (v) => 760 - v / 75 * 400;
      const p = E.inOutSine(inv(6, 14, b));
      c.save(); c.globalAlpha = a * 0.6; c.strokeStyle = rgba(WHITE, 0.08); c.beginPath(); c.moveTo(320, 760); c.lineTo(1420, 760); c.stroke(); c.restore();
      glowLine(c, A.map((v, i) => [X(i), Y(v)]), p, hex('#9aa5b8'), 2.5, a);
      const h = glowLine(c, Bv.map((v, i) => [X(i), Y(v)]), p, acc, 3.5, a);
      if (h) { c.save(); c.globalCompositeOperation = 'lighter'; sparkle(c, h[0], h[1], 8, acc, a); c.restore(); }
      ptxt(c, 'A · 资本回报 6% · 半价买入', 340, 690, 'small', a * inv(6, 7, b), { align: 'left', col: '#c5cdd9', scale: 1.05 });
      ptxt(c, 'B · 资本回报 18% · 两倍价格买入', 340, 640, 'small', a * inv(6, 7, b), { align: 'left', col: '#ffe6a6', scale: 1.05 });
      ptxt(c, '≈ ' + Math.round(A[n] * inv(13, 14, b)) + ' 倍', X(n) + 20, Y(A[n]) + 10, 'numS', a * inv(13, 14, b), { align: 'left', scale: 0.5, col: '#c5cdd9', glow: 0 });
      ptxt(c, '≈ ' + Math.round(Bv[n] * inv(13, 14, b)) + ' 倍', X(n) + 20, Y(Bv[n]) + 20, 'numS', a * inv(13, 14, b), { align: 'left', scale: 0.62 });
      txt(c, b, '示意：持有 30 年', CX, 805, 'small', 8, 19.4);
      txt(c, b, '买得再便宜，也敌不过 [企业本身的平庸]', CX, 890, 'h2', 16, 19.4, { scale: 0.92 });
    }
    if (b > 19.8 && b < 30.6) {
      const a = vis(b, 20, 29.4);
      const fl = 0.75 + 0.25 * noise1(b * 5);
      c.save(); c.globalCompositeOperation = 'lighter';
      glow(c, 560, 400, 160 * fl, hex('#ff6a1a'), 0.45 * a * (1 - 0.5 * inv(22, 24, b)));
      glow(c, 560, 400, 14, hex('#ffd08a'), a * fl * (1 - 0.5 * inv(22, 24, b)), 1);
      glow(c, 1360, 400, 220, GOLD, 0.45 * a * inv(22, 23.5, b));
      c.restore();
      const cs = [[-110, 0], [-110, -120], [-80, -120], [-80, -150], [-50, -150], [-50, -120], [-20, -120], [-20, -190], [0, -220], [20, -190], [20, -120], [50, -120], [50, -150], [80, -150], [80, -120], [110, -120], [110, 0]];
      glowLine(c, cs.map(([x, y]) => [1360 + x, 470 + y]), E.inOutCubic(inv(21.8, 23.6, b)), GOLD, 2, a);
      const ap = E.inOutCubic(inv(21, 22.8, b));
      const h = glowLine(c, [[720, 400], [1180, 400]], ap, vio, 2, a);
      if (h && ap > 0.98) { c.save(); c.globalAlpha = a; c.strokeStyle = rgba(vio); c.lineWidth = 2; c.beginPath(); c.moveTo(1162, 388); c.lineTo(1180, 400); c.lineTo(1162, 412); c.stroke(); c.restore(); }
      ptxt(c, '格雷厄姆：便宜的“烟蒂”', 560, 560, 'body', a, { col: '#ffc9a0', scale: 0.85 });
      ptxt(c, '芒格：伟大的企业', 1360, 560, 'body', a * inv(22.5, 23.2, b), { col: '#ffe6a6', scale: 0.85 });
      txt(c, b, '“他给我的蓝图很简单：忘掉以极低价格买入一般企业，', CX, 710, 'quote', 23, 29.4, { scale: 0.82 });
      txt(c, b, '改为以合理价格，买入优秀的企业。”', CX, 778, 'quote', 24.5, 29.4, { scale: 0.82 });
      txt(c, b, '—— 巴菲特，2014 年致股东信（伯克希尔 50 周年）', CX, 845, 'small', 26, 29.4, { scale: 1.05 });
    }
    if (b > 29.8 && b < 40.6) {
      const a = vis(b, 30, 39.4);
      txt(c, b, "CASE · 1972 · 喜诗糖果 SEE'S CANDIES", CX, 190, 'label', 30.1, 39.4);
      txt(c, b, '他力主以 3 倍账面价值，买下一家糖果公司', CX, 275, 'h2', 30.5, 39.4, { scale: 0.92 });
      const base = 720, sx = 760, gx = 1160, g = E.outCubic(inv(32.5, 35.6, b));
      c.save(); c.globalAlpha = a;
      c.fillStyle = rgba(hex('#cbb6ff'), 0.9); c.shadowColor = rgba(vio); c.shadowBlur = 20;
      const s0 = E.outCubic(inv(31.5, 32.3, b)); c.fillRect(sx - 60, base - 14 * s0, 120, 14 * s0);
      const hh = 270 * g, gg = c.createLinearGradient(0, base - 270, 0, base); gg.addColorStop(0, rgba(GOLD2)); gg.addColorStop(1, rgba(hex('#7c3aed'), 0.6));
      c.fillStyle = gg; c.shadowColor = rgba(GOLD); c.shadowBlur = 30; c.fillRect(gx - 60, base - hh, 120, hh);
      c.restore();
      ptxt(c, '收购价 $2,500 万', sx, base - 40, 'body', a * s0, { col: '#e8deff', scale: 0.8 });
      ptxt(c, '此后累计税前利润', gx, base - hh - 70, 'small', a * g, { col: '#ffe6a6' });
      ptxt(c, '> $' + Math.round(lerp(0, 20, g)) + ' 亿', gx, base - hh - 22, 'numS', a * g, { scale: 0.62 });
      txt(c, b, '这笔“贵”交易，让巴菲特真正看懂了 [定价权]', CX, 850, 'body', 36.5, 39.4);
    }
    if (b > 39.8 && b < 52.6) {
      const a = vis(b, 40, 51.4);
      const bl = hex('#5aa9ff');
      c.save(); c.globalAlpha = a * 0.35; c.strokeStyle = rgba(bl, 0.5); c.lineWidth = 1;
      for (let x = 360; x <= 1560; x += 40) { c.beginPath(); c.moveTo(x, 180); c.lineTo(x, 600); c.stroke(); }
      for (let y = 180; y <= 600; y += 40) { c.beginPath(); c.moveTo(360, y); c.lineTo(1560, y); c.stroke(); }
      c.restore();
      const bld = [[620, 580], [620, 360], [760, 360], [760, 260], [900, 260], [900, 200], [1020, 200], [1020, 260], [1160, 260], [1160, 360], [1300, 360], [1300, 580], [620, 580]];
      glowLine(c, bld, E.inOutSine(inv(40.2, 44.5, b)), mixc(bl, WHITE, 0.3), 2, a);
      c.save(); c.globalCompositeOperation = 'lighter';
      for (let i = 0; i < 4; i++) for (let j = 0; j < 3; j++) { const on = inv(44 + (i + j) * 0.2, 44.4 + (i + j) * 0.2, b); glow(c, 700 + i * 150, 420 + j * 50, 14, GOLD, 0.8 * on * a, 1); }
      c.restore();
      txt(c, b, '“查理是今日伯克希尔的「建筑师」，', CX, 720, 'quote', 42, 51.4);
      txt(c, b, '而我，是负责日常施工的「总承包商」。”', CX, 795, 'quote', 43.5, 51.4);
      txt(c, b, '—— 巴菲特，2023 年致股东信', CX, 865, 'small', 45, 51.4, { scale: 1.05 });
    }
    if (b > 51.8 && b < 68.6) {
      const a = vis(b, 52, 67.4);
      txt(c, b, '芒格眼中的 [好生意]', CX, 215, 'h2', 52.3, 67.4, { scale: 1.1 });
      const T = [['高资本回报', '赚钱不需要不停砸钱'], ['定价权', '涨价，顾客依然买单'], ['护城河', '对手难以复制'], ['可靠的管理层', '能干，而且诚实'], ['简单易懂', '看得清十年后的样子'], ['长期顺风', '行业在变大，而不是萎缩']];
      T.forEach(([t, s], i) => {
        const x = 420 + (i % 3) * 540, y = 410 + Math.floor(i / 3) * 210, u = E.outCubic(inv(54 + i * 0.8, 54.8 + i * 0.8, b)), col = LATCOL[i % 5];
        card(c, x - 230, y - 75 + (1 - u) * 30, 460, 160, col, a * u, inv(54 + i * 0.8, 55 + i * 0.8, b) * (1 - inv(55.5 + i * 0.8, 57 + i * 0.8, b)));
        ptxt(c, t, x, y + (1 - u) * 30, 'h2', a * u, { scale: 0.68, col: rgba(mixc(col, WHITE, 0.6)) });
        ptxt(c, s, x, y + 50 + (1 - u) * 30, 'body', a * u, { scale: 0.75, col: '#c6cdda' });
      });
      txt(c, b, '他最爱举的例子：[好市多]——他在其董事会任职 20 多年', CX, 860, 'bodyL', 61.5, 67.4, { scale: 1.05 });
    }
    if (b > 67.8) {
      txt(c, b, '找到了好生意，下一个问题是——', CX, 470, 'h2', 68.5, 79.4);
      txt(c, b, '何时出手？', CX, 610, 'h1', 72, 79.4, { anim: 'scale', from: 1.4, scale: 1.1 });
    }
  },

  // ============================================================ CH6 PATIENCE
  ch6(c, b) {
    chapterCard(c, b, '06', '等待', '少数高胜率机会', '像猎人一样耐心');
    const acc = PAL.acc;
    if (b > 3.8 && b < 20.6) {
      const a = vis(b, 4, 19.4);
      const x0 = 240, y0 = 250, rowH = 50;
      c.save(); c.globalAlpha = a; c.fillStyle = 'rgba(8,20,28,0.7)'; c.strokeStyle = rgba(acc, 0.5); c.lineWidth = 1.2;
      c.beginPath(); c.roundRect(x0 - 20, y0 - 50, 740, 600, 12); c.fill(); c.stroke();
      c.font = `500 14px ${FAM.mono}`; c.fillStyle = rgba(acc, 0.7); c.letterSpacing = '3px';
      c.fillText('ODDS BOARD · 赔率由大众决定', x0, y0 - 18);
      c.restore();
      for (let i = 0; i < 10; i++) {
        const y = y0 + 20 + i * rowH, on = inv(4.6 + i * 0.25, 5 + i * 0.25, b), star = i === 6 ? inv(13.5, 14.3, b) : 0;
        const odds = (2.2 + i * 0.7 + noise1(b * 2 + i * 7) * 0.4).toFixed(1), crowd = 0.25 + 0.7 * Math.abs(noise1(i * 3.1 + b * 0.3));
        c.save(); c.globalAlpha = a * on;
        if (star > 0) { c.fillStyle = rgba(GOLD, 0.16 * star); c.fillRect(x0 - 10, y - 30, 720, rowH - 6); c.strokeStyle = rgba(GOLD, star); c.lineWidth = 1.5; c.shadowColor = rgba(GOLD); c.shadowBlur = 20; c.strokeRect(x0 - 10, y - 30, 720, rowH - 6); c.shadowBlur = 0; }
        c.font = `600 18px ${FAM.mono}`; c.fillStyle = star > 0 ? rgba(GOLD2) : rgba(WHITE, 0.55);
        c.fillText(`#${String(i + 1).padStart(2, '0')}`, x0, y);
        c.fillStyle = rgba(star > 0 ? GOLD : hex('#6b7a8c'), 0.7); c.fillRect(x0 + 80, y - 12, 380 * crowd, 10);
        c.font = `700 20px ${FAM.mono}`; c.fillStyle = star > 0 ? rgba(GOLD2) : rgba(WHITE, 0.6);
        c.fillText(odds, x0 + 500, y);
        c.font = `400 16px ${FAM.sans}`; c.fillStyle = star > 0 ? rgba(GOLD2) : rgba(WHITE, 0.3);
        c.fillText(star > 0 ? '胜算明显 · 下重注' : '不下注', x0 + 580, y);
        c.restore();
      }
      txt(c, b, 'PARI-MUTUEL', 1060, 300, 'label', 4.4, 19.4, { align: 'left' });
      txt(c, b, '股市，就像赛马场的彩池', 1056, 385, 'h2', 5, 19.4, { align: 'left', scale: 0.88 });
      txt(c, b, '赔率由大众决定——', 1060, 470, 'body', 7.5, 19.4, { align: 'left' });
      txt(c, b, '只有大众出错时，赔率才会 [站在你这边]', 1060, 528, 'body', 9, 19.4, { align: 'left', scale: 0.92 });
      txt(c, b, '“聪明人只在胜算很大时下重注，', 1060, 640, 'quote', 12, 19.4, { align: 'left', scale: 0.78 });
      txt(c, b, '其余时间，按兵不动。”', 1060, 700, 'quote', 13, 19.4, { align: 'left', scale: 0.78 });
    }
    if (b > 19.8 && b < 36.6) {
      const a = vis(b, 20, 35.4);
      txt(c, b, '“赚大钱靠的不是买进卖出，而是 [等待]。”', CX, 330, 'quote', 21, 35.4, { scale: 1.05 });
      const x0 = 180, x1 = 1740, y = 560, sp = E.inOutSine(inv(21.5, 34, b)), xs = lerp(x0, x1, sp);
      const peaks = [0.18, 0.47, 0.71, 0.9];
      c.save(); c.globalAlpha = a;
      for (let i = 0; i <= 80; i++) { const x = lerp(x0, x1, i / 80); c.fillStyle = rgba(WHITE, 0.12 + (Math.abs(x - xs) < 30 ? 0.4 : 0)); c.fillRect(x - 1, y - 8, 2, 16); }
      c.restore();
      c.save(); c.globalCompositeOperation = 'lighter';
      glow(c, xs, y, 70, acc, 0.5 * a); glow(c, xs, y, 6, WHITE, a, 1);
      for (const pk of peaks) {
        const px = lerp(x0, x1, pk), on = clamp((xs - px) / 60);
        if (on <= 0) continue;
        glowLine(c, [[px, y], [px, y - 160 * E.outBack(on)]], 1, GOLD, 3, a);
        glow(c, px, y - 160 * E.outBack(on), 40, GOLD, 0.6 * a); glow(c, px, y - 160 * E.outBack(on), 6, WHITE, a, 1);
      }
      c.restore();
      txt(c, b, '大部分时间，什么都不做', CX, 710, 'body', 25, 35.4, { scale: 1.1 });
      txt(c, b, '一生中真正重要的机会，往往只有 [寥寥几次]', CX, 785, 'bodyL', 29, 35.4, { scale: 1.1 });
    }
    if (b > 35.8 && b < 48.6) {
      txt(c, b, '当真正的机会出现时——', CX, 470, 'h2', 36.5, 39.5, { scale: 1.1 });
      if (b > 40) {
        const u = inv(40, 43, b);
        c.save(); c.globalCompositeOperation = 'lighter';
        glow(c, CX, 520, 700 * E.outExpo(u), GOLD, 0.55 * (1 - u * 0.6));
        for (let k = 0; k < 3; k++) { const uu = clamp(u * 1.3 - k * 0.12); c.strokeStyle = rgba(GOLD, (1 - uu) * 0.7); c.lineWidth = 3; c.beginPath(); c.ellipse(CX, 520, 60 + 900 * E.outExpo(uu), 30 + 360 * E.outExpo(uu), 0, 0, Math.PI * 2); c.stroke(); }
        c.restore();
      }
      txt(c, b, '下重注', CX, 600, 'mega', 40, 47.4, { from: 2.2, scale: 1.1 });
      txt(c, b, '“如果把我们最好的 15 个决策拿掉，我们的业绩将非常平庸。”', CX, 790, 'quote', 42.5, 47.4, { scale: 0.8 });
      txt(c, b, '—— 芒格', CX, 855, 'small', 44, 47.4);
    }
    if (b > 47.8) {
      const a = vis(b, 48, 63.4);
      const C = [['2008 · 比亚迪', ['他力主伯克希尔入股', '这家中国电池与汽车公司'], hex('#7ef0c4'), 560], ['2009 · 富国银行', ['金融危机最深处，他用', '《每日期刊》的现金大举买入'], GOLD, 1360]];
      C.forEach(([t, ls, col, x], i) => {
        const u = E.outCubic(inv(48.5 + i * 1.2, 49.3 + i * 1.2, b));
        card(c, x - 300, 250 + (1 - u) * 30, 600, 260, col, a * u, 0.4);
        ptxt(c, t, x, 330 + (1 - u) * 30, 'h2', a * u, { scale: 0.75, col: rgba(mixc(col, WHITE, 0.5)) });
        lines(c, ls, x, 405 + (1 - u) * 30, 'body', a * u, { scale: 0.85, col: '#d5dbe6' }, 46);
      });
      txt(c, b, '他把这叫作 [“坐着不动的投资法”]', CX, 680, 'h2', 55, 63.4);
      txt(c, b, '买入伟大的企业，然后——耐心地坐着', CX, 760, 'body', 57, 63.4);
    }
  },

  // ============================================================ CH7 COMPOUNDING
  ch7(c, b) {
    chapterCard(c, b, '07', '复利', '长期 · 不打断', '复利的第一条规则');
    const acc = PAL.acc;
    if (b > 3.8 && b < 20.6) {
      const a = vis(b, 4, 19.4);
      txt(c, b, '“复利的第一条规则：', CX, 225, 'quote', 4.5, 19.4, { scale: 1.05 });
      txt(c, b, '除非万不得已，永远不要 [打断] 它。”', CX, 300, 'quote', 6, 19.4, { scale: 1.05 });
      const n = 40, A = [1], Bv = [1], cuts = [8, 16, 24, 32];
      for (let i = 1; i <= n; i++) { A.push(A[i - 1] * 1.12); Bv.push(Bv[i - 1] * 1.12 * (cuts.includes(i) ? 0.78 : 1)); }
      const X = (i) => lerp(320, 1420, i / n), Y = (v) => 800 - v / 95 * 400;
      const p = E.inOutSine(inv(7, 14.5, b));
      glowLine(c, Bv.map((v, i) => [X(i), Y(v)]), p, hex('#9aa5b8'), 2.5, a);
      const h = glowLine(c, A.map((v, i) => [X(i), Y(v)]), p, acc, 3.5, a);
      if (h) { c.save(); c.globalCompositeOperation = 'lighter'; sparkle(c, h[0], h[1], 9, acc, a); c.restore(); }
      for (const ci of cuts) { if (p * n < ci) continue; c.save(); c.globalAlpha = a; c.strokeStyle = rgba(RED); c.lineWidth = 2.5; const x = X(ci), y = Y(Bv[ci]); c.beginPath(); c.moveTo(x - 7, y - 7); c.lineTo(x + 7, y + 7); c.moveTo(x + 7, y - 7); c.lineTo(x - 7, y + 7); c.stroke(); c.restore(); }
      ptxt(c, '一直持有 · ×' + Math.round(A[n]), X(n) + 16, Y(A[n]) + 10, 'body', a * inv(14.5, 15.2, b), { align: 'left', col: '#ffe6a6', scale: 0.85 });
      ptxt(c, '每 8 年折腾一次 · ×' + Math.round(Bv[n]), X(n) + 16, Y(Bv[n]) + 10, 'body', a * inv(14.5, 15.2, b), { align: 'left', col: '#c5cdd9', scale: 0.85 });
      txt(c, b, '示意：年化 12%，40 年；每次“打断”损失 22%（税费、踏空、失误）', CX, 860, 'small', 16, 19.4);
    }
    if (b > 19.8 && b < 36.6) {
      const a = vis(b, 20, 35.4);
      txt(c, b, '伯克希尔的股价，曾经 [三次腰斩]', CX, 230, 'h2', 20.5, 35.4, { scale: 1.05 });
      const K = [[0, 1], [0.1, 3], [0.16, 1.4], [0.24, 4], [0.38, 20], [0.48, 60], [0.53, 30], [0.62, 90], [0.74, 200], [0.8, 100], [0.9, 220], [1, 420]];
      const X = (u) => lerp(320, 1600, u), Y = (v) => 760 - Math.log10(v) / Math.log10(500) * 420;
      const r = rng(4), pts = [];
      for (let i = 0; i < K.length - 1; i++) for (let j = 0; j < 6; j++) { const f = j / 6; pts.push([X(lerp(K[i][0], K[i + 1][0], f)), Y(Math.exp(lerp(Math.log(K[i][1]), Math.log(K[i + 1][1]), f)) * (1 + (j ? (r() - 0.5) * 0.12 : 0)))]); }
      pts.push([X(1), Y(420)]);
      const p = E.inOutSine(inv(21, 27, b));
      const h = glowLine(c, pts, p, acc, 3, a);
      if (h && p < 1) { c.save(); c.globalCompositeOperation = 'lighter'; sparkle(c, h[0], h[1], 8, acc, a); c.restore(); }
      [[0.1, 0.16, 3, '1973—1975'], [0.48, 0.53, 60, '1998—2000'], [0.74, 0.8, 200, '2007—2009']].forEach(([u0, u1, v, lab], i) => {
        const on = inv(21 + u1 * 6, 22 + u1 * 6, b); if (on <= 0) return;
        c.save(); c.globalCompositeOperation = 'lighter'; glow(c, X((u0 + u1) / 2), Y(v * 0.7), 110, RED, 0.35 * on * a); c.restore();
        ptxt(c, '-50%', X((u0 + u1) / 2), Y(v) - 40, 'numS', a * on, { scale: 0.42, col: '#ff8a8a', glow: 0.3 });
        ptxt(c, lab, X((u0 + u1) / 2), Y(v / 2.2) + 40, 'small', a * on, { col: '#ffc2c2' });
      });
      ptxt(c, '示意图', 1600, 790, 'small', a * 0.8, { align: 'right' });
      txt(c, b, '“如果你不能平静地面对一个世纪两三次的 50% 下跌，', CX, 860, 'quote', 27, 35.4, { scale: 0.8 });
      txt(c, b, '你就不配做普通股股东。”', CX, 925, 'quote', 28.5, 35.4, { scale: 0.8 });
    }
    if (b > 35.8) {
      const a = vis(b, 36, 55.4);
      [['好企业', -380], ['合理价格', 0], ['足够长的时间', 380]].forEach(([t, dx], i) => pill(c, CX + dx, 250, t, LATCOL[[3, 0, 1][i]], a * inv(36.5 + i * 0.6, 37.1 + i * 0.6, b), { s: 30, w: 700 }));
      txt(c, b, '复利只需要三样东西，而最难的一样，是 [忍住不动]', CX, 370, 'h2', 39.5, 55.4, { scale: 0.88 });
      // accelerating curve into the climax
      const p = E.inCubic(inv(43, 48, b));
      const pts = []; for (let i = 0; i <= 60; i++) { const u = i / 60; pts.push([lerp(260, 1660, u), 900 - (Math.exp(u * 4.2) - 1) / (Math.exp(4.2) - 1) * 420]); }
      const h = glowLine(c, pts, p, GOLD, 4, a * (1 - 0.6 * inv(49, 51, b)));
      if (h && p > 0) { c.save(); c.globalCompositeOperation = 'lighter'; sparkle(c, h[0], h[1], 10 + 10 * p, GOLD, a); c.restore(); }
      if (b > 48) {
        const u = inv(48, 51, b);
        c.save(); c.globalCompositeOperation = 'lighter';
        glow(c, 1660, 480, 800 * E.outExpo(u), GOLD, 0.5 * (1 - u * 0.6) * a);
        const r = rng(2);
        for (let i = 0; i < 120; i++) { const ang = r() * Math.PI * 2, d = (200 + r() * 900) * E.outCubic(u); glow(c, 1660 + Math.cos(ang) * d, 480 + Math.sin(ang) * d * 0.6, 3 + r() * 4, GOLD2, (1 - u) * a, 1); }
        c.restore();
      }
      txt(c, b, '“理解复利的力量，以及获得它有多难，', CX, 640, 'quote', 48, 55.4, { scale: 1.05 });
      txt(c, b, '是理解许多事情的核心。”', CX, 725, 'quote', 49.5, 55.4, { scale: 1.05 });
      txt(c, b, '—— 查理·芒格', CX, 800, 'small', 51, 55.4, { scale: 1.1 });
    }
  },

  // ============================================================ CH8 LIFE
  ch8(c, b) {
    chapterCard(c, b, '08', '人生', '同一套原则', '投资，只是人生的一个特例');
    const acc = PAL.acc, warm = PAL.acc2;
    if (b > 3.8 && b < 20.6) {
      const a = vis(b, 4, 19.4);
      for (let i = 0; i < 8; i++) {
        const on = inv(4.5 + i * 0.5, 5 + i * 0.5, b), x = 420 + i * 140, y = 520 - i * 40;
        c.save(); c.globalAlpha = a * on; c.fillStyle = rgba(mixc(acc, warm, i / 7), 0.85); c.shadowColor = rgba(acc); c.shadowBlur = 20; c.fillRect(x, y, 120, 6); c.restore();
      }
      const top = inv(8.5, 9.5, b); orb(c, 420 + 7 * 140 + 60, 520 - 7 * 40 - 30, 10, warm, a * top);
      txt(c, b, '“想得到你想要的东西，最好的办法，', CX, 650, 'quote', 5, 19.4, { scale: 1.05 });
      txt(c, b, '是让自己 [配得上] 它。”', CX, 730, 'quote', 6.5, 19.4, { scale: 1.05 });
      txt(c, b, '—— 2007 年，南加州大学法学院毕业演讲', CX, 800, 'small', 8, 19.4, { scale: 1.05 });
      txt(c, b, '这条原则，对投资、事业、婚姻同样成立', CX, 885, 'body', 11, 19.4);
    }
    if (b > 19.8 && b < 36.6) {
      const a = vis(b, 20, 35.4);
      const u = E.inOutSine(inv(20, 33, b)), ang = Math.PI * (1 - u);
      c.save(); c.globalAlpha = a * 0.5; c.strokeStyle = rgba(warm, 0.5); c.setLineDash([4, 8]); c.beginPath(); c.arc(CX, 600, 420, Math.PI, 0); c.stroke(); c.restore();
      const sx = CX + Math.cos(ang) * 420, sy = 600 - Math.sin(ang) * 420;
      c.save(); c.globalCompositeOperation = 'lighter'; glow(c, sx, sy, 140, warm, 0.6 * a); glow(c, sx, sy, 22, WHITE, a, 1); c.restore();
      c.save(); c.globalAlpha = a; c.strokeStyle = rgba(acc, 0.9); c.lineWidth = 2.5; c.shadowColor = rgba(acc); c.shadowBlur = 14; c.beginPath();
      for (let i = 0; i <= 40; i++) { const x = lerp(560, 1360, i / 40), y = 600 - (Math.pow(1.06, i) - 1) / (Math.pow(1.06, 40) - 1) * 200; if (i / 40 > u) break; i ? c.lineTo(x, y) : c.moveTo(x, y); }
      c.stroke(); c.restore();
      txt(c, b, '“每天睡觉前，都比早上醒来时聪明一点。”', CX, 720, 'quote', 21, 35.4, { scale: 1.05 });
      txt(c, b, '知识和金钱一样，会 [复利]', CX, 805, 'body', 26, 35.4, { scale: 1.05 });
      txt(c, b, '直到 99 岁，他仍然每天读书', CX, 870, 'bodyL', 29, 35.4);
    }
    if (b > 35.8 && b < 52.6) {
      const a = vis(b, 36, 51.4);
      ['嫉妒', '怨恨', '报复', '自怜'].forEach((s, i) => {
        const x = 480 + i * 320, y = 400, d = inv(46 + i * 0.4, 48.5 + i * 0.4, b);
        c.save(); c.globalAlpha = a * (1 - d);
        const g = c.createRadialGradient(x, y, 0, x, y, 90); g.addColorStop(0, 'rgba(60,20,30,0.95)'); g.addColorStop(1, 'rgba(60,20,30,0)');
        c.fillStyle = g; c.beginPath(); c.arc(x, y, 90, 0, Math.PI * 2); c.fill();
        c.strokeStyle = rgba(hex('#ff6b7a'), 0.5); c.lineWidth = 1.5; c.beginPath(); c.arc(x, y, 70, 0, Math.PI * 2); c.stroke();
        c.restore();
        ptxt(c, s, x, y + 14, 'h2', a * (1 - d), { scale: 0.75, col: '#ffb4b4' });
        if (d > 0) { c.save(); c.globalCompositeOperation = 'lighter'; const r = rng(30 + i); for (let k = 0; k < 30; k++) { const an = r() * Math.PI * 2, dd = 140 * E.outCubic(d) * (0.4 + r()); glow(c, x + Math.cos(an) * dd, y + Math.sin(an) * dd - 60 * d, 3, warm, (1 - d) * a, 1); } c.restore(); }
      });
      txt(c, b, '“嫉妒、怨恨、报复和自怜，都是灾难性的思维方式。”', CX, 640, 'quote', 38, 51.4, { scale: 0.88 });
      txt(c, b, '他说：嫉妒是七宗罪里，唯一一个 [毫无乐趣] 的', CX, 730, 'body', 42.5, 51.4);
      txt(c, b, '远离它们，人生就已经赢了一大半', CX, 800, 'bodyL', 47, 51.4, { scale: 1.05 });
    }
    if (b > 51.8 && b < 64.6) {
      const a = vis(b, 52, 63.4);
      txt(c, b, '他给年轻人的 [职业三原则]', CX, 250, 'h2', 52.3, 63.4, { scale: 1.05 });
      const R = [['一', ['不卖你自己', '不会买的东西']], ['二', ['不为你不尊重、', '不欣赏的人工作']], ['三', ['只和你喜欢的人', '一起共事']]];
      R.forEach(([n, ls], i) => {
        const x = 480 + i * 480, u = E.outCubic(inv(53.5 + i * 1.5, 54.3 + i * 1.5, b)), col = LATCOL[[3, 1, 0][i]];
        card(c, x - 200, 360 + (1 - u) * 30, 400, 340, col, a * u, inv(53.5 + i * 1.5, 54 + i * 1.5, b) * (1 - inv(55 + i * 1.5, 56 + i * 1.5, b)));
        ptxt(c, n, x, 470 + (1 - u) * 30, 'h1', a * u, { scale: 0.85, col: rgba(mixc(col, WHITE, 0.4)), glow: 0.4 });
        lines(c, ls, x, 570 + (1 - u) * 30, 'body', a * u, { scale: 0.95 }, 48);
      });
    }
    if (b > 63.8) {
      const a = vis(b, 64, 79.4);
      const k = inv(64, 67, b);
      c.save(); c.globalCompositeOperation = 'lighter';
      glow(c, CX, 200, 160 + 60 * Math.sin(b * 0.8), warm, (0.25 + 0.25 * k) * a);
      glow(c, CX, 200, 10, WHITE, a, 1);
      c.restore();
      txt(c, b, '2023.11.28', CX, 330, 'year', 64.4, 79.4, { scale: 0.6 });
      txt(c, b, '查理·芒格辞世，享年 99 岁', CX, 430, 'h2', 65.3, 79.4, { scale: 1.05 });
      txt(c, b, '距离他的 100 岁生日，只差 34 天', CX, 500, 'bodyL', 66.5, 79.4, { scale: 1.05 });
      txt(c, b, '“没有查理的启发、智慧和参与，', CX, 640, 'quote', 69, 79.4);
      txt(c, b, '伯克希尔不可能有今天。”', CX, 718, 'quote', 70.5, 79.4);
      txt(c, b, '—— 巴菲特', CX, 790, 'small', 72, 79.4, { scale: 1.1 });
      txt(c, b, '他留下的，不只是财富，而是一种 [思考的方法]', CX, 895, 'body', 74, 79.4);
    }
  },

  // ============================================================ OUTRO
  outro(c, b) {
    const acc = PAL.acc;
    if (b < 16.6) {
      const a = vis(b, 0, 15.4);
      txt(c, b, '芒格的世界模型', CX, 150, 'h2', 0.3, 15.4);
      const N = ['多学科思维', '反过来想', '避免愚蠢', '能力圈', '好企业', '耐心等待', '长期复利'];
      const ox = CX, oy = 545, rx = 600, ry = 290;
      const P = N.map((_, i) => { const th = -Math.PI / 2 + i / N.length * Math.PI * 2; return [ox + Math.cos(th) * rx, oy + Math.sin(th) * ry]; });
      c.save(); c.globalCompositeOperation = 'lighter';
      N.forEach((_, i) => {
        const t0 = 0.8 + i * 1.2, u = inv(t0, t0 + 0.6, b); if (u <= 0) return;
        const j = (i + 1) % N.length, col = LATCOL[i % 5], uj = inv(t0 + 0.6, t0 + 1.6, b);
        if (uj > 0 && (j > i || b > 9.5)) { c.strokeStyle = rgba(col, 0.5 * a * uj); c.lineWidth = 1.5; c.beginPath(); c.moveTo(P[i][0], P[i][1]); c.lineTo(lerp(P[i][0], P[j][0], uj), lerp(P[i][1], P[j][1], uj)); c.stroke(); }
        c.strokeStyle = rgba(col, 0.25 * a * u); c.lineWidth = 1; c.beginPath(); c.moveTo(ox, oy); c.lineTo(lerp(ox, P[i][0], u), lerp(oy, P[i][1], u)); c.stroke();
        glow(c, P[i][0], P[i][1], 60 * E.outBack(u), col, 0.45 * a); glow(c, P[i][0], P[i][1], 7, WHITE, a * u, 1);
        const fu = ((b * 0.25 + i / N.length) % 1), fi = Math.floor(fu * N.length), ff = fu * N.length - fi;
        if (b > 10) glow(c, lerp(P[fi][0], P[(fi + 1) % N.length][0], ff), lerp(P[fi][1], P[(fi + 1) % N.length][1], ff), 4, GOLD2, 0.8 * a, 1);
      });
      glow(c, ox, oy, 230, acc, 0.4 * a); glow(c, ox, oy, 14, WHITE, a, 1);
      c.restore();
      N.forEach((s, i) => { const below = P[i][1] >= oy - 10; txt(c, b, s, P[i][0], P[i][1] + (below ? 50 : -28), 'body', 0.9 + i * 1.2, 15.4, { col: rgba(mixc(LATCOL[i % 5], WHITE, 0.5)), scale: 0.9 }); });
      txt(c, b, '人生', ox, oy + 20, 'h2', 0.4, 15.4, { col: 'gold', glow: 0.6, scale: 1.2 });
      txt(c, b, '同一套原则，从投资延伸到人生', CX, 930, 'bodyL', 10, 15.4, { scale: 1.05 });
    }
    if (b > 15.8 && b < 26.6) {
      txt(c, b, '投资，是这套世界观 [最赚钱] 的应用', CX, 470, 'h2', 16.5, 25.4, { scale: 1.1 });
      txt(c, b, '人生，是它 [最重要] 的应用', CX, 580, 'h2', 18.5, 25.4, { scale: 1.1 });
    }
    if (b > 25.8 && b < 32.6) {
      txt(c, b, '“我没什么要补充的。”', CX, 520, 'h1', 26, 31.2, { anim: 'scale', from: 1.3, col: '#f6f1e7', scale: 0.9 });
      txt(c, b, '—— 芒格在伯克希尔股东大会上最经典的一句台词', CX, 610, 'small', 27.5, 31.2, { scale: 1.1 });
      txt(c, b, '资料来源：伯克希尔·哈撒韦致股东信、芒格公开演讲等 · 仅供学习交流，不构成任何投资建议', CX, 960, 'small', 28.5, 31.2, { scale: 0.85 });
    }
    // ---- brand ending: particles converge into the logo -> clear logo -> gold 巴芒价值 on the heavy beat -> sheen -> fade
    if (b > 31.4) {
      const lx = CX, ly = 390, S = 220;
      const r = rng(91);
      c.save(); c.globalCompositeOperation = 'lighter';
      LOGO_PTS.forEach(([nx, ny, col], i) => {
        const sx = r() * W, sy = r() * H, d = r(), sw = r() - 0.5;
        const k = E.inOutCubic(clamp((b - 31.8 - d * 0.7) / 1.8));
        const tx = lx + nx * S, ty = ly + ny * S, ang = sw * (1 - k) * 2.6;
        const dx = lerp(sx, tx, k) - tx, dy = lerp(sy, ty, k) - ty;
        let x = tx + dx * Math.cos(ang) - dy * Math.sin(ang), y = ty + dx * Math.sin(ang) + dy * Math.cos(ang);
        const dr = E.inOutSine(clamp((b - 35.2) / 3.8));          // after the clear logo appears the dust drifts away
        x += nx * dr * 320 + Math.sin(i * 1.7) * dr * 50; y += ny * dr * 320 + Math.cos(i * 1.3) * dr * 50;
        const a = clamp((b - 31.4) / 0.6) * (0.9 - 0.7 * dr);
        glow(c, x, y, 2 + 1.4 * (1 - k), mixc(col, WHITE, 0.25), a, 1);
      });
      const flash = b >= 36 ? Math.exp(-(b - 36) * TL.BEAT / 0.35) : 0;
      glow(c, lx, ly, 300, LOGO_BLUE, (0.22 + 0.45 * flash) * E.outCubic(inv(32, 34, b)));
      c.restore();
      drawLogoImg(c, lx, ly, S, E.outCubic(inv(34, 35.35, b)));
      if (b >= 36) {
        const T1 = brandText(LOGO_TEXT, `900 112px ${FAM.serif}`, 112, 0.08, 'gold');
        const T2 = brandText(LOGO_SUB, `600 30px ${FAM.cor}`, 30, 0.46, SUB_GOLD);
        const sh = inv(37.4, 39.5, b);
        c.save(); c.shadowColor = 'rgba(255,186,80,0.35)'; c.shadowBlur = 24;
        blitText(c, T1, CX, 662, 'center', 1, inv(36, 37.35, b), sh > 0 && sh < 1 ? sh : null);
        c.restore();
        const hw = T1.w / 2 + 44, ln = 170 * E.outCubic(inv(36.45, 37.95, b));
        c.save(); c.strokeStyle = 'rgba(214,178,112,0.7)'; c.lineWidth = 1.2;
        for (const sg of [-1, 1]) { c.beginPath(); c.moveTo(CX + sg * hw, 620); c.lineTo(CX + sg * (hw + ln), 620); c.stroke(); }
        c.restore();
        blitText(c, T2, CX, 722, 'center', 1, inv(36.75, 38.1, b));
      }
    }
  },
};
window.SCENE_DRAW = SCENE_DRAW;
window.SCENE_YEARS = SCENE_YEARS;
