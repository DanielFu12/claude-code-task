// 《出厂设置》v3 画面编排：按 story.js 的段落 id 组织；S.T(i) = 本段第 i 张卡片开始的时间。
// 粒子/3D 用世界坐标（原点在画面中心，y 向上，1 单位 ≈ 1 像素）；文字卡片由引擎自动生成（底部 y≈905 / 中央 / 顶部）。
import { PB, C, textPoints, imagePoints, spherePoints, ringPoints, galaxyPoints, brainPoints, helixPoints, linePoints, boxPoints,
  glowSprites, lines, polyline, grid, rng, E as EZ, clamp, lerp, DIST as D } from './engine.js';

const emName = ch => { const cps = [...ch].map(c => c.codePointAt(0).toString(16)); return cps.includes('200d') ? cps.join('-') : cps.filter(c => c !== 'fe0f').join('-'); };
const em = ch => `/assets/emoji/${emName(ch)}.svg`;
const tb = n => `/video2/node_modules/@tabler/icons/icons/outline/${n}.svg`;
const I = {
  snake: em('🐍'), spider: tb('spider'), car: tb('car'), plug: tb('plug'), tea: em('🧋'), phone: tb('device-mobile'),
  eagle: em('🦅'), book: em('📖'), heart: tb('heart'), eye: tb('eye'), city: em('🏙️'), apple: em('🍎'), donut: em('🍩'),
  fries: em('🍟'), lion: em('🦁'), monkey: em('🐒'), flower: em('🌸'), film: em('🎬'), broken: em('💔'), shake: em('🤝'),
  sprout: em('🌱'), scroll: em('📜'), house: em('🏠'), wind: em('🌬️'), alarm: tb('alarm'), msgs: tb('messages'),
};
export const PRELOAD = Object.values(I);

// ---------- 工具
const mk = (seed, fn) => () => { const pb = new PB(seed); fn(pb); return pb.build(); };
const ic = (pb, src, x, y, size, o = {}) => imagePoints(pb, src, { x, y, size, count: o.count || Math.round(size * size * 0.11), ps: o.ps || 2.2, color: o.color, keep: o.keep, bright: (o.bright ?? 1) * 1.25, depth: o.depth, edges: o.edges });
const txt = (pb, s, x, y, size, o = {}) => textPoints(pb, s, { x, y, size, font: `${o.w || 200} ${size}px ${o.f || 'Inter'}`, count: o.count, color: o.color, ps: o.ps || 2.2, bright: o.bright, depth: o.depth });
const cap = (S, en, cn, o = {}) => S.cap(`${en} · <b>${cn}</b>`, { y: 66, ...o });
const R = (x, y) => [x, y, 0];
const dim = (pb, k) => { for (let i = 0; i < pb.c.length; i++) pb.c[i] *= k; };

function grassBlades(pb, o = {}) {
  const r = pb.r, { y0 = -250, w = 1800, n = 560, h = 300, color = C.champ } = o;
  for (let i = 0; i < n; i++) {
    const x0 = (r() - .5) * w, hh = h * (0.35 + r() * 0.8), bend = (r() - .4) * 70, z = (r() - .5) * 360;
    const pts = []; for (let k = 0; k <= 6; k++) { const t = k / 6; pts.push([x0 + bend * t * t, y0 + hh * t]); }
    linePoints(pb, pts, { count: 34, color, ps: 1.9, w: 3, z });
  }
}
function treeOfLife(pb, o = {}) {
  const r = pb.r;
  const br = (x, y, ang, len, depth) => {
    const x2 = x + Math.cos(ang) * len, y2 = y + Math.sin(ang) * len;
    linePoints(pb, [[x, y], [x2, y2]], { count: Math.round(len * (depth > 5 ? 1.4 : 0.9)), color: depth < 3 ? C.warm : C.champ, ps: 2, w: Math.max(2, depth * 1.6) });
    if (depth > 0) { const sp = 0.32 + r() * 0.25; br(x2, y2, ang + sp, len * (0.68 + r() * 0.1), depth - 1); br(x2, y2, ang - sp, len * (0.68 + r() * 0.1), depth - 1); }
    else for (let k = 0; k < 14; k++) pb.add(x2 + (r() - .5) * 14, y2 + (r() - .5) * 14, (r() - .5) * 20, C.white, 2.4, 1.3);
  };
  br(o.x || 0, o.y || -300, Math.PI / 2, o.len || 170, o.depth || 7);
}
const circlePts = (n, Rr, cx = 0, cy = 0) => Array.from({ length: n }, (_, i) => [cx + Rr * Math.cos(i / n * Math.PI * 2), cy + Rr * Math.sin(i / n * Math.PI * 2)]);
function iconGrid(pb, src, cols, rows, cx, cy, step, size, o = {}) {
  for (let j = 0; j < rows; j++) for (let i = 0; i < cols; i++) ic(pb, typeof src === 'function' ? src(i, j) : src, cx + (i - (cols - 1) / 2) * step, cy - (j - (rows - 1) / 2) * step, size, o);
}
function dotBlock(pb, n, cols, x0, y0, step, color) {
  const r = pb.r;
  for (let i = 0; i < n; i++) { const c = i % cols, rr = Math.floor(i / cols); for (let k = 0; k < 5; k++) pb.add(x0 + c * step + (r() - .5) * 3, y0 - rr * step + (r() - .5) * 3, (r() - .5) * 6, color, 2.2, 1.1); }
}
const people = (n, seed, Rr = 330, cx = 0, cy = 0) => { const r = rng(seed); return Array.from({ length: n }, () => { const a = r() * Math.PI * 2, d = Math.sqrt(r()) * Rr; return { x: cx + Math.cos(a) * d * 1.5, y: cy + Math.sin(a) * d * 0.8, z: (r() - .5) * 200, size: 30, color: C.champ }; }); };
function knn(nodes, k = 2) { const segs = []; nodes.forEach((a, i) => { nodes.map((b, j) => [j, Math.hypot(a.x - b.x, a.y - b.y)]).filter(([j]) => j !== i).sort((p, q) => p[1] - q[1]).slice(0, k).forEach(([j]) => { if (j > i) segs.push([a.x, a.y, a.z || 0, nodes[j].x, nodes[j].y, nodes[j].z || 0]); }); }); return segs; }
function ecg(x0, x1, y, amp) {   // 心电图折线
  const pts = []; const n = 220;
  for (let i = 0; i <= n; i++) {
    const x = lerp(x0, x1, i / n), ph = (i / n * 6) % 1;
    let v = 0;
    if (ph > 0.42 && ph < 0.46) v = -0.25; else if (ph >= 0.46 && ph < 0.5) v = 1.0; else if (ph >= 0.5 && ph < 0.54) v = -0.45; else if (ph > 0.66 && ph < 0.76) v = 0.18 * Math.sin((ph - 0.66) / 0.1 * Math.PI);
    pts.push([x, y + v * amp, 0]);
  }
  return pts;
}
const scanRing = (pb, color, r_ = 330) => { ringPoints(pb, { r: r_, w: 10, count: 9000, color }); ringPoints(pb, { r: r_ * 1.25, w: 3, count: 2500, color: C.champ }); };
const settingIntro = (S, n, en) => {
  S.mono(`SETTING 0${n} / 04 · ${en}`, { at: 0, d: 0.3, x: 960, y: 395, size: 17, style: { letterSpacing: '.45em' }, out: 1 });
  S.mono('DECODING ▍', { at: 0, d: 0.6, x: 960, y: 690, size: 15, out: 1 });
};
export const SCENES = {};

// ============================================================ 冷开场
SCENES.cold = S => {
  S.form(mk(1, pb => grassBlades(pb)), { at: 2, d: -0.4, dur: 2.6, scatter: 260 });
  S.obj(polyline(ecg(-820, 820, 140, 120), { color: C.teal, opacity: 0.85 }), { at: 3, draw: true, drawDur: 4.5, out: 5 });
  S.form(mk(2, pb => { grassBlades(pb, { n: 420 }); brainPoints(pb, { y: 160, s: 170, count: 11000 }); dim(pb, 0.8); }), { at: 4, dur: 2.0 });
  S.form(mk(3, pb => { grassBlades(pb, { n: 320 }); dim(pb, 0.6); txt(pb, '?', 0, 120, 520, { w: 100, count: 20000 }); }), { at: 5, dur: 1.8, scatter: 300 });
};

// ============================================================ 悖论
SCENES.paradox = S => {
  cap(S, 'A PARADOX', '一个悖论');
  const carBlock = pb => { ic(pb, I.car, -470, 300, 150, { color: C.white }); dotBlock(pb, 1190, 35, -810, 210, 19.5, C.white); };
  S.form(mk(10, carBlock), { at: 0, dur: 2.0, radial: 400 });
  S.num('1,190,000', { at: 0, f: 0.3, world: R(-150, 300), size: 64, al: 'l', out: 2 });
  S.mono('ROAD DEATHS / YEAR · 每个光点 ≈ 1,000 人', { at: 0, f: 0.5, world: R(-148, 245), size: 14, al: 'l', out: 2 });
  S.form(mk(11, pb => { carBlock(pb); ic(pb, I.snake, 470, 300, 150, { color: C.orange }); dotBlock(pb, 110, 11, 370, 210, 19.5, C.orange); }), { at: 1, dur: 1.6 });
  S.num('~100,000', { at: 1, f: 0.3, world: R(660, 180), size: 48, al: 'l', style: { color: '#ffb070' }, out: 2 });
  S.mono('SNAKEBITE DEATHS / YEAR', { at: 1, f: 0.4, world: R(662, 135), size: 14, al: 'l', out: 2 });
  S.form(mk(12, pb => { ic(pb, I.snake, -330, 60, 420, { color: C.orange, keep: 0.15 }); ic(pb, I.car, 380, 20, 200, { color: C.white, bright: 0.45 }); }), { at: 2, dur: 1.8 });
  S.mono('FEAR ████████', { at: 2, f: 0.4, world: R(-330, -200), size: 16 , out: 3 });
  S.mono('FEAR ▏', { at: 2, f: 0.5, world: R(380, -120), size: 16, out: 3 });
  S.form(mk(13, pb => { ic(pb, I.spider, -330, 60, 380, { color: C.warm }); ic(pb, I.plug, 380, 20, 200, { color: C.white, bright: 0.45 }); }), { at: 3, dur: 1.4 });
  S.form(mk(14, pb => ic(pb, I.tea, 0, 60, 400, { color: C.champ, keep: 0.3 })), { at: 4, dur: 1.4 });
  S.form(mk(15, pb => { ic(pb, I.phone, -260, 50, 360, { color: C.white }); }), { at: 5, dur: 1.4 });
  S.box({ at: 5, f: 0.15, title: 'GROUP CHAT', html: '周末有空一起吃饭吗？', typing: 1.0, world: R(250, 120), w: 460, h: 120, fs: 28, out: 6 });
  S.mono('已读 · 无人回复', { at: 5, f: 0.6, world: R(400, 30), size: 16, out: 6 });
  S.form(mk(16, pb => spherePoints(pb, { r: 640, count: 30000, color: C.champ, shell: 0.2 })), { at: 6, dur: 1.6, scatter: 500, swirl: 2.5 });
  S.form(mk(17, pb => spherePoints(pb, { r: 60, count: 26000, color: C.white, shell: 0.1 })), { at: 7, dur: 2.0, swirl: 3 });
};

// ============================================================ 片名
SCENES.title = S => {
  S.flash({ at: 0, amt: 0.035 });
  S.warp({ at: 0, d: -0.3, dur: 2.2 });
  S.form(mk(20, pb => txt(pb, '出厂设置', 0, 30, 300, { w: 600, f: 'SHSerif', count: 40000, ps: 2.0 })), { at: 0, dur: 1.6, scatter: 200, radial: 900, stagger: 0.25 });
  S.mono('FACTORY  SETTINGS', { at: 1, d: 0.2, x: 960, y: 720, size: 22, style: { letterSpacing: '.8em' } });
  S.el('进化心理学 · 一份写给普通人的大脑说明书', { cls: 't-label', size: 30, at: 1, d: 0.8, x: 960, y: 790, anim: 'blur', style: { letterSpacing: '.3em' } });
};

// ============================================================ 出厂于 30 万年前
SCENES.origin = S => {
  cap(S, 'ORIGIN', '出厂');
  S.form(mk(30, pb => brainPoints(pb, { y: 60, s: 300, count: 26000 })), { at: 0, dur: 2.4, spin: 0.15, center: [0, 60, 0], radial: 600 });
  S.mono('MANUFACTURED · ~300,000 YEARS AGO', { at: 0, f: 0.5, x: 960, y: 150, size: 16, out: 2 });
  const tags = [['草原', -600, 240], ['部落', 600, 240], ['饥荒', -600, -120], ['猛兽', 600, -120]];
  tags.forEach(([s, x, y], i) => S.box({ at: 1, f: 0.1 + i * 0.12, html: s, world: R(x, y), w: 150, h: 64, fs: 26, kind: 'w', style: { textAlign: 'center' }, out: 2 }));
  S.obj(lines(tags.map(([, x, y]) => [x * 0.86, y * 0.86 + 20, 0, x * 0.42, y * 0.3 + 60, 0]), { color: C.champ, opacity: 0.35 }), { at: 1, f: 0.3, out: 2 });
  S.form(mk(31, pb => { brainPoints(pb, { x: -430, y: 60, s: 220, count: 17000 }); ic(pb, I.city, 430, 60, 380, { color: C.white, keep: 0.15, count: 15000 }); }), { at: 2, dur: 2.0 });
  [['城市', 250, 300], ['手机', 610, 300], ['外卖', 250, -180], ['社交网络', 610, -180]].forEach(([s, x, y], i) => S.box({ at: 3, f: 0.1 + i * 0.12, html: s, world: R(x, y), w: s.length > 2 ? 190 : 140, h: 60, fs: 24, kind: 't', style: { textAlign: 'center' }, out: 4 }));
  S.mono('RUNTIME · 2026', { at: 3, f: 0.2, world: R(430, -260), size: 15, out: 4 });
  S.form(mk(32, pb => txt(pb, '进化心理学', 0, 60, 220, { w: 500, f: 'SHSerif', count: 36000, ps: 2.0 })), { at: 5, d: -0.2, dur: 1.6, scatter: 400, radial: 500 });
  S.mono('EVOLUTIONARY  PSYCHOLOGY', { at: 5, f: 0.4, x: 960, y: 690, size: 20, style: { letterSpacing: '.6em' } });
};

// ============================================================ 达尔文
SCENES.darwin = S => {
  cap(S, '1859 · CHARLES DARWIN', '自然选择');
  S.form(mk(40, pb => txt(pb, '1859', 0, 70, 340, { w: 200, count: 26000 })), { at: 0, dur: 2.0, scatter: 500 });
  S.mono('ON THE ORIGIN OF SPECIES', { at: 0, f: 0.4, x: 960, y: 700, size: 18, style: { letterSpacing: '.5em' }, out: 1 });
  S.form(mk(41, pb => treeOfLife(pb, { y: -300, len: 160, depth: 8 })), { at: 1, dur: 2.6, scatter: 300 });
  S.mono('VARIATION  →  SELECTION  →  INHERITANCE', { at: 1, f: 0.4, x: 960, y: 150, size: 17, style: { letterSpacing: '.3em' }, out: 3 });
  S.form(mk(42, pb => ic(pb, I.book, 0, 60, 400, { color: C.champ, keep: 0.15, count: 17000 })), { at: 3, dur: 1.8 });
  S.form(mk(43, pb => { ringPoints(pb, { r: 480, w: 26, count: 11000, color: C.champ, tilt: 1.22 }); ringPoints(pb, { r: 560, w: 6, count: 3000, color: C.warm, tilt: 1.22 }); }), { at: 4, dur: 2.0, spin: 0.2 });
  S.mono('— CHARLES DARWIN, 1859', { at: 4, f: 0.5, x: 1260, y: 640, size: 16 });
};

// ============================================================ 器官
SCENES.organ = S => {
  cap(S, 'CORE IDEA', '核心观点');
  S.form(mk(50, pb => ic(pb, I.heart, -520, 80, 300, { color: C.red })), { at: 0, dur: 1.4, radial: 400 });
  S.mono('HEART → PUMP', { at: 0, f: 0.3, world: R(-520, -110), size: 15 });
  S.form(mk(51, pb => { ic(pb, I.heart, -520, 80, 300, { color: C.red }); ic(pb, I.eye, 0, 80, 300, { color: C.white }); }), { at: 1, dur: 1.4 });
  S.mono('EYE → SEE', { at: 1, f: 0.3, world: R(0, -110), size: 15 });
  S.form(mk(52, pb => { ic(pb, I.heart, -520, 80, 300, { color: C.red, bright: 0.6 }); ic(pb, I.eye, 0, 80, 300, { color: C.white, bright: 0.6 }); brainPoints(pb, { x: 520, y: 90, s: 170, count: 14000 }); }), { at: 2, dur: 1.6 });
  S.mono('BRAIN → ?', { at: 2, f: 0.2, world: R(520, -110), size: 15, out: 4 });
  ['恐惧', '食欲', '嫉妒', '爱'].forEach((s, i) => S.box({ at: 2, f: 0.35 + i * 0.12, html: s, world: R(340 + i * 122, -190), w: 112, h: 56, fs: 22, kind: 't', style: { textAlign: 'center' }, out: 4 }));
  S.form(mk(53, pb => helixPoints(pb, { y: -260, len: 1600, r: 90, turns: 6, count: 20000 })), { at: 4, dur: 1.6, radial: 300 });
};

// ============================================================ 30 万年压缩成一天
SCENES.clock = S => {
  cap(S, 'TIME MISMATCH', '时间错配');
  const L = -820, Rr = 820, xOf = h => L + (Rr - L) * h / 24;
  S.obj(grid({ y: -160, size: 4000, step: 120, opacity: 0.12 }), { at: 0, out: 5 });
  S.form(mk(60, pb => linePoints(pb, [[L, 0], [Rr, 0]], { count: 14000, color: C.teal, ps: 1.9, w: 10 })), { at: 0, dur: 2.0, radial: 300 });
  [0, 6, 12, 18, 24].forEach(h => S.mono(`${h}:00`, { at: 0, f: 0.5, world: [xOf(h), -40, 0], size: 15, out: 5 }));
  const clock = S.el('00:00', { cls: 't-num', size: 96, at: 1, x: 960, y: 190, anim: 'fade', out: 5 });
  S.update(lt => {
    const segs = [[S.T(1), S.T(1, 0.95), 0, 23 * 60 + 12], [S.T(2, 0.9), S.T(3, 0.6), 23 * 60 + 12, 23 * 60 + 58.72], [S.T(3, 0.9), S.T(4, 0.7), 23 * 60 + 58.72, 23 * 60 + 59.92]];
    let m = 0; for (const [a, b, x0, x1] of segs) if (lt >= a) m = lerp(x0, x1, EZ.inOut(clamp((lt - a) / (b - a))));
    const hh = Math.floor(m / 60), mm = Math.floor(m % 60), ss = Math.floor((m * 60) % 60);
    clock.e.textContent = lt >= S.T(3, 0.9) ? `${hh}:${String(mm).padStart(2, '0')}:${String(ss).padStart(2, '0')}` : `${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}`;
  });
  S.form(mk(61, pb => { linePoints(pb, [[L, 0], [xOf(23.2), 0]], { count: 13000, color: C.teal, ps: 1.9, w: 10 }); linePoints(pb, [[xOf(23.2), 0], [Rr, 0]], { count: 2200, color: C.orange, ps: 2.4, w: 14 }); }), { at: 1, dur: 3.0, stagger: 0.8, scatter: 30, swirl: 0 });
  S.label('狩猎 · 采集', { at: 1, f: 0.5, world: [xOf(11.5), 60, 0], size: 30, out: 5 });
  const mark = (h, color) => glowSprites([{ x: xOf(h), y: 0, size: 60, color }]);
  S.obj(mark(23.2, C.orange), { at: 2, out: 5 });
  S.label('农业 <span class="hl">23:12</span>', { at: 2, f: 0.2, world: [xOf(23.2), 90, 0], size: 24, out: 5 });
  S.obj(mark(23.979, C.orange), { at: 3, f: 0.5, out: 5 });
  S.label('工业革命 <span class="hl">23:58:43</span>', { at: 3, f: 0.5, world: [xOf(23.979), 150, 0], size: 20, out: 5 });
  S.obj(mark(23.9986, C.red), { at: 4, f: 0.4, out: 5 });
  S.label('智能手机 <span class="hl">23:59:55</span>', { at: 4, f: 0.4, world: [xOf(23.9986), -70, 0], size: 20, out: 5 });
  S.form(mk(62, pb => { brainPoints(pb, { x: -480, y: 60, s: 230, count: 17000 }); ic(pb, I.city, 480, 60, 380, { color: C.white, keep: 0.15, count: 14000 }); }), { at: 5, dur: 2.0, radial: 300 });
  S.hero('<span class="hl">≠</span>', { at: 5, f: 0.4, world: R(0, 60), size: 140, anim: 'zoom' });
  S.mono('STONE AGE BRAIN', { at: 5, f: 0.6, world: R(-480, -150), size: 15 });
  S.mono('MODERN WORLD', { at: 5, f: 0.7, world: R(480, -150), size: 15 });
  const z = 1.0 * D;
  S.cam({ keys: [{ t: 0, pos: [0, 120, z * 1.04] }, { t: S.T(3), pos: [0, 120, z * 1.04] }, { t: S.T(4, 0.6), pos: [690, 60, z * 0.39], tgt: [780, 0, 0] }, { t: S.T(5), pos: [690, 60, z * 0.39], tgt: [780, 0, 0] }, { t: S.T(5, 0.5), pos: [0, 0, z] }] });
};

// ============================================================ 设置 01：宁可多虑
SCENES.set1 = S => {
  S.warp({ at: 0, d: -0.3, dur: 2.0 });
  settingIntro(S, 1, 'SMOKE DETECTOR');
  S.form(mk(70, pb => scanRing(pb, C.teal)), { at: 0, dur: 1.4, spinZ: 0.6, radial: 800 });
  S.form(mk(71, pb => grassBlades(pb, { y0: -230, n: 560, h: 320 })), { at: 1, dur: 2.0 });
  S.form(mk(72, pb => { grassBlades(pb, { y0: -230, n: 420, h: 280 }); ic(pb, I.lion, -460, -40, 280, { color: C.orange, keep: 0.2 }); }), { at: 2, f: 0.2, dur: 1.6 });
  S.box({ at: 2, f: 0.3, title: 'ERROR A · 漏报', html: '以为是风 → 其实是<span class="hl">狮子</span>', world: R(-460, 280), w: 560, h: 110, fs: 28, out: 4 });
  S.box({ at: 3, f: 0.2, title: 'ERROR B · 误报', html: '以为是狮子 → 其实是<span class="hl2">风</span>', world: R(460, 280), w: 560, h: 110, fs: 28, kind: 't', out: 4 });
  S.form(mk(73, pb => { grassBlades(pb, { y0: -230, n: 320, h: 260 }); ic(pb, I.lion, -460, -40, 280, { color: C.orange, keep: 0.2 }); ic(pb, I.wind, 460, -20, 240, { color: C.white, keep: 0.1 }); }), { at: 3, f: 0.3, dur: 1.4 });
  S.obj(grid({ y: -300, size: 3000, step: 100, opacity: 0.13 }), { at: 4, out: 5 });
  S.form(mk(74, pb => { boxPoints(pb, { x: -240, y: -300, w: 150, h: 560, d: 150, count: 10000, color: C.orange }); boxPoints(pb, { x: 240, y: -300, w: 150, h: 26, d: 150, count: 1300, color: C.teal }); }), { at: 4, dur: 1.6 });
  S.label('漏报的代价 · <span class="hl">出局</span>', { at: 4, f: 0.3, world: [-240, 300, 0], size: 24, out: 5 });
  S.label('误报的代价 · <span class="hl2">白跑</span>', { at: 4, f: 0.4, world: [240, -240, 0], size: 24, out: 5 });
  S.form(mk(75, pb => { ringPoints(pb, { y: 40, r: 250, w: 14, count: 11000, color: C.teal }); ic(pb, I.alarm, 0, 40, 240, { color: C.white, count: 5000 }); }), { at: 5, dur: 1.6, spinZ: 0.4, center: [0, 40, 0] });
  S.counter({ at: 5, f: 0.3, to: 10, cdur: 2.4, pre: '误报 × ', world: R(-560, 40), size: 56 });
  S.text('漏报 × <span class="hl">0</span>', { at: 5, f: 0.5, world: R(560, 40), size: 56, cls: 't-num' });
  S.cam({ keys: [{ t: 0, pos: [0, 0, D] }, { t: S.T(4), pos: [0, 0, D] }, { t: S.T(5), pos: [-160, 200, D * 0.94], tgt: [0, -40, 0] }, { t: S.T(5, 0.3), pos: [0, 0, D] }] });
};

// ============================================================ 怕蛇
SCENES.snake = S => {
  cap(S, 'LOBUE & DELOACHE 2008 · COOK & MINEKA 1989', '实验');
  S.form(mk(80, pb => iconGrid(pb, (i, j) => (i === 2 && j === 1) ? I.snake : I.flower, 3, 3, 0, 60, 190, 140, { color: C.champ, keep: 0.35, count: 2000 })), { at: 0, dur: 1.8 });
  S.box({ at: 1, html: '', world: R(190, 60), w: 175, h: 175, anim: 'box', out: 2 });
  S.num('更快', { at: 1, f: 0.2, world: R(500, 60), size: 64, cls: 't-hero', style: { color: '#ffad5c' }, out: 2 });
  const mon = (pb, x, sub, col) => { ic(pb, I.film, x - 80, 240, 120, { color: C.white, count: 1800 }); ic(pb, sub, x + 80, 240, 130, { color: col, keep: 0.3, count: 2200 }); ic(pb, I.monkey, x, -30, 280, { color: col, keep: 0.2, count: 9000 }); };
  S.form(mk(81, pb => mon(pb, -420, I.snake, C.orange)), { at: 2, dur: 1.8 });
  S.label('学会怕蛇 <span class="hl">✓</span>', { at: 2, f: 0.5, world: R(-420, -210), size: 26, out: 4 });
  S.form(mk(82, pb => { mon(pb, -420, I.snake, C.orange); mon(pb, 420, I.flower, C.champ); }), { at: 3, dur: 1.6 });
  S.label('学不会怕花 <span class="hl2">✗</span>', { at: 3, f: 0.4, world: R(420, -210), size: 26, out: 4 });
  S.form(mk(83, pb => ic(pb, I.snake, 0, 60, 500, { color: C.orange, keep: 0.15, count: 20000 })), { at: 4, dur: 1.6, radial: 300 });
  S.mono('PREPARED LEARNING · 有准备的学习', { at: 4, f: 0.4, x: 960, y: 150, size: 16, out: 5 });
  S.form(mk(84, pb => { ic(pb, I.snake, -380, 60, 380, { color: C.orange, keep: 0.15, count: 13000 }); ic(pb, I.car, 300, 40, 170, { color: C.white, bright: 0.45 }); ic(pb, I.plug, 520, 40, 170, { color: C.white, bright: 0.45 }); }), { at: 5, dur: 1.4 });
  S.mono('300,000 YRS', { at: 5, f: 0.3, world: R(-380, -150), size: 15, out: 6 });
  S.mono('< 150 YRS', { at: 5, f: 0.4, world: R(410, -110), size: 15, out: 6 });
  S.form(mk(85, pb => { ic(pb, I.lion, -300, 60, 300, { color: C.orange, keep: 0.2 }); ic(pb, I.wind, 300, 60, 280, { color: C.white, keep: 0.1 }); }), { at: 6, dur: 1.6 });
  S.hero('?', { at: 6, f: 0.3, world: R(0, 60), size: 90, anim: 'zoom' });
};

// ============================================================ 设置 02：囤积热量
SCENES.set2 = S => {
  settingIntro(S, 2, 'CALORIE HOARDING');
  S.form(mk(90, pb => scanRing(pb, C.warm)), { at: 0, dur: 1.4, spinZ: 0.6, radial: 800 });
  S.form(mk(91, pb => ic(pb, I.apple, 0, 60, 330, { color: C.red, keep: 0.4, count: 11000 })), { at: 1, dur: 1.8 });
  S.mono('ANCESTRAL · CALORIES SCARCE', { at: 1, f: 0.4, x: 960, y: 150, size: 16, out: 3 });
  S.num('SURVIVAL <span class="hl2">✓</span>', { at: 2, f: 0.2, world: R(0, -170), size: 40, cls: 't-mono', out: 3 });
  S.form(mk(92, pb => iconGrid(pb, (i, j) => [I.donut, I.tea, I.fries][(i + j) % 3], 7, 3, 0, 80, 200, 135, { color: C.warm, keep: 0.3, count: 2400 })), { at: 3, dur: 1.8, radial: 400 });
  S.mono('TODAY · CALORIES EVERYWHERE', { at: 3, f: 0.2, x: 960, y: 150, size: 16, out: 4 });
  S.form(mk(93, pb => iconGrid(pb, (i, j) => [I.donut, I.tea, I.fries][(i + j) % 3], 7, 3, 0, 80, 200, 135, { color: C.red, keep: 0.15, count: 2400 })), { at: 4, dur: 1.0, scatter: 40, swirl: 0 });
  S.mono('OBESITY · DIABETES', { at: 4, f: 0.3, x: 960, y: 150, size: 16, out: 5, style: { color: 'rgba(255,120,100,.8)' } });
  S.form(mk(94, pb => ic(pb, I.house, 0, 60, 380, { color: C.champ, keep: 0.2, count: 13000 })), { at: 5, dur: 1.6 });
};

// ============================================================ 设置 03：社交雷达
SCENES.set3 = S => {
  S.warp({ at: 0, d: -0.3, dur: 2.0 });
  settingIntro(S, 3, 'SOCIAL RADAR');
  S.form(mk(100, pb => scanRing(pb, C.teal)), { at: 0, dur: 1.4, spinZ: 0.6, radial: 800 });
  S.form(mk(101, pb => { const r = pb.r; for (let i = 0; i < 16000; i++) { const a = r() * Math.PI * 2, rr = 260 + (r() - .5) * 40; const on = ((Math.PI / 2 - a) % (Math.PI * 2) + Math.PI * 2) % (Math.PI * 2) < Math.PI * 2 * 0.667; pb.add(rr * Math.cos(a), 60 + rr * Math.sin(a), (r() - .5) * 20, on ? C.orange : C.white, on ? 2.3 : 1.6, on ? 1 : 0.3); } }), { at: 1, dur: 1.8 });
  S.num('2/3', { at: 1, f: 0.3, world: R(0, 60), size: 110, out: 2 });
  const ppl = people(24, 11, 330, 0, 60);
  S.form(mk(102, pb => ppl.forEach(p => spherePoints(pb, { x: p.x, y: p.y, z: p.z, r: 15, count: 300, color: C.champ, shell: 0.5 }))), { at: 2, dur: 1.8 });
  const segs = knn(ppl, 3);
  S.obj(lines(segs.filter((_, i) => i % 4), { color: C.teal, opacity: 0.45 }), { at: 2, f: 0.3, out: 4 });
  S.obj(lines(segs.filter((_, i) => !(i % 4)), { color: C.red, opacity: 0.6 }), { at: 2, f: 0.5, out: 4 });
  S.mono('TRUST · BETRAYAL · ALLIANCE', { at: 3, x: 960, y: 150, size: 16, out: 4 });
  S.form(mk(103, pb => circlePts(150, 300, 0, 60).forEach(([x, y]) => spherePoints(pb, { x, y, r: 9, count: 100, color: C.champ, shell: 0.4 }))), { at: 4, dur: 1.8 });
  S.num('150', { at: 4, f: 0.3, world: R(0, 60), size: 130, out: 5 });
  S.mono("DUNBAR'S NUMBER · 约数，仍有争议", { at: 4, f: 0.5, x: 960, y: 115, size: 15, out: 5 });
  const grp = people(46, 3, 170, -280, 60);
  S.form(mk(104, pb => { grp.forEach(p => spherePoints(pb, { x: p.x, y: p.y, z: p.z, r: 10, count: 200, color: C.champ, shell: 0.5 })); spherePoints(pb, { x: 560, y: 60, r: 12, count: 700, color: C.white, shell: 0.4 }); }), { at: 5, dur: 1.8 });
  S.form(mk(105, pb => ic(pb, I.phone, -300, 50, 340, { color: C.white })), { at: 6, dur: 1.4 });
  S.box({ at: 6, f: 0.1, title: 'GROUP CHAT', html: '在吗？', typing: 0.6, world: R(240, 130), w: 420, h: 110, fs: 30, out: 7 });
  S.mono('已读 · 2 小时前', { at: 6, f: 0.5, world: R(360, 40), size: 16, out: 7 });
  S.form(mk(106, pb => { brainPoints(pb, { y: 60, s: 290, count: 18000, color: [0.5, 0.45, 0.4] }); spherePoints(pb, { x: -60, y: 120, r: 95, count: 4500, color: C.red, shell: 0.3 }); spherePoints(pb, { x: 50, y: 120, r: 95, count: 4500, color: C.teal, shell: 0.3 }); }), { at: 7, dur: 1.8, spin: 0.12, center: [0, 60, 0] });
  S.label('被冷落', { at: 7, f: 0.4, world: R(-330, 180), size: 26, cls: 't-label hl', out: 8 });
  S.label('身体疼痛', { at: 7, f: 0.5, world: R(330, 180), size: 26, cls: 't-label hl2', out: 8 });
  S.form(mk(107, pb => ic(pb, I.broken, 0, 60, 400, { color: C.red, keep: 0.3, count: 14000 })), { at: 8, dur: 1.4 });
  S.form(mk(108, pb => galaxyPoints(pb, { y: 60, r: 560, count: 34000, arms: 4, tilt: 1.2 })), { at: 9, dur: 2.0, spin: 0.04, center: [0, 60, 0], radial: 300 });
  S.counter({ at: 9, f: 0.2, from: 150, to: 8200000000, cdur: 2.6, world: R(0, 60), size: 64 });
  S.mono('YOUR TRIBE: 150 → 8,200,000,000', { at: 9, f: 0.5, x: 960, y: 150, size: 16 });
};

// ============================================================ 设置 04：骗子侦测器
SCENES.set4 = S => {
  S.warp({ at: 0, d: -0.3, dur: 2.0 });
  settingIntro(S, 4, 'CHEATER DETECTOR');
  S.form(mk(120, pb => scanRing(pb, C.orange)), { at: 0, dur: 1.4, spinZ: 0.6, radial: 800 });
  const ppl = people(26, 7, 300, 0, 60);
  const bad = ppl[5];
  S.form(mk(121, pb => { ppl.forEach((p, i) => spherePoints(pb, { x: p.x, y: p.y, z: p.z, r: 16, count: 280, color: C.champ, shell: 0.6 })); }), { at: 1, dur: 1.6, radial: 300 });
  S.obj(lines(knn(ppl, 3), { color: C.champ, opacity: 0.32 }), { at: 1, f: 0.3, out: 3 });
  S.form(mk(122, pb => { ppl.forEach((p, i) => spherePoints(pb, { x: p.x, y: p.y, z: p.z, r: 16, count: 280, color: i === 5 ? C.red : C.champ, shell: 0.6 })); ringPoints(pb, { x: bad.x, y: bad.y, z: bad.z, r: 80, w: 5, count: 3500, color: C.teal }); }), { at: 2, dur: 1.2, scatter: 30 });
  S.label('只拿不给的人', { at: 2, f: 0.4, world: [bad.x, bad.y + 100, bad.z], size: 22, cls: 't-label hl', out: 3 });
  const nodes = [{ x: 0, y: 60, size: 90, color: C.white }, { x: -420, y: 60, size: 70, color: C.teal }, { x: 420, y: 60, size: 60, color: C.warm }];
  S.form(mk(124, pb => { linePoints(pb, [[-420, 60], [0, 60]], { count: 4500, color: C.teal, w: 6 }); linePoints(pb, [[0, 60], [420, 60]], { count: 1100, color: C.warm, w: 6 }); }), { at: 3, dur: 1.6 });
  S.obj(glowSprites(nodes), { at: 3, out: 5 });
  S.label('你', { at: 3, world: [0, -30, 0], size: 28, out: 5 });
  S.label('兄弟姐妹', { at: 3, f: 0.2, world: [-420, -30, 0], size: 26, out: 5 });
  S.label('堂表亲', { at: 3, f: 0.4, world: [420, -30, 0], size: 26, out: 5 });
  S.num('1/2', { at: 4, f: 0.15, world: [-420, 180, 0], size: 72, out: 5 });
  S.num('1/8', { at: 4, f: 0.45, world: [420, 180, 0], size: 72, out: 5 });
  S.form(mk(125, pb => helixPoints(pb, { y: -250, len: 1600, r: 80, turns: 6, count: 16000 })), { at: 5, dur: 1.6 });
  S.mono('— J. B. S. HALDANE', { at: 5, f: 0.4, x: 1320, y: 650, size: 15 });
  S.mono('2 × 1/2 = 1     8 × 1/8 = 1', { at: 5, f: 0.7, x: 960, y: 170, size: 22, style: { color: 'rgba(255,170,100,.9)' } });
  S.form(mk(126, pb => ic(pb, I.shake, 0, 60, 420, { color: C.champ, keep: 0.2, count: 15000 })), { at: 6, dur: 1.6 });
};

// ============================================================ 三个提醒
SCENES.warning = S => {
  cap(S, 'THREE WARNINGS', '三个提醒');
  S.form(mk(130, pb => [C.orange, C.warm, C.teal, C.champ].forEach((c, i) => ringPoints(pb, { x: -390 + i * 260, y: -250, r: 70, w: 6, count: 3500, color: c }))), { at: 0, dur: 1.8, radial: 400 });
  S.form(mk(131, pb => txt(pb, '≠', 0, 270, 300, { w: 100, count: 9000, color: C.orange })), { at: 2, dur: 1.4, scatter: 300 });
  S.form(mk(132, pb => { txt(pb, '≠', 0, 270, 300, { w: 100, count: 6000, color: C.orange, bright: 0.6 }); ic(pb, I.sprout, 0, -230, 230, { color: C.green, keep: 0.3, count: 6000 }); }), { at: 4, dur: 1.4 });
  S.form(mk(133, pb => { txt(pb, '≠', 0, 270, 300, { w: 100, count: 6000, color: C.teal, bright: 0.6 }); ic(pb, I.scroll, 0, -230, 230, { color: C.champ, keep: 0.2, count: 6000 }); }), { at: 6, dur: 1.4 });
  S.mono('REPLICATION · 可重复性', { at: 7, f: 0.3, x: 960, y: 150, size: 16 });
};

// ============================================================ 回到草丛
SCENES.return = S => {
  cap(S, 'BACK TO THE GRASS', '回到草丛');
  S.form(mk(140, pb => grassBlades(pb)), { at: 0, dur: 2.2, radial: 300 });
  S.obj(polyline(ecg(-820, 820, 160, 120), { color: C.teal, opacity: 0.85 }), { at: 1, draw: true, drawDur: 3.5, out: 3 });
  S.form(mk(141, pb => { grassBlades(pb, { n: 300 }); dim(pb, 0.5); brainPoints(pb, { y: 90, s: 230, count: 18000 }); dim(pb, 0.75); }), { at: 2, dur: 1.8 });
  S.form(mk(142, pb => brainPoints(pb, { y: 60, s: 330, count: 26000, color: C.champ })), { at: 4, dur: 1.6, spin: 0.15, center: [0, 60, 0] });
  S.form(mk(143, pb => ic(pb, I.eye, 0, 210, 400, { color: C.champ, count: 18000 })), { at: 5, dur: 1.8, scatter: 300 });
};

// ============================================================ 终章
SCENES.finale = S => {
  S.warp({ at: 0, d: -0.3, dur: 2.2 });
  S.form(mk(150, pb => galaxyPoints(pb, { y: -40, r: 720, count: 42000, arms: 4, tilt: 1.2 })), { at: 0, dur: 2.4, spin: 0.08, center: [0, -40, 0], radial: 700 });
  S.flash({ at: 2, amt: 0.02 });
  S.form(mk(150, pb => { galaxyPoints(pb, { y: -40, r: 720, count: 42000, arms: 4, tilt: 1.2 }); dim(pb, 0.5); }), { at: 2, dur: 1.2, spin: 0.08, center: [0, -40, 0] });
  S.form(mk(151, pb => spherePoints(pb, { r: 6, count: 3000, color: C.white, shell: 0.2 })), { at: 3, dur: 2.4, scatter: 200, swirl: 3 });
  S.el('出厂设置', { cls: 't-hero', size: 110, at: 3, d: 0.8, x: 960, y: 470, anim: 'blur', style: { fontFamily: 'SHSerif', fontWeight: 600, letterSpacing: '.3em' } });
  S.mono('FACTORY SETTINGS · EVOLUTIONARY PSYCHOLOGY', { at: 3, d: 1.4, x: 960, y: 600, size: 18, style: { letterSpacing: '.4em' } });
  S.cam({ keys: [{ t: 0, pos: [0, 320, D * 1.06], tgt: [0, -40, 0] }, { t: S.T(3), pos: [0, 120, D * 0.92], tgt: [0, 0, 0] }, { t: S.dur, pos: [0, 0, D] }] });
};

// ============================================================ 参考资料
SCENES.refs = S => {
  S.form(mk(160, pb => spherePoints(pb, { r: 4, count: 600, color: C.white, shell: 0.2 })), { at: 0, d: -0.3, dur: 0.6 });
  S.cap('REFERENCES · <b>参考资料</b>', { y: 120 });
  S.el([
    'Darwin, C. (1859). On the Origin of Species.',
    'Barkow, Cosmides & Tooby (Eds.) (1992). The Adapted Mind.',
    'Nesse, R. M. (2005). The smoke detector principle.',
    'LoBue & DeLoache (2008). Detecting the snake in the grass.',
    'Cook & Mineka (1989). Observational conditioning of fear in rhesus monkeys.',
    'Cosmides, L. (1989). The logic of social exchange. Cognition.',
    'Dunbar, R. (1997). Grooming, Gossip, and the Evolution of Language.',
    'Eisenberger, Lieberman & Williams (2003). Does rejection hurt?',
    'Hamilton, W. D. (1964). The genetical evolution of social behaviour.',
    'Gould & Lewontin (1979). The spandrels of San Marco.',
    'World Health Organization (2023). Road safety report; snakebite envenoming fact sheet.',
  ].join('<br>'), { cls: 't-mono', size: 19, at: 0, d: 0.3, x: 960, y: 520, align: 'left', anim: 'fade', style: { lineHeight: '1.9', letterSpacing: '.04em' } });
  S.mono('音乐与画面均由代码生成 · 图标：Twemoji CC-BY 4.0 / Tabler MIT · 字体：思源宋体 / 思源黑体 OFL', { at: 0, d: 0.6, x: 960, y: 930, size: 15, style: { letterSpacing: '.1em' } });
};
