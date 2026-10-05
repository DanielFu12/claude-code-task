// Render frames with headless Chromium and encode with ffmpeg.
// node render.js <out.mp4> [--from s] [--to s] [--workers n] [--stills t1,t2,...] [--outdir dir]
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const { TL } = require('./timeline.js');

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf('--' + k); return i >= 0 ? args[i + 1] : d; };
const OUT = args[0];
const FPS = TL.FPS;
const from = +opt('from', 0), to = +opt('to', TL.DURATION);
const workers = +opt('workers', 4);
const stills = opt('stills', null);
const url = 'file://' + path.resolve(__dirname, 'index.html');

async function openPage(browser) {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  page.on('pageerror', (e) => console.error('PAGE ERROR', e.message));
  page.on('console', (m) => { if (m.type() === 'error') console.error('CONSOLE', m.text()); });
  await page.goto(url);
  await page.waitForFunction(() => window.READY === true, null, { timeout: 120000 });
  return page;
}
const grab = (page, t, q) => page.evaluate(([t, q]) => { window.renderFrame(t); return document.getElementById('c').toDataURL('image/jpeg', q); }, [t, q]);

(async () => {
  const browser = await chromium.launch({ args: ['--disable-gpu-vsync', '--disable-frame-rate-limit'] });
  if (stills) {
    const page = await openPage(browser);
    const dir = opt('outdir', '.');
    for (const s of stills.split(',')) {
      const d = await grab(page, +s, 0.92);
      fs.writeFileSync(path.join(dir, `still_${(+s).toFixed(2)}.jpg`), Buffer.from(d.split(',')[1], 'base64'));
    }
    await browser.close();
    return;
  }
  const f0 = Math.round(from * FPS), f1 = Math.round(to * FPS);
  const n = f1 - f0, per = Math.ceil(n / workers);
  const t0 = Date.now();
  let done = 0;
  const segs = [];
  await Promise.all(Array.from({ length: workers }, async (_, w) => {
    const a = f0 + w * per, b = Math.min(f1, a + per);
    if (a >= b) return;
    const seg = `${OUT}.part${w}.mp4`; segs[w] = seg;
    const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
      '-c:v', 'libx264', '-preset', 'slow', '-crf', opt('crf', '19'), '-pix_fmt', 'yuv420p', '-tune', 'film', '-x264-params', 'keyint=60:min-keyint=30', seg], { stdio: ['pipe', 'inherit', 'inherit'] });
    const page = await openPage(browser);
    for (let f = a; f < b; f++) {
      const d = await grab(page, f / FPS, 0.94);
      const buf = Buffer.from(d.split(',')[1], 'base64');
      if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
      done++;
      if (done % 300 === 0) { const el = (Date.now() - t0) / 1000; console.log(`${done}/${n} frames  ${(done / el).toFixed(1)} fps  eta ${((n - done) / (done / el) / 60).toFixed(1)} min`); }
    }
    ff.stdin.end();
    await new Promise((r) => ff.on('close', r));
    await page.close();
  }));
  await browser.close();
  const list = `${OUT}.list.txt`;
  fs.writeFileSync(list, segs.filter(Boolean).map((s) => `file '${path.resolve(s)}'`).join('\n'));
  await new Promise((r) => spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', OUT], { stdio: 'inherit' }).on('close', r));
  segs.filter(Boolean).forEach((s) => fs.unlinkSync(s)); fs.unlinkSync(list);
  console.log('video done', OUT, ((Date.now() - t0) / 60000).toFixed(1), 'min');
})();
