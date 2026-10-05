// 进化心理学 v2 渲染引擎：three.js 粒子 + 辉光后期 + DOM 排版层，按时间 t 确定性渲染。
import * as THREE from 'three';

export const W = 1920, H = 1080, FOV = 35;
export const DIST = (H / 2) / Math.tan(FOV * Math.PI / 360);   // z=0 平面上 1 单位 = 1 像素
export const N = 48000;

// ------------------------------------------------------------------ 工具
export const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const lerp = (a, b, t) => a + (b - a) * t;
export const E = {
  out: p => 1 - Math.pow(1 - p, 3),
  inOut: p => p < .5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2,
  in: p => p * p * p,
  sine: p => -(Math.cos(Math.PI * p) - 1) / 2,
};
export function rng(seed) {
  let s = (seed * 2654435761) >>> 0 || 1;
  return () => { s ^= s << 13; s >>>= 0; s ^= s >>> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; };
}
function hashStr(str) { let h = 2166136261; for (const c of str) { h ^= c.charCodeAt(0); h = Math.imul(h, 16777619); } return h >>> 0; }

export const C = {
  champ: [1.0, 0.84, 0.62], warm: [1.0, 0.64, 0.34], orange: [1.0, 0.46, 0.16], white: [0.86, 0.9, 1.0],
  teal: [0.35, 0.95, 0.85], red: [1.0, 0.3, 0.24], blue: [0.55, 0.7, 1.0], green: [0.5, 1.0, 0.6],
};

// ------------------------------------------------------------------ 渲染器
const canvas = document.getElementById('gl');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: false, preserveDrawingBuffer: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(1);
renderer.setSize(W, H, false);
renderer.setClearColor(0x000000, 1);
const scene3 = new THREE.Scene();
export const camera = new THREE.PerspectiveCamera(FOV, W / H, 1, 30000);
camera.position.set(0, 0, DIST);

// 自制轻量辉光：1/4 与 1/8 分辨率高斯模糊后叠加
const mkRT = (w, h) => new THREE.WebGLRenderTarget(w, h, { type: THREE.UnsignedByteType, minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter, depthBuffer: false });
const rtScene = new THREE.WebGLRenderTarget(W, H, { type: THREE.UnsignedByteType, depthBuffer: false });
const rtA = mkRT(W / 4, H / 4), rtB = mkRT(W / 4, H / 4), rtC = mkRT(W / 8, H / 8), rtD = mkRT(W / 8, H / 8);
const VS = `varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position.xy, 0., 1.); }`;
const quadGeo = new THREE.PlaneGeometry(2, 2);
const quadScene = new THREE.Scene(), quadCam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
const quad = new THREE.Mesh(quadGeo); quad.frustumCulled = false; quadScene.add(quad);
function runQuad(mat, target) { quad.material = mat; renderer.setRenderTarget(target); renderer.render(quadScene, quadCam); }
const downMat = new THREE.ShaderMaterial({ uniforms: { t: { value: null }, px: { value: new THREE.Vector2(1 / W, 1 / H) }, thr: { value: 0.12 } }, vertexShader: VS, depthTest: false, depthWrite: false,
  fragmentShader: `uniform sampler2D t; uniform vec2 px; uniform float thr; varying vec2 vUv;
    void main(){ vec3 c = vec3(0.); for (int i = 0; i < 4; i++) { vec2 o = vec2(float(i - (i/2)*2) - .5, float(i/2) - .5) * px * 2.; c += texture2D(t, vUv + o).rgb; } c *= .25;
      float l = max(c.r, max(c.g, c.b)); gl_FragColor = vec4(c * smoothstep(thr, thr + .35, l), 1.); }` });
const blurMat = new THREE.ShaderMaterial({ uniforms: { t: { value: null }, dir: { value: new THREE.Vector2() } }, vertexShader: VS, depthTest: false, depthWrite: false,
  fragmentShader: `uniform sampler2D t; uniform vec2 dir; varying vec2 vUv;
    void main(){ vec3 c = texture2D(t, vUv).rgb * .227;
      c += (texture2D(t, vUv + dir * 1.384).rgb + texture2D(t, vUv - dir * 1.384).rgb) * .316;
      c += (texture2D(t, vUv + dir * 3.230).rgb + texture2D(t, vUv - dir * 3.230).rgb) * .070;
      gl_FragColor = vec4(c, 1.); }` });
const copyMat = new THREE.ShaderMaterial({ uniforms: { t: { value: null } }, vertexShader: VS, depthTest: false, depthWrite: false,
  fragmentShader: `uniform sampler2D t; varying vec2 vUv; void main(){ gl_FragColor = texture2D(t, vUv); }` });
const finalMat = new THREE.ShaderMaterial({
  uniforms: { t: { value: rtScene.texture }, b1: { value: rtA.texture }, b2: { value: rtC.texture }, k1: { value: 0.9 }, k2: { value: 0.9 },
    uTime: { value: 0 }, uCA: { value: 0.0 }, uFade: { value: 1 }, uGrain: { value: 0.006 }, uFlash: { value: 0 } },
  vertexShader: VS, depthTest: false, depthWrite: false,
  fragmentShader: `
    uniform sampler2D t, b1, b2; uniform float k1, k2, uTime, uCA, uFade, uGrain, uFlash; varying vec2 vUv;
    float hash(vec2 p){ return fract(sin(dot(p, vec2(12.9898,78.233))) * 43758.5453); }
    void main(){
      vec2 d = vUv - .5; float r2 = dot(d,d);
      vec2 off = d * uCA * r2 * 4.0;
      vec3 c = vec3(texture2D(t, vUv + off).r, texture2D(t, vUv).g, texture2D(t, vUv - off).b);
      c += texture2D(b1, vUv).rgb * k1 + texture2D(b2, vUv).rgb * k2;
      c *= smoothstep(1.05, 0.25, length(d * vec2(1.0, 0.85)) * 1.25) * 0.35 + 0.65;
      c = c / (1.0 + max(0.0, max(c.r, max(c.g, c.b)) - 1.0) * 0.5);
      c += (hash(vUv * vec2(1920., 1080.)) - .5) * uGrain;
      c = max(c * uFade + uFlash, 0.0);
      c = mix(c * 12.92, 1.055 * pow(c, vec3(1.0/2.4)) - 0.055, step(0.0031308, c));
      gl_FragColor = vec4(c, 1.);
    }`,
});
const finalPass = { uniforms: finalMat.uniforms };
function renderAll() {
  renderer.setRenderTarget(rtScene); renderer.clear(); renderer.render(scene3, camera);
  downMat.uniforms.t.value = rtScene.texture; runQuad(downMat, rtA);
  blurMat.uniforms.t.value = rtA.texture; blurMat.uniforms.dir.value.set(4 / W, 0); runQuad(blurMat, rtB);
  blurMat.uniforms.t.value = rtB.texture; blurMat.uniforms.dir.value.set(0, 4 / H); runQuad(blurMat, rtA);
  copyMat.uniforms.t.value = rtA.texture; runQuad(copyMat, rtC);
  blurMat.uniforms.t.value = rtC.texture; blurMat.uniforms.dir.value.set(8 / W, 0); runQuad(blurMat, rtD);
  blurMat.uniforms.t.value = rtD.texture; blurMat.uniforms.dir.value.set(0, 8 / H); runQuad(blurMat, rtC);
  blurMat.uniforms.t.value = rtC.texture; blurMat.uniforms.dir.value.set(16 / W, 0); runQuad(blurMat, rtD);
  blurMat.uniforms.t.value = rtD.texture; blurMat.uniforms.dir.value.set(0, 16 / H); runQuad(blurMat, rtC);
  runQuad(finalMat, null);
}

// ------------------------------------------------------------------ 粒子群
const PERM = (() => { const r = rng(99), a = new Uint32Array(N); for (let i = 0; i < N; i++) a[i] = i; for (let i = N - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; })();
const DUST = (() => {
  const r = rng(7), p = new Float32Array(N * 3), c = new Float32Array(N * 3), s = new Float32Array(N);
  for (let i = 0; i < N; i++) {
    p[i * 3] = (r() - .5) * 3600; p[i * 3 + 1] = (r() - .5) * 2100; p[i * 3 + 2] = -2400 + r() * 2600;
    const b = 0.025 + r() * 0.06 * (r() < .08 ? 4 : 1);
    c[i * 3] = b * 0.95; c[i * 3 + 1] = b * 0.9; c[i * 3 + 2] = b * 0.85; s[i] = 1.2 + r() * 1.4;
  }
  return { p, c, s };
})();

const swarmGeo = new THREE.BufferGeometry();
const A = {};
for (const [k, n] of [['aFrom', 3], ['aTo', 3], ['aCF', 3], ['aCT', 3], ['aSF', 1], ['aST', 1], ['aRand', 4]]) {
  A[k] = new THREE.BufferAttribute(new Float32Array(N * n), n); A[k].setUsage(THREE.DynamicDrawUsage); swarmGeo.setAttribute(k, A[k]);
}
swarmGeo.setAttribute('position', A.aTo);
{ const r = rng(3); for (let i = 0; i < N * 4; i++) A.aRand.array[i] = r(); }
const swarmMat = new THREE.ShaderMaterial({
  uniforms: { uMix: { value: 1 }, uTime: { value: 0 }, uStagger: { value: .35 }, uScatter: { value: 260 }, uSwirl: { value: 1.2 },
    uJitter: { value: 0.12 }, uDist: { value: DIST }, uBright: { value: 1 }, uSpin: { value: 0 }, uSpinZ: { value: 0 }, uPulse: { value: 0 }, uRadial: { value: 0 }, uCenter: { value: new THREE.Vector3() } },
  vertexShader: `
    attribute vec3 aFrom, aTo, aCF, aCT; attribute float aSF, aST; attribute vec4 aRand;
    uniform float uMix, uTime, uStagger, uScatter, uSwirl, uJitter, uDist, uBright, uSpin, uSpinZ, uPulse, uRadial; uniform vec3 uCenter;
    varying vec3 vCol;
    void main(){
      float m = clamp((uMix - aRand.x * uStagger) / (1.0 - uStagger), 0.0, 1.0);
      m = m < .5 ? 4.0*m*m*m : 1.0 - pow(-2.0*m + 2.0, 3.0) / 2.0;
      vec3 p = mix(aFrom, aTo, m);
      float travel = clamp(length(aTo - aFrom) / 380.0, 0.0, 1.0);
      float s = sin(m * 3.14159265) * travel;
      p += (aRand.yzw - .5) * uScatter * s;
      vec3 rd = mix(aFrom, aTo, 0.5) - uCenter; p += normalize(rd + vec3(0.001)) * uRadial * s * (0.6 + aRand.x * 0.8);
      float ang = s * uSwirl * (aRand.y - .5) * 2.0;
      vec2 q = p.xy - uCenter.xy; p.xy = uCenter.xy + mat2(cos(ang), -sin(ang), sin(ang), cos(ang)) * q;
      float sp = uSpin; vec3 pc = p - uCenter;
      p.xz = uCenter.xz + mat2(cos(sp), -sin(sp), sin(sp), cos(sp)) * pc.xz;
      vec2 pz2 = p.xy - uCenter.xy; p.xy = uCenter.xy + mat2(cos(uSpinZ), -sin(uSpinZ), sin(uSpinZ), cos(uSpinZ)) * pz2;
      p += vec3(sin(uTime * 1.3 + aRand.y * 60.), cos(uTime * 1.1 + aRand.z * 60.), sin(uTime * .9 + aRand.w * 60.)) * uJitter * (0.5 + aRand.w);
      vec4 mv = modelViewMatrix * vec4(p, 1.0);
      gl_PointSize = max(0.0, mix(aSF, aST, m)) * uDist / max(1.0, -mv.z) * (1.0 + 0.16 * uPulse);
      float tw = 0.9 + 0.1 * sin(uTime * (0.4 + aRand.z * 0.8) + aRand.x * 80.0);
      vCol = mix(aCF, aCT, m) * tw * uBright * (1.0 + 0.5 * uPulse);
      gl_Position = projectionMatrix * mv;
    }`,
  fragmentShader: `
    varying vec3 vCol;
    void main(){ vec2 d = gl_PointCoord - .5; float r = length(d); float a = smoothstep(.5, .0, r); a = a * a * a * 1.6;
      gl_FragColor = vec4(vCol * a, 1.0); }`,
  blending: THREE.AdditiveBlending, depthWrite: false, depthTest: false, transparent: true,
});
const swarm = new THREE.Points(swarmGeo, swarmMat);
swarm.frustumCulled = false;
scene3.add(swarm);

// 构建一个阵型：points=[x,y,z,...] colors=[r,g,b,...] sizes=[...]，其余粒子变成背景尘埃
export function formation(pts, cols, sizes) {
  const M = Math.min(N, sizes.length);
  const pos = new Float32Array(DUST.p), col = new Float32Array(DUST.c), size = new Float32Array(DUST.s);
  for (let j = 0; j < M; j++) {
    const i = PERM[j];
    pos[i * 3] = pts[j * 3]; pos[i * 3 + 1] = pts[j * 3 + 1]; pos[i * 3 + 2] = pts[j * 3 + 2];
    col[i * 3] = cols[j * 3]; col[i * 3 + 1] = cols[j * 3 + 1]; col[i * 3 + 2] = cols[j * 3 + 2];
    size[i] = sizes[j];
  }
  return { pos, col, size };
}

// 点集构建器
export class PB {
  constructor(seed = 1) { this.p = []; this.c = []; this.s = []; this.r = rng(seed); }
  add(x, y, z, col, size, bright = 1) {
    const r = this.r, b = bright * 0.85 * (0.35 + 0.65 * r()) * (r() < 0.035 ? 2.6 : 1);
    this.p.push(x, y, z); this.c.push(col[0] * b, col[1] * b, col[2] * b); this.s.push(size * (0.7 + 0.6 * r()));
  }
  get n() { return this.s.length; }
  build() { return formation(this.p, this.c, this.s); }
}

// 从 2D 画布采样
const scratch = document.createElement('canvas');
const sctx = scratch.getContext('2d', { willReadFrequently: true });
function sampleCanvas(drawFn, w, h, count, place, seed) {
  scratch.width = w; scratch.height = h;
  sctx.clearRect(0, 0, w, h);
  drawFn(sctx, w, h);
  const data = sctx.getImageData(0, 0, w, h).data;
  const filled = [];
  for (let y = 0; y < h; y += 1) for (let x = 0; x < w; x += 1) { const a = data[(y * w + x) * 4 + 3]; if (a > 110) filled.push(x, y); }
  const r = rng(seed), K = filled.length / 2;
  const out = [];
  if (!K) return out;
  for (let j = 0; j < count; j++) { const k = Math.floor(r() * K); out.push(place(filled[k * 2] + r() - .5, filled[k * 2 + 1] + r() - .5, data, filled, k)); }
  return out;
}

// 文字粒子
export function textPoints(pb, str, o = {}) {
  const size = o.size || 220, font = o.font || `900 ${size}px SHS`, x = o.x || 0, y = o.y || 0, z = o.z || 0;
  sctx.font = font;
  const lines = str.split('\n');
  const tw = Math.max(...lines.map(l => sctx.measureText(l).width)) + size * 0.4, th = size * 1.25 * lines.length + size * 0.3;
  const w = Math.ceil(tw), h = Math.ceil(th);
  const count = o.count || 22000, col = o.color || C.champ, ps = o.ps || 2.4, depth = o.depth ?? 24;
  const res = sampleCanvas((ctx) => {
    ctx.font = font; ctx.fillStyle = '#fff'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    if (o.ls) ctx.letterSpacing = o.ls;
    lines.forEach((l, i) => ctx.fillText(l, w / 2, h / 2 + (i - (lines.length - 1) / 2) * size * 1.25));
  }, w, h, count, (px, py) => [px - w / 2 + x, -(py - h / 2) + y], hashStr(str) + 11);
  const r = pb.r;
  for (const [px, py] of res) pb.add(px, py, z + (r() - .5) * depth, col, ps, o.bright ?? 1);
  return pb;
}

// 图片/图标粒子（需先 preload）
const IMG = {};
export function preloadImage(url) {
  if (IMG[url]) return IMG[url].p;
  const im = new Image(); im.crossOrigin = 'anonymous';
  IMG[url] = { im, p: new Promise((res, rej) => { im.onload = () => res(im); im.onerror = rej; }) };
  im.src = url;
  return IMG[url].p;
}
export function imagePoints(pb, url, o = {}) {
  // 采样图片：一部分点落在边缘/细节上（线稿感），其余点均匀填充
  const im = IMG[url].im, size = o.size || 400, x = o.x || 0, y = o.y || 0, z = o.z || 0;
  const count = o.count || 14000, ps = o.ps || 2.4, depth = o.depth ?? 30, edges = o.edges ?? 0.6;
  scratch.width = size; scratch.height = size;
  sctx.clearRect(0, 0, size, size); sctx.drawImage(im, 0, 0, size, size);
  const d = sctx.getImageData(0, 0, size, size).data;
  const L = new Float32Array(size * size);
  for (let i = 0; i < size * size; i++) L[i] = d[i * 4 + 3] < 110 ? -1 : (0.3 * d[i * 4] + 0.59 * d[i * 4 + 1] + 0.11 * d[i * 4 + 2]) / 255;
  const fill = [], edge = [];
  for (let yy = 1; yy < size - 1; yy++) for (let xx = 1; xx < size - 1; xx++) {
    const i = yy * size + xx; if (L[i] < 0) continue;
    fill.push(i);
    const a = L[i - 1], b = L[i + 1], c = L[i - size], e = L[i + size];
    const g = (a < 0 || b < 0 || c < 0 || e < 0) ? 1 : Math.abs(a - b) + Math.abs(c - e);
    if (g > 0.12) edge.push(i);
  }
  if (!fill.length) return pb;
  const r = rng(hashStr(url) + size);
  for (let j = 0; j < count; j++) {
    const isE = edge.length && r() < edges, arr = isE ? edge : fill, i = arr[Math.floor(r() * arr.length)];
    const px = i % size + r() - .5, py = Math.floor(i / size) + r() - .5;
    let col = o.color || C.champ;
    if (o.keep) { const cr = d[i * 4] / 255, cg = d[i * 4 + 1] / 255, cb = d[i * 4 + 2] / 255, l = 0.3 * cr + 0.59 * cg + 0.11 * cb, k = o.keep; col = [lerp(col[0] * l * 1.6, cr, k), lerp(col[1] * l * 1.6, cg, k), lerp(col[2] * l * 1.6, cb, k)]; }
    pb.add(px - size / 2 + x, -(py - size / 2) + y, z + (pb.r() - .5) * depth, col, isE ? ps : ps * 0.85, (o.bright ?? 1) * (isE ? 1.25 : 0.55));
  }
  return pb;
}

// 几何阵型
export function spherePoints(pb, o = {}) {
  const { x = 0, y = 0, z = 0, r: R = 300, count = 15000, color = C.champ, ps = 2.2, shell = 0.85 } = o;
  const r = pb.r;
  for (let i = 0; i < count; i++) {
    const u = r() * 2 - 1, th = r() * Math.PI * 2, s = Math.sqrt(1 - u * u), rr = R * (shell + (1 - shell) * Math.cbrt(r()));
    pb.add(x + rr * s * Math.cos(th), y + rr * u, z + rr * s * Math.sin(th), color, ps);
  }
  return pb;
}
export function ringPoints(pb, o = {}) {
  const { x = 0, y = 0, z = 0, r: R = 300, w = 18, count = 8000, color = C.teal, ps = 2.2, tilt = 0 } = o;
  const r = pb.r;
  for (let i = 0; i < count; i++) {
    const a = r() * Math.PI * 2, rr = R + (r() - .5) * w * (r() < .2 ? 3 : 1);
    const px = rr * Math.cos(a), py = rr * Math.sin(a);
    pb.add(x + px, y + py * Math.cos(tilt), z + py * Math.sin(tilt) + (r() - .5) * 8, color, ps);
  }
  return pb;
}
export function galaxyPoints(pb, o = {}) {
  const { x = 0, y = 0, z = 0, r: R = 600, count = 30000, arms = 3, color = C.champ, ps = 2.0, tilt = 1.15, twist = 3.2 } = o;
  const r = pb.r;
  for (let i = 0; i < count; i++) {
    const d = Math.pow(r(), 0.7), arm = Math.floor(r() * arms), a = arm / arms * Math.PI * 2 + d * twist + (r() - .5) * 0.5 * (1.2 - d);
    const rr = d * R, px = rr * Math.cos(a), pz = rr * Math.sin(a), py = (r() - .5) * 40 * (1.2 - d);
    const c = d < 0.15 ? C.white : (r() < 0.25 ? C.warm : color);
    pb.add(x + px, y + py * Math.cos(tilt) - pz * Math.sin(tilt), z + py * Math.sin(tilt) + pz * Math.cos(tilt), c, ps, 1.2 - d * 0.6);
  }
  return pb;
}
export function brainPoints(pb, o = {}) {
  // 侧视大脑：前后长、上下矮，两半球 + 脑回褶皱 + 小脑 + 脑干
  const { x = 0, y = 0, z = 0, s = 300, count = 24000, color = C.champ, ps = 2.0, rotY = -1.25 } = o;
  const r = pb.r, cy = Math.cos(rotY), sy = Math.sin(rotY);
  for (let i = 0; i < count; i++) {
    let px, py, pz, c = color, br = 1;
    const k = r();
    if (k < 0.84) {
      const u = r() * 2 - 1, th = r() * Math.PI * 2, q = Math.sqrt(1 - u * u);
      const dx = q * Math.cos(th), dy = u, dz = q * Math.sin(th);
      const hemi = dx >= 0 ? 1 : -1;
      const fold = 1 + 0.045 * Math.sin(16 * dy + 7 * Math.sin(8 * dz) + hemi) + 0.035 * Math.sin(19 * dz + 6 * dy);
      const sh = r() < 0.9 ? 1 : 0.75 + 0.25 * r();
      px = (dx * 0.58 + hemi * 0.05) * fold * sh;
      py = dy * 0.66 * fold * sh * (dy < 0 ? 0.72 : 1) + 0.06;
      pz = dz * 1.0 * fold * sh;
      br = Math.abs(dx) < 0.05 ? 0.35 : 1;
    } else if (k < 0.95) {            // 小脑
      const a = r() * Math.PI * 2, b = r() * 2 - 1, w = Math.sqrt(1 - b * b);
      const f = 1 + 0.06 * Math.sin(30 * b);
      px = 0.42 * w * Math.cos(a) * f; py = -0.42 + 0.17 * b * f; pz = -0.62 + 0.25 * w * Math.sin(a) * f; c = C.warm;
    } else {                          // 脑干
      const t = r(), a = r() * Math.PI * 2;
      px = 0.09 * Math.cos(a); py = -0.3 - t * 0.45; pz = -0.28 - t * 0.08 + 0.09 * Math.sin(a); c = C.warm; br = 0.7;
    }
    const X = px * cy + pz * sy, Z = -px * sy + pz * cy;
    pb.add(x + X * s, y + py * s, z + Z * s, c, ps, br);
  }
  return pb;
}
export function helixPoints(pb, o = {}) {
  const { x = 0, y = 0, z = 0, len = 1400, r: R = 140, turns = 4, count = 16000, ps = 2.2 } = o;
  const r = pb.r;
  for (let i = 0; i < count; i++) {
    const t = r(), a = t * turns * Math.PI * 2, kind = r();
    const px = (t - .5) * len;
    if (kind < 0.8) { const ph = kind < 0.4 ? 0 : Math.PI; pb.add(x + px, y + R * Math.cos(a + ph) + (r() - .5) * 10, z + R * Math.sin(a + ph), kind < 0.4 ? C.champ : C.warm, ps); }
    else { const k = Math.round(t * turns * 10) / (turns * 10), aa = k * turns * Math.PI * 2, f = r() * 2 - 1; pb.add(x + (k - .5) * len, y + R * Math.cos(aa) * f, z + R * Math.sin(aa) * f, C.white, ps * 0.8, 0.6); }
  }
  return pb;
}
export function linePoints(pb, pts2, o = {}) {   // 沿折线均匀撒点
  const { count = 3000, color = C.champ, ps = 2, w = 4, z = 0 } = o, r = pb.r;
  const seg = []; let L = 0;
  for (let i = 0; i < pts2.length - 1; i++) { const [a, b] = [pts2[i], pts2[i + 1]]; const l = Math.hypot(b[0] - a[0], b[1] - a[1]); seg.push([a, b, l]); L += l; }
  for (let j = 0; j < count; j++) {
    let d = r() * L, k = 0; while (k < seg.length - 1 && d > seg[k][2]) { d -= seg[k][2]; k++; }
    const [a, b, l] = seg[k], t = l ? d / l : 0;
    pb.add(lerp(a[0], b[0], t) + (r() - .5) * w, lerp(a[1], b[1], t) + (r() - .5) * w, z + (r() - .5) * w, color, ps);
  }
  return pb;
}
export function boxPoints(pb, o = {}) {   // 粒子填充的立方柱
  const { x = 0, y = 0, z = 0, w = 80, h = 300, d = 80, count = 4000, color = C.champ, ps = 2 } = o, r = pb.r;
  for (let i = 0; i < count; i++) {
    const edge = r() < 0.35;
    let px = (r() - .5) * w, py = r() * h, pz = (r() - .5) * d;
    if (edge) { if (r() < .5) px = Math.sign(px) * w / 2; else pz = Math.sign(pz) * d / 2; }
    pb.add(x + px, y + py, z + pz, py > h - 6 ? C.white : color, ps, edge ? 1.1 : 0.55);
  }
  return pb;
}
export const dust = () => formation([], [], []);

// ------------------------------------------------------------------ 辅助 3D 对象
export function glowSprites(points, o = {}) {      // 发光节点 [{x,y,z,size,color}]
  const g = new THREE.BufferGeometry();
  const P = new Float32Array(points.length * 3), Cc = new Float32Array(points.length * 3), S = new Float32Array(points.length);
  points.forEach((p, i) => { P.set([p.x, p.y, p.z || 0], i * 3); const c = p.color || C.champ; Cc.set(c, i * 3); S[i] = p.size || 40; });
  g.setAttribute('position', new THREE.BufferAttribute(P, 3)); g.setAttribute('color', new THREE.BufferAttribute(Cc, 3)); g.setAttribute('aS', new THREE.BufferAttribute(S, 1));
  const m = new THREE.ShaderMaterial({
    uniforms: { uOp: { value: 1 }, uDist: { value: DIST }, uTime: { value: 0 } },
    vertexShader: `attribute float aS; attribute vec3 color; varying vec3 vC; uniform float uDist, uTime;
      void main(){ vC = color; vec4 mv = modelViewMatrix * vec4(position,1.); gl_PointSize = aS * uDist / -mv.z * (0.94 + 0.06*sin(uTime*3. + position.x)); gl_Position = projectionMatrix * mv; }`,
    fragmentShader: `varying vec3 vC; uniform float uOp; void main(){ float r = length(gl_PointCoord - .5) * 2.;
      float core = smoothstep(.22, .0, r); float halo = pow(max(0., 1. - r), 3.) * .55;
      gl_FragColor = vec4((vC * halo + vec3(1.) * core * .9 + vC * core) * uOp, 1.); }`,
    blending: THREE.AdditiveBlending, depthWrite: false, depthTest: false, transparent: true,
  });
  const pts = new THREE.Points(g, m); pts.frustumCulled = false;
  pts.userData.setOpacity = v => { m.uniforms.uOp.value = v; };
  pts.userData.tick = t => { m.uniforms.uTime.value = t; };
  return pts;
}
export function lines(segs, o = {}) {      // segs: [[x1,y1,z1,x2,y2,z2], ...]
  const g = new THREE.BufferGeometry();
  const P = new Float32Array(segs.length * 6); segs.forEach((s, i) => P.set(s.length === 4 ? [s[0], s[1], 0, s[2], s[3], 0] : s, i * 6));
  g.setAttribute('position', new THREE.BufferAttribute(P, 3));
  const col = new THREE.Color(...(o.color || C.champ));
  const m = new THREE.LineBasicMaterial({ color: col, transparent: true, opacity: o.opacity ?? 0.5, blending: THREE.AdditiveBlending, depthWrite: false, depthTest: false });
  const L = new THREE.LineSegments(g, m); L.frustumCulled = false;
  const base = o.opacity ?? 0.5;
  L.userData.setOpacity = v => { m.opacity = base * v; };
  L.userData.total = segs.length;
  return L;
}
export function polyline(pts, o = {}) {    // 可逐步绘制的折线
  const g = new THREE.BufferGeometry();
  const P = new Float32Array(pts.length * 3); pts.forEach((p, i) => P.set([p[0], p[1], p[2] || 0], i * 3));
  g.setAttribute('position', new THREE.BufferAttribute(P, 3));
  const m = new THREE.LineBasicMaterial({ color: new THREE.Color(...(o.color || C.champ)), transparent: true, opacity: o.opacity ?? 0.9, blending: THREE.AdditiveBlending, depthWrite: false, depthTest: false });
  const L = new THREE.Line(g, m); L.frustumCulled = false;
  const base = o.opacity ?? 0.9;
  L.userData.setOpacity = v => { m.opacity = base * v; };
  L.userData.draw = p => g.setDrawRange(0, Math.max(0, Math.floor(p * pts.length)));
  L.userData.pts = pts;
  return L;
}
export function grid(o = {}) {          // 透视地面网格
  const { size = 3000, step = 100, y = -300, color = C.white, opacity = 0.18 } = o, segs = [];
  for (let v = -size / 2; v <= size / 2; v += step) { segs.push([v, y, -size / 2, v, y, size / 2]); segs.push([-size / 2, y, v, size / 2, y, v]); }
  return lines(segs, { color, opacity });
}

// 光束穿梭
const warpGeo = new THREE.BufferGeometry();
{
  const K = 2400, P = new Float32Array(K * 2 * 3), R = new Float32Array(K * 2 * 4), r = rng(5);
  for (let i = 0; i < K; i++) { const a = r(), b = r(), c = r(), d = r(); for (let e = 0; e < 2; e++) { R.set([a, b, c, e], (i * 2 + e) * 4); } }
  warpGeo.setAttribute('position', new THREE.BufferAttribute(P, 3));
  warpGeo.setAttribute('aR', new THREE.BufferAttribute(R, 4));
}
const warpMat = new THREE.ShaderMaterial({
  uniforms: { uT: { value: 0 }, uAmt: { value: 0 }, uCol: { value: new THREE.Vector3(1, .85, .7) } },
  vertexShader: `attribute vec4 aR; uniform float uT, uAmt; varying float vA;
    void main(){ float ang = aR.x * 6.2831853; float sp = .35 + aR.y * .9; float ph = fract(aR.z + uT * sp * .6);
      float r0 = 40. + ph * ph * 2600.; float len = (60. + 900. * ph * ph) * uAmt;
      float r = r0 + len * aR.w; vec3 p = vec3(cos(ang) * r, sin(ang) * r * .9, 0.);
      vA = uAmt * (aR.w > .5 ? .0 : 1.) * smoothstep(0., .25, ph) * (0.3 + aR.y * .7);
      gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.); }`,
  fragmentShader: `uniform vec3 uCol; varying float vA; void main(){ gl_FragColor = vec4(uCol * vA, 1.); }`,
  blending: THREE.AdditiveBlending, depthWrite: false, depthTest: false, transparent: true,
});
const warp = new THREE.LineSegments(warpGeo, warpMat); warp.frustumCulled = false;
scene3.add(warp);

// 冲击光环：每次低频冲击时扩散的一圈粒子
const ringGeo = new THREE.BufferGeometry();
{ const K = 5000, P = new Float32Array(K * 3), r = rng(11); for (let i = 0; i < K; i++) { const a = r() * Math.PI * 2, w = (r() - .5) * 0.06; P.set([Math.cos(a) * (1 + w), Math.sin(a) * (1 + w) * 0.92, (r() - .5) * 40], i * 3); } ringGeo.setAttribute('position', new THREE.BufferAttribute(P, 3)); }
const ringMat = new THREE.ShaderMaterial({ uniforms: { uR: { value: 0 }, uA: { value: 0 }, uDist: { value: DIST } },
  vertexShader: `uniform float uR, uDist; void main(){ vec4 mv = modelViewMatrix * vec4(position.xy * uR, position.z, 1.); gl_PointSize = 2.6 * uDist / -mv.z; gl_Position = projectionMatrix * mv; }`,
  fragmentShader: `uniform float uA; void main(){ float r = length(gl_PointCoord - .5); gl_FragColor = vec4(vec3(1., .82, .6) * smoothstep(.5, 0., r) * uA, 1.); }`,
  blending: THREE.AdditiveBlending, depthWrite: false, depthTest: false, transparent: true });
const shock = new THREE.Points(ringGeo, ringMat); shock.frustumCulled = false; scene3.add(shock);

let KICKS = [], IMPACTS = [], UNLOCKS = [], LABELS = [], HUDWIN = [0, 0];
function lastBefore(arr, t, key = x => x) { let lo = 0, hi = arr.length - 1, k = -1; while (lo <= hi) { const m = (lo + hi) >> 1; if (key(arr[m]) <= t) { k = m; lo = m + 1; } else hi = m - 1; } return k; }
function kickEnv(t) { let e = 0; const k = lastBefore(KICKS, t, x => x[0]); for (let j = k; j >= 0 && j > k - 3; j--) { const d = t - KICKS[j][0]; e = Math.max(e, KICKS[j][1] * Math.exp(-d * 7)); } return e; }

// 贯穿全片的“出厂设置”解锁进度
const hud = document.getElementById('hud');
hud.innerHTML = `<div class="fs"><div class="fs-t">FACTORY SETTINGS · <b>出厂设置</b></div><div class="fs-row">${[0, 1, 2, 3].map(i => `<div class="fs-seg"><div class="fs-bar"><i></i></div><div class="fs-lab"><span class="n">0${i + 1}</span> <span class="l"></span></div></div>`).join('')}</div></div>`;
const fsBox = hud.querySelector('.fs'), fsSegs = [...hud.querySelectorAll('.fs-seg')];
function updateHud(t, si) {
  const a = clamp((t - HUDWIN[0]) / 0.8) * clamp((HUDWIN[1] - t) / 0.8);
  fsBox.style.opacity = a;
  if (a <= 0) return;
  fsSegs.forEach((seg, i) => {
    const u = UNLOCKS[i], on = u !== undefined && t >= u, q = on ? clamp((t - u) / 0.6) : 0;
    const scanning = !on && LABELS[i] && t >= LABELS[i].start && t < (u ?? 1e9);
    const fill = seg.querySelector('i'), lab = seg.querySelector('.l');
    fill.style.width = on ? `${100 * E.out(q)}%` : scanning ? `${8 + 6 * Math.sin(t * 6)}%` : '0%';
    fill.style.opacity = on ? 1 : 0.6;
    seg.classList.toggle('on', on);
    seg.style.opacity = on ? 1 : scanning ? 0.75 + 0.25 * Math.sin(t * 5) : 0.35;
    lab.textContent = on || scanning ? LABELS[i].label : '';
    seg.style.transform = on && q < 1 ? `scale(${1 + 0.12 * Math.sin(Math.PI * q)})` : '';
  });
}

// ------------------------------------------------------------------ 场景 DSL
const ui = document.getElementById('ui');
const prog = document.createElement('div'); prog.className = 'prog'; document.getElementById('stage').appendChild(prog);

class SceneCtx {
  constructor(idx, tl) {
    this.idx = idx; this.tl = tl; this.ls = tl.ls; this.ld = tl.ld; this.dur = tl.dur; this.start = tl.start;
    this.layer = document.createElement('div'); this.layer.className = 'layer'; this.layer.style.display = 'none'; ui.appendChild(this.layer);
    this.group = new THREE.Group(); this.group.visible = false; scene3.add(this.group);
    this.els = []; this.cardEls = []; this.objs = []; this.forms = []; this.ups = []; this.camKeys = null; this.warps = []; this.flashes = []; this.spins = [];
  }
  T(at = 0, f = 0, d = 0) { if (!this.ls.length) return d; if (at >= this.ls.length) return this.dur + d; return this.ls[at] + f * this.ld[at] + d; }
  _time(o) { return this.T(o.at ?? 0, o.f ?? 0, o.d ?? 0); }
  _out(o) { return o.out === undefined ? null : (typeof o.out === 'number' ? this.T(o.out, o.of ?? 0, o.od ?? 0) : null); }
  // DOM 元素
  el(html, o = {}) {
    const e = document.createElement('div'); e.className = 'el ' + (o.cls || ''); e.innerHTML = html;
    if (o.size) e.style.fontSize = o.size + 'px';
    if (o.style) Object.assign(e.style, o.style);
    if (o.w) { e.style.width = o.w + 'px'; e.style.whiteSpace = 'normal'; }
    if (o.h) e.style.height = o.h + 'px';
    if (o.align) e.style.textAlign = o.align;
    this.layer.appendChild(e);
    const item = { e, o, t0: this._time(o), t1: this._out(o), x: o.x ?? 960, y: o.y ?? 540, anim: o.anim || 'blur', dur: o.dur ?? 0.9, al: o.al || 'c' };
    if (item.anim === 'type') { item.full = e.textContent; item.html = html; }
    this.els.push(item);
    return item;
  }
  text(html, o = {}) { return this.el(html, { cls: 't-body', size: 46, ...o }); }
  hero(html, o = {}) { return this.el(html, { cls: 't-hero', size: 120, ...o }); }
  cap(html, o = {}) { return this.el(html, { cls: 'cap', y: 70, anim: 'fade', ...o }); }
  label(html, o = {}) { return this.el(html, { cls: 't-label', size: 30, anim: 'fade', ...o }); }
  mono(html, o = {}) { return this.el(html, { cls: 't-mono', size: 22, anim: 'fade', ...o }); }
  num(html, o = {}) { return this.el(html, { cls: 't-num', size: 150, ...o }); }
  box(o = {}) {
    const inner = `${o.title ? `<div class="bt">${o.title}</div>` : ''}<div class="bx" style="position:absolute;left:28px;right:28px;top:${o.title ? 52 : 26}px;font-family:SHS;font-weight:300;font-size:${o.fs || 30}px;letter-spacing:.06em;line-height:1.6;white-space:normal;color:#ece9e2">${o.html || ''}</div>`;
    const it = this.el(inner, { cls: 'box ' + (o.kind || ''), w: o.w || 700, h: o.h || 200, anim: o.anim || 'box', ...o, style: { whiteSpace: 'normal', ...(o.style || {}) } });
    if (o.typing) { it.typeEl = it.e.querySelector('.bx'); it.typeFull = o.html; it.typeT = o.typing; }
    return it;
  }
  counter(o) { const it = this.el('0', { cls: 't-num', size: o.size || 150, ...o }); it.counter = o; return it; }
  // 粒子阵型
  form(make, o = {}) { this.forms.push({ t: this._time(o), make, dur: o.dur ?? 2.2, stagger: o.stagger ?? .35, scatter: o.scatter ?? 220, swirl: o.swirl ?? 1.0, key: `${this.idx}:${this.forms.length}`, bright: o.bright ?? 1, spin: o.spin ?? 0, spinZ: o.spinZ ?? 0, radial: o.radial ?? 0, center: o.center || [0, 0, 0] }); }
  // three 对象
  obj(o3, o = {}) { this.group.add(o3); this.objs.push({ o3, t0: this._time(o), t1: this._out(o), dur: o.dur ?? 0.9, draw: o.draw, drawDur: o.drawDur ?? 1.5 }); return o3; }
  cam(keys) { this.camKeys = keys; }
  warp(o = {}) { this.warps.push({ t: this._time(o), dur: o.dur ?? 1.6, amt: o.amt ?? 1 }); }
  flash(o = {}) { this.flashes.push({ t: this._time(o), amt: o.amt ?? 0.35 }); }
  update(fn) { this.ups.push(fn); }
  // 文字卡片：逐字浮现，结束前上浮淡出
  makeCards() {
    (this.tl.cards || []).forEach((c, i) => {
      if (c.none || !c.t || c.custom) return;
      let cls = '', html = '', n = 0;
      for (const ch of c.t) {
        if (ch === '[') { cls = 'hl'; continue; } if (ch === ']') { cls = ''; continue; }
        if (ch === '{') { cls = 'hl2'; continue; } if (ch === '}') { cls = ''; continue; }
        if (ch === '|') { html += '<br>'; continue; }
        html += `<span class="ch ${cls}">${ch === ' ' ? '&nbsp;' : ch}</span>`; n++;
      }
      const pos = c.pos || 'b';
      const e = document.createElement('div'); e.className = `card pos-${pos}`; e.innerHTML = html;
      e.style.fontSize = (c.size || (pos === 'c' ? 64 : pos === 't' ? 44 : 46)) + 'px';
      this.layer.appendChild(e);
      const y = c.y ?? (pos === 'c' ? 540 : pos === 't' ? 175 : 905);
      this.cardEls.push({ e, chars: [...e.querySelectorAll('.ch')], t0: this.ls[i], t1: this.ls[i] + this.ld[i], y, n, pos, last: i === this.tl.cards.length - 1 });
    });
  }
}

let SC = [], TL = null, FORMS = [];
const fcache = new Map();
function getForm(k) {
  const F = FORMS[k];
  if (!fcache.has(F.key)) { fcache.set(F.key, F.make()); if (fcache.size > 10) fcache.delete(fcache.keys().next().value); }
  return fcache.get(F.key);
}
const fromCache = new Map();
function fromState(k) {     // 第 k 次变形开始时的粒子状态
  if (k <= 0) return dust();
  const key = 'from' + k;
  if (fromCache.has(key)) return fromCache.get(key);
  const prev = FORMS[k - 1], q = clamp((FORMS[k].t - prev.t) / prev.dur);
  let res;
  if (q >= 1) res = getForm(k - 1);
  else {
    const a = fromState(k - 1), b = getForm(k - 1), e = E.inOut(q);
    res = { pos: new Float32Array(N * 3), col: new Float32Array(N * 3), size: new Float32Array(N) };
    for (let i = 0; i < N * 3; i++) { res.pos[i] = lerp(a.pos[i], b.pos[i], e); res.col[i] = lerp(a.col[i], b.col[i], e); }
    for (let i = 0; i < N; i++) res.size[i] = lerp(a.size[i], b.size[i], e);
  }
  fromCache.set(key, res); if (fromCache.size > 4) fromCache.delete(fromCache.keys().next().value);
  return res;
}
let loadedK = -2;
function setSwarm(t) {
  let k = -1;
  for (let i = 0; i < FORMS.length; i++) if (FORMS[i].t <= t) k = i; else break;
  if (k !== loadedK) {
    const a = k < 0 ? dust() : fromState(k), b = k < 0 ? dust() : getForm(k);
    A.aFrom.array.set(a.pos); A.aCF.array.set(a.col); A.aSF.array.set(a.size);
    A.aTo.array.set(b.pos); A.aCT.array.set(b.col); A.aST.array.set(b.size);
    for (const n of ['aFrom', 'aTo', 'aCF', 'aCT', 'aSF', 'aST']) A[n].needsUpdate = true;
    loadedK = k;
  }
  const F = FORMS[k];
  const u = swarmMat.uniforms;
  if (!F) { u.uMix.value = 1; return; }
  u.uMix.value = clamp((t - F.t) / F.dur);
  u.uRadial.value = F.radial || 0;
  u.uStagger.value = F.stagger; u.uScatter.value = F.scatter; u.uSwirl.value = F.swirl; u.uBright.value = F.bright;
  const P = FORMS[k - 1], prevAng = P ? P.spin * (F.t - P.t) : 0;
  u.uSpin.value = F.spin * (t - F.t) + prevAng * (1 - E.inOut(u.uMix.value));
  u.uCenter.value.set(...F.center);
  const prevZ = P ? P.spinZ * (F.t - P.t) : 0;
  u.uSpinZ.value = F.spinZ * (t - F.t) + prevZ * (1 - E.inOut(u.uMix.value));
}

function animEl(it, lt, sc) {
  const { e } = it;
  let a = 0, tx = 0, ty = 0, sc_ = 1, blur = 0, ls = null;
  if (lt >= it.t0) {
    const p = clamp((lt - it.t0) / it.dur), q = E.out(p);
    a = q;
    if (it.anim === 'blur') { blur = (1 - q) * 14; sc_ = 1.04 - 0.04 * q; }
    else if (it.anim === 'up') { ty = (1 - q) * 30; }
    else if (it.anim === 'zoom') { sc_ = 1.25 - 0.25 * q; blur = (1 - q) * 10; }
    else if (it.anim === 'box') { sc_ = 0.96 + 0.04 * q; a = p < 0.15 ? (Math.floor(p * 40) % 2 ? 0.3 : 0.9) : q; }
    else if (it.anim === 'type') { a = 1; const n = Math.floor(clamp((lt - it.t0) / Math.max(0.3, it.full.length * 0.06)) * it.full.length); e.textContent = it.full.slice(0, n) + (n < it.full.length ? '▍' : ''); }
    if (it.typeEl) { const full = it.typeFull, n = Math.floor(clamp((lt - it.t0 - 0.3) / it.typeT) * full.length); it.typeEl.textContent = full.slice(0, n) + (n < full.length && lt > it.t0 ? '▍' : ''); }
    if (it.counter) { const c = it.counter, p2 = E.out(clamp((lt - it.t0) / (c.cdur || 2))), v = Math.round(lerp(c.from || 0, c.to, p2)); e.innerHTML = (c.pre || '') + v.toLocaleString('en-US') + (c.post || ''); }
  }
  if (it.t1 !== null && lt >= it.t1) { const q = clamp((lt - it.t1) / 0.5); a *= 1 - q; blur += q * 10; }
  a *= clamp((sc.dur - lt) / 0.45);
  if (a <= 0.002) { e.style.opacity = 0; return; }
  if (it.o.world) { const v = new THREE.Vector3(...it.o.world).project(camera); it.x = (v.x + 1) / 2 * W + (it.o.dx || 0); it.y = (1 - v.y) / 2 * H + (it.o.dy || 0); }
  const w = e.offsetWidth, h = e.offsetHeight;
  const ox = it.al === 'l' ? 0 : it.al === 'r' ? w : w / 2;
  e.style.opacity = a;
  e.style.transform = `translate(${it.x - ox + tx}px, ${it.y - h / 2 + ty}px) scale(${sc_})`;
  e.style.filter = blur > 0.2 ? `blur(${blur.toFixed(1)}px)` : 'none';
}

const EZ_out = p => 1 - Math.pow(1 - p, 3);
function animCard(c, lt, sc) {
  const { e } = c;
  const endOut = c.last ? sc.dur : c.t1;
  if (lt < c.t0 - 0.02 || lt > endOut + 0.05) { if (e.style.opacity !== '0') e.style.opacity = 0; return; }
  const stg = Math.min(0.045, 0.75 / Math.max(1, c.n)), big = c.pos === 'c';
  c.chars.forEach((ch, i) => {
    const p = clamp((lt - c.t0 - i * stg) / (big ? 0.6 : 0.45)), q = EZ_out(p);
    ch.style.opacity = q;
    ch.style.transform = `translateY(${((1 - q) * (big ? 26 : 18)).toFixed(1)}px)` + (big ? ` scale(${(1.25 - 0.25 * q).toFixed(3)})` : '');
    ch.style.filter = q < 0.98 ? `blur(${((1 - q) * (big ? 12 : 8)).toFixed(1)}px)` : 'none';
  });
  const od = 0.34, q = clamp((lt - (endOut - od)) / od);
  e.style.opacity = 1 - q;
  const w = e.offsetWidth, h = e.offsetHeight;
  e.style.transform = `translate(${960 - w / 2}px, ${c.y - h / 2 - q * 16}px)`;
  e.style.filter = q > 0.01 ? `blur(${(q * 7).toFixed(1)}px)` : 'none';
}

function camAt(sc, lt) {
  const k = sc.camKeys;
  let pos = [0, 0, DIST], tgt = [0, 0, 0];
  if (k && k.keys) {
    // 多关键帧镜头：keys = [{ t: 本场景时间, pos, tgt }]
    const ks = k.keys; let i = 0; while (i < ks.length - 1 && ks[i + 1].t <= lt) i++;
    const a = ks[i], b = ks[Math.min(i + 1, ks.length - 1)];
    const p = b === a ? 0 : E.inOut(clamp((lt - a.t) / Math.max(0.01, b.t - a.t)));
    const ta = a.tgt || [0, 0, 0], tb = b.tgt || [0, 0, 0];
    return { pos: a.pos.map((v, j) => lerp(v, b.pos[j], p)), tgt: ta.map((v, j) => lerp(v, tb[j], p)) };
  }
  if (k) {
    const p = E.sine(clamp(lt / sc.dur));
    const a = k.from, b = k.to || k.from;
    pos = [lerp(a.pos[0], b.pos[0], p), lerp(a.pos[1], b.pos[1], p), lerp(a.pos[2], b.pos[2], p)];
    const ta = a.tgt || [0, 0, 0], tb = b.tgt || ta;
    tgt = [lerp(ta[0], tb[0], p), lerp(ta[1], tb[1], p), lerp(ta[2], tb[2], p)];
  } else {
    pos = [0, 0, DIST];
  }
  return { pos, tgt };
}

let curScene = -1;
export async function seek(t) {
  const scenes = TL.scenes;
  let si = 0; while (si < scenes.length - 1 && scenes[si + 1].start <= t) si++;
  const sc = SC[si], lt = t - sc.start;
  if (si !== curScene) {
    SC.forEach((s, i) => { s.layer.style.display = i === si ? 'block' : 'none'; s.group.visible = i === si; });
    curScene = si;
  }
  // 相机：场景之间平滑过渡
  let cm = camAt(sc, lt);
  if (si > 0 && lt < 1.2) { const prev = SC[si - 1], pc = camAt(prev, prev.dur), q = E.inOut(clamp(lt / 1.2)); cm = { pos: cm.pos.map((v, i) => lerp(pc.pos[i], v, q)), tgt: cm.tgt.map((v, i) => lerp(pc.tgt[i], v, q)) }; }
  const drift = [0, 0, 0];
  { const k = lastBefore(IMPACTS, t), x = k >= 0 ? t - IMPACTS[k] : 99; const bump = x < 2.5 ? Math.exp(-x * 2.6) * Math.min(1, x * 12) : 0; cm.pos = [cm.pos[0], cm.pos[1], cm.pos[2] * (1 - 0.045 * bump)]; }
  camera.position.set(cm.pos[0] + drift[0], cm.pos[1] + drift[1], cm.pos[2]);
  camera.lookAt(cm.tgt[0] + drift[0] * 0.5, cm.tgt[1] + drift[1] * 0.5, cm.tgt[2]);

  setSwarm(t);
  swarmMat.uniforms.uTime.value = t;
  const pulse = kickEnv(t);
  swarmMat.uniforms.uPulse.value = pulse;
  finalMat.uniforms.k1.value = 0.9 + 0.55 * pulse;
  finalMat.uniforms.k2.value = 0.9 + 0.35 * pulse;
  // 冲击光环
  const ik = lastBefore(IMPACTS, t);
  const ix = ik >= 0 ? t - IMPACTS[ik] : 99;
  if (ix < 1.6) { const e = EZ_out(clamp(ix / 1.6)); ringMat.uniforms.uR.value = 60 + 1900 * e; ringMat.uniforms.uA.value = Math.pow(1 - clamp(ix / 1.6), 2) * 0.9; shock.visible = true; }
  else shock.visible = false;

  // 场景 3D 对象
  const endF = clamp((sc.dur - lt) / 0.5);
  for (const ob of sc.objs) {
    let a = lt >= ob.t0 ? E.out(clamp((lt - ob.t0) / ob.dur)) : 0;
    if (ob.t1 !== null && lt >= ob.t1) a *= 1 - clamp((lt - ob.t1) / 0.6);
    a *= endF;
    ob.o3.visible = a > 0.002;
    ob.o3.traverse(o => { o.userData.setOpacity && o.userData.setOpacity(a); o.userData.tick && o.userData.tick(t); });
    if (ob.draw) ob.o3.traverse(o => o.userData.draw && o.userData.draw(E.inOut(clamp((lt - ob.t0) / ob.drawDur))));
  }
  for (const fn of sc.ups) fn(lt, sc, t);

  // 光束与闪白（跨场景生效）
  let wa = 0, fl = 0;
  for (const s of SC) {
    for (const w of s.warps) { const gt = s.start + w.t, x = (t - gt) / w.dur; if (x >= 0 && x <= 1) wa = Math.max(wa, w.amt * Math.sin(Math.PI * x)); }
    for (const f of s.flashes) { const gt = s.start + f.t, x = t - gt; if (x >= 0 && x < 0.6) fl = Math.max(fl, f.amt * Math.exp(-x * 7)); }
  }
  warpMat.uniforms.uAmt.value = wa; warpMat.uniforms.uT.value = t;
  finalPass.uniforms.uTime.value = t;
  finalPass.uniforms.uFlash.value = fl;
  finalPass.uniforms.uCA.value = wa * 0.02 + fl * 0.03 + (ix < 0.5 ? (0.5 - ix) * 0.03 : 0);
  finalPass.uniforms.uFade.value = clamp(t / 1.0) * clamp((TL.total - t) / 1.5);

  for (const it of sc.els) animEl(it, lt, sc);
  for (const c of sc.cardEls) animCard(c, lt, sc);
  updateHud(t, si);
  prog.style.width = (W * t / TL.total) + 'px';

  renderAll();
  return performance.now();
}

// ------------------------------------------------------------------ 启动
async function init() {
  const TLJ = await (await fetch('/build/v3_timeline.json')).json();
  const BJ = await (await fetch('/build/v3_beats.json')).json();
  TL = { total: TLJ.total, scenes: TLJ.sections.map(s => ({ ...s, ls: s.cards.map(c => c.start), ld: s.cards.map(c => c.dur), subs: [] })) };
  KICKS = BJ.kicks.sort((a, b) => a[0] - b[0]); IMPACTS = BJ.impacts.sort((a, b) => a - b); UNLOCKS = BJ.unlocks.sort((a, b) => a - b);
  LABELS = TLJ.sections.filter(s => s.label).map(s => ({ label: s.label, start: s.start }));
  const fsStart = TLJ.sections.find(s => s.id === 'set1'), fsEnd = TLJ.sections.find(s => s.id === 'warning');
  HUDWIN = [fsStart.start + 0.5, fsEnd.start + fsEnd.dur - 0.3];
  await document.fonts.load('500 40px SHSerif'); await document.fonts.load('300 40px SHSerif'); await document.fonts.load('700 40px SHSerif');
  await document.fonts.load('200 40px SHS'); await document.fonts.load('300 40px SHS'); await document.fonts.load('900 40px SHS');
  await document.fonts.load('200 40px Inter'); await document.fonts.load('300 20px Mono');
  const { SCENES, PRELOAD } = await import('./visuals.js');
  await Promise.all((PRELOAD || []).map(preloadImage));
  SC = TL.scenes.map((tl, i) => { const s = new SceneCtx(i, tl); (SCENES[tl.id] || (() => {}))(s); s.makeCards(); return s; });
  FORMS = [];
  SC.forEach(s => s.forms.forEach(f => FORMS.push({ ...f, t: s.start + f.t })));
  // 场景开头若没有自己的阵型，先让粒子散成背景尘埃，避免上一场的图形残留
  window.DUST_SCENES = [];
  SC.forEach(s => {
    const first = Math.min(Infinity, ...s.forms.map(f => f.t));
    if (s.idx > 0 && first > 1.5 && s.ls.length) { FORMS.push({ t: s.start + 0.1, make: dust, dur: 1.6, stagger: .3, scatter: 160, swirl: .6, key: 'dust' + s.idx, bright: 1, spin: 0, spinZ: 0, center: [0, 0, 0] }); window.DUST_SCENES.push(s.idx); }
  });
  FORMS.sort((a, b) => a.t - b.t);
  FORMS.sort((a, b) => a.t - b.t);
  window.FORMS_DUMP = FORMS.map(f => ({ t: f.t, dur: f.dur, key: f.key }));
  window.TOTAL = TL.total;
  window.READY = true;
}
window.seek = seek;
window.initDone = init().catch(e => { window.INIT_ERROR = String(e && e.stack || e); console.error(e); });
