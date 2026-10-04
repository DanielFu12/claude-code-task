// 进化心理学 v2：逐场景画面编排（与 build/timeline.json 的 38 个场景一一对应）
// 坐标：粒子/3D 用世界坐标（原点在画面中心，y 向上，z=0 平面 1 单位 = 1 像素）；DOM 用屏幕坐标（左上角为原点）。
import { PB, C, textPoints, imagePoints, spherePoints, ringPoints, galaxyPoints, brainPoints, helixPoints, linePoints, boxPoints,
  glowSprites, lines, polyline, grid, dust, rng, E as EZ, clamp, lerp, DIST as D } from './engine.js';

const emName = ch => { const cps = [...ch].map(c => c.codePointAt(0).toString(16)); return cps.includes('200d') ? cps.join('-') : cps.filter(c => c !== 'fe0f').join('-'); };
const em = ch => `/assets/emoji/${emName(ch)}.svg`;
const tb = n => `/video2/node_modules/@tabler/icons/icons/outline/${n}.svg`;
const I = {
  snake: em('🐍'), spider: tb('spider'), rope: em('🪢'), car: tb('car'), plug: tb('plug'), burger: tb('burger'), tea: em('🧋'),
  chicken: em('🍗'), msgs: tb('messages'), phone: tb('device-mobile'), eagle: em('🦅'), bear: em('🐻‍❄️'), book: em('📖'),
  heart: tb('heart'), eye: tb('eye'), brainI: tb('brain'), city: em('🏙️'), apple: em('🍎'), donut: em('🍩'), fries: em('🍟'),
  lion: em('🦁'), fire: em('🔥'), hand: em('✋'), monkey: em('🐒'), flower: em('🌸'), film: em('🎬'), beer: em('🍺'), cola: em('🥤'),
  broken: em('💔'), shake: em('🤝'), globe: em('🌍'), sprout: em('🌱'), scroll: em('📜'), house: em('🏠'), walk: tb('walk'),
  sun: tb('sun'), tree: tb('tree'), moon: tb('moon'), users: tb('users'), alarm: tb('alarm'), key: tb('key'), scale: tb('scale'),
  wind: em('🌬️'), toast: em('🍞'), user: tb('user'), dna: em('🧬'),
};
export const PRELOAD = Object.values(I);

// ---------- 小工具
const mk = (seed, fn) => () => { const pb = new PB(seed); fn(pb); return pb.build(); };
const X = wx => 960 + wx, Y = wy => 540 - wy;      // 世界坐标 → 屏幕坐标
const ic = (pb, src, x, y, size, o = {}) => imagePoints(pb, src, { x, y, size, count: o.count || Math.round(size * size * 0.11), ps: o.ps || 2.2, color: o.color, keep: o.keep, bright: (o.bright ?? 1) * 1.25, depth: o.depth, edges: o.edges });
const txt = (pb, s, x, y, size, o = {}) => textPoints(pb, s, { x, y, size, font: `${o.w || 200} ${size}px ${o.f || 'Inter'}`, count: o.count, color: o.color, ps: o.ps || 2.2, bright: o.bright, depth: o.depth });
const capCN = (en, cn) => `${en} · <b>${cn}</b>`;
function chapter(num, cn, en) {
  return S => {
    S.warp({ at: 0, d: -0.2, dur: 2.0 });
    S.form(mk(500 + +num, pb => txt(pb, num, 0, 70, 360, { w: 100, count: 20000 })), { at: 0, dur: 1.6, scatter: 500, swirl: 2.2 });
    S.cap(`CHAPTER ${num}`, { y: 250 });
    S.hero(cn, { at: 0, d: 0.5, y: 760, size: 72 });
    S.mono(en, { at: 0, d: 0.8, y: 840, size: 18, style: { letterSpacing: '.45em' } });
    S.cam({ from: { pos: [0, 0, 1.261 * D] }, to: { pos: [0, 0, 1.043 * D] } });
  };
}
function grassBlades(pb, o = {}) {
  const r = pb.r, { y0 = -260, w = 1500, n = 420, h = 230, color = C.champ } = o;
  for (let i = 0; i < n; i++) {
    const x0 = (r() - .5) * w, hh = h * (0.4 + r() * 0.8), bend = (r() - .4) * 60, z = (r() - .5) * 300;
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
function circlePts(n, R, cx = 0, cy = 0, a0 = 0) { return Array.from({ length: n }, (_, i) => [cx + R * Math.cos(a0 + i / n * Math.PI * 2), cy + R * Math.sin(a0 + i / n * Math.PI * 2)]); }
function iconGrid(pb, src, cols, rows, cx, cy, step, size, o = {}) {
  for (let j = 0; j < rows; j++) for (let i = 0; i < cols; i++) ic(pb, typeof src === 'function' ? src(i, j) : src, cx + (i - (cols - 1) / 2) * step, cy - (j - (rows - 1) / 2) * step, size, o);
}
function bell(pb, mu, sigma, color, o = {}) {
  const r = pb.r, { w = 1100, h = 300, y0 = -170, count = 7000 } = o;
  for (let i = 0; i < count; i++) {
    const x = (r() - .5) * 2, yv = Math.exp(-((x - mu) ** 2) / (2 * sigma * sigma));
    const fill = r() < 0.35;
    pb.add(x * w / 2, y0 + (fill ? r() * yv : yv) * h + (r() - .5) * 3, (r() - .5) * 20, color, fill ? 1.6 : 2.2, fill ? 0.35 : 1.1);
  }
}
const people = (n, seed, R = 330, cx = 0, cy = 0) => { const r = rng(seed); return Array.from({ length: n }, (_, i) => { const a = r() * Math.PI * 2, d = Math.sqrt(r()) * R; return { x: cx + Math.cos(a) * d * 1.5, y: cy + Math.sin(a) * d * 0.8, z: (r() - .5) * 200, size: 26 + r() * 22, color: C.champ }; }); };
function knn(nodes, k = 2) { const segs = []; nodes.forEach((a, i) => { nodes.map((b, j) => [j, Math.hypot(a.x - b.x, a.y - b.y)]).filter(([j]) => j !== i).sort((p, q) => p[1] - q[1]).slice(0, k).forEach(([j]) => { if (j > i) segs.push([a.x, a.y, a.z || 0, nodes[j].x, nodes[j].y, nodes[j].z || 0]); }); }); return segs; }

// ======================================================================
export const SCENES = [];
const add = fn => SCENES.push(fn);

// 0 开场钩子
add(S => {
  S.cap(capCN('A QUESTION', '先问你一个问题'));
  S.form(mk(1, pb => txt(pb, '?', 0, 30, 640, { w: 100, count: 24000 })), { at: 0, d: -0.3, dur: 2.2, scatter: 600 });
  const left = pb => { ic(pb, I.car, -760, 60, 210, { color: C.white }); ic(pb, I.plug, -520, 60, 210, { color: C.white }); ic(pb, I.burger, -280, 60, 210, { color: C.white }); };
  S.form(mk(2, left), { at: 1, f: 0.55, dur: 2.0 });
  S.label('真正可能伤害你的', { at: 1, f: 0.6, world: [-520, 250, 0], size: 30 });
  S.mono('REAL RISK', { at: 1, f: 0.7, world: [-520, 205, 0], size: 16 });
  [['汽车', -760], ['插座', -520], ['高热量食物', -280]].forEach(([s, x], i) => S.label(s, { at: 2, f: 0.15 + i * 0.25, world: [x, -90, 0], size: 26, cls: 't-label dim' }));
  S.form(mk(3, pb => { left(pb); pb.s = pb.s.map(v => v * 0.8); ic(pb, I.snake, 330, 60, 250, { color: C.orange }); ic(pb, I.spider, 600, 60, 220, { color: C.warm }); }), { at: 3, f: 0.75, dur: 2.0 });
  S.label('让你害怕的', { at: 3, f: 0.5, world: [520, 250, 0], size: 30, cls: 't-label hl' });
  S.mono('FEAR', { at: 3, f: 0.6, world: [520, 205, 0], size: 16 });
  S.form(mk(4, pb => { left(pb); ic(pb, I.snake, 290, 60, 230, { color: C.orange }); ic(pb, I.spider, 530, 60, 200, { color: C.warm }); ic(pb, I.rope, 770, 60, 210, { color: C.champ, keep: 0.2 }); }), { at: 5, f: 0.25, dur: 1.6 });
  [['蛇', 290], ['蜘蛛', 530], ['一根绳子', 770]].forEach(([s, x], i) => S.label(s, { at: i < 2 ? 4 : 5, f: i === 1 ? 0.5 : 0.3, world: [x, -90, 0], size: 26, cls: 't-label dim' }));
});

// 1 交通事故数字
add(S => {
  S.cap(capCN('WHO · GLOBAL ROAD DEATHS PER YEAR', '全球每年道路交通死亡'));
  S.counter({ at: 0, f: 0.2, to: 1190000, cdur: 2.6, x: 960, y: 250, size: 130 });
  S.mono('每个光点 ≈ 1,000 人 · WHO 2023', { at: 0, f: 0.5, x: 960, y: 345, size: 18 });
  S.form(mk(10, pb => { const r = pb.r; for (let i = 0; i < 1190; i++) { const c = i % 70, rr = Math.floor(i / 70); for (let k = 0; k < 6; k++) pb.add(-690 + c * 20 + (r() - .5) * 3, -40 - rr * 20 + (r() - .5) * 3, (r() - .5) * 6, C.champ, 2.2, 1); } }), { at: 0, f: 0.25, dur: 2.4, scatter: 400 });
  S.form(mk(11, pb => { ic(pb, I.car, -300, -120, 260, { color: C.white }); linePoints(pb, [[-60, -120], [700, -120]], { count: 2500, color: C.teal, ps: 1.8, w: 2 }); }), { at: 1, dur: 1.8 });
  S.text('本能的恐惧 <span class="hl2">≈ 0</span>', { at: 1, f: 0.4, world: [320, -40, 0], size: 46 });
  S.mono('INSTINCTIVE FEAR · FLATLINE', { at: 1, f: 0.5, world: [320, -190, 0], size: 16 });
});

// 2 更多奇怪的事
add(S => {
  S.cap(capCN('THREE MORE PUZZLES', '还有更多奇怪的事'));
  S.form(mk(20, pb => { ic(pb, I.tea, -90, 170, 280, { color: C.champ, keep: 0.25 }); ic(pb, I.chicken, 150, 170, 230, { color: C.warm, keep: 0.25 }); }), { at: 1, dur: 1.8 });
  S.form(mk(21, pb => ic(pb, I.msgs, 0, 170, 330, { color: C.champ, count: 9000 })), { at: 2, dur: 1.8 });
  S.form(mk(22, pb => { ic(pb, I.phone, 0, 170, 340, { color: C.white, count: 7000 }); ringPoints(pb, { x: 0, y: 170, r: 230, w: 6, count: 3000, color: C.orange }); }), { at: 3, dur: 1.8 });
  const bx = [['01 · APPETITE', '明知奶茶炸鸡不健康，<br>为什么偏偏忍不住？', -560], ['02 · GOSSIP', '为什么一条八卦，<br>比科普文章更上头？', 0], ['03 · SILENCE', '群里消息没人回，<br>为什么焦虑一整晚？', 560]];
  bx.forEach(([t, h, x], i) => S.box({ at: i + 1, title: t, html: h, world: [x, -190, 0], w: 480, h: 170, fs: 27, kind: i === 2 ? '' : 'w' }));
});

// 3 同一个答案：石器时代的大脑
add(S => {
  S.cap(capCN('ONE ANSWER', '同一个答案'));
  S.form(mk(30, pb => brainPoints(pb, { s: 330, y: 40, count: 26000 })), { at: 0, f: 0.3, dur: 2.6, spin: 0.12, center: [0, 40, 0], scatter: 350 });
  S.mono('MANUFACTURED', { at: 1, f: 0.4, world: [-620, 130, 0], size: 16 });
  S.text('出厂日期：<span class="hl">石器时代</span>', { at: 1, f: 0.45, world: [-620, 80, 0], size: 36 });
  S.mono('≈ 300,000 YEARS AGO', { at: 1, f: 0.6, world: [-620, 30, 0], size: 16 });
  S.mono('RUNTIME', { at: 2, f: 0.1, world: [620, 130, 0], size: 16 });
  S.text('运行环境：<span class="hl2">21 世纪</span>', { at: 2, f: 0.15, world: [620, 80, 0], size: 36 });
  S.mono('SMARTPHONES · CITIES · FAST FOOD', { at: 2, f: 0.3, world: [620, 30, 0], size: 16 });
  S.flash({ at: 3, f: 0.72, amt: 0.25 });
  S.form(mk(31, pb => txt(pb, '进化心理学', 0, 40, 230, { w: 300, f: 'SHS', count: 34000, ps: 2.0 })), { at: 3, f: 0.7, dur: 1.6, scatter: 700, swirl: 2.5 });
});

// 4 片名
add(S => {
  S.form(mk(40, pb => txt(pb, '进化心理学', 0, 70, 230, { w: 300, f: 'SHS', count: 34000, ps: 2.0 })), { at: 0, d: -1, dur: 0.1 });
  S.mono('EVOLUTIONARY  PSYCHOLOGY', { at: 0, d: 0.2, x: 960, y: 650, size: 20, style: { letterSpacing: '.6em' } });
  S.hero('你大脑的「出厂设置」', { at: 0, d: 0.6, y: 740, size: 52, cls: 't-hero' });
});

// 5 第一章
add(chapter('01', '什么是进化心理学', 'WHAT IS EVOLUTIONARY PSYCHOLOGY'));

// 6 达尔文 1859
add(S => {
  S.cap(capCN('1859 · CHARLES DARWIN', '自然选择'));
  S.form(mk(60, pb => txt(pb, '1859', 0, 60, 330, { w: 200, count: 26000 })), { at: 0, d: -0.2, dur: 2.0, scatter: 500 });
  S.text('达尔文《物种起源》', { at: 0, f: 0.4, x: 960, y: 760, size: 40 });
  S.mono('ON THE ORIGIN OF SPECIES', { at: 0, f: 0.5, x: 960, y: 815, size: 17 });
  S.form(mk(61, pb => treeOfLife(pb, { y: -320, len: 165, depth: 8 })), { at: 1, dur: 2.4, scatter: 300 });
  const steps = [['个体有差异', 'VARIATION', -620, 1, 0.2], ['更能生存繁殖', 'SELECTION', -620, 1, 0.65], ['特征传给后代', 'INHERITANCE', -620, 2, 0.2]];
  steps.forEach(([s, en, x, at, f], i) => { S.text(`<span class="dim">0${i + 1}</span>  ${s}`, { at, f, world: [x, 150 - i * 110, 0], size: 36, al: 'l' }); S.mono(en, { at, f: f + 0.1, world: [x + 62, 108 - i * 110, 0], size: 15, al: 'l' }); });
  S.form(mk(62, pb => { treeOfLife(pb, { y: -320, len: 165, depth: 8 }); pb.s = pb.s.map(v => v * 0.6); ic(pb, I.eagle, 560, 170, 260, { color: C.champ, keep: 0.2 }); ic(pb, I.bear, 560, -150, 260, { color: C.white, keep: 0.15 }); }), { at: 3, dur: 2.0 });
  S.label('锐利的眼睛', { at: 3, f: 0.4, world: [780, 170, 0], size: 26, al: 'l' });
  S.label('厚厚的皮毛', { at: 3, f: 0.6, world: [780, -150, 0], size: 26, al: 'l' });
});

// 7 达尔文的预言
add(S => {
  S.cap(capCN('A PROPHECY', '达尔文的预言'));
  S.form(mk(70, pb => ic(pb, I.book, 0, 80, 360, { color: C.champ, keep: 0.15, count: 16000 })), { at: 0, dur: 2.0 });
  S.form(mk(71, pb => ringPoints(pb, { r: 420, w: 30, count: 9000, color: C.champ, tilt: 1.25, y: 60 })), { at: 1, dur: 2.0, spin: 0.15, center: [0, 60, 0] });
  S.hero('“心理学，将建立在<br>一个新的基础之上。”', { at: 1, f: 0.1, y: 470, size: 64, align: 'center', style: { lineHeight: '1.6' } });
  S.mono('— CHARLES DARWIN, 1859', { at: 1, f: 0.6, x: 1260, y: 640, size: 17 });
  const tl = polyline([[-600, -230], [600, -230]], { color: C.champ, opacity: 0.7 });
  S.obj(tl, { at: 2, draw: true, drawDur: 2.5 });
  S.obj(glowSprites([{ x: -600, y: -230, size: 46, color: C.warm }, { x: 600, y: -230, size: 56, color: C.orange }]), { at: 2 });
  S.label('1859 · 预言', { at: 2, world: [-600, -290, 0], size: 26 });
  S.label('1990s · <span class="hl">进化心理学诞生</span>', { at: 2, f: 0.6, world: [600, -290, 0], size: 26 });
});

// 8 核心观点
add(S => {
  S.cap(capCN('CORE IDEA', '核心观点'));
  S.form(mk(80, pb => brainPoints(pb, { s: 280, y: 20, count: 24000 })), { at: 1, d: -0.4, dur: 2.2, spin: 0.15, center: [0, 20, 0] });
  S.hero('大脑，也是被自然选择塑造的<span class="hl">器官</span>', { at: 1, f: 0.35, y: 860, size: 46, out: 2 });
  const row = pb => { ic(pb, I.heart, -560, 90, 230, { color: C.red }); ic(pb, I.eye, 0, 90, 240, { color: C.white }); brainPoints(pb, { x: 560, y: 90, s: 160, count: 12000 }); };
  S.form(mk(81, row), { at: 2, dur: 2.0 });
  S.text('心脏 → 泵血', { at: 2, f: 0.2, world: [-560, -110, 0], size: 36 });
  S.text('眼睛 → 看见', { at: 2, f: 0.6, world: [0, -110, 0], size: 36 });
  S.text('心理机制 → <span class="hl">?</span>', { at: 3, world: [560, -110, 0], size: 36, out: 5 });
  ['恐惧', '食欲', '嫉妒', '爱'].forEach((s, i) => S.box({ at: 3, f: 0.3 + i * 0.15, html: s, world: [410 + i * 100, -200, 0], w: 88, h: 56, fs: 22, kind: 't', style: { textAlign: 'center' }, anim: 'box' }));
  S.text('心理机制 → <span class="hl">适应</span>', { at: 5, world: [560, -110, 0], size: 36 });
  S.text('功能：帮祖先解决<span class="hl">生存</span>与<span class="hl">繁殖</span>的难题', { at: 5, f: 0.3, x: 960, y: 860, size: 40 });
});

// 9 第二章
add(chapter('02', '四把钥匙', 'FOUR KEYS TO THE MIND'));

// 10 时间错配：30 万年压缩成一天
add(S => {
  S.cap(capCN('KEY 01 · TIME MISMATCH', '时间错配'));
  const L = -820, R = 820, xOf = h => L + (R - L) * h / 24;
  S.obj(grid({ y: -160, size: 4000, step: 120, opacity: 0.12 }), { at: 0 });
  S.form(mk(100, pb => linePoints(pb, [[L, 0], [R, 0]], { count: 14000, color: C.teal, ps: 1.9, w: 10 })), { at: 1, dur: 2.2 });
  S.text('把智人约 30 万年的历史，压缩成一天', { at: 1, f: 0.2, x: 960, y: 230, size: 38 });
  [0, 6, 12, 18, 24].forEach(h => S.mono(`${h}:00`, { at: 1, f: 0.5, world: [xOf(h), -40, 0], size: 16 }));
  const clock = S.el('00:00', { cls: 't-num', size: 120, at: 2, x: 960, y: 360, anim: 'fade' });
  S.update(lt => {
    const segs = [[S.T(2), S.T(2, 0.95), 0, 23 * 60 + 12], [S.T(3, 0.9), S.T(4, 0.6), 23 * 60 + 12, 23 * 60 + 58.72], [S.T(4, 0.9), S.T(5, 0.7), 23 * 60 + 58.72, 23 * 60 + 59.92]];
    let m = 0; for (const [a, b, x0, x1] of segs) if (lt >= a) m = lerp(x0, x1, EZ.inOut(clamp((lt - a) / (b - a))));
    const hh = Math.floor(m / 60), mm = Math.floor(m % 60), ss = Math.floor((m * 60) % 60);
    clock.e.textContent = lt >= S.T(4, 0.9) ? `${hh}:${String(mm).padStart(2, '0')}:${String(ss).padStart(2, '0')}` : `${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}`;
  });
  S.form(mk(101, pb => { linePoints(pb, [[L, 0], [xOf(23.2), 0]], { count: 13000, color: C.teal, ps: 1.9, w: 10 }); linePoints(pb, [[xOf(23.2), 0], [R, 0]], { count: 2000, color: C.orange, ps: 2.4, w: 14 }); }), { at: 2, dur: 3.0, stagger: 0.8, scatter: 30, swirl: 0 });
  S.label('狩猎 · 采集', { at: 2, f: 0.5, world: [xOf(11.5), 60, 0], size: 30 });
  S.mono('HUNTER-GATHERERS · 290,000 YEARS', { at: 2, f: 0.6, world: [xOf(11.5), 25, 0], size: 14 });
  const mk3 = (h, color) => glowSprites([{ x: xOf(h), y: 0, size: 60, color }]);
  S.obj(mk3(23.2, C.orange), { at: 3 });
  S.label('农业 <span class="hl">23:12</span>', { at: 3, f: 0.2, world: [xOf(23.2), 90, 0], size: 26 });
  S.obj(mk3(23.979, C.orange), { at: 4, f: 0.5 });
  S.label('工业革命 <span class="hl">23:58:43</span>', { at: 4, f: 0.5, world: [xOf(23.979), 150, 0], size: 22 });
  S.obj(mk3(23.9986, C.red), { at: 5, f: 0.4 });
  S.label('智能手机 <span class="hl">最后 5 秒</span>', { at: 5, f: 0.4, world: [xOf(23.9986), -70, 0], size: 22 });
  S.cam({ from: { pos: [0, 120, 1.043 * D], tgt: [0, 0, 0] }, to: { pos: [690, 60, 0.391 * D], tgt: [780, 0, 0] } });
});

// 11 错配
add(S => {
  S.cap(capCN('MISMATCH', '错配'));
  S.form(mk(110, pb => { brainPoints(pb, { x: -480, y: 40, s: 230, count: 18000 }); ic(pb, I.city, 480, 40, 380, { color: C.white, keep: 0.15, count: 14000 }); }), { at: 0, dur: 2.2 });
  S.mono('BRAIN v1.0 · STONE AGE', { at: 0, f: 0.4, world: [-480, -200, 0], size: 16 });
  S.mono('ENVIRONMENT · 2026', { at: 0, f: 0.6, world: [480, -200, 0], size: 16 });
  S.hero('<span class="hl">≠</span>', { at: 1, x: 960, y: Y(40), size: 150, anim: 'zoom' });
  S.text('为远古设计的本能，在现代常常<span class="hl">帮倒忙</span>', { at: 2, x: 960, y: 830, size: 40 });
});

// 12 爱吃甜
add(S => {
  S.cap(capCN('EXAMPLE · SWEET TOOTH', '为什么爱吃甜'));
  S.form(mk(120, pb => ic(pb, I.apple, 0, 80, 300, { color: C.red, keep: 0.4, count: 9000 })), { at: 1, dur: 2.0 });
  S.mono('ANCESTRAL · CALORIES SCARCE', { at: 1, f: 0.4, x: 960, y: 150, size: 17, out: 3 });
  S.text('远古：一颗熟果 = 宝贵的能量', { at: 1, f: 0.5, x: 960, y: 770, size: 36, out: 3 });
  S.text('爱吃甜 = <span class="hl2">生存优势</span>', { at: 2, x: 960, y: 850, size: 40, out: 3 });
  S.form(mk(121, pb => iconGrid(pb, (i, j) => [I.donut, I.tea, I.fries][(i + j) % 3], 7, 3, 0, 70, 190, 125, { color: C.warm, keep: 0.3, count: 2400 })), { at: 3, dur: 2.0, scatter: 400 });
  S.mono('TODAY · CALORIES EVERYWHERE', { at: 3, x: 960, y: 150, size: 17 });
  S.text('今天：糖和脂肪随处可见', { at: 3, f: 0.3, x: 960, y: 800, size: 36 });
  S.text('爱吃甜 = <span class="hl">肥胖与糖尿病风险</span>', { at: 4, x: 960, y: 870, size: 40 });
});

// 13 烟雾报警器原理
add(S => {
  S.cap(capCN('KEY 02 · SMOKE DETECTOR PRINCIPLE', '烟雾报警器原理'));
  S.form(mk(130, pb => grassBlades(pb, { y0: -200, w: 1700, n: 520, h: 260 })), { at: 1, d: -0.5, dur: 2.2 });
  S.text('沙沙……', { at: 1, f: 0.6, x: 960, y: 330, size: 50, cls: 't-hero', out: 2 });
  S.box({ at: 2, title: 'ERROR A · 漏报', html: '以为是风 → 其实是<span class="hl">狮子</span><br>代价：<span class="hl">丢掉性命</span>', world: [-460, 240, 0], w: 620, h: 170, fs: 30, out: 4 });
  S.box({ at: 3, title: 'ERROR B · 误报', html: '以为是狮子 → 其实是风<br>代价：<span class="hl2">白跑一趟</span>', world: [460, 240, 0], w: 620, h: 170, fs: 30, kind: 't', out: 4 });
  S.form(mk(131, pb => { grassBlades(pb, { y0: -200, w: 1700, n: 380, h: 220 }); ic(pb, I.lion, -460, -60, 260, { color: C.orange, keep: 0.2 }); }), { at: 2, f: 0.4, dur: 1.8 });
  S.form(mk(132, pb => { boxPoints(pb, { x: -260, y: -330, w: 150, h: 520, d: 150, count: 9000, color: C.orange }); boxPoints(pb, { x: 260, y: -330, w: 150, h: 26, d: 150, count: 1200, color: C.teal }); }), { at: 4, dur: 2.0 });
  S.label('漏报的代价', { at: 4, f: 0.3, world: [-260, -380, 0], size: 26 });
  S.label('误报的代价', { at: 4, f: 0.3, world: [260, -380, 0], size: 26 });
  S.text('两种错误，代价<span class="hl">完全不对等</span>', { at: 4, f: 0.5, x: 960, y: 880, size: 38 });
  S.obj(grid({ y: -330, size: 3000, step: 100, opacity: 0.12 }), { at: 4 });
  S.cam({ from: { pos: [0, 60, 1.022 * D] }, to: { pos: [-150, 180, 0.935 * D], tgt: [0, -40, 0] } });
});

// 14 宁可多虑
add(S => {
  S.cap(capCN('BETTER SAFE THAN SORRY', '宁可多虑'));
  S.hero('宁可<span class="hl">多虑</span>，不可大意', { at: 0, y: 200, size: 70 });
  S.form(mk(140, pb => { ringPoints(pb, { y: -10, r: 230, w: 16, count: 11000, color: C.teal }); ic(pb, I.alarm, 0, -10, 230, { color: C.white, count: 5000 }); }), { at: 1, d: -0.3, dur: 2.0, spinZ: 0.3, center: [0, -10, 0] });
  S.counter({ at: 1, f: 0.3, to: 10, cdur: 1.8, pre: '误报 × ', world: [-560, -10, 0], size: 64 });
  S.mono('FALSE ALARMS · TOAST', { at: 1, f: 0.4, world: [-560, -75, 0], size: 15 });
  S.form(mk(141, pb => { ringPoints(pb, { y: -10, r: 230, w: 16, count: 11000, color: C.orange }); ic(pb, I.fire, 0, -10, 240, { color: C.orange, keep: 0.4, count: 6000 }); }), { at: 2, dur: 1.4 });
  S.text('真火灾：<span class="hl">一次也不能漏</span>', { at: 2, f: 0.3, world: [560, -10, 0], size: 36 });
  S.form(mk(142, pb => ic(pb, I.snake, 0, -10, 380, { color: C.orange, keep: 0.15, count: 12000 })), { at: 4, dur: 1.4 });
  S.form(mk(143, pb => ic(pb, I.rope, 0, -10, 380, { color: C.champ, keep: 0.15, count: 12000 })), { at: 4, f: 0.55, dur: 1.4 });
  S.text('容易焦虑 · <span class="hl">一朝被蛇咬，十年怕井绳</span>', { at: 3, f: 0.3, x: 960, y: 860, size: 36 });
});

// 15 两种为什么
add(S => {
  S.cap(capCN('KEY 03 · TWO KINDS OF "WHY"', '两种为什么'));
  S.hero('人为什么爱吃甜？', { at: 1, y: 190, size: 60 });
  S.form(mk(150, pb => brainPoints(pb, { x: -470, y: 0, s: 210, count: 17000 })), { at: 2, dur: 2.0 });
  S.box({ at: 2, f: 0.2, title: 'PROXIMATE · 近因', html: '糖激活大脑的奖赏系统<br>→ 让人感觉愉快', world: [-470, -260, 0], w: 520, h: 150, fs: 27, kind: 't' });
  S.mono('HOW IT WORKS · 身体里的机制', { at: 3, world: [-470, -360, 0], size: 15 });
  S.form(mk(151, pb => { brainPoints(pb, { x: -470, y: 0, s: 210, count: 15000 }); helixPoints(pb, { x: 470, y: 0, len: 520, r: 110, turns: 3, count: 12000 }); }), { at: 4, dur: 2.0 });
  S.box({ at: 4, f: 0.2, title: 'ULTIMATE · 终极原因', html: '爱吃甜的祖先<br>更容易活下来', world: [470, -260, 0], w: 520, h: 150, fs: 27 });
  S.mono('WHY IT EXISTS · 演化的来历', { at: 5, world: [470, -360, 0], size: 15 });
  S.obj(lines([[-230, 0, 0, 200, 0, 0]], { color: C.champ, opacity: 0.5 }), { at: 6 });
  S.text('不冲突：同一个问题的<span class="hl">两个层面</span>', { at: 6, f: 0.3, x: 960, y: 300, size: 36 });
});

// 16 如果……那么……
add(S => {
  S.cap(capCN('KEY 04 · IF → THEN', '如果……那么……'));
  S.form(mk(160, pb => ic(pb, I.hand, 0, 80, 360, { color: C.champ, keep: 0.15, count: 13000 })), { at: 0, f: 0.4, dur: 2.0 });
  S.box({ at: 1, title: 'RULE', html: '<span class="hl2">IF</span>  皮肤反复摩擦   <span class="hl2">THEN</span>  长出老茧', x: 960, y: 820, w: 760, h: 120, fs: 32, kind: 't' });
  S.form(mk(161, pb => { ic(pb, I.hand, -400, 80, 320, { color: C.champ, keep: 0.1, count: 10000 }); const r = pb.r; for (let k = 0; k < 4; k++) for (let i = 0; i < 500; i++) pb.add(-400 - 90 + k * 52 + (r() - .5) * 26, 170 + (r() - .5) * 26, 10, C.orange, 2.4, 1.6); ic(pb, I.hand, 400, 80, 320, { color: C.champ, keep: 0.1, count: 10000 }); }), { at: 2, dur: 2.0 });
  S.label('经常摩擦 → <span class="hl">有茧</span>', { at: 2, f: 0.3, world: [-400, -130, 0], size: 28 });
  S.label('很少摩擦 → 没茧', { at: 2, f: 0.5, world: [400, -130, 0], size: 28 });
  S.text('但“会长茧”的机制，<span class="hl">人人都有</span>', { at: 3, x: 960, y: 230, size: 38, out: 4 });
  const pts = [[-600, 40], [0, 40], [600, 40]];
  S.form(mk(162, pb => linePoints(pb, pts, { count: 9000, color: C.champ, ps: 2, w: 8 })), { at: 4, dur: 2.0 });
  S.obj(glowSprites(pts.map((p, i) => ({ x: p[0], y: p[1], size: 70, color: [C.warm, C.teal, C.orange][i] }))), { at: 4, f: 0.3 });
  [['进化给的程序', 'PROGRAM'], ['环境输入', 'INPUT'], ['最终的行为', 'OUTPUT']].forEach(([s, en], i) => { S.text(s, { at: i < 2 ? 4 : 5, f: i === 1 ? 0.6 : 0.3, world: [pts[i][0], 150, 0], size: 34 }); S.mono(en, { at: i < 2 ? 4 : 5, f: i === 1 ? 0.7 : 0.4, world: [pts[i][0], -50, 0], size: 15 }); });
});

// 17 第三章
add(chapter('03', '生活里的进化痕迹', 'TRACES OF EVOLUTION IN DAILY LIFE'));

// 18 为什么怕蛇：儿童实验
add(S => {
  S.cap(capCN('LOBUE & DELOACHE · 2008', '儿童找蛇实验'));
  S.form(mk(180, pb => ic(pb, I.snake, 0, 60, 460, { color: C.orange, keep: 0.15, count: 16000 })), { at: 0, d: -0.3, dur: 2.0 });
  S.hero('我们为什么<span class="hl">怕蛇</span>？', { at: 0, f: 0.3, y: 840, size: 52, out: 1 });
  S.form(mk(181, pb => iconGrid(pb, (i, j) => (i === 2 && j === 1) ? I.snake : I.flower, 3, 3, -380, 30, 170, 130, { color: C.champ, keep: 0.35, count: 1700 })), { at: 1, f: 0.4, dur: 2.0 });
  S.box({ at: 2, html: '', world: [-380 + 170, 30, 0], w: 160, h: 160, kind: '', anim: 'box' });
  S.mono('DETECTION TIME · 示意', { at: 2, world: [420, 170, 0], size: 16 });
  S.label('蛇', { at: 2, f: 0.2, world: [170, 90, 0], size: 28 });
  S.el('<div style="width:300px;height:10px;background:linear-gradient(90deg,#ff8a3d,#ffcf9a);box-shadow:0 0 18px #ff8a3d"></div>', { at: 2, f: 0.2, world: [220, 90, 0], al: 'l', anim: 'up' });
  S.label('花', { at: 2, f: 0.4, world: [170, 10, 0], size: 28 });
  S.el('<div style="width:520px;height:10px;background:rgba(230,225,215,.45)"></div>', { at: 2, f: 0.4, world: [220, 10, 0], al: 'l', anim: 'up' });
  S.text('找到蛇，<span class="hl">更快</span>', { at: 2, f: 0.6, world: [420, -90, 0], size: 40 });
});

// 19 猴子实验
add(S => {
  S.cap(capCN('COOK & MINEKA · 1989', '猴子的恐惧学习'));
  S.form(mk(190, pb => ic(pb, I.monkey, 0, 40, 380, { color: C.champ, keep: 0.25, count: 13000 })), { at: 0, dur: 2.0 });
  S.text('实验室长大的猴子：原本<span class="hl2">不怕蛇</span>', { at: 0, f: 0.4, x: 960, y: 830, size: 36, out: 1 });
  S.form(mk(191, pb => { ic(pb, I.film, -560, 220, 140, { color: C.white, count: 2500 }); ic(pb, I.snake, -400, 220, 150, { color: C.orange, count: 3000 }); ic(pb, I.monkey, -480, -60, 270, { color: C.orange, keep: 0.2, count: 8000 }); }), { at: 1, dur: 2.0 });
  S.text('看过同伴怕蛇的录像 → <span class="hl">学会怕蛇</span>', { at: 1, f: 0.5, world: [-480, -260, 0], size: 30 });
  S.form(mk(192, pb => { ic(pb, I.film, -560, 220, 140, { color: C.white, count: 2500 }); ic(pb, I.snake, -400, 220, 150, { color: C.orange, count: 3000 }); ic(pb, I.monkey, -480, -60, 270, { color: C.orange, keep: 0.2, count: 8000 }); ic(pb, I.film, 400, 220, 140, { color: C.white, count: 2500 }); ic(pb, I.flower, 560, 220, 150, { color: C.champ, keep: 0.4, count: 3000 }); ic(pb, I.monkey, 480, -60, 270, { color: C.champ, keep: 0.2, count: 8000 }); }), { at: 2, dur: 2.0 });
  S.text('换成花 → <span class="hl2">怎么也学不会</span>', { at: 2, f: 0.5, world: [480, -260, 0], size: 30 });
  S.hero('大脑天生“准备好了”去怕蛇', { at: 3, y: 170, size: 46 });
  S.mono('PREPARED LEARNING', { at: 3, f: 0.3, x: 960, y: 230, size: 16 });
  S.text('汽车、插座才一百多年 —— 大脑<span class="hl">还没准备好</span>', { at: 4, x: 960, y: 880, size: 32 });
});

// 20 沃森选择任务（抽象版）
const cards = (S, labels, at, o = {}) => labels.map((l, i) => S.box({ at, f: i * 0.12, html: `<div style="font-family:${o.emoji ? 'SHS' : 'Inter'};font-weight:200;font-size:${o.fs || 120}px;text-align:center;line-height:${o.lh || 230}px;letter-spacing:0">${l}</div>`, world: [(i - 1.5) * 260, 90, 0], w: 200, h: 270, kind: 'w', out: o.out, ...((o.dims || []).includes(i) ? { dimAt: o.dimAt } : {}) }));
add(S => {
  S.cap(capCN('WASON SELECTION TASK', '小测试'));
  const cs = cards(S, ['E', 'K', '4', '7'], 1);
  S.text('规则：如果一面是<span class="hl">元音字母</span>，那么另一面一定是<span class="hl">偶数</span>', { at: 2, x: 960, y: 690, size: 34 });
  S.text('要检验规则，必须翻开哪几张？', { at: 3, x: 960, y: 770, size: 34, cls: 't-body dim', out: 5 });
  ['3', '2', '1'].forEach((n, k) => S.form(mk(200 + k, pb => txt(pb, n, 0, 90, 380, { w: 100, count: 9000, color: C.orange })), { at: 4, f: 1.0, d: 0.15 + k, dur: 0.7, scatter: 300, stagger: 0.2 }));
  S.form(mk(203, pb => ringPoints(pb, { y: 90, r: 520, w: 6, count: 3000, color: C.champ, tilt: 0 })), { at: 5, dur: 1.2 });
  S.update(lt => {
    const on = lt >= S.T(5, 0.3);
    cs.forEach((c, i) => { const hit = i === 0 || i === 3; c.e.style.borderColor = on ? (hit ? 'rgba(255,150,80,.95)' : 'rgba(230,230,235,.18)') : ''; c.e.style.boxShadow = on && hit ? '0 0 34px rgba(255,130,60,.55), inset 0 0 22px rgba(255,130,60,.2)' : ''; c.e.querySelector('.bx').style.opacity = on && !hit ? 0.25 : 1; });
  });
  S.mono('翻开看：背面是偶数吗？', { at: 6, world: [-390, -75, 0], size: 18 });
  S.mono('翻开看：背面是元音吗？', { at: 6, f: 0.5, world: [390, -75, 0], size: 18 });
  S.num('≈ 10%', { at: 7, x: 960, y: 820, size: 96 });
  S.mono('ANSWERED CORRECTLY', { at: 7, f: 0.2, x: 960, y: 890, size: 16 });
});

// 21 沃森选择任务（社会契约版）
add(S => {
  S.cap(capCN('SAME LOGIC · SOCIAL CONTRACT', '换一个说法'));
  S.text('规则：如果有人<span class="hl">喝酒</span>，那么他必须<span class="hl">年满 18 岁</span>', { at: 1, f: 0.3, x: 960, y: 690, size: 34 });
  const cs = cards(S, ['🍺<br><span style="font-size:30px">啤酒</span>', '🥤<br><span style="font-size:30px">可乐</span>', '25<span style="font-size:36px">岁</span>', '16<span style="font-size:36px">岁</span>'], 2, { emoji: true, fs: 90, lh: 100 });
  cs.forEach(c => { c.e.querySelector('.bx').style.top = '50px'; });
  S.text('你要检查谁？', { at: 3, x: 960, y: 770, size: 34, cls: 't-body dim', out: 4 });
  S.update(lt => {
    const on = lt >= S.T(4, 0.5);
    cs.forEach((c, i) => { const hit = i === 0 || i === 3; c.e.style.borderColor = on ? (hit ? 'rgba(255,150,80,.95)' : 'rgba(230,230,235,.18)') : ''; c.e.style.boxShadow = on && hit ? '0 0 34px rgba(255,130,60,.55), inset 0 0 22px rgba(255,130,60,.2)' : ''; c.e.querySelector('.bx').style.opacity = on && !hit ? 0.25 : 1; });
  });
  S.form(mk(210, pb => ringPoints(pb, { y: 90, r: 520, w: 6, count: 3000, color: C.teal })), { at: 4, f: 0.5, dur: 1.2 });
  S.num('≈ 73%', { at: 5, x: 960, y: 820, size: 96 });
  S.mono('GRIGGS & COX · 1982', { at: 5, f: 0.2, x: 960, y: 890, size: 16 });
});

// 22 骗子侦测器
add(S => {
  S.cap(capCN('COSMIDES & TOOBY · CHEATER DETECTION', '骗子侦测器'));
  S.obj(grid({ y: -260, size: 3000, step: 100, opacity: 0.14 }), { at: 0 });
  S.form(mk(220, pb => { boxPoints(pb, { x: -260, y: -260, w: 160, h: 60, d: 160, count: 2500, color: C.white }); boxPoints(pb, { x: 260, y: -260, w: 160, h: 440, d: 160, count: 10000, color: C.orange }); }), { at: 0, dur: 2.0 });
  S.label('抽象逻辑 <span class="hl2">≈10%</span>', { at: 0, f: 0.4, world: [-260, -170, 0], size: 26 });
  S.label('抓违规者 <span class="hl">≈73%</span>', { at: 0, f: 0.6, world: [260, 230, 0], size: 26 });
  S.text('逻辑结构，<span class="hl">一模一样</span>', { at: 0, f: 0.3, x: 960, y: 210, size: 40, out: 2 });
  S.mono('— COSMIDES & TOOBY', { at: 1, x: 960, y: 270, size: 16, out: 2 });
  const ppl = people(26, 7, 300, 0, 40);
  S.form(mk(221, pb => { ppl.forEach(p => spherePoints(pb, { x: p.x, y: p.y, z: p.z, r: 16, count: 260, color: C.champ, shell: 0.6 })); }), { at: 2, dur: 2.0 });
  S.obj(lines(knn(ppl, 3), { color: C.champ, opacity: 0.35 }), { at: 2, f: 0.4 });
  const bad = ppl[5];
  S.form(mk(222, pb => { ppl.forEach((p, i) => spherePoints(pb, { x: p.x, y: p.y, z: p.z, r: 16, count: 260, color: i === 5 ? C.red : C.champ, shell: 0.6 })); ringPoints(pb, { x: bad.x, y: bad.y, z: bad.z, r: 70, w: 4, count: 2500, color: C.teal }); }), { at: 3, f: 0.5, dur: 1.4 });
  S.hero('骗子侦测器', { at: 3, f: 0.6, y: 200, size: 60 });
  S.mono('CHEATER DETECTION MODULE', { at: 3, f: 0.7, x: 960, y: 265, size: 16 });
  S.text('抽象逻辑很难，但“抓骗子”，我们<span class="hl">天生擅长</span>', { at: 4, x: 960, y: 870, size: 34 });
  S.cam({ from: { pos: [0, 200, 1.000 * D], tgt: [0, -40, 0] }, to: { pos: [0, 60, 0.978 * D], tgt: [0, 20, 0] } });
});

// 23 八卦与邓巴数
add(S => {
  S.cap(capCN('ROBIN DUNBAR · GOSSIP', '为什么爱八卦'));
  S.form(mk(230, pb => { const r = pb.r; for (let i = 0; i < 16000; i++) { const a = r() * Math.PI * 2, rr = 250 + (r() - .5) * 40; const on = ((Math.PI / 2 - a) % (Math.PI * 2) + Math.PI * 2) % (Math.PI * 2) < Math.PI * 2 * 0.667; pb.add(rr * Math.cos(a), 40 + rr * Math.sin(a), (r() - .5) * 20, on ? C.orange : C.white, on ? 2.3 : 1.6, on ? 1 : 0.3); } }), { at: 1, f: 0.4, dur: 2.0, spin: 0 });
  S.num('≈ 2/3', { at: 2, x: 960, y: Y(40), size: 110, out: 3 });
  S.text('聊天时间，与<span class="hl">社交话题</span>有关', { at: 2, f: 0.3, x: 960, y: 860, size: 36, out: 3 });
  const ppl = people(22, 11, 320, 0, 30);
  S.form(mk(231, pb => ppl.forEach(p => spherePoints(pb, { x: p.x, y: p.y, z: p.z, r: 14, count: 300, color: C.champ, shell: 0.5 }))), { at: 3, dur: 2.0 });
  const segs = knn(ppl, 3);
  S.obj(lines(segs.filter((_, i) => i % 4), { color: C.teal, opacity: 0.4 }), { at: 3, f: 0.3, out: 5 });
  S.obj(lines(segs.filter((_, i) => !(i % 4)), { color: C.red, opacity: 0.55 }), { at: 3, f: 0.5, out: 5 });
  S.mono('谁可靠 · 谁失信 · 谁和谁结盟', { at: 3, f: 0.5, x: 960, y: 200, size: 18, out: 5 });
  S.hero('八卦 = 古老的<span class="hl">社交情报系统</span>', { at: 4, y: 860, size: 44, out: 6 });
  S.form(mk(232, pb => { circlePts(150, 300, 0, 40).forEach(([x, y]) => spherePoints(pb, { x, y, r: 9, count: 90, color: C.champ, shell: 0.4 })); }), { at: 5, f: 0.3, dur: 2.2 });
  S.num('150', { at: 5, f: 0.5, x: 960, y: Y(40), size: 150 });
  S.mono("DUNBAR'S NUMBER · 稳定关系的人数上限", { at: 5, f: 0.7, x: 960, y: 140, size: 18 });
  S.text('≈ 一个远古部落的规模 <span class="dim">（仍有争议）</span>', { at: 6, x: 960, y: 860, size: 34 });
});

// 24 被排斥的痛
add(S => {
  S.cap(capCN('SOCIAL PAIN', '被排斥的痛'));
  S.box({ at: 0, d: 0.2, title: 'GROUP CHAT', html: '周末有空一起吃饭吗？', typing: 1.2, x: 960, y: 420, w: 620, h: 130, fs: 32, out: 1 });
  S.mono('已读 · 无人回复', { at: 0, f: 0.75, x: 1180, y: 520, size: 18, out: 1 });
  const grp = people(40, 3, 160, -250, 40);
  S.form(mk(240, pb => { grp.forEach(p => spherePoints(pb, { x: p.x, y: p.y, z: p.z, r: 10, count: 200, color: C.champ, shell: 0.5 })); spherePoints(pb, { x: 520, y: 40, r: 12, count: 600, color: C.white, shell: 0.4 }); }), { at: 1, dur: 2.2 });
  S.text('被群体抛弃，几乎<span class="hl">等于死亡</span>', { at: 1, f: 0.4, x: 960, y: 850, size: 38, out: 3 });
  S.form(mk(241, pb => { grp.forEach(p => spherePoints(pb, { x: p.x - 200, y: p.y, z: p.z, r: 10, count: 120, color: C.champ, shell: 0.5, ps: 1.6 })); spherePoints(pb, { x: 520, y: 40, r: 12, count: 600, color: C.white, shell: 0.4 }); ic(pb, I.lion, 760, 40, 220, { color: C.orange, keep: 0.15, count: 5000 }); }), { at: 2, dur: 2.0 });
  S.form(mk(242, pb => brainPoints(pb, { y: 30, s: 300, count: 24000 })), { at: 3, dur: 2.0, spin: 0.1, center: [0, 30, 0] });
  S.hero('对“被排斥”<span class="hl">极其敏感</span>', { at: 3, f: 0.3, y: 190, size: 46, out: 4 });
  S.form(mk(243, pb => { brainPoints(pb, { y: 30, s: 300, count: 18000, color: [0.5, 0.45, 0.4] }); spherePoints(pb, { x: -60, y: 90, r: 95, count: 4000, color: C.red, shell: 0.3 }); spherePoints(pb, { x: 50, y: 90, r: 95, count: 4000, color: C.teal, shell: 0.3 }); }), { at: 4, f: 0.3, dur: 1.8 });
  S.label('被冷落', { at: 4, f: 0.5, world: [-330, 150, 0], size: 28, cls: 't-label hl' });
  S.label('身体疼痛', { at: 4, f: 0.6, world: [330, 150, 0], size: 28, cls: 't-label hl2' });
  S.mono('部分重叠 · EISENBERGER ET AL. 2003', { at: 4, f: 0.7, x: 960, y: 200, size: 16 });
  S.form(mk(244, pb => ic(pb, I.broken, 0, 40, 380, { color: C.red, keep: 0.3, count: 12000 })), { at: 5, dur: 1.6 });
  S.hero('“心痛”，也许不只是比喻', { at: 5, f: 0.3, y: 860, size: 44 });
});

// 25 亲缘选择
add(S => {
  S.cap(capCN('W. D. HAMILTON · KIN SELECTION', '亲缘选择'));
  S.hero('人为什么愿意<span class="hl">帮助别人</span>？', { at: 0, y: 200, size: 52, out: 1 });
  S.form(mk(250, pb => helixPoints(pb, { y: 30, len: 1300, r: 150, turns: 4, count: 20000 })), { at: 1, dur: 2.2, spin: 0, center: [0, 30, 0] });
  S.text('汉密尔顿：<span class="hl">亲缘选择</span>', { at: 1, f: 0.5, x: 960, y: 230, size: 40, out: 2 });
  const nodes = [{ x: 0, y: 60, size: 90, color: C.white }, { x: -420, y: 60, size: 70, color: C.teal }, { x: 420, y: 60, size: 60, color: C.warm }];
  S.form(mk(251, pb => { linePoints(pb, [[-420, 60], [0, 60]], { count: 4000, color: C.teal, w: 6 }); linePoints(pb, [[0, 60], [420, 60]], { count: 1000, color: C.warm, w: 6 }); }), { at: 2, dur: 1.8 });
  S.obj(glowSprites(nodes), { at: 2, out: 4 });
  S.label('你', { at: 2, world: [0, -30, 0], size: 30, out: 4 });
  S.label('亲兄弟姐妹', { at: 2, f: 0.1, world: [-420, -30, 0], size: 28, out: 4 });
  S.num('1/2', { at: 2, f: 0.2, world: [-420, 170, 0], size: 70, out: 4 });
  S.label('堂表兄弟姐妹', { at: 2, f: 0.55, world: [420, -30, 0], size: 28, out: 4 });
  S.num('1/8', { at: 2, f: 0.65, world: [420, 170, 0], size: 70, out: 4 });
  S.text('帮亲人 = 帮“<span class="hl">自己的基因</span>”传下去', { at: 3, x: 960, y: 860, size: 36, out: 4 });
  S.form(mk(252, pb => helixPoints(pb, { y: -150, len: 1500, r: 70, turns: 6, count: 12000 })), { at: 4, dur: 2.0 });
  S.hero('“我愿意为两个亲兄弟，<br>或者八个堂兄弟献出生命。”', { at: 5, y: 380, size: 52, align: 'center', style: { lineHeight: '1.6' } });
  S.mono('— J. B. S. HALDANE', { at: 5, f: 0.4, x: 1300, y: 520, size: 16 });
  S.num('2 × ½ = 1    8 × ⅛ = 1', { at: 5, f: 0.7, x: 960, y: 640, size: 54, cls: 't-num', style: { color: '#ff9a4d' } });
});

// 26 互惠利他
add(S => {
  S.cap(capCN('RECIPROCAL ALTRUISM', '互惠利他'));
  S.form(mk(260, pb => ic(pb, I.shake, 0, 60, 380, { color: C.champ, keep: 0.2, count: 13000 })), { at: 0, dur: 2.0 });
  S.hero('互惠利他', { at: 0, f: 0.5, y: 220, size: 56 });
  S.text('今天：我 → 你', { at: 1, world: [-520, 60, 0], size: 40 });
  S.text('明天：你 → 我', { at: 1, f: 0.5, world: [520, 60, 0], size: 40 });
  S.text('最讨厌：<span class="hl">只占便宜、从不回报</span>的人', { at: 2, f: 0.4, x: 960, y: 860, size: 38 });
});

// 27 择偶
add(S => {
  S.cap(capCN('DAVID BUSS · 37 CULTURES', '择偶研究'));
  S.form(mk(270, pb => { spherePoints(pb, { x: -420, y: 40, r: 260, count: 16000, color: C.blue, shell: 0.97 }); const r = rng(3); for (let k = 0; k < 37; k++) { const u = r() * 1.4 - .7, th = r() * Math.PI * 2, q = Math.sqrt(1 - u * u); spherePoints(pb, { x: -420 + 262 * q * Math.cos(th), y: 40 + 262 * u, z: 262 * q * Math.sin(th), r: 7, count: 70, color: C.orange, shell: 0.3, ps: 2.6 }); } }), { at: 1, d: -0.3, dur: 2.0, spin: 0.25, center: [-420, 40, 0] });
  S.counter({ at: 1, f: 0.3, to: 37, cdur: 1.6, post: ' <span style="font-size:40px">种文化</span>', world: [330, 150, 0], size: 110, out: 4 });
  S.counter({ at: 1, f: 0.5, to: 10047, cdur: 2, post: ' <span style="font-size:30px">人</span>', world: [330, 30, 0], size: 64, out: 4 });
  S.box({ at: 3, title: '男女共同看重 · TOP 4', html: '① 彼此相爱、相互吸引<br>② 性格可靠<br>③ 情绪稳定、成熟<br>④ 待人友善', world: [330, -170, 0], w: 520, h: 250, fs: 28, out: 4 });
  S.form(mk(271, pb => { bell(pb, -0.11, 0.24, C.teal); bell(pb, 0.11, 0.24, C.orange); }), { at: 4, f: 0.2, dur: 2.0 });
  S.mono('某项偏好在两个群体中的分布 · 示意', { at: 4, f: 0.4, x: 960, y: 230, size: 17 });
  S.label('平均差异', { at: 4, f: 0.6, x: 960, y: 330, size: 26, cls: 't-label dim' });
  S.text('个体之间的差异，往往<span class="hl">大于</span>平均差异', { at: 5, f: 0.3, x: 960, y: 820, size: 36, out: 6 });
  S.hero('爱上谁，从来不只由进化决定', { at: 6, f: 0.2, y: 820, size: 42 });
});

// 28 第四章
add(chapter('04', '三个误区', 'THREE MISCONCEPTIONS'));

// 29 误区一
const strike = (S, at, y, w, o = {}) => S.el(`<div style="width:${w}px;height:3px;background:#ff6a3d;box-shadow:0 0 16px #ff6a3d"></div>`, { at, x: 960, y, anim: 'up', dur: 0.4, ...o });
add(S => {
  S.cap(capCN('MYTH 01', '误区一'));
  S.form(mk(290, pb => txt(pb, '自然的 = 对的', 0, 140, 170, { w: 300, f: 'SHS', count: 24000 })), { at: 0, d: -0.3, dur: 2.0 });
  S.form(mk(291, pb => txt(pb, '自然的 = 对的', 0, 140, 170, { w: 300, f: 'SHS', count: 24000, color: [0.5, 0.42, 0.36] })), { at: 1, dur: 0.8, scatter: 40, swirl: 0 });
  strike(S, 1, Y(140), 1180);
  S.hero('解释 <span class="hl">≠</span> 辩护', { at: 1, f: 0.4, y: 590, size: 76 });
  S.text('能解释攻击冲动，不等于为暴力找借口', { at: 2, f: 0.2, x: 960, y: 700, size: 36 });
  S.box({ at: 3, title: 'NATURALISTIC FALLACY · 自然主义谬误', html: '从“是什么”，推不出“应该怎样”', x: 960, y: 820, w: 700, h: 120, fs: 32 });
});

// 30 误区二
add(S => {
  S.cap(capCN('MYTH 02', '误区二'));
  S.form(mk(300, pb => txt(pb, '基因决定一切', 0, 140, 170, { w: 300, f: 'SHS', count: 24000 })), { at: 0, d: -0.3, dur: 2.0 });
  strike(S, 1, Y(140), 1100, { out: 1, of: 0.5 });
  S.form(mk(301, pb => txt(pb, '基因 × 环境 × 选择', 0, 140, 140, { w: 300, f: 'SHS', count: 24000, color: C.warm })), { at: 1, f: 0.5, dur: 2.0, scatter: 400 });
  S.form(mk(302, pb => { txt(pb, '基因 × 环境 × 选择', 0, 140, 140, { w: 300, f: 'SHS', count: 18000, color: C.warm }); ic(pb, I.sprout, 0, -170, 240, { color: C.green, keep: 0.4, count: 7000 }); }), { at: 2, dur: 2.0 });
  S.text('人类最独特的进化成果：<span class="hl2">学习 · 反思 · 改变自己</span>', { at: 2, f: 0.4, x: 960, y: 860, size: 36 });
});

// 31 误区三
add(S => {
  S.cap(capCN('MYTH 03 · JUST-SO STORIES', '误区三'));
  S.form(mk(310, pb => ic(pb, I.scroll, 0, 60, 380, { color: C.champ, keep: 0.2, count: 13000 })), { at: 0, dur: 2.0 });
  S.hero('编个远古故事 ≠ 科学', { at: 0, f: 0.4, y: 850, size: 46, out: 1 });
  S.text('“原来如此的故事”', { at: 1, f: 0.4, x: 960, y: 200, size: 44, out: 2 });
  S.mono('— STEPHEN JAY GOULD', { at: 1, f: 0.6, x: 960, y: 260, size: 16, out: 2 });
  const pts = [[-600, 40], [0, 40], [600, 40]];
  S.form(mk(311, pb => linePoints(pb, pts, { count: 9000, color: C.champ, w: 8 })), { at: 2, dur: 2.0 });
  S.obj(glowSprites(pts.map((p, i) => ({ x: p[0], y: p[1], size: 70, color: [C.warm, C.orange, C.teal][i] }))), { at: 2, f: 0.3 });
  [['提出假设', 'HYPOTHESIS', 2, 0.3], ['可检验的预测', 'PREDICTION', 2, 0.6], ['跨文化 · 实验 · 数据', 'EVIDENCE', 3, 0.2]].forEach(([s, en, at, f], i) => { S.text(s, { at, f, world: [pts[i][0], 150, 0], size: 32 }); S.mono(en, { at, f: f + 0.1, world: [pts[i][0], -50, 0], size: 15 }); });
  S.box({ at: 4, title: 'REPLICATION · 可重复性', html: '部分研究未能被重复，至今仍有争论', x: 960, y: 760, w: 640, h: 110, fs: 30 });
  S.hero('保持<span class="hl">好奇</span>，也保持<span class="hl2">怀疑</span>', { at: 5, y: 210, size: 52 });
});

// 32 第五章
add(chapter('05', '能用上的建议', 'FOUR THINGS YOU CAN DO'));

// 33 建议一、二
add(S => {
  S.cap(capCN('TIPS 01 – 02', '建议'));
  S.form(mk(330, pb => { ic(pb, I.lion, -560, 120, 220, { color: C.orange, keep: 0.2, count: 6000 }); ic(pb, I.wind, -320, 120, 200, { color: C.white, keep: 0.1, count: 5000 }); }), { at: 0, f: 0.3, dur: 2.0 });
  S.num('01', { at: 0, world: [-440, 330, 0], size: 60 });
  S.text('识别焦虑的“误报”', { at: 0, f: 0.4, world: [-440, -80, 0], size: 40 });
  S.mono('真的是狮子，还是风吹草动？', { at: 0, f: 0.6, world: [-440, -140, 0], size: 18 });
  S.text('看见它，就能<span class="hl2">少被它控制</span>', { at: 1, f: 0.6, world: [-440, -220, 0], size: 32 });
  S.form(mk(331, pb => { ic(pb, I.lion, -560, 120, 220, { color: C.orange, keep: 0.2, count: 5000 }); ic(pb, I.wind, -320, 120, 200, { color: C.white, keep: 0.1, count: 4000 }); ic(pb, I.house, 440, 120, 260, { color: C.champ, keep: 0.2, count: 7000 }); }), { at: 2, dur: 2.0 });
  S.num('02', { at: 2, world: [440, 330, 0], size: 60 });
  S.text('改变环境 <span class="hl">&gt;</span> 硬拼意志力', { at: 2, f: 0.4, world: [440, -80, 0], size: 40 });
  S.mono('不囤零食，比硬忍更有效', { at: 3, f: 0.4, world: [440, -140, 0], size: 18 });
});

// 34 建议三、四
add(S => {
  S.cap(capCN('TIPS 03 – 04', '建议'));
  S.num('03', { at: 0, world: [-440, 330, 0], size: 60 });
  S.text('对社交媒体保持清醒', { at: 0, f: 0.3, world: [-440, -80, 0], size: 40 });
  S.form(mk(340, pb => circlePts(150, 150, -440, 120).forEach(([x, y]) => spherePoints(pb, { x, y, r: 6, count: 40, color: C.champ, shell: 0.3 }))), { at: 0, f: 0.3, dur: 1.8 });
  S.form(mk(341, pb => galaxyPoints(pb, { x: -440, y: 120, r: 280, count: 26000, tilt: 0.55 })), { at: 1, f: 0.5, dur: 2.0 });
  S.counter({ at: 1, f: 0.5, from: 150, to: 8200000000, cdur: 2.4, world: [-440, -150, 0], size: 44 });
  S.mono('比较对象：部落 150 人 → 全世界', { at: 1, f: 0.6, world: [-440, -205, 0], size: 17 });
  S.text('不是你不够好，是<span class="hl2">尺度错了</span>', { at: 2, f: 0.3, world: [-440, -270, 0], size: 30 });
  S.num('04', { at: 3, world: [440, 330, 0], size: 60 });
  S.text('给大脑“熟悉”的东西', { at: 3, f: 0.3, world: [440, -80, 0], size: 40 });
  const icons = [I.walk, I.sun, I.tree, I.users, I.moon];
  S.form(mk(342, pb => { galaxyPoints(pb, { x: -440, y: 120, r: 280, count: 20000, tilt: 0.55 }); icons.forEach((src, i) => ic(pb, src, 440 + (i - 2) * 120, 120, 110, { color: [C.champ, C.warm, C.green, C.white, C.blue][i], count: 1600 })); }), { at: 4, dur: 2.2 });
  S.mono('走路 · 阳光 · 自然 · 面对面 · 睡眠', { at: 4, f: 0.6, world: [440, -140, 0], size: 18 });
  S.text('祖先的日常，仍是<span class="hl2">健康的基础</span>', { at: 5, f: 0.3, world: [440, -220, 0], size: 30 });
});

// 35 回顾
add(S => {
  S.cap(capCN('RECAP', '回顾'));
  S.form(mk(350, pb => brainPoints(pb, { x: -480, y: 40, s: 260, count: 22000 })), { at: 0, f: 0.3, dur: 2.0, spin: 0.15, center: [-480, 40, 0] });
  [['我们的心智，是漫长进化的产物', 1], ['“不理性”的情绪，曾是<span class="hl">救命的智慧</span>', 2], ['看懂“出厂设置”，做<span class="hl">更清醒</span>的人', 4]].forEach(([s, at], i) => {
    S.num(`0${i + 1}`, { at, world: [-60, 190 - i * 150, 0], size: 40, al: 'l', cls: 't-num dim' });
    S.text(s, { at, f: 0.1, world: [30, 190 - i * 150, 0], size: 38, al: 'l' });
  });
  S.text('了解它们，不是为了找借口', { at: 3, world: [30, -280, 0], size: 28, al: 'l', cls: 't-body dim' });
});

// 36 结尾
add(S => {
  S.form(mk(360, pb => galaxyPoints(pb, { y: -40, r: 700, count: 40000, arms: 4, tilt: 1.2 })), { at: 0, d: -0.5, dur: 2.6, spin: 0.08, center: [0, -40, 0], scatter: 600 });
  S.hero('你是三十万年进化的结果，', { at: 0, d: 0.3, y: 330, size: 56 });
  S.hero('但你的未来，由<span class="hl">你自己</span>决定。', { at: 1, y: 430, size: 56 });
  S.form(mk(361, pb => spherePoints(pb, { r: 6, count: 3000, color: C.white, shell: 0.2 })), { at: 2, f: 0.6, dur: 2.6, scatter: 200, swirl: 3 });
  S.mono('EVOLUTIONARY PSYCHOLOGY · 进化心理学', { at: 2, f: 0.8, x: 960, y: 760, size: 18 });
  S.cam({ from: { pos: [0, 300, 1.043 * D], tgt: [0, -40, 0] }, to: { pos: [0, 120, 0.870 * D], tgt: [0, 0, 0] } });
});

// 37 参考资料
add(S => {
  S.form(mk(370, pb => spherePoints(pb, { r: 4, count: 600, color: C.white, shell: 0.2 })), { at: 0, d: -0.5, dur: 0.5 });
  S.cap('REFERENCES · <b>参考资料</b>', { y: 120 });
  S.el([
    'Darwin, C. (1859). On the Origin of Species.',
    'Barkow, Cosmides & Tooby (Eds.) (1992). The Adapted Mind.',
    'Nesse, R. M. (2005). The smoke detector principle.',
    'Tinbergen, N. (1963). On aims and methods of ethology.',
    'LoBue & DeLoache (2008). Detecting the snake in the grass.',
    'Cook & Mineka (1989). Observational conditioning of fear in rhesus monkeys.',
    'Wason (1968); Griggs & Cox (1982); Cosmides (1989). Selection task studies.',
    'Dunbar, R. (1997). Grooming, Gossip, and the Evolution of Language.',
    'Eisenberger, Lieberman & Williams (2003). Does rejection hurt?',
    'Hamilton, W. D. (1964). The genetical evolution of social behaviour.',
    'Buss, D. M. (1989). Sex differences in human mate preferences: 37 cultures.',
    'Gould & Lewontin (1979). The spandrels of San Marco.',
    'World Health Organization (2023). Global status report on road safety.',
  ].join('<br>'), { cls: 't-mono', size: 19, at: 0, d: 0.3, x: 960, y: 520, align: 'left', anim: 'fade', style: { lineHeight: '1.9', letterSpacing: '.04em' } });
  S.mono('配音：Kokoro（sherpa-onnx 离线合成） · 图标：Twemoji CC-BY 4.0 / Tabler MIT · 字体：思源黑体 OFL', { at: 0, d: 0.6, x: 960, y: 930, size: 15, style: { letterSpacing: '.1em' } });
});
