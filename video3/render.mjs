// 用 headless Chromium 逐帧渲染 video2 页面，输出 mp4。
// 用法：node render.mjs [--from 秒] [--to 秒] [--workers N] [--out 文件] [--preview 秒,秒] [--noaudio]
import { chromium } from 'playwright-core';
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const args = Object.fromEntries(process.argv.slice(2).reduce((acc, a, i, arr) => { if (a.startsWith('--')) acc.push([a.slice(2), arr[i + 1] && !arr[i + 1].startsWith('--') ? arr[i + 1] : true]); return acc; }, []));
const FPS = 30;
const workers = +(args.workers || 4);
const BUILD = path.join(ROOT, 'build');

// 简易静态服务器
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.otf': 'font/otf', '.ttf': 'font/ttf', '.svg': 'image/svg+xml', '.png': 'image/png' };
const server = http.createServer((req, res) => {
  const p = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]));
  if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'Content-Type': MIME[path.extname(p)] || 'application/octet-stream' });
  fs.createReadStream(p).pipe(res);
});
await new Promise(r => server.listen(0, '127.0.0.1', r));
const PORT = server.address().port;

const browser = await chromium.launch({
  executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
  args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--disable-gpu-sandbox', '--font-render-hinting=none'],
});

async function openPage() {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  page.on('console', m => { if (m.type() === 'error') console.error('[page]', m.text()); });
  page.on('pageerror', e => console.error('[pageerror]', e.message));
  await page.goto(`http://127.0.0.1:${PORT}/video3/index.html`);
  await page.waitForFunction(() => window.READY || window.INIT_ERROR, null, { timeout: 180000 });
  const err = await page.evaluate(() => window.INIT_ERROR);
  if (err) throw new Error(err);
  return page;
}

async function shot(page, t, type = 'jpeg') {
  await page.evaluate(t => window.seek(t), t);
  return page.screenshot({ type, quality: type === 'jpeg' ? 92 : undefined, clip: { x: 0, y: 0, width: 1920, height: 1080 } });
}

if (args.preview) {
  const page = await openPage();
  console.log('DUST_SCENES', JSON.stringify(await page.evaluate(() => window.DUST_SCENES)));
  if (args.dumpforms) fs.writeFileSync(path.join(BUILD, 'forms.json'), JSON.stringify(await page.evaluate(() => window.FORMS_DUMP)));
  fs.mkdirSync(path.join(BUILD, 'v3prev'), { recursive: true });
  for (const s of String(args.preview).split(',')) {
    const t = +s, t0 = Date.now();

    const buf = await shot(page, t, "png");
    const f = path.join(BUILD, 'v3prev', `p${t.toFixed(2).padStart(7, '0')}.png`);
    fs.writeFileSync(f, buf);
    console.log(f, (Date.now() - t0) + 'ms');
  }
  await browser.close(); server.close(); process.exit(0);
}

const total = await (async () => { const p = await openPage(); const v = await p.evaluate(() => window.TOTAL); await p.close(); return v; })();
const from = +(args.from || 0), to = Math.min(total, +(args.to || total));
const f0 = Math.round(from * FPS), f1 = Math.round(to * FPS);
const per = Math.ceil((f1 - f0) / workers);
console.log(`render ${from}-${to}s, frames ${f1 - f0}, workers ${workers}`);
const t0 = Date.now();
let done = 0;
const parts = await Promise.all(Array.from({ length: workers }, async (_, w) => {
  const a = f0 + w * per, b = Math.min(f1, a + per), out = path.join(BUILD, `v3part${w}.mp4`);
  if (a >= b) return null;
  const page = await openPage();
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-pix_fmt', 'yuv420p', '-g', '120', '-threads', '1', out], { stdio: ['pipe', 'inherit', 'inherit'] });
  for (let f = a; f < b; f++) {
    const buf = await shot(page, f / FPS);
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    done++;
    if (w === 0 && (f - a) % 150 === 0) { const el = (Date.now() - t0) / 1000; console.log(`  ${done}/${f1 - f0} frames, ${el.toFixed(0)}s, eta ${(el / done * (f1 - f0 - done)).toFixed(0)}s`); }
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
  await page.close();
  return out;
}));
await browser.close(); server.close();
const list = path.join(BUILD, 'v3parts.txt');
fs.writeFileSync(list, parts.filter(Boolean).map(p => `file '${p}'`).join('\n'));
const out = args.out || path.join(ROOT, 'output', 'v3.mp4');
const ffArgs = ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', list];
if (!args.noaudio) ffArgs.push('-ss', String(from), '-t', String(to - from), '-i', path.join(BUILD, 'v3_music.wav'));
ffArgs.push('-map', '0:v');
if (!args.noaudio) ffArgs.push('-map', '1:a', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000');
ffArgs.push('-c:v', 'copy', '-movflags', '+faststart', '-shortest', out);
await new Promise((res, rej) => { const p = spawn('ffmpeg', ffArgs, { stdio: 'inherit' }); p.on('close', c => c ? rej(new Error('ffmpeg ' + c)) : res()); });
console.log('done', out, ((Date.now() - t0) / 1000).toFixed(0) + 's');
